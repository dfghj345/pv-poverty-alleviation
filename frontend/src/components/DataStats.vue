<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  markRaw,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from 'vue';
import * as echarts from 'echarts';

import type { PanelDataFilters, PanelDataListParams, PanelDataPage, PanelDataStats } from '@/api/panel_data';
import { useProjectStore } from '@/store/project';

const WeatherRadiationPanel = defineAsyncComponent(() => import('@/components/WeatherRadiationPanel.vue'));
const PovertyPanel = defineAsyncComponent(() => import('@/components/PovertyPanel.vue'));
const PolicyPanel = defineAsyncComponent(() => import('@/components/PolicyPanel.vue'));
const CostPanel = defineAsyncComponent(() => import('@/components/CostPanel.vue'));

type QueryState = Required<Pick<PanelDataListParams, 'page' | 'page_size'>> & Omit<PanelDataListParams, 'page' | 'page_size'>;

const props = withDefaults(defineProps<{
  stats?: PanelDataStats | null;
  filters?: PanelDataFilters;
  tableData?: PanelDataPage;
  query?: QueryState;
  loading?: {
    stats: boolean;
    filters: boolean;
    list: boolean;
  };
  errors?: {
    stats: string | null;
    filters: string | null;
    list: string | null;
  };
  showSummary?: boolean;
  showFilters?: boolean;
  showCharts?: boolean;
  showTable?: boolean;
  showToolkit?: boolean;
}>(), {
  stats: null,
  filters: () => ({
    provinces: [],
    cities: [],
    years: [],
  }),
  tableData: () => ({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
  }),
  query: () => ({
    page: 1,
    page_size: 20,
    province: undefined,
    city: undefined,
    year: undefined,
    keyword: undefined,
  }),
  loading: () => ({
    stats: false,
    filters: false,
    list: false,
  }),
  errors: () => ({
    stats: null,
    filters: null,
    list: null,
  }),
  showSummary: true,
  showFilters: true,
  showCharts: true,
  showTable: true,
  showToolkit: true,
});

const emit = defineEmits<{
  (e: 'query-change', patch: Partial<QueryState>): void;
  (e: 'reload'): void;
}>();

const projectStore = useProjectStore();
const keywordInput = ref(props.query.keyword ?? '');
const provinceChartRef = ref<HTMLElement | null>(null);
const trendChartRef = ref<HTMLElement | null>(null);
const charts: echarts.ECharts[] = [];
const isDarkTheme = ref(document.documentElement.classList.contains('dark'));

const summaryCards = computed(() => [
  {
    title: '总记录数',
    value: formatInteger(props.stats?.total_count ?? 0),
    accent: 'text-emerald-600 dark:text-emerald-300',
    tone: 'bg-emerald-50 dark:bg-emerald-500/10',
  },
  {
    title: '覆盖省份',
    value: formatInteger(props.stats?.province_count ?? 0),
    accent: 'text-cyan-600 dark:text-cyan-300',
    tone: 'bg-cyan-50 dark:bg-cyan-500/10',
  },
  {
    title: '覆盖城市',
    value: formatInteger(props.stats?.city_count ?? 0),
    accent: 'text-amber-600 dark:text-amber-300',
    tone: 'bg-amber-50 dark:bg-amber-500/10',
  },
  {
    title: '覆盖年份',
    value: formatInteger(props.stats?.year_count ?? 0),
    accent: 'text-rose-600 dark:text-rose-300',
    tone: 'bg-rose-50 dark:bg-rose-500/10',
  },
]);

const hasStatsData = computed(() => (props.stats?.total_count ?? 0) > 0);
const totalPages = computed(() => Math.max(1, Math.ceil(props.tableData.total / props.query.page_size)));
const canPrevPage = computed(() => props.query.page > 1);
const canNextPage = computed(() => props.query.page < totalPages.value);
const pageStart = computed(() => (props.tableData.total === 0 ? 0 : (props.query.page - 1) * props.query.page_size + 1));
const pageEnd = computed(() => Math.min(props.tableData.total, props.query.page * props.query.page_size));

let observer: MutationObserver | null = null;

function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null) {
    return '--';
  }
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(value);
}

function formatInteger(value: number): string {
  return new Intl.NumberFormat('zh-CN', { maximumFractionDigits: 0 }).format(value);
}

function syncKeywordInput(): void {
  keywordInput.value = props.query.keyword ?? '';
}

function handleProvinceChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value.trim();
  emit('query-change', {
    province: value || undefined,
    city: undefined,
  });
}

