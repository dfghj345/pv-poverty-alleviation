<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue';
import AMapLoader from '@amap/amap-jsapi-loader';
import gcoord from 'gcoord';

import { buildAggregateKey, type PanelDataMapAggregate } from '@/composables/useProjectMap';
import type { PowerStationFeature } from '@/api/types';

const props = withDefaults(defineProps<{
  points: { type: 'FeatureCollection'; features: PowerStationFeature[] };
  aggregates?: PanelDataMapAggregate[];
  selectedKey?: string | null;
  loading?: boolean;
  errorMessage?: string | null;
}>(), {
  aggregates: () => [],
  selectedKey: null,
  loading: false,
  errorMessage: null,
});

const emit = defineEmits<{
  (e: 'point-click', feature: PowerStationFeature): void;
  (e: 'aggregate-click', aggregate: PanelDataMapAggregate): void;
  (e: 'location-picked', payload: { longitude: number; latitude: number }): void;
  (e: 'location-cleared'): void;
}>();

const mapContainer = ref<HTMLElement | null>(null);
const map = shallowRef<any>(null);
const internalMapError = ref<string | null>(null);
const mapNotice = ref<string | null>(null);
const selectedPoint = ref<{ longitude: number; latitude: number } | null>(null);

const hasAggregateData = computed(() => props.aggregates.length > 0);
const hasMapPoints = computed(() => props.points.features.length > 0);
const visibleAggregates = computed(() =>
  [...props.aggregates].sort((left, right) => right.value - left.value || right.count - left.count),
);
const effectiveError = computed(() => props.errorMessage ?? internalMapError.value);

let AMapInstance: any = null;
let currentMarkers: any[] = [];
let activeStationMarker: any = null;
let infoWindow: any = null;
let pickedMarker: any = null;
let mapClickHandler: ((event: any) => void) | null = null;

function markerStyleByCapacity(capacity: number): { radius: number; color: string } {
  if (capacity >= 100) {
    return { radius: 12, color: '#f59e0b' };
  }
  if (capacity >= 50) {
    return { radius: 9, color: '#10b981' };
  }
  return { radius: 6, color: '#3b82f6' };
}

