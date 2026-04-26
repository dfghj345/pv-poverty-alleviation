import { onMounted, ref } from 'vue';

import { getRegionLocationsApi, reverseRegionByCoordinateApi } from '@/api/region';
import { useProjectStore } from '@/store/project';
import type { PowerStationFeature } from '@/api/types';

export type FeatureCollection = { type: 'FeatureCollection'; features: PowerStationFeature[] };

function buildLocationFeature(item: {
  province: string;
  city: string;
  latitude: number;
  longitude: number;
  source: string;
}): PowerStationFeature {
  return {
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [item.longitude, item.latitude] },
    properties: {
      site_id: `${item.province}${item.city}`,
      address: `${item.province} ${item.city}`,
      area_sqm: 0,
      installed_capacity: 0,
      status: 'planning',
      province: item.province,
      city: item.city,
      source: item.source,
    },
  };
}

export function useProjectMap() {
  const projectStore = useProjectStore();
  const mapData = ref<FeatureCollection>({ type: 'FeatureCollection', features: [] });

  async function loadMapFeatures(): Promise<void> {
    try {
      const locations = await getRegionLocationsApi({ limit: 1000 });
      mapData.value = {
        type: 'FeatureCollection',
        features: locations.map(buildLocationFeature),
      };
    } catch (error) {
      console.error('获取地图真实点位失败:', error);
      mapData.value = { type: 'FeatureCollection', features: [] };
    }
  }

  function handlePointClick(feature: PowerStationFeature): void {
    projectStore.setSelectedStation(feature);
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

  onMounted(() => {
    void loadMapFeatures();
  });

  return {
    mapData,
    loadMapFeatures,
    handlePointClick,
    handleLocationPicked,
    handleLocationCleared,
    projectStore,
  };
}
