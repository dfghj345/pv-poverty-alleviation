import { defineStore } from 'pinia';
import { ref, shallowRef } from 'vue';
import type { PowerStationFeature, CalcROIResponse } from '@/api/types';

type FilterStatus = 'all' | 'planning' | 'constructing' | 'operating';

export interface SelectedMapPoint {
  latitude: number;
  longitude: number;
  province?: string | null;
  city?: string | null;
}

export const useProjectStore = defineStore('project', () => {
  const selectedStation = ref<PowerStationFeature | null>(null);
  const selectedMapPoint = ref<SelectedMapPoint | null>(null);

  const calcResults = shallowRef<CalcROIResponse | null>(null);
  const loading = ref(false);

  const appliedPolicy = ref<{ province: string; electricity_price: number } | null>(null);
  const appliedWeather = ref<{
    latitude: number;
    longitude: number;
    equivalent_hours: number;
    province?: string | null;
    city?: string | null;
  } | null>(null);
  const appliedCost = ref<{ province: string | null; unit_cost_yuan_per_kw: number } | null>(null);
  const appliedProject = ref<{ project_id: number; capacity_kw: number; province: string; latitude: number; longitude: number } | null>(null);

  const filterConditions = ref<{
    keyword: string;
    minCapacity: number;
    status: FilterStatus;
  }>({
    keyword: '',
    minCapacity: 0,
    status: 'all'
  });

  function setSelectedStation(station: PowerStationFeature | null): void {
    selectedStation.value = station;
  }

  function setSelectedMapPoint(point: SelectedMapPoint | null): void {
    selectedMapPoint.value = point;
  }

  function setCalcResults(results: CalcROIResponse | null): void {
    calcResults.value = results;
  }

  function setLoading(value: boolean): void {
    loading.value = value;
  }

  function updateFilters(filters: Partial<typeof filterConditions.value>): void {
    filterConditions.value = { ...filterConditions.value, ...filters };
  }

  function clearSelection(): void {
    selectedStation.value = null;
    selectedMapPoint.value = null;
    calcResults.value = null;
  }

  function setAppliedPolicy(policy: { province: string; electricity_price: number } | null): void {
    appliedPolicy.value = policy;
  }

  function setAppliedWeather(
    payload: {
      latitude: number;
      longitude: number;
      equivalent_hours: number;
      province?: string | null;
      city?: string | null;
    } | null,
  ): void {
    appliedWeather.value = payload;
  }

  function setAppliedCost(payload: { province: string | null; unit_cost_yuan_per_kw: number } | null): void {
    appliedCost.value = payload;
  }

  function setAppliedProject(payload: { project_id: number; capacity_kw: number; province: string; latitude: number; longitude: number } | null): void {
    appliedProject.value = payload;
  }

  return {
    selectedStation,
    selectedMapPoint,
    calcResults,
    loading,
    appliedPolicy,
    appliedWeather,
    appliedCost,
    appliedProject,
    filterConditions,
    setSelectedStation,
    setSelectedMapPoint,
    setCalcResults,
    setLoading,
    setAppliedPolicy,
    setAppliedWeather,
    setAppliedCost,
    setAppliedProject,
    updateFilters,
    clearSelection
  };
});