function applyMarkerNormalStyle(marker: any): void {
  const feature: PowerStationFeature | undefined = marker?.getExtData?.();
  const capacity = feature?.properties?.installed_capacity ?? 0;
  const style = markerStyleByCapacity(capacity);

  marker.setOptions({
    radius: style.radius,
    fillColor: style.color,
    strokeColor: '#ffffff',
    strokeWeight: 1.5,
    fillOpacity: 0.88,
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
  const { site_id, installed_capacity, province, city, built_year, area_sqm } = feature.properties;

  const contentHTML = `
    <div style="min-width:220px;background:#0f172acc;border:1px solid #334155;padding:12px;border-radius:12px;color:#e2e8f0;backdrop-filter: blur(6px);">
      <div style="font-weight:700;margin-bottom:6px;">${site_id}</div>
      <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">${province ?? ''} ${city ?? ''}</div>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;">
        <span>年份</span>
        <span>${built_year ?? '-'}</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;">
        <span>记录数</span>
        <span>${area_sqm ?? 0}</span>
      </div>
      <div style="margin-top:8px;font-size:12px;color:#94a3b8;">光伏装机量</div>
      <div style="font-size:20px;font-weight:700;color:#34d399;">${installed_capacity} <span style="font-size:12px;color:#94a3b8;">万千瓦</span></div>
    </div>
  `;

  if (!infoWindow) {
    infoWindow = new AMapInstance.InfoWindow({
      isCustom: true,
      autoMove: true,
      offset: new AMapInstance.Pixel(0, -20),
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
  if (!AMapInstance || !map.value) {
    return;
  }

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

  const [longitude, latitude] = gcoord.transform(pointGcj02, gcoord.GCJ02, gcoord.WGS84) as [number, number];
  selectedPoint.value = { longitude, latitude };
  emit('location-picked', { longitude, latitude });
}

function markerMatchesAggregate(marker: any, aggregate: PanelDataMapAggregate): boolean {
  const feature: PowerStationFeature | undefined = marker?.getExtData?.();
  return (
    feature?.properties?.province === aggregate.province &&
    feature?.properties?.city === aggregate.city &&
    feature?.properties?.built_year === aggregate.year
  );
}

function focusAggregateOnMap(aggregate: PanelDataMapAggregate): void {
  if (!map.value || !AMapInstance) {
    return;
  }

  const marker = currentMarkers.find((item) => markerMatchesAggregate(item, aggregate));
  if (!marker) {
    return;
  }

  if (activeStationMarker && activeStationMarker !== marker) {
    applyMarkerNormalStyle(activeStationMarker);
  }

  activeStationMarker = marker;
  applyMarkerActiveStyle(marker);

  const feature: PowerStationFeature = marker.getExtData();
  const center = marker.getCenter();
  const position: [number, number] = [center.lng, center.lat];

  showPopup(feature, position);
  map.value.setCenter(position);
  map.value.setZoom(Math.max(map.value.getZoom(), 6));
}

function renderPoints(features: PowerStationFeature[]): void {
  if (!map.value || !AMapInstance) {
    return;
  }

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
      fillOpacity: 0.88,
      cursor: 'pointer',
      extData: feature,
    });

    marker.on('click', (event: any) => {
      const clickedFeature: PowerStationFeature = event.target.getExtData();

      if (activeStationMarker && activeStationMarker !== marker) {
        applyMarkerNormalStyle(activeStationMarker);
      }

      activeStationMarker = marker;
      applyMarkerActiveStyle(marker);
      showPopup(clickedFeature, gcj02Coord);
      emit('point-click', clickedFeature);
    });

    currentMarkers.push(marker);
  });

  if (currentMarkers.length > 0) {
    map.value.add(currentMarkers);
    map.value.setFitView(currentMarkers, false, [80, 80, 80, 80]);
  }
}

function handleAggregateClick(item: PanelDataMapAggregate): void {
  focusAggregateOnMap(item);
  emit('aggregate-click', item);
}

onMounted(async () => {
  const amapKey = (import.meta.env.VITE_APP_AMAP_KEY as string | undefined)?.trim();
  const amapSecurityCode = (import.meta.env.VITE_APP_AMAP_SECURITY_CODE as string | undefined)?.trim();

  if (!amapKey || !amapSecurityCode) {
    mapNotice.value = '未配置高德地图密钥，当前展示省市聚合列表。';
    return;
  }

  (window as any)._AMapSecurityConfig = { securityJsCode: amapSecurityCode };

  try {
    AMapInstance = await AMapLoader.load({
      key: amapKey,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.CircleMarker', 'AMap.InfoWindow'],
    });

    if (!mapContainer.value) {
      return;
    }

    map.value = new AMapInstance.Map(mapContainer.value, {
      viewMode: '3D',
      pitch: 30,
      zoom: 4.5,
      center: [105.0, 35.0],
      mapStyle: 'amap://styles/darkblue',
    });

    map.value.on('complete', () => {
      renderPoints(props.points.features);
    });

    mapClickHandler = (event: any) => {
      const lng = Number(event?.lnglat?.getLng?.());
      const lat = Number(event?.lnglat?.getLat?.());
      if (!Number.isFinite(lng) || !Number.isFinite(lat)) {
        return;
      }
      setPickedPoint([lng, lat]);
    };

    map.value.on('click', mapClickHandler);
  } catch (error) {
    console.error('Map initialization failed.', error);
    internalMapError.value = '地图初始化失败，已切换为聚合列表展示。';
  }
});

watch(
  () => props.points,
  (nextData) => {
    renderPoints(nextData.features);
  },
  { deep: true },
);

watch(
  () => props.selectedKey,
  (nextKey) => {
    if (!nextKey) {
      if (activeStationMarker) {
        applyMarkerNormalStyle(activeStationMarker);
      }
      activeStationMarker = null;
      return;
    }

    const nextAggregate = props.aggregates.find((item) => buildAggregateKey(item) === nextKey);
    if (nextAggregate) {
      focusAggregateOnMap(nextAggregate);
    }
  },
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
  <div class="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
    <div class="relative h-[520px] overflow-hidden rounded-2xl border border-slate-200 bg-slate-950/95 shadow-inner">
      <div v-if="!mapNotice" ref="mapContainer" class="h-full w-full"></div>
      <div v-else class="flex h-full items-center justify-center px-8 text-center text-sm text-slate-200">
        {{ mapNotice }}
      </div>

      <div
        v-if="loading"
        class="absolute inset-0 flex items-center justify-center bg-slate-950/70 text-sm text-slate-100"
      >
        正在加载地图数据...
      </div>

      <div
        v-if="effectiveError"
        class="absolute inset-0 flex items-center justify-center bg-slate-950/80 px-6 text-center text-sm text-slate-100"
      >
        {{ effectiveError }}
      </div>

      <div
        v-else-if="!hasMapPoints && hasAggregateData"
        class="absolute left-3 top-3 rounded-full border border-slate-700 bg-slate-900/85 px-3 py-1 text-xs text-slate-100 shadow-lg"
      >
        当前未匹配到城市坐标，已切换为省市聚合视图
      </div>

      <div
        v-if="selectedPoint"
        class="absolute bottom-3 left-3 rounded-xl border border-slate-700 bg-slate-900/85 px-3 py-2 text-xs text-slate-100 shadow-lg"
      >
        <div>选点经纬度：{{ selectedPoint.latitude.toFixed(6) }}, {{ selectedPoint.longitude.toFixed(6) }}</div>
        <button class="mt-1 text-rose-300 hover:text-rose-200" @click.stop="clearPickedPoint">
          清除选点
        </button>
      </div>
    </div>

    <aside class="flex h-[520px] flex-col rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-dark-card">
      <div class="mb-4 flex items-start justify-between gap-3">
        <div>
          <h3 class="text-lg font-semibold text-slate-900 dark:text-dark-text">地图聚合数据</h3>
          <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">
            已定位 {{ points.features.length }} / {{ aggregates.length }} 个省市点位
          </p>
        </div>
        <span class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
          panel_data
        </span>
      </div>

      <div
        v-if="!loading && !hasAggregateData"
        class="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-200 px-4 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60"
      >
        当前筛选条件下暂无地图数据
      </div>

      <div v-else class="flex-1 overflow-y-auto pr-1">
        <div class="space-y-3">
          <button
            v-for="item in visibleAggregates"
            :key="buildAggregateKey(item)"
            type="button"
            class="block w-full rounded-2xl border px-4 py-3 text-left transition hover:-translate-y-0.5 hover:shadow-sm"
            :class="
              selectedKey === buildAggregateKey(item)
                ? 'border-emerald-300 bg-emerald-50 shadow-sm dark:border-emerald-400/40 dark:bg-emerald-500/10'
                : 'border-slate-100 bg-slate-50 hover:border-slate-200 dark:border-slate-800 dark:bg-slate-900/40'
            "
            @click="handleAggregateClick(item)"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="font-medium text-slate-900 dark:text-dark-text">{{ item.city || '未知城市' }}</p>
                <p class="text-xs text-slate-500 dark:text-dark-text/60">{{ item.province }} · {{ item.year }}</p>
              </div>
              <span
                class="rounded-full px-2.5 py-1 text-xs font-medium"
                :class="
                  item.hasCoordinate
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300'
                    : 'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-300'
                "
              >
                {{ item.hasCoordinate ? '已定位' : '聚合' }}
              </span>
            </div>
            <div class="mt-3 flex items-center justify-between text-sm">
              <span class="text-slate-500 dark:text-dark-text/60">光伏装机量</span>
              <span class="font-semibold text-slate-900 dark:text-dark-text">{{ item.value.toFixed(2) }} 万千瓦</span>
            </div>
            <div class="mt-1 flex items-center justify-between text-sm">
              <span class="text-slate-500 dark:text-dark-text/60">记录数</span>
              <span class="font-medium text-slate-700 dark:text-dark-text/80">{{ item.count }}</span>
            </div>
          </button>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
:deep(.amap-logo),
:deep(.amap-copyright) {
  display: none !important;
}
</style>
