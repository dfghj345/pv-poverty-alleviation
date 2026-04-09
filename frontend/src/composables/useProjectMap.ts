import { ref, onMounted } from 'vue';
import { useProjectStore } from '@/store/project';
import { getProjectListApi } from '@/api/project';
import { reverseRegionByCoordinateApi } from '@/api/region';
import type { PowerStationFeature } from '@/api/types';

export type FeatureCollection = { type: 'FeatureCollection'; features: PowerStationFeature[] };

export function useProjectMap() {
  const projectStore = useProjectStore();
  const mapData = ref<FeatureCollection>({ type: 'FeatureCollection', features: [] });

  async function loadMapFeatures(): Promise<void> {
    try {
      const res = await getProjectListApi(0, 1000);

      const features: PowerStationFeature[] = res.items.map(item => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [item.longitude, item.latitude] },
        properties: {
          project_id: item.id,
          site_id: item.name,
          address: '详见后台记录',
          area_sqm: 0,
          installed_capacity: item.capacity,
          status: 'operating'
        }
      }));

      mapData.value = { type: 'FeatureCollection', features };
    } catch (error) {
      console.error('获取项目地图点位失败:', error);
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
      // reverse lookup fail does not block map point selection
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