function handleCityChange(event: Event): void {
  const value = (event.target as HTMLSelectElement).value.trim();
  emit('query-change', {
    city: value || undefined,
  });
}

function handleYearChange(event: Event): void {
  const rawValue = (event.target as HTMLSelectElement).value.trim();
  emit('query-change', {
    year: rawValue ? Number(rawValue) : undefined,
  });
}

function handleKeywordSearch(): void {
  emit('query-change', {
    keyword: keywordInput.value.trim() || undefined,
  });
}

function clearFilters(): void {
  keywordInput.value = '';
  emit('query-change', {
    province: undefined,
    city: undefined,
    year: undefined,
    keyword: undefined,
  });
}

function goToPage(page: number): void {
  if (page < 1 || page > totalPages.value || page === props.query.page) {
    return;
  }
  emit('query-change', { page });
}

function changePageSize(event: Event): void {
  const nextSize = Number((event.target as HTMLSelectElement).value);
  emit('query-change', {
    page_size: nextSize,
    page: 1,
  });
}

function onApplyPrice(payload: { province: string; electricity_price: number }): void {
  projectStore.setAppliedPolicy(payload);
}

function onApplyCost(payload: { province: string | null; unit_cost_yuan_per_kw: number }): void {
  projectStore.setAppliedCost(payload);
}

function disposeCharts(): void {
  charts.forEach((chart) => chart.dispose());
  charts.length = 0;
}

function handleResize(): void {
  charts.forEach((chart) => chart.resize());
}

function initCharts(): void {
  disposeCharts();

  if (!props.showCharts || !hasStatsData.value || !props.stats) {
    return;
  }

  const textColor = isDarkTheme.value ? '#F8FAFC' : '#0F172A';
  const splitLineColor = isDarkTheme.value ? '#334155' : '#E2E8F0';

  if (provinceChartRef.value) {
    const provinceChart = markRaw(echarts.init(provinceChartRef.value));
    provinceChart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '5%', right: '4%', top: '12%', bottom: '18%', containLabel: true },
      xAxis: {
        type: 'category',
        data: props.stats.by_province.slice(0, 12).map((item) => item.province),
        axisLabel: { color: textColor, rotate: 25, interval: 0 },
        axisLine: { lineStyle: { color: splitLineColor } },
      },
      yAxis: {
        type: 'value',
        name: '记录数',
        axisLabel: { color: textColor },
        splitLine: { lineStyle: { color: splitLineColor } },
      },
      series: [
        {
          type: 'bar',
          data: props.stats.by_province.slice(0, 12).map((item) => item.count),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#10b981' },
              { offset: 1, color: '#0f766e' },
            ]),
            borderRadius: [8, 8, 0, 0],
          },
        },
      ],
    });
    charts.push(provinceChart);
  }

  if (trendChartRef.value) {
    const trendChart = markRaw(echarts.init(trendChartRef.value));
    trendChart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      grid: { left: '5%', right: '4%', top: '12%', bottom: '14%', containLabel: true },
      legend: {
        top: '2%',
        textStyle: { color: textColor },
      },
      xAxis: {
        type: 'category',
        data: props.stats.by_year.map((item) => item.year),
        axisLabel: { color: textColor },
        axisLine: { lineStyle: { color: splitLineColor } },
      },
      yAxis: [
        {
          type: 'value',
          name: '记录数',
          axisLabel: { color: textColor },
          splitLine: { lineStyle: { color: splitLineColor } },
        },
        {
          type: 'value',
          name: '装机量(万千瓦)',
          axisLabel: { color: textColor },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '记录数',
          type: 'bar',
          data: props.stats.by_year.map((item) => item.count),
          barMaxWidth: 24,
          itemStyle: { color: '#38bdf8', borderRadius: [6, 6, 0, 0] },
        },
        {
          name: '装机量',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: props.stats.by_year.map((item) => Number(item.value.toFixed(2))),
          itemStyle: { color: '#f59e0b' },
          lineStyle: { width: 3, color: '#f59e0b' },
          areaStyle: {
            color: 'rgba(245, 158, 11, 0.12)',
          },
        },
      ],
    });
    charts.push(trendChart);
  }
}

watch(() => props.query.keyword, syncKeywordInput);

watch(
  () => [props.stats, props.loading.stats, props.showCharts],
  async () => {
    await nextTick();
    initCharts();
  },
  { deep: true },
);

