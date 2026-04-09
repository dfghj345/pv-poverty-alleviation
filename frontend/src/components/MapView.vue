<script setup lang="ts">
import { onMounted, onUnmounted, ref, shallowRef, watch } from 'vue';
import AMapLoader from '@amap/amap-jsapi-loader';
import gcoord from 'gcoord';
import type { PowerStationFeature } from '@/api/types';

const props = defineProps<{
  points: { type: 'FeatureCollection'; features: PowerStationFeature[] };
}>();

const emit = defineEmits<{
  (e: 'point-click', feature: PowerStationFeature): void;
  (e: 'location-picked', payload: { longitude: number; latitude: number }): void;
  (e: 'location-cleared'): void;
}>();

const mapContainer = ref<HTMLElement | null>(null);
const map = shallowRef<any>(null);

const mapError = ref<string | null>(null);
const selectedPoint = ref<{ longitude: number; latitude: number } | null>(null);

let AMapInstance: any = null;
let currentMarkers: any[] = [];
let activeStationMarker: any = null;
let infoWindow: any = null;
let pickedMarker: any = null;
let mapClickHandler: ((e: any) => void) | null = null;

function markerStyleByCapacity(capacity: number): { radius: number; color: string } {
  if (capacity >= 500) {
    return { radius: 12, color: '#f59e0b' };
  }
  if (capacity >= 200) {
    return { radius: 9, color: '#10b981' };
  }
  return { radius: 6, color: '#3b82f6' };
}

function applyMarkerNormalStyle(marker: any): void {
  const feature: PowerStationFeature | undefined = marker?.getExtData?.();
  const cap = feature?.properties?.installed_capacity ?? 0;
  const style = markerStyleByCapacity(cap);
  marker.setOptions({
    radius: style.radius,
    fillColor: style.color,
    strokeColor: '#ffffff',
    strokeWeight: 1.5,
    fillOpacity: 0.85,
  });
}

function applyMarkerActiveStyle(marker: any): void {
  marker.setOptions({
    strokeColor: '#f43f5e',
    strokeWeight: 3,
    fillOpacity: 1,
  });
}

function showPopup(feature: PowerStationFeature, positionGcj02: [number, number]): void {
  const { site_id, installed_capacity } = feature.properties;

  const contentHTML = `
    <div style="min-width:190px;background:#0f172acc;border:1px solid #334155;padding:12px;border-radius:10px;color:#e2e8f0;backdrop-filter: blur(6px);">
      <div style="font-weight:700;margin-bottom:6px;">${site_id}</div>
      <div style="font-size:12px;color:#94a3b8;">规划容量</div>
      <div style="font-size:20px;font-weight:700;color:#34d399;">${installed_capacity} <span style="font-size:12px;color:#94a3b8;">kW</span></div>
    </div>
  `;

  if (!infoWindow) {
    infoWindow = new AMapInstance.InfoWindow({
      isCustom: true,
      autoMove: true,
      offset: new AMapInstance.Pixel(0, -20)
    });
  }

  infoWindow.setContent(contentHTML);
  infoWindow.open(map.value, positionGcj02);
}

function clearPickedPoint(): void {
  selectedPoint.value = null;
  if (pickedMarker && map.value) {
    map.value.remove(pickedMarker);
  }
  pickedMarker = null;
  emit('location-cleared');
}

function setPickedPoint(pointGcj02: [number, number]): void {
  if (!AMapInstance || !map.value) return;

  if (pickedMarker) {
    map.value.remove(pickedMarker);
    pickedMarker = null;
  }

  pickedMarker = new AMapInstance.CircleMarker({
    center: pointGcj02,
    radius: 8,
    fillColor: '#ef4444',
    fillOpacity: 0.95,
    strokeColor: '#ffffff',
    strokeWeight: 2,
    cursor: 'pointer',
  });

  map.value.add(pickedMarker);

  const [lngWgs, latWgs] = gcoord.transform(pointGcj02, gcoord.GCJ02, gcoord.WGS84) as [number, number];
  selectedPoint.value = { longitude: lngWgs, latitude: latWgs };
  emit('location-picked', { longitude: lngWgs, latitude: latWgs });
}

