import { ref } from 'vue';

import { getPanelDataMapApi, type PanelDataListParams, type PanelDataMapItem } from '@/api/panel_data';
import type { PowerStationFeature } from '@/api/types';
import { useProjectStore } from '@/store/project';

export interface PanelDataMapAggregate extends PanelDataMapItem {
  hasCoordinate: boolean;
}

export interface MapViewport {
  center: [number, number];
  zoom: number;
}

const DEFAULT_CENTER: [number, number] = [105.0, 35.0];
const DEFAULT_ZOOM = 4.5;
const PROVINCE_ZOOM = 6;
const CITY_ZOOM = 9.5;

export function buildAggregateKey(item: Pick<PanelDataMapItem, 'province' | 'city' | 'year'>): string {
  return [item.province, item.city, item.year].join('::');
}

function pickLatestByCity(items: PanelDataMapItem[]): PanelDataMapItem[] {
  const latest = new Map<string, PanelDataMapItem>();

  items.forEach((item) => {
    const key = `${item.province}::${item.city}`;
    const current = latest.get(key);
    if (!current || item.year > current.year) {
      latest.set(key, item);
    }
  });

  return Array.from(latest.values()).sort(
    (left, right) => right.value - left.value || right.year - left.year || left.city.localeCompare(right.city, 'zh-CN'),
  );
}

function buildStationFeature(item: PanelDataMapAggregate): PowerStationFeature {
  return {
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: [item.longitude, item.latitude],
    },
    properties: {
      site_id: `${item.province}-${item.city}-${item.year}`,
      address: `${item.province} ${item.city}`,
      area_sqm: item.count,
      installed_capacity: item.value,
      status: 'operating',
      built_year: item.year,
      province: item.province,
      city: item.city,
      source: 'panel_data',
    },
  };
}

function averageCoordinates(items: PanelDataMapAggregate[]): [number, number] | null {
  if (items.length === 0) {
    return null;
  }

  const longitude = items.reduce((total, item) => total + item.longitude, 0) / items.length;
  const latitude = items.reduce((total, item) => total + item.latitude, 0) / items.length;
  return [longitude, latitude];
}

function resolveViewport(
  items: PanelDataMapAggregate[],
  filters?: Omit<PanelDataListParams, 'page' | 'page_size'>,
  selected?: PanelDataMapAggregate | null,
): MapViewport {
  if (selected) {
    return {
      center: [selected.longitude, selected.latitude],
      zoom: CITY_ZOOM,
    };
  }

  if (filters?.city && items[0]) {
    return {
      center: [items[0].longitude, items[0].latitude],
      zoom: CITY_ZOOM,
    };
  }

  if (filters?.province) {
    const provinceCenter = averageCoordinates(items);
    if (provinceCenter) {
      return {
        center: provinceCenter,
        zoom: PROVINCE_ZOOM,
      };
    }
  }

  return {
    center: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
  };
}

export function useProjectMap() {
  const projectStore = useProjectStore();
  const mapData = ref<PanelDataMapAggregate[]>([]);
  const mapViewport = ref<MapViewport>({
    center: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
  });
  const selectedMapData = ref<PanelDataMapAggregate | null>(null);
  const mapLoading = ref(false);
  const mapError = ref<string | null>(null);

  function applySelection(item: PanelDataMapAggregate | null): void {
    selectedMapData.value = item;
    projectStore.setSelectedStation(item ? buildStationFeature(item) : null);
  }

  async function loadMapData(params?: Omit<PanelDataListParams, 'page' | 'page_size'>): Promise<void> {
    mapLoading.value = true;
    mapError.value = null;

    try {
      const mapItems = await getPanelDataMapApi(params);
      const displayItems = params?.year != null ? mapItems : pickLatestByCity(mapItems);
      const nextItems = displayItems.map<PanelDataMapAggregate>((item) => ({
        ...item,
        hasCoordinate: true,
      }));

      mapData.value = nextItems;

      if (selectedMapData.value) {
        const nextSelection =
          nextItems.find((item) => buildAggregateKey(item) === buildAggregateKey(selectedMapData.value!)) ?? null;
        applySelection(nextSelection);
        mapViewport.value = resolveViewport(nextItems, params, nextSelection);
      } else {
        mapViewport.value = resolveViewport(nextItems, params);
      }
    } catch (error) {
      console.error('Failed to load panel data map.', error);
      mapError.value = error instanceof Error ? error.message : '地图数据加载失败';
      mapData.value = [];
      mapViewport.value = {
        center: DEFAULT_CENTER,
        zoom: DEFAULT_ZOOM,
      };
      applySelection(null);
    } finally {
      mapLoading.value = false;
    }
  }

  function selectAggregateItem(item: PanelDataMapAggregate): void {
    applySelection(item);
    mapViewport.value = resolveViewport(mapData.value, undefined, item);
  }

  function handlePointClick(): void {
    // Legacy compatibility for the unused component-based dashboard.
  }

  async function handleLocationPicked(): Promise<void> {
    // Legacy compatibility for the unused component-based dashboard.
  }

  function handleLocationCleared(): void {
    // Legacy compatibility for the unused component-based dashboard.
  }

  return {
    mapData,
    mapViewport,
    selectedMapData,
    mapLoading,
    mapError,
    loadMapData,
    selectAggregateItem,
    handlePointClick,
    handleLocationPicked,
    handleLocationCleared,
  };
}
