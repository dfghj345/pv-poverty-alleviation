<script setup lang="ts">
import { computed, ref, watch } from 'vue';

import { getCostsApi } from '@/api/cost';
import type { PanelDataItem } from '@/api/panel_data';
import { getPoliciesApi } from '@/api/policy';
import { getWeatherRadiationApi } from '@/api/weather';
import type { PanelDataMapAggregate } from '@/composables/useProjectMap';
import { useProjectStore } from '@/store/project';

const REGION_SUFFIXES = ['维吾尔自治区', '壮族自治区', '回族自治区', '自治区', '特别行政区', '省', '市'] as const;

const props = withDefaults(defineProps<{
  selectedData?: PanelDataMapAggregate | null;
  selectedRecord?: PanelDataItem | null;
  detailLoading?: boolean;
  detailError?: string | null;
}>(), {
  selectedData: null,
  selectedRecord: null,
  detailLoading: false,
  detailError: null,
});

const projectStore = useProjectStore();
const loading = ref(false);
const errorMsg = ref<string | null>(null);
const infoMsg = ref<string | null>(null);

const fallbackStation = computed(() => projectStore.selectedStation);
const hasSelection = computed(() => Boolean(props.selectedData || fallbackStation.value));

const selectedTitle = computed(() => {
  if (props.selectedData) {
    return `${props.selectedData.province} ${props.selectedData.city} · ${props.selectedData.year}`;
  }

  if (fallbackStation.value) {
    return fallbackStation.value.properties.site_id;
  }

  return '未选择数据';
});

const detailRows = computed(() => {
  if (!props.selectedData) {
    return [];
  }

  return [
    { label: '省份', value: props.selectedData.province },
    { label: '城市', value: props.selectedData.city || '--' },
    { label: '年份', value: String(props.selectedData.year) },
    { label: '数据值', value: `${formatNumber(props.selectedData.value)} 万千瓦` },
    { label: '数量', value: formatInteger(props.selectedData.count) },
    { label: '坐标状态', value: props.selectedData.hasCoordinate ? '已定位' : '仅聚合数据' },
  ];
});

const recordRows = computed(() => {
  const record = props.selectedRecord;
  if (!record) {
    return [];
  }

  const rows = [
    { label: '装机容量', value: formatNullable(record.pv_installed_capacity_wan_kw, '万千瓦') },
    { label: '人均收入', value: formatNullable(record.disposable_income_per_capita_yuan, '元') },
    { label: '医疗支出', value: formatNullable(record.healthcare_expenditure_per_capita_yuan, '元') },
    { label: '城乡收入比', value: formatNullable(record.urban_rural_income_ratio) },
    { label: '死亡率', value: formatNullable(record.mortality_per_mille, '‰') },
    { label: 'PM2.5', value: formatNullable(record.pm25_annual_avg_ug_per_m3, 'ug/m3') },
    { label: 'GDP', value: formatNullable(record.gdp_100m_yuan, '亿元') },
  ];

  return rows.filter((item) => item.value !== '--');
});

function normalizeProvince(value: string | null | undefined): string {
  const normalized = (value ?? '').trim().replace(/\s+/g, '');
  return REGION_SUFFIXES.reduce((result, suffix) => {
    return result.endsWith(suffix) ? result.slice(0, -suffix.length) : result;
  }, normalized);
}

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null) {
    return '--';
  }
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatInteger(value: number | null | undefined): string {
  if (value == null) {
    return '--';
  }
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(value);
}

function formatNullable(value: number | null | undefined, suffix = ''): string {
  if (value == null) {
    return '--';
  }
  return `${formatNumber(value)}${suffix ? ` ${suffix}` : ''}`;
}

function resolveCapacityKw(): number | null {
  if (props.selectedRecord?.pv_installed_capacity_wan_kw != null) {
    return props.selectedRecord.pv_installed_capacity_wan_kw * 10000;
  }

  if (props.selectedData?.value != null) {
    return props.selectedData.value * 10000;
  }

  if (fallbackStation.value?.properties?.installed_capacity != null) {
    const capacity = fallbackStation.value.properties.installed_capacity;
    return fallbackStation.value.properties.source === 'panel_data' ? capacity * 10000 : capacity;
  }

  return null;
}

function buildSelectionContext() {
  if (props.selectedData) {
    return {
      siteName: `${props.selectedData.province}-${props.selectedData.city}-${props.selectedData.year}`,
      province: normalizeProvince(props.selectedData.province),
      city: props.selectedData.city || undefined,
      latitude: props.selectedData.latitude ?? projectStore.selectedMapPoint?.latitude ?? 0,
      longitude: props.selectedData.longitude ?? projectStore.selectedMapPoint?.longitude ?? 0,
      capacityKw: resolveCapacityKw(),
    };
  }

  const station = fallbackStation.value;
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
    capacityKw: resolveCapacityKw(),
  };
}