const renderPoints = (features: PowerStationFeature[]) => {
  if (!map.value || !AMapInstance) return;

  if (currentMarkers.length > 0) {
    map.value.remove(currentMarkers);
    currentMarkers = [];
    activeStationMarker = null;
  }

  features.forEach((feature) => {
    const { coordinates } = feature.geometry;
    const gcj02Coord = gcoord.transform(coordinates, gcoord.WGS84, gcoord.GCJ02) as [number, number];
    const style = markerStyleByCapacity(feature.properties.installed_capacity ?? 0);

    const marker = new AMapInstance.CircleMarker({
      center: gcj02Coord,
      radius: style.radius,
      fillColor: style.color,
      strokeColor: '#ffffff',
      strokeWeight: 1.5,
      fillOpacity: 0.85,
      cursor: 'pointer',
      extData: feature,
    });

    marker.on('click', (e: any) => {
      const feat: PowerStationFeature = e.target.getExtData();
      if (activeStationMarker && activeStationMarker !== marker) {
        applyMarkerNormalStyle(activeStationMarker);
      }
      activeStationMarker = marker;
      applyMarkerActiveStyle(marker);
      showPopup(feat, gcj02Coord);
      emit('point-click', feat);
    });

    currentMarkers.push(marker);
  });

  map.value.add(currentMarkers);
};

onMounted(async () => {
  const amapKey = (import.meta.env.VITE_APP_AMAP_KEY as string | undefined)?.trim();
  const amapSecurityCode = (import.meta.env.VITE_APP_AMAP_SECURITY_CODE as string | undefined)?.trim();

  if (!amapKey || !amapSecurityCode) {
    mapError.value = '缺少高德地图环境变量：VITE_APP_AMAP_KEY / VITE_APP_AMAP_SECURITY_CODE';
    return;
  }

  (window as any)._AMapSecurityConfig = { securityJsCode: amapSecurityCode };

  try {
    AMapInstance = await AMapLoader.load({
      key: amapKey,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.CircleMarker', 'AMap.InfoWindow']
    });

    if (!mapContainer.value) return;

    map.value = new AMapInstance.Map(mapContainer.value, {
      viewMode: '3D',
      pitch: 35,
      zoom: 4.5,
      center: [105.0, 35.0],
      mapStyle: 'amap://styles/darkblue',
    });

    map.value.on('complete', () => {
      renderPoints(props.points.features);
    });

    mapClickHandler = (e: any) => {
      const lng = Number(e?.lnglat?.getLng?.());
      const lat = Number(e?.lnglat?.getLat?.());
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
        return;
      }
      setPickedPoint([lng, lat]);
    };
    map.value.on('click', mapClickHandler);
  } catch (e) {
    console.error('高德地图加载失败', e);
    mapError.value = '地图初始化失败，请检查 key、网络或浏览器控制台日志';
  }
});

watch(
  () => props.points,
  (newData) => {
    renderPoints(newData.features);
  },
  { deep: true }
);

onUnmounted(() => {
  if (map.value && mapClickHandler) {
    map.value.off('click', mapClickHandler);
  }
  if (map.value) {
    map.value.destroy();
  }
});
</script>

<template>
  <div class="relative w-full h-[500px] rounded-lg overflow-hidden z-0">
    <div ref="mapContainer" class="w-full h-full"></div>

    <div
      v-if="selectedPoint"
      class="absolute left-3 bottom-3 px-3 py-2 rounded-lg bg-slate-900/85 text-slate-100 text-xs border border-slate-700 shadow-lg"
    >
      <div>选点经纬度：{{ selectedPoint.latitude.toFixed(6) }}, {{ selectedPoint.longitude.toFixed(6) }}</div>
      <button
        class="mt-1 text-rose-300 hover:text-rose-200"
        @click.stop="clearPickedPoint"
      >
        清除选点
      </button>
    </div>

    <div
      v-if="mapError"
      class="absolute inset-0 bg-slate-900/80 text-slate-100 flex items-center justify-center p-6 text-sm"
    >
      {{ mapError }}
    </div>
  </div>
</template>

<style scoped>
:deep(.amap-logo),
:deep(.amap-copyright) {
  display: none !important;
}
</style>
