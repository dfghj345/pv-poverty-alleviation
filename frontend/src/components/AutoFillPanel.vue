<script setup lang="ts">
import { computed, ref } from 'vue';

import { getCostsApi } from '@/api/cost';
import { getPoliciesApi } from '@/api/policy';
import { getProjectDetailApi } from '@/api/project_detail';
import { getWeatherRadiationApi } from '@/api/weather';
import { useProjectStore } from '@/store/project';

const projectStore = useProjectStore();
const loading = ref(false);
const errorMsg = ref<string | null>(null);
const infoMsg = ref<string | null>(null);

const selected = computed(() => projectStore.selectedStation);
const projectId = computed(() => selected.value?.properties?.project_id ?? null);

function normalizeProvince(value: string | null | undefined): string {
  return (value ?? '')
    .replace(/维吾尔自治区|壮族自治区|回族自治区|自治区|特别行政区|省|市/g, '')
    .trim();
}

function buildSelectedStationContext() {
  const station = selected.value;
  if (!station) {
    return null;
  }

  const [longitude, latitude] = station.geometry.coordinates;
  return {
    siteName: station.properties.site_id,
    province: normalizeProvince(station.properties.province),
    city: station.properties.city?.trim() || undefined,
    latitude,
    longitude,
    capacityKw: station.properties.installed_capacity > 0 ? station.properties.installed_capacity : null,
  };
}

async function runAutoFill(): Promise<void> {
  errorMsg.value = null;
  infoMsg.value = null;

  loading.value = true;
  try {
    let siteName = '地图点位';
    let province = '';
    let city: string | undefined;
    let latitude = 0;
    let longitude = 0;

    if (projectId.value) {
      const project = await getProjectDetailApi(projectId.value);
      siteName = project.name;
      province = normalizeProvince(project.province);
      latitude = project.latitude;
      longitude = project.longitude;

      projectStore.setAppliedProject({
        project_id: project.id,
        capacity_kw: project.capacity_kw,
        province,
        latitude,
        longitude,
      });
    } else {
      const stationContext = buildSelectedStationContext();
      if (!stationContext) {
        errorMsg.value = '请先在地图上选择一个真实点位。';
        return;
      }

      siteName = stationContext.siteName;
      province = stationContext.province;
      city = stationContext.city;
      latitude = stationContext.latitude;
      longitude = stationContext.longitude;

      if (stationContext.capacityKw != null) {
        projectStore.setAppliedProject({
          project_id: 0,
          capacity_kw: stationContext.capacityKw,
          province,
          latitude,
          longitude,
        });
      }
    }

    if (province) {
      const policies = await getPoliciesApi({ province, limit: 50 });
      if (policies.length > 0) {
        const row = policies[0];
        const price = (row.benchmark_price_yuan_per_kwh ?? 0) + (row.subsidy_yuan_per_kwh ?? 0);
        projectStore.setAppliedPolicy({ province, electricity_price: price });
      }
    }

    const weather = city && province
      ? await getWeatherRadiationApi({ province, city, limit: 400 })
      : await getWeatherRadiationApi({ latitude, longitude, limit: 400 });
    const eqh = weather.find((item) => item.equivalent_hours_h != null)?.equivalent_hours_h ?? null;
    if (eqh != null) {
      projectStore.setAppliedWeather({
        latitude,
        longitude,
        equivalent_hours: Number(eqh),
        province: province || undefined,
        city,
      });
    }

    const costsByProvince = province
      ? await getCostsApi({ category: 'total', province, limit: 50 })
      : [];
    const fallbackCosts = costsByProvince.length > 0 ? costsByProvince : await getCostsApi({ category: 'total', limit: 50 });
    const matchedCost = fallbackCosts.find((item) => item.unit_cost_yuan_per_kw != null) ?? null;
    if (matchedCost?.unit_cost_yuan_per_kw != null) {
      projectStore.setAppliedCost({
        province: matchedCost.province ?? null,
        unit_cost_yuan_per_kw: matchedCost.unit_cost_yuan_per_kw,
      });
    }

    infoMsg.value = province
      ? `已完成自动填参：${siteName} / ${province}${city ? ` ${city}` : ''}`
      : `已完成自动填参：${siteName}`;
  } catch (error) {
    errorMsg.value = error instanceof Error ? error.message : '自动填参失败';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text">自动填参</h3>
        <p class="text-sm text-gray-500 dark:text-dark-text/60 mt-1">
          支持从地图选中的项目点位或城市坐标点位，一次性联动政策电价、天气利用小时和成本参数。
        </p>
      </div>
      <button
        @click="runAutoFill"
        class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium disabled:opacity-60"
        :disabled="loading"
      >
        {{ loading ? '填充中...' : '一键自动填参' }}
      </button>
    </div>

    <div class="mt-3 text-sm text-gray-600 dark:text-dark-text/70">
      当前选中：
      <span class="font-medium">{{ selected?.properties?.site_id ?? '未选择' }}</span>
      <span class="ml-2 text-xs" v-if="projectId">project_id={{ projectId }}</span>
    </div>

    <div v-if="errorMsg" class="mt-3 text-sm text-red-600 dark:text-red-400">{{ errorMsg }}</div>
    <div v-if="infoMsg" class="mt-3 text-sm text-emerald-600 dark:text-emerald-400">{{ infoMsg }}</div>
  </div>
</template>