async function runAutoFill(options?: { silent?: boolean }): Promise<void> {
  const silent = options?.silent ?? false;
  const selection = buildSelectionContext();

  errorMsg.value = null;
  infoMsg.value = null;

  if (!selection) {
    if (!silent) {
      errorMsg.value = '请先在地图或聚合列表中选择一条数据';
    }
    return;
  }

  loading.value = true;
  try {
    if (selection.capacityKw != null) {
      projectStore.setAppliedProject({
        project_id: 0,
        capacity_kw: selection.capacityKw,
        province: selection.province,
        latitude: selection.latitude,
        longitude: selection.longitude,
      });
    }

    if (selection.province) {
      const policies = await getPoliciesApi({ province: selection.province, limit: 50 });
      const policy = policies[0] ?? null;

      if (policy) {
        const electricityPrice = (policy.benchmark_price_yuan_per_kwh ?? 0) + (policy.subsidy_yuan_per_kwh ?? 0);
        projectStore.setAppliedPolicy({
          province: selection.province,
          electricity_price: electricityPrice,
        });
      }
    }

    const weather = selection.city && selection.province
      ? await getWeatherRadiationApi({ province: selection.province, city: selection.city, limit: 400 })
      : await getWeatherRadiationApi({ latitude: selection.latitude, longitude: selection.longitude, limit: 400 });
    const equivalentHours = weather.find((item) => item.equivalent_hours_h != null)?.equivalent_hours_h ?? null;

    if (equivalentHours != null) {
      projectStore.setAppliedWeather({
        latitude: selection.latitude,
        longitude: selection.longitude,
        equivalent_hours: Number(equivalentHours),
        province: selection.province || undefined,
        city: selection.city,
      });
    }

    const provinceCosts = selection.province
      ? await getCostsApi({ category: 'total', province: selection.province, limit: 50 })
      : [];
    const fallbackCosts = provinceCosts.length > 0 ? provinceCosts : await getCostsApi({ category: 'total', limit: 50 });
    const matchedCost = fallbackCosts.find((item) => item.unit_cost_yuan_per_kw != null) ?? null;

    if (matchedCost?.unit_cost_yuan_per_kw != null) {
      projectStore.setAppliedCost({
        province: matchedCost.province ?? null,
        unit_cost_yuan_per_kw: matchedCost.unit_cost_yuan_per_kw,
      });
    }

    infoMsg.value = `已同步默认测算参数：${selection.siteName}`;
  } catch (error) {
    errorMsg.value = error instanceof Error ? error.message : '自动填参失败';
  } finally {
    loading.value = false;
  }
}

watch(
  () => {
    if (props.selectedData) {
      return [
        props.selectedData.province,
        props.selectedData.city,
        props.selectedData.year,
        props.selectedData.value,
        props.selectedRecord?.id ?? '',
      ].join('::');
    }

    return fallbackStation.value?.properties?.site_id ?? '';
  },
  (nextToken, previousToken) => {
    if (nextToken && nextToken !== previousToken) {
      void runAutoFill({ silent: true });
    }
  },
);
</script>

<template>
  <div class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-dark-card">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div>
        <p class="text-sm uppercase tracking-[0.28em] text-emerald-600 dark:text-emerald-300">Auto Fill</p>
        <h3 class="mt-2 text-2xl font-semibold text-slate-900 dark:text-dark-text">自动填参</h3>
        <p class="mt-2 text-sm leading-7 text-slate-500 dark:text-dark-text/60">
          选中地图点位或聚合列表后，自动把省市、装机量、电价、天气利用小时和成本参数同步到收益测算。
        </p>
      </div>
      <button
        class="rounded-2xl bg-emerald-500 px-5 py-3 text-sm font-medium text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="loading || !hasSelection"
        @click="runAutoFill()"
      >
        {{ loading ? '同步中...' : '重新同步参数' }}
      </button>
    </div>

    <div
      v-if="!hasSelection"
      class="mt-6 rounded-2xl border border-dashed border-slate-200 px-6 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60"
    >
      请先在地图或聚合列表中选择一条数据
    </div>

    <div v-else class="mt-6 space-y-6">
      <div class="rounded-2xl border border-slate-100 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-900/40">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm text-slate-500 dark:text-dark-text/60">当前选中</p>
            <p class="mt-2 text-lg font-semibold text-slate-900 dark:text-dark-text">{{ selectedTitle }}</p>
          </div>
          <span class="rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
            panel_data
          </span>
        </div>

        <div class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="item in detailRows"
            :key="item.label"
            class="rounded-2xl border border-white/70 bg-white px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-950/40"
          >
            <p class="text-xs uppercase tracking-[0.16em] text-slate-400">{{ item.label }}</p>
            <p class="mt-2 text-sm font-medium text-slate-900 dark:text-dark-text">{{ item.value }}</p>
          </div>
        </div>
      </div>

      <div class="rounded-2xl border border-slate-100 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-900/40">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm text-slate-500 dark:text-dark-text/60">关键字段</p>
            <p class="mt-2 text-lg font-semibold text-slate-900 dark:text-dark-text">当前选中数据详情</p>
          </div>
          <span
            v-if="detailLoading"
            class="rounded-full bg-slate-200 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-dark-text/70"
          >
            加载中
          </span>
        </div>

        <div v-if="detailError" class="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
          {{ detailError }}
        </div>

        <div
          v-else-if="!detailLoading && recordRows.length === 0"
          class="mt-4 rounded-xl border border-dashed border-slate-200 px-4 py-6 text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60"
        >
          当前只有聚合信息，暂无更多明细字段
        </div>

        <div v-else class="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <div
            v-for="item in recordRows"
            :key="item.label"
            class="rounded-2xl border border-white/70 bg-white px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-950/40"
          >
            <p class="text-xs uppercase tracking-[0.16em] text-slate-400">{{ item.label }}</p>
            <p class="mt-2 text-sm font-medium text-slate-900 dark:text-dark-text">{{ item.value }}</p>
          </div>
        </div>
      </div>

      <div v-if="errorMsg" class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300">
        {{ errorMsg }}
      </div>
      <div v-if="infoMsg" class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700 dark:border-emerald-500/20 dark:bg-emerald-500/10 dark:text-emerald-300">
        {{ infoMsg }}
      </div>
    </div>
  </div>
</template>
