import { computed, ref } from 'vue';

import { getPanelDataMapApi, type PanelDataListParams, type PanelDataMapItem } from '@/api/panel_data';
import { getRegionLocationsApi, reverseRegionByCoordinateApi, type RegionLocation } from '@/api/region';
import { useProjectStore } from '@/store/project';
import type { PowerStationFeature } from '@/api/types';

export type FeatureCollection = { type: 'FeatureCollection'; features: PowerStationFeature[] };

export interface PanelDataMapAggregate extends PanelDataMapItem {
  hasCoordinate: boolean;
  longitude?: number;
  latitude?: number;
}

const REGION_SUFFIXES = ['维吾尔自治区', '壮族自治区', '回族自治区', '自治区', '特别行政区', '省', '市'] as const;

let cachedLocations: RegionLocation[] | null = null;

export function buildAggregateKey(item: Pick<PanelDataMapItem, 'province' | 'city' | 'year'>): string {
  return [item.province, item.city, item.year].join('::');
}

function normalizeRegionName(value: string): string {
  const normalized = value.trim().replace(/\s+/g, '');
  return REGION_SUFFIXES.reduce((result, suffix) => {
    return result.endsWith(suffix) ? result.slice(0, -suffix.length) : result;
  }, normalized);
}

function buildLocationKeys(province: string, city: string): string[] {
  const normalizedProvince = normalizeRegionName(province);
  const normalizedCity = normalizeRegionName(city);

  return [
    `${province}::${city}`,
    `${normalizedProvince}::${normalizedCity}`,
    city,
    normalizedCity,
  ];
}

function createLocationIndex(locations: RegionLocation[]): Map<string, RegionLocation> {
  const index = new Map<string, RegionLocation>();

  locations.forEach((location) => {
    buildLocationKeys(location.province, location.city).forEach((key) => {
      if (!index.has(key)) {
        index.set(key, location);
      }
    });
  });

  return index;
}

function pickLatestByCity(items: PanelDataMapItem[]): PanelDataMapItem[] {
  const latest = new Map<string, PanelDataMapItem>();

  items.forEach((item) => {
    const key = `${item.province}::${item.city}`;
    if (!latest.has(key)) {
      latest.set(key, item);
    }
  });

  return Array.from(latest.values());
}

function buildLocationFeature(item: PanelDataMapAggregate): PowerStationFeature {
  return {
    type: 'Feature',
    geometry: {
      type: 'Point',
      coordinates: [item.longitude ?? 0, item.latitude ?? 0],
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

async function getLocationReference(): Promise<RegionLocation[]> {
  if (cachedLocations) {
    return cachedLocations;
  }

  cachedLocations = await getRegionLocationsApi({ limit: 1000 });
  return cachedLocations;
}

export function useProjectMap() {
  const projectStore = useProjectStore();
  const mapData = ref<FeatureCollection>({ type: 'FeatureCollection', features: [] });
  const mapAggregates = ref<PanelDataMapAggregate[]>([]);
  const selectedMapData = ref<PanelDataMapAggregate | null>(null);
  const mapLoading = ref(false);
  const mapError = ref<string | null>(null);

  const mapMatchedCount = computed(() => mapData.value.features.length);

  function findFeatureForAggregate(item: PanelDataMapAggregate): PowerStationFeature | null {
    return (
      mapData.value.features.find((feature) => {
        return (
          feature.properties.province === item.province &&
          feature.properties.city === item.city &&
          feature.properties.built_year === item.year
        );
      }) ?? null
    );
  }

  function applySelection(item: PanelDataMapAggregate | null): void {
    selectedMapData.value = item;
    projectStore.setSelectedStation(item ? findFeatureForAggregate(item) : null);
  }

  async function loadMapData(params?: Omit<PanelDataListParams, 'page' | 'page_size'>): Promise<void> {
    mapLoading.value = true;
    mapError.value = null;

    try {
      const mapItems = await getPanelDataMapApi(params);
      const displayItems = params?.year != null ? mapItems : pickLatestByCity(mapItems);

      let locationIndex = new Map<string, RegionLocation>();
      try {
        locationIndex = createLocationIndex(await getLocationReference());
      } catch (error) {
        console.warn('Failed to load region coordinates, fallback to aggregate map list.', error);
      }

      const nextAggregates = displayItems.map<PanelDataMapAggregate>((item) => {
        const location = buildLocationKeys(item.province, item.city)
          .map((key) => locationIndex.get(key))
          .find((value): value is RegionLocation => Boolean(value));

        return {
          ...item,
          hasCoordinate: Boolean(location),
          longitude: location?.longitude,
          latitude: location?.latitude,
        };
      });

      mapAggregates.value = nextAggregates;
      mapData.value = {
        type: 'FeatureCollection',
        features: nextAggregates.filter((item) => item.hasCoordinate).map(buildLocationFeature),
      };

      if (selectedMapData.value) {
        const nextSelection =
          nextAggregates.find((item) => buildAggregateKey(item) === buildAggregateKey(selectedMapData.value!)) ?? null;
        applySelection(nextSelection);
      }
    } catch (error) {
      console.error('Failed to load panel data map.', error);
      mapError.value = error instanceof Error ? error.message : '地图数据加载失败';
      mapData.value = { type: 'FeatureCollection', features: [] };
      mapAggregates.value = [];
      applySelection(null);
    } finally {
      mapLoading.value = false;
    }
  }

  function handlePointClick(feature: PowerStationFeature): void {
    const matched =
      mapAggregates.value.find((item) => {
        return (
          item.province === feature.properties.province &&
          item.city === feature.properties.city &&
          item.year === feature.properties.built_year
        );
      }) ?? null;

    if (matched) {
      applySelection(matched);
      return;
    }

    projectStore.setSelectedStation(feature);
    selectedMapData.value = null;
  }

  function selectAggregateItem(item: PanelDataMapAggregate): void {
    applySelection(item);
  }

  async function handleLocationPicked(payload: { longitude: number; latitude: number }): Promise<void> {
    let province: string | null = null;
    let city: string | null = null;

    try {
      const location = await reverseRegionByCoordinateApi({
        latitude: payload.latitude,
        longitude: payload.longitude,
      });
      province = location?.province ?? null;
      city = location?.city ?? null;
    } catch {
      // Reverse lookup failure should not block manual point selection.
    }

    projectStore.setSelectedMapPoint({
      latitude: payload.latitude,
      longitude: payload.longitude,
      province,
      city,
    });
  }

  function handleLocationCleared(): void {
    projectStore.setSelectedMapPoint(null);
  }

  return {
    mapData,
    mapAggregates,
    selectedMapData,
    mapLoading,
    mapError,
    mapMatchedCount,
    loadMapData,
    handlePointClick,
    selectAggregateItem,
    handleLocationPicked,
    handleLocationCleared,
    projectStore,
  };
}