onMounted(async () => {
  window.addEventListener('resize', handleResize);
  observer = new MutationObserver(async () => {
    isDarkTheme.value = document.documentElement.classList.contains('dark');
    await nextTick();
    initCharts();
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  await nextTick();
  initCharts();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  observer?.disconnect();
  disposeCharts();
});
</script>

<template>
  <div class="w-full space-y-8">
    <section
      v-if="showSummary"
      class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
    >
      <article
        v-for="card in summaryCards"
        :key="card.title"
        class="rounded-3xl border border-slate-200 p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md dark:border-slate-800"
        :class="card.tone"
      >
        <p class="text-sm text-slate-500 dark:text-dark-text/60">{{ card.title }}</p>
        <p class="mt-3 text-3xl font-semibold" :class="card.accent">{{ card.value }}</p>
      </article>
    </section>

    <div
      v-if="showSummary && errors.stats"
      class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"
    >
      {{ errors.stats }}
    </div>

    <section
      v-if="showFilters"
      class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-dark-card"
    >
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-emerald-600 dark:text-emerald-300">Panel Data</p>
          <h3 class="mt-2 text-2xl font-semibold text-slate-900 dark:text-dark-text">筛选与检索</h3>
          <p class="mt-2 text-sm text-slate-500 dark:text-dark-text/60">
            统一查看省市年度面板数据，联动地图、图表和明细表格。
          </p>
        </div>
        <div class="flex items-center gap-3">
          <button
            class="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:text-emerald-600 dark:border-slate-700 dark:text-dark-text/80 dark:hover:border-emerald-400 dark:hover:text-emerald-300"
            @click="$emit('reload')"
          >
            刷新数据
          </button>
        </div>
      </div>

      <div
        v-if="errors.filters"
        class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"
      >
        {{ errors.filters }}
      </div>

      <div class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        <label class="space-y-2">
          <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">省份</span>
          <select
            class="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-emerald-400 focus:bg-white dark:border-slate-700 dark:bg-slate-900/40 dark:text-dark-text"
            :disabled="loading.filters"
            :value="query.province ?? ''"
            @change="handleProvinceChange"
          >
            <option value="">全部省份</option>
            <option v-for="province in filters.provinces" :key="province" :value="province">
              {{ province }}
            </option>
          </select>
        </label>

        <label class="space-y-2">
          <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">城市</span>
          <select
            class="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-emerald-400 focus:bg-white disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900/40 dark:text-dark-text"
            :disabled="loading.filters || filters.cities.length === 0"
            :value="query.city ?? ''"
            @change="handleCityChange"
          >
            <option value="">全部城市</option>
            <option v-for="city in filters.cities" :key="city" :value="city">
              {{ city }}
            </option>
          </select>
        </label>

        <label class="space-y-2">
          <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">年份</span>
          <select
            class="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-emerald-400 focus:bg-white dark:border-slate-700 dark:bg-slate-900/40 dark:text-dark-text"
            :value="query.year ?? ''"
            @change="handleYearChange"
          >
            <option value="">全部年份</option>
            <option v-for="year in filters.years" :key="year" :value="year">
              {{ year }}
            </option>
          </select>
        </label>

        <label class="space-y-2 xl:col-span-2">
          <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">关键词</span>
          <div class="flex gap-3">
            <input
              v-model="keywordInput"
              type="text"
              placeholder="搜索省份、城市或年份"
              class="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-emerald-400 focus:bg-white dark:border-slate-700 dark:bg-slate-900/40 dark:text-dark-text"
              @keyup.enter="handleKeywordSearch"
            />
            <button
              class="rounded-2xl bg-emerald-500 px-5 py-3 text-sm font-medium text-white transition hover:bg-emerald-600"
              @click="handleKeywordSearch"
            >
              查询
            </button>
            <button
              class="rounded-2xl border border-slate-200 px-4 py-3 text-sm font-medium text-slate-700 transition hover:border-slate-300 dark:border-slate-700 dark:text-dark-text/80"
              @click="clearFilters"
            >
              重置
            </button>
          </div>
        </label>
      </div>
    </section>

    <section
      v-if="showCharts"
      class="grid grid-cols-1 gap-6 xl:grid-cols-2"
    >
      <article class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-dark-card">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">各省数据量分布</h4>
            <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">展示记录数最高的前 12 个省级区域</p>
          </div>
        </div>
        <div v-if="loading.stats" class="flex h-80 items-center justify-center text-sm text-slate-500 dark:text-dark-text/60">
          正在加载省份图表...
        </div>
        <div v-else-if="!hasStatsData" class="flex h-80 items-center justify-center rounded-2xl border border-dashed border-slate-200 text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60">
          暂无省份统计数据
        </div>
        <div v-else ref="provinceChartRef" class="h-80 w-full"></div>
      </article>

      <article class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-dark-card">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">年份趋势</h4>
            <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">按年份查看记录数量与光伏装机量变化</p>
          </div>
        </div>
        <div v-if="loading.stats" class="flex h-80 items-center justify-center text-sm text-slate-500 dark:text-dark-text/60">
          正在加载年份趋势...
        </div>
        <div v-else-if="!hasStatsData" class="flex h-80 items-center justify-center rounded-2xl border border-dashed border-slate-200 text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60">
          暂无年份统计数据
        </div>
        <div v-else ref="trendChartRef" class="h-80 w-full"></div>
      </article>
    </section>

    <section
      v-if="showTable"
      class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-dark-card"
    >
      <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">面板数据明细</h4>
          <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">
            {{ pageStart }} - {{ pageEnd }} / {{ formatInteger(tableData.total) }} 条
          </p>
        </div>
        <div class="flex items-center gap-3">
          <label class="text-sm text-slate-500 dark:text-dark-text/60">每页</label>
          <select
            class="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900/40 dark:text-dark-text"
            :value="query.page_size"
            @change="changePageSize"
          >
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </div>
      </div>

      <div
        v-if="errors.list"
        class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"
      >
        {{ errors.list }}
      </div>

      <div class="mt-5 overflow-x-auto">
        <table class="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-800">
          <thead class="bg-slate-50 text-slate-500 dark:bg-slate-900/50 dark:text-dark-text/60">
            <tr>
              <th class="px-4 py-3 font-medium">省份</th>
              <th class="px-4 py-3 font-medium">城市</th>
              <th class="px-4 py-3 font-medium">年份</th>
              <th class="px-4 py-3 font-medium">光伏装机量</th>
              <th class="px-4 py-3 font-medium">人均收入</th>
              <th class="px-4 py-3 font-medium">GDP</th>
              <th class="px-4 py-3 font-medium">PM2.5</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
            <tr v-if="loading.list">
              <td colspan="7" class="px-4 py-12 text-center text-sm text-slate-500 dark:text-dark-text/60">
                正在加载明细数据...
              </td>
            </tr>
            <tr v-else-if="tableData.items.length === 0">
              <td colspan="7" class="px-4 py-12 text-center text-sm text-slate-500 dark:text-dark-text/60">
                当前筛选条件下暂无数据
              </td>
            </tr>
            <tr
              v-for="item in tableData.items"
              v-else
              :key="item.id"
              class="transition hover:bg-slate-50/80 dark:hover:bg-slate-900/40"
            >
              <td class="px-4 py-3 font-medium text-slate-900 dark:text-dark-text">{{ item.province }}</td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ item.city }}</td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ item.year }}</td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">
                {{ formatNumber(item.pv_installed_capacity_wan_kw) }} 万千瓦
              </td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">
                {{ formatNumber(item.disposable_income_per_capita_yuan, 0) }} 元
              </td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">
                {{ formatNumber(item.gdp_100m_yuan) }} 亿元
              </td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">
                {{ formatNumber(item.pm25_annual_avg_ug_per_m3) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="mt-5 flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <p class="text-sm text-slate-500 dark:text-dark-text/60">
          第 {{ query.page }} / {{ totalPages }} 页
        </p>
        <div class="flex items-center gap-3">
          <button
            class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-dark-text/80"
            :disabled="!canPrevPage"
            @click="goToPage(query.page - 1)"
          >
            上一页
          </button>
          <button
            class="rounded-xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:text-dark-text/80"
            :disabled="!canNextPage"
            @click="goToPage(query.page + 1)"
          >
            下一页
          </button>
        </div>
      </div>
    </section>

    <section
      v-if="showToolkit"
      class="space-y-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-dark-card"
    >
      <div>
        <p class="text-sm uppercase tracking-[0.28em] text-slate-400">Toolkit</p>
        <h4 class="mt-2 text-xl font-semibold text-slate-900 dark:text-dark-text">业务辅助面板</h4>
      </div>

      <div class="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <WeatherRadiationPanel />
        <PovertyPanel />
      </div>

      <PolicyPanel @apply-price="onApplyPrice" />
      <CostPanel @apply-cost="onApplyCost" />
    </section>
  </div>
</template>
