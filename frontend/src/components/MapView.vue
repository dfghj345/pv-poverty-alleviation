<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue';
import AMapLoader from '@amap/amap-jsapi-loader';
import gcoord from 'gcoord';

import { buildAggregateKey, type MapViewport, type PanelDataMapAggregate } from '@/composables/useProjectMap';
import { useMobilePager } from '@/composables/useMobilePager';

const props = withDefaults(defineProps<{
  items?: PanelDataMapAggregate[];
  points?: any;
  selectedKey?: string | null;
  viewport?: MapViewport | null;
  loading?: boolean;
  errorMessage?: string | null;
}>(), {
  items: () => [],
  points: null,
  selectedKey: null,
  viewport: null,
  loading: false,
  errorMessage: null,
});

const emit = defineEmits<{
  (e: 'aggregate-click', aggregate: PanelDataMapAggregate): void;
  (e: 'point-click', payload: unknown): void;
  (e: 'location-picked', payload: { longitude: number; latitude: number }): void;
  (e: 'location-cleared'): void;
}>();

const mapContainer = ref<HTMLElement | null>(null);
const map = shallowRef<any>(null);
const internalMapError = ref<string | null>(null);
const mapNotice = ref<string | null>(null);
const showMobileDetails = ref(false);

const hasMapPoints = computed(() => props.items.length > 0);
const visibleItems = computed(() =>
  [...props.items].sort((left, right) => right.value - left.value || right.count - left.count || right.year - left.year),
);
const effectiveError = computed(() => props.errorMessage ?? internalMapError.value);
const {
  page: mobilePage,
  totalPages: mobileTotalPages,
  pagedItems: mobileItems,
  canPrev: canPrevMobilePage,
  canNext: canNextMobilePage,
  next: nextMobilePage,
  prev: prevMobilePage,
  onTouchStart,
  onTouchEnd,
} = useMobilePager(visibleItems, 1);

let AMapInstance: any = null;
let currentMarkers: any[] = [];
let activeMarker: any = null;
let infoWindow: any = null;
const markerIndex = new Map<string, any>();
let mapResizeObserver: ResizeObserver | null = null;

function markerStyleByValue(value: number): { radius: number; color: string } {
  if (value >= 100) {
    return { radius: 12, color: '#f59e0b' };
  }
  if (value >= 50) {
    return { radius: 9, color: '#10b981' };
  }
  return { radius: 6, color: '#3b82f6' };
}

