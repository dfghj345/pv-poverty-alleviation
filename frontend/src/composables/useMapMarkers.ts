import { shallowRef, onMounted, onUnmounted, watch } from 'vue';
import AMapLoader from '@amap/amap-jsapi-loader';
import type { PowerStationFeature } from '@/api/types';

declare global {
  interface Window {
    _AMapSecurityConfig?: { securityJsCode: string };
  }
}

export function useMapMarkers(
  getContainer: () => HTMLElement | null,
  getFeatures: () => PowerStationFeature[],
  onPointClick: (feature: PowerStationFeature) => void
) {
  const map = shallowRef<Record<string, unknown> | null>(null);
  let AMap: Record<string, unknown> | null = null;
  const markers: Record<string, unknown>[] = [];
  let infoWindow: Record<string, unknown> | null = null;

  function renderPoints(features: PowerStationFeature[]): void {
    if (!map.value || !AMap) return;
    const m = map.value as { remove: (a: unknown[]) => void; add: (a: unknown[]) => void };
    if (markers.length > 0) {
      m.remove(markers);
      markers.length = 0;
    }
    features.forEach((feature) => {
      const { coordinates } = feature.geometry;
      const { installed_capacity } = feature.properties;
      let radius = 6;
      let fillColor = '#3b82f6';
      if (installed_capacity >= 500) {
        radius = 12;
        fillColor = '#f59e0b';
      } else if (installed_capacity >= 200) {
        radius = 9;
        fillColor = '#10b981';
      }
      const CircleMarker = AMap!.CircleMarker as new (o: Record<string, unknown>) => Record<string, unknown>;
      const marker = new CircleMarker({
        center: coordinates,
        radius,
        fillColor,
        strokeColor: '#ffffff',
        strokeWeight: 1.5,
        fillOpacity: 0.85,
        cursor: 'pointer',
        extData: feature
      });
      (marker as { on(ev: string, fn: (e: { target: { getExtData: () => PowerStationFeature } }) => void): void }).on('click', (e: { target: { getExtData: () => PowerStationFeature } }) => {
        const feat = e.target.getExtData();
        showPopup(feat, coordinates);
        onPointClick(feat);
      });
      markers.push(marker);
    });
    m.add(markers);
  }

  function showPopup(feature: PowerStationFeature, coordinates: [number, number]): void {
    const { site_id, installed_capacity } = feature.properties;
    const contentHTML = `
    <div class="bg-slate-900/90 backdrop-blur-xl border border-slate-700/50 p-4 rounded-xl shadow-2xl shadow-black/50 text-slate-100 min-w-[180px]">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-1.5 h-4 bg-pv-gold rounded-full"></div>
        <h3 class="font-bold text-sm tracking-wide">${site_id}</h3>
      </div>
      <div class="flex justify-between items-end border-t border-slate-700/50 pt-2 mt-2">
        <span class="text-xs text-slate-400">规划容量</span>
        <span class="text-emerald-400 font-mono font-bold text-lg">${installed_capacity} <span class="text-xs text-slate-500">kW</span></span>
      </div>
    </div>
  `;
    if (!infoWindow && AMap) {
      const Pixel = AMap.Pixel as new (x: number, y: number) => Record<string, unknown>;
      infoWindow = new (AMap.InfoWindow as new (o: Record<string, unknown>) => Record<string, unknown>)({
        isCustom: true,
        autoMove: true,
        offset: new Pixel(0, -20)
      });
    }
    if (infoWindow && map.value) {
      (infoWindow as { setContent: (s: string) => void }).setContent(contentHTML);
      (infoWindow as { open: (m: unknown, pos: [number, number]) => void }).open(map.value, coordinates);
    }
  }

  onMounted(async () => {
    window._AMapSecurityConfig = { securityJsCode: import.meta.env.VITE_APP_AMAP_SECURITY_CODE ?? '' };
    try {
      AMap = (await AMapLoader.load({
        key: import.meta.env.VITE_APP_AMAP_KEY ?? '',
        version: '2.0',
        plugins: ['AMap.Scale', 'AMap.CircleMarker', 'AMap.InfoWindow']
      })) as Record<string, unknown>;
      const el = getContainer();
      if (!el) return;
      const MapCtor = AMap.Map as new (el: HTMLElement, o: Record<string, unknown>) => Record<string, unknown>;
      map.value = new MapCtor(el, {
        viewMode: '3D',
        pitch: 45,
        zoom: 4.5,
        center: [105.0, 35.0],
        mapStyle: 'amap://styles/darkblue'
      });
      (map.value as { on: (ev: string, fn: () => void) => void }).on('complete', () => renderPoints(getFeatures()));
    } catch (e) {
      console.error('高德地图加载失败:', e);
    }
  });

  watch(getFeatures, (features) => renderPoints(features), { deep: true });

  onUnmounted(() => {
    if (map.value && typeof (map.value as { destroy: () => void }).destroy === 'function') {
      (map.value as { destroy: () => void }).destroy();
    }
  });

  return { map };
}
