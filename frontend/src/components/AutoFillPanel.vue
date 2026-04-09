<script setup lang="ts">
import { computed, ref } from 'vue';
import { useProjectStore } from '@/store/project';
import { getProjectDetailApi } from '@/api/project_detail';
import { getPoliciesApi } from '@/api/policy';
import { getWeatherRadiationApi } from '@/api/weather';
import { getCostsApi } from '@/api/cost';

const projectStore = useProjectStore();
const loading = ref(false);
const errorMsg = ref<string | null>(null);
const infoMsg = ref<string | null>(null);

const selected = computed(() => projectStore.selectedStation);
const projectId = computed(() => selected.value?.properties?.project_id ?? null);

function normProvince(p: string): string {
  return p.replace(/(省|市)$/g, '').trim();
}

async function runAutoFill(): Promise<void> {
  errorMsg.value = null;
  infoMsg.value = null;
  const id = projectId.value;
  if (!id) {
    errorMsg.value = '请先在地图上点击选择一个电站点位（需包含 project_id）。';
    return;
  }

  loading.value = true;
  try {
    const p = await getProjectDetailApi(id);
    const prov = normProvince(p.province);

    projectStore.setAppliedProject({
      project_id: p.id,
      capacity_kw: p.capacity_kw,
      province: prov,
      latitude: p.latitude,
      longitude: p.longitude
    });

    // 1) 政策电价（取第一条；后续可做“最新/最优”选择策略）
    const policies = await getPoliciesApi({ province: prov, limit: 50 });
    if (policies.length > 0) {
      const row = policies[0];
      const price = (row.benchmark_price_yuan_per_kwh ?? 0) + (row.subsidy_yuan_per_kwh ?? 0);
      projectStore.setAppliedPolicy({ province: prov, electricity_price: price });
    }

    // 2) 天气利用小时（找任意一条含 equivalent_hours_h 的记录）
    const weather = await getWeatherRadiationApi({ latitude: p.latitude, longitude: p.longitude, limit: 400 });
    const eqh = weather.find(x => x.equivalent_hours_h != null)?.equivalent_hours_h ?? null;
    if (eqh != null) {
      projectStore.setAppliedWeather({
        latitude: p.latitude,
        longitude: p.longitude,
        equivalent_hours: Number(eqh),
        province: prov,
      });
    }

    // 3) 成本单位造价（优先省份，其次全国）
    const costsProv = await getCostsApi({ category: 'total', province: prov, limit: 50 });
    const pick = (costsProv.find(x => x.unit_cost_yuan_per_kw != null) ?? null)
      ?? ((await getCostsApi({ category: 'total', limit: 50 })).find(x => x.unit_cost_yuan_per_kw != null) ?? null);
    if (pick?.unit_cost_yuan_per_kw != null) {
      projectStore.setAppliedCost({ province: pick.province ?? null, unit_cost_yuan_per_kw: pick.unit_cost_yuan_per_kw });
    }

    infoMsg.value = `已完成自动填参：项目=${p.name} 省份=${prov}`;
  } catch (e: any) {
    errorMsg.value = e?.message ?? '自动填参失败';
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text">自动填参模式（地图选点 → 一键填充测算）</h3>
        <p class="text-sm text-gray-500 dark:text-dark-text/60 mt-1">
          将所选电站的省份/坐标联动：政策电价 + 天气利用小时 + 成本单位造价。
        </p>
      </div>
      <button @click="runAutoFill"
              class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium disabled:opacity-60"
              :disabled="loading">
        {{ loading ? '填充中...' : '一键自动填参' }}
      </button>
    </div>

    <div class="mt-3 text-sm text-gray-600 dark:text-dark-text/70">
      当前选中：<span class="font-medium">{{ selected?.properties?.site_id ?? '未选择' }}</span>
      <span class="ml-2 text-xs" v-if="projectId">project_id={{ projectId }}</span>
    </div>

    <div v-if="errorMsg" class="mt-3 text-sm text-red-600 dark:text-red-400">{{ errorMsg }}</div>
    <div v-if="infoMsg" class="mt-3 text-sm text-emerald-600 dark:text-emerald-400">{{ infoMsg }}</div>
  </div>
</template>