function applyMarkerNormalStyle(marker: any): void {
  const item: PanelDataMapAggregate | undefined = marker?.getExtData?.();
  const style = markerStyleByValue(item?.value ?? 0);

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

function showPopup(item: PanelDataMapAggregate, positionGcj02: [number, number]): void {
  const contentHTML = `
    <div style="width:min(220px,calc(100vw - 72px));max-width:220px;background:#0f172acc;border:1px solid #334155;padding:12px;border-radius:12px;color:#e2e8f0;backdrop-filter: blur(6px);">
      <div style="font-weight:700;margin-bottom:6px;">${item.city}</div>
      <div style="font-size:12px;color:#94a3b8;margin-bottom:4px;">${item.province}</div>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;">
        <span>年份</span>
        <span>${item.year}</span>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;">
        <span>记录数</span>
        <span>${item.count}</span>
      </div>
      <div style="margin-top:8px;font-size:12px;color:#94a3b8;">装机容量</div>
      <div style="font-size:20px;font-weight:700;color:#34d399;">${item.value.toFixed(2)} <span style="font-size:12px;color:#94a3b8;">万千瓦</span></div>
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

function clearMarkers(): void {
  if (map.value && currentMarkers.length > 0) {
    map.value.remove(currentMarkers);
  }
  currentMarkers = [];
  markerIndex.clear();
  activeMarker = null;
}

function applyMapViewport(viewport: MapViewport | null | undefined): void {
  if (!map.value || !viewport) {
    return;
  }

  const centerGcj02 = gcoord.transform(viewport.center, gcoord.WGS84, gcoord.GCJ02) as [number, number];
  map.value.setZoomAndCenter(viewport.zoom, centerGcj02);
}

function syncMapSize(): void {
  if (!map.value) {
    return;
  }

  requestAnimationFrame(() => {
    map.value?.resize?.();
  });
}

function focusAggregateOnMap(item: PanelDataMapAggregate, recenter: boolean): void {
  if (!map.value || !AMapInstance) {
    return;
  }

  const marker = markerIndex.get(buildAggregateKey(item));
  if (!marker) {
    return;
  }

  if (activeMarker && activeMarker !== marker) {
    applyMarkerNormalStyle(activeMarker);
  }

  activeMarker = marker;
  applyMarkerActiveStyle(marker);

  const center = marker.getCenter();
  const position: [number, number] = [center.lng, center.lat];
  showPopup(item, position);

  if (recenter) {
    map.value.setZoomAndCenter(9.5, position);
  }
}

function renderMarkers(items: PanelDataMapAggregate[]): void {
  if (!map.value || !AMapInstance) {
    return;
  }

  clearMarkers();

  currentMarkers = items.map((item) => {
    const centerGcj02 = gcoord.transform([item.longitude, item.latitude], gcoord.WGS84, gcoord.GCJ02) as [number, number];
    const style = markerStyleByValue(item.value);
    const marker = new AMapInstance.CircleMarker({
      center: centerGcj02,
      radius: style.radius,
      fillColor: style.color,
      strokeColor: '#ffffff',
      strokeWeight: 1.5,
      fillOpacity: 0.88,
      cursor: 'pointer',
      extData: item,
    });

    marker.on('click', () => {
      focusAggregateOnMap(item, true);
      emit('aggregate-click', item);
    });

    markerIndex.set(buildAggregateKey(item), marker);
    return marker;
  });

  if (currentMarkers.length > 0) {
    map.value.add(currentMarkers);
  }

  applyMapViewport(props.viewport);

  if (props.selectedKey) {
    const selectedItem = items.find((item) => buildAggregateKey(item) === props.selectedKey);
    if (selectedItem) {
      focusAggregateOnMap(selectedItem, false);
    }
  }
}

function handleAggregateClick(item: PanelDataMapAggregate): void {
  focusAggregateOnMap(item, true);
  emit('aggregate-click', item);
}

onMounted(async () => {
  const amapKey = (import.meta.env.VITE_APP_AMAP_KEY as string | undefined)?.trim();
  const amapSecurityCode = (import.meta.env.VITE_APP_AMAP_SECURITY_CODE as string | undefined)?.trim();

  if (!amapKey || !amapSecurityCode) {
    mapNotice.value = '未配置高德地图密钥，当前仅展示右侧聚合列表。';
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
      pitch: 20,
      zoom: 4.5,
      center: [105.0, 35.0],
      mapStyle: 'amap://styles/darkblue',
    });

    map.value.on('complete', () => {
      syncMapSize();
      renderMarkers(props.items);
    });

    mapResizeObserver = new ResizeObserver(() => {
      syncMapSize();
    });
    mapResizeObserver.observe(mapContainer.value);
  } catch (error) {
    console.error('Map initialization failed.', error);
    internalMapError.value = '地图初始化失败，已切换为聚合列表展示。';
  }
});

watch(
  () => props.items,
  (nextItems) => {
    renderMarkers(nextItems);
  },
  { deep: true },
);

watch(
  () => props.viewport,
  (nextViewport) => {
    applyMapViewport(nextViewport);
  },
  { deep: true },
);

watch(
  () => props.selectedKey,
  (nextKey) => {
    if (!nextKey) {
      if (activeMarker) {
        applyMarkerNormalStyle(activeMarker);
      }
      activeMarker = null;
      return;
    }

    const selectedItem = props.items.find((item) => buildAggregateKey(item) === nextKey);
    if (selectedItem) {
      focusAggregateOnMap(selectedItem, false);
    }
  },
);

onUnmounted(() => {
  clearMarkers();
  infoWindow?.close?.();
  mapResizeObserver?.disconnect();
  if (map.value) {
    map.value.destroy();
  }
});
</script>

<template>
  <div class="space-y-4 lg:grid lg:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.85fr)] lg:items-start lg:gap-8 lg:space-y-0">
    <div class="relative h-[45vh] min-h-[320px] max-h-[520px] overflow-hidden rounded-[26px] border border-black/[0.05] bg-slate-950/95 shadow-[0_12px_30px_rgba(15,23,42,0.08)] sm:min-h-[360px] lg:h-[520px] lg:max-h-none">
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
        v-else-if="effectiveError"
        class="absolute inset-0 flex items-center justify-center bg-slate-950/80 px-6 text-center text-sm text-slate-100"
      >
        {{ effectiveError }}
      </div>

      <div
        v-else-if="!hasMapPoints"
        class="absolute inset-0 flex items-center justify-center bg-slate-950/70 px-6 text-center text-sm text-slate-100"
      >
        暂无可展示的地图坐标数据
      </div>
    </div>

    <div class="lg:hidden">
      <button
        type="button"
        class="apple-pill-primary w-full"
        :disabled="loading || !hasMapPoints"
        @click="showMobileDetails = true"
      >
        查看数据明细
      </button>
    </div>

    <aside class="apple-card hidden min-h-0 flex-col p-4 sm:p-5 lg:flex lg:h-[520px] lg:max-h-none lg:p-6">
      <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 class="text-lg font-semibold text-slate-900 dark:text-dark-text">地图聚合数据</h3>
          <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">
            当前展示 {{ items.length }} 个市级聚合点
          </p>
        </div>
        <span class="inline-flex w-fit rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
          panel_data
        </span>
      </div>

      <div
        v-if="!loading && !hasMapPoints"
        class="flex h-full items-center justify-center rounded-xl border border-dashed border-slate-200 px-4 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60"
      >
        暂无可展示的地图坐标数据
      </div>

      <div v-else class="touch-scroll flex-1 overflow-y-auto pr-1">
        <div class="space-y-3">
          <button
            v-for="item in visibleItems"
            :key="buildAggregateKey(item)"
            type="button"
            class="block w-full rounded-[24px] border px-4 py-4 text-left transition hover:-translate-y-0.5 hover:shadow-sm"
            :class="
              selectedKey === buildAggregateKey(item)
                ? 'border-emerald-300 bg-emerald-50 shadow-sm dark:border-emerald-400/40 dark:bg-emerald-500/10'
                : 'border-black/[0.04] bg-[#fbfbfd] hover:border-slate-200 dark:border-slate-800 dark:bg-slate-900/40'
            "
            @click="handleAggregateClick(item)"
          >
            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p class="font-medium text-slate-900 dark:text-dark-text">{{ item.city || '未知城市' }}</p>
                <p class="text-xs text-slate-500 dark:text-dark-text/60">{{ item.province }} · {{ item.year }}</p>
              </div>
              <span class="inline-flex w-fit rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                已定位
              </span>
            </div>
            <div class="mt-3 flex items-center justify-between text-sm">
              <span class="text-slate-500 dark:text-dark-text/60">装机容量</span>
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

  <div v-if="showMobileDetails" class="fixed inset-0 z-[70] lg:hidden">
    <button
      type="button"
      class="absolute inset-0 h-full w-full bg-slate-950/45"
      aria-label="关闭地图明细"
      @click="showMobileDetails = false"
    ></button>

    <div class="absolute inset-x-0 bottom-0 max-h-[75vh] overflow-y-auto rounded-t-[28px] bg-white p-4 shadow-[0_-16px_40px_rgba(15,23,42,0.16)] dark:bg-dark-card">
      <div class="mb-4 flex items-center justify-between gap-3">
        <div>
          <h3 class="text-lg font-semibold text-slate-900 dark:text-dark-text">地图数据明细</h3>
          <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">当前展示 {{ items.length }} 个聚合点</p>
        </div>
        <button
          type="button"
          class="apple-pill-secondary min-h-[40px] px-4 py-2"
          @click="showMobileDetails = false"
        >
          关闭
        </button>
      </div>

      <div v-if="!hasMapPoints" class="rounded-2xl border border-dashed border-slate-200 px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60">
        暂无可查看的数据明细
      </div>

      <div
        v-else
        class="space-y-3"
        @touchstart.passive="onTouchStart"
        @touchend.passive="onTouchEnd"
      >
        <button
          v-for="item in mobileItems"
          :key="buildAggregateKey(item)"
          type="button"
          class="apple-subcard block w-full px-4 py-4 text-left"
          @click="handleAggregateClick(item)"
        >
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="font-medium text-slate-900 dark:text-dark-text">{{ item.city || '未知城市' }}</p>
              <p class="mt-1 text-xs text-slate-500 dark:text-dark-text/60">{{ item.province }} · {{ item.year }}</p>
            </div>
            <span class="inline-flex rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
              {{ item.count }} 条
            </span>
          </div>
          <div class="mt-4 flex items-center justify-between text-sm">
            <span class="text-slate-500 dark:text-dark-text/60">装机容量</span>
            <span class="font-semibold text-slate-900 dark:text-dark-text">{{ item.value.toFixed(2) }} 万千瓦</span>
          </div>
        </button>

        <div class="apple-subcard flex items-center justify-between gap-3 px-3 py-2">
          <button
            type="button"
            class="min-h-[40px] rounded-full px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
            :disabled="!canPrevMobilePage"
            @click="prevMobilePage"
          >
            上一页
          </button>
          <span class="text-sm text-slate-500 dark:text-dark-text/60">{{ mobilePage + 1 }} / {{ mobileTotalPages }}</span>
          <button
            type="button"
            class="min-h-[40px] rounded-full px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
            :disabled="!canNextMobilePage"
            @click="nextMobilePage"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
:deep(.amap-logo),
:deep(.amap-copyright) {
  display: none !important;
}
</style>
