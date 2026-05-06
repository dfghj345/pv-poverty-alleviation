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
import { useMobilePager } from '@/composables/useMobilePager';
import { useProjectStore } from '@/store/project';

const WeatherRadiationPanel = defineAsyncComponent(() => import('@/components/WeatherRadiationPanel.vue'));
const PovertyPanel = defineAsyncComponent(() => import('@/components/PovertyPanel.vue'));
const PolicyPanel = defineAsyncComponent(() => import('@/components/PolicyPanel.vue'));
const CostPanel = defineAsyncComponent(() => import('@/components/CostPanel.vue'));
const GenerationPanel = defineAsyncComponent(() => import('@/components/GenerationPanel.vue'));

type QueryState = Required<Pick<PanelDataListParams, 'page' | 'page_size'>> & Omit<PanelDataListParams, 'page' | 'page_size'>;
type MobileToolKey = 'weather' | 'poverty' | 'policy' | 'cost' | 'generation';

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
const containerRef = ref<HTMLElement | null>(null);
const keywordInput = ref(props.query.keyword ?? '');
const provinceChartRef = ref<HTMLElement | null>(null);
const trendChartRef = ref<HTMLElement | null>(null);
const charts: echarts.ECharts[] = [];
const isDarkTheme = ref(document.documentElement.classList.contains('dark'));
const isCompactLayout = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false);
const showMobileFilters = ref(false);
const showMobileAdvancedFilters = ref(false);
const showMobileTable = ref(false);
const isMobileToolPanelOpen = ref(false);
const activeMobileTool = ref<MobileToolKey>('weather');
const mobileToolItems: Array<{ key: MobileToolKey; label: string; caption: string }> = [
  { key: 'weather', label: '天气与辐射', caption: '查天气与利用小时' },
  { key: 'poverty', label: '贫困地区数据', caption: '看人口与收入标签' },
  { key: 'policy', label: '政策信息', caption: '查电价与补贴口径' },
  { key: 'cost', label: '成本分析', caption: '查单位造价区间' },
  { key: 'generation', label: '发电量分析', caption: '看项目发电表现' },
];
const mobileTableSource = computed(() => props.tableData.items);
const {
  page: mobileTablePage,
  totalPages: mobileTableTotalPages,
  pagedItems: mobileTableItems,
  canPrev: canPrevMobileTablePage,
  canNext: canNextMobileTablePage,
  next: nextMobileTablePage,
  prev: prevMobileTablePage,
  onTouchStart: onMobileTableTouchStart,
  onTouchEnd: onMobileTableTouchEnd,
} = useMobilePager(mobileTableSource, 1);

const summaryCards = computed(() => [
  {
    title: '总记录数',
    value: formatInteger(props.stats?.total_count ?? 0),
    accent: 'text-emerald-600 dark:text-emerald-300',
    tone: 'border-emerald-200/80 bg-emerald-50/85 dark:border-emerald-500/20 dark:bg-emerald-500/10',
  },
  {
    title: '覆盖省份',
    value: formatInteger(props.stats?.province_count ?? 0),
    accent: 'text-cyan-600 dark:text-cyan-300',
    tone: 'border-cyan-200/80 bg-cyan-50/85 dark:border-cyan-500/20 dark:bg-cyan-500/10',
  },
  {
    title: '覆盖城市',
    value: formatInteger(props.stats?.city_count ?? 0),
    accent: 'text-amber-600 dark:text-amber-300',
    tone: 'border-amber-200/80 bg-amber-50/85 dark:border-amber-500/20 dark:bg-amber-500/10',
  },
  {
    title: '覆盖年份',
    value: formatInteger(props.stats?.year_count ?? 0),
    accent: 'text-rose-500 dark:text-rose-300',
    tone: 'border-rose-200/80 bg-rose-50/80 dark:border-rose-500/20 dark:bg-rose-500/10',
  },
]);

const hasStatsData = computed(() => (props.stats?.total_count ?? 0) > 0);
const totalPages = computed(() => Math.max(1, Math.ceil(props.tableData.total / props.query.page_size)));
const canPrevPage = computed(() => props.query.page > 1);
const canNextPage = computed(() => props.query.page < totalPages.value);
const pageStart = computed(() => (props.tableData.total === 0 ? 0 : (props.query.page - 1) * props.query.page_size + 1));
const pageEnd = computed(() => Math.min(props.tableData.total, props.query.page * props.query.page_size));
const activeMobileToolMeta = computed(() => mobileToolItems.find((item) => item.key === activeMobileTool.value) ?? mobileToolItems[0]);
const provinceInsight = computed(() => {
  const topProvince = props.stats?.by_province?.[0];
  return topProvince
    ? `${topProvince.province} 当前记录量最高，共 ${formatInteger(topProvince.count)} 条。`
    : '优先关注记录量更集中的省份。';
});
const trendInsight = computed(() => {
  const latestYear = props.stats?.by_year?.[props.stats.by_year.length - 1];
  return latestYear
    ? `${latestYear.year} 年装机量约 ${formatNumber(latestYear.value)} 万千瓦。`
    : '通过年度趋势识别装机变化。';
});

let observer: MutationObserver | null = null;
let resizeObserver: ResizeObserver | null = null;

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

function formatProvinceAxisLabel(value: string): string {
  const shortName = value
    .replace(/维吾尔自治区|壮族自治区|回族自治区|特别行政区|自治区|省|市/g, '')
    .slice(0, 2);
  return shortName.split('').join('\n');
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

function selectMobileTool(key: MobileToolKey): void {
  activeMobileTool.value = key;
  isMobileToolPanelOpen.value = true;
}

function closeMobileToolPanel(): void {
  isMobileToolPanelOpen.value = false;
}

function handleMobileToolTarget(event: Event): void {
  const target = (event as CustomEvent<string>).detail;
  const targetMap: Record<string, MobileToolKey> = {
    'weather-section': 'weather',
    'poverty-section': 'poverty',
    'policy-section': 'policy',
    'cost-section': 'cost',
    'generation-section': 'generation',
  };
  const nextTool = targetMap[target];
  if (!nextTool) {
    return;
  }
  activeMobileTool.value = nextTool;
  isMobileToolPanelOpen.value = true;
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
  isCompactLayout.value = window.innerWidth < 768;
  charts.forEach((chart) => chart.resize());
}

function initCharts(): void {
  disposeCharts();

  if (!props.showCharts || !hasStatsData.value || !props.stats) {
    return;
  }

  const isCompact = isCompactLayout.value;
  const textColor = isDarkTheme.value ? '#F8FAFC' : '#0F172A';
  const splitLineColor = isDarkTheme.value ? '#334155' : '#E2E8F0';

  if (provinceChartRef.value) {
    const provinceChart = markRaw(echarts.init(provinceChartRef.value));
    provinceChart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, confine: true },
      grid: {
        left: isCompact ? '9%' : '5%',
        right: isCompact ? '6%' : '4%',
        top: isCompact ? '12%' : '12%',
        bottom: isCompact ? '26%' : '18%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: props.stats.by_province.slice(0, 12).map((item) => item.province),
        axisLabel: {
          color: textColor,
          formatter: formatProvinceAxisLabel,
          interval: 0,
          lineHeight: isCompact ? 12 : 14,
          fontSize: isCompact ? 11 : 12,
        },
        axisLine: { lineStyle: { color: splitLineColor } },
      },
      yAxis: {
        type: 'value',
        name: '记录数',
        axisLabel: { color: textColor, fontSize: isCompact ? 10 : 12 },
        nameTextStyle: { color: textColor, fontSize: isCompact ? 11 : 12 },
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
      tooltip: { trigger: 'axis', confine: true },
      grid: {
        left: isCompact ? '9%' : '5%',
        right: isCompact ? '9%' : '4%',
        top: isCompact ? '14%' : '12%',
        bottom: isCompact ? '24%' : '14%',
        containLabel: true,
      },
      legend: {
        top: isCompact ? 'auto' : '2%',
        bottom: isCompact ? 0 : 'auto',
        textStyle: { color: textColor, fontSize: isCompact ? 11 : 12 },
      },
      xAxis: {
        type: 'category',
        data: props.stats.by_year.map((item) => item.year),
        axisLabel: { color: textColor, fontSize: isCompact ? 10 : 12 },
        axisLine: { lineStyle: { color: splitLineColor } },
      },
      yAxis: [
        {
          type: 'value',
          name: '记录数',
          axisLabel: { color: textColor, fontSize: isCompact ? 10 : 12 },
          nameTextStyle: { color: textColor, fontSize: isCompact ? 11 : 12 },
          splitLine: { lineStyle: { color: splitLineColor } },
        },
        {
          type: 'value',
          name: '装机量（万千瓦）',
          axisLabel: { color: textColor, fontSize: isCompact ? 10 : 12 },
          nameTextStyle: { color: textColor, fontSize: isCompact ? 11 : 12 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '记录数',
          type: 'bar',
          data: props.stats.by_year.map((item) => item.count),
          barMaxWidth: isCompact ? 18 : 24,
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
  window.addEventListener('mobile-tool-target', handleMobileToolTarget as EventListener);
  resizeObserver = new ResizeObserver(() => {
    handleResize();
  });
  if (containerRef.value) {
    resizeObserver.observe(containerRef.value);
  }
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
  window.removeEventListener('mobile-tool-target', handleMobileToolTarget as EventListener);
  resizeObserver?.disconnect();
  observer?.disconnect();
  disposeCharts();
});
</script>

<template>
  <div ref="containerRef" class="w-full space-y-6 sm:space-y-8 lg:space-y-12">
    <section
      v-if="showSummary"
      class="grid grid-cols-2 gap-2 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5"
    >
      <article
        v-for="card in summaryCards"
        :key="card.title"
        class="apple-card p-3.5 transition hover:-translate-y-0.5 sm:p-4 lg:p-6"
        :class="card.tone"
      >
        <p class="text-xs text-slate-500 dark:text-dark-text/60 sm:text-sm">{{ card.title }}</p>
        <p class="mt-2 text-lg font-semibold tracking-[-0.03em] sm:text-2xl lg:mt-4 lg:text-4xl" :class="card.accent">{{ card.value }}</p>
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
      class="apple-card p-4 sm:p-6 lg:p-8"
    >
      <div class="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p class="text-sm uppercase tracking-[0.28em] text-emerald-600 dark:text-emerald-300">Panel Data</p>
          <h3 class="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-900 dark:text-dark-text lg:text-[2rem]">筛选与检索</h3>
          <p class="mt-3 text-sm text-slate-500 dark:text-dark-text/60 lg:max-w-2xl lg:text-base lg:leading-7">
            统一查看省市年份面板数据，联动地图、图表和明细表格。          </p>
        </div>
        <div class="flex items-center gap-3">
          <button
            class="apple-pill-secondary w-full sm:w-auto"
            @click="$emit('reload')"
          >
            刷新数据
          </button>
        </div>
      </div>

      <div class="mt-4 md:hidden">
        <button
          type="button"
          class="apple-pill-secondary w-full justify-center"
          @click="showMobileFilters = !showMobileFilters"
        >
          {{ showMobileFilters ? '收起筛选条件' : '筛选条件' }}
        </button>
      </div>

      <div
        v-if="errors.filters"
        class="mt-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-300"
      >
        {{ errors.filters }}
      </div>

      <div v-if="showMobileFilters" class="mt-4 grid grid-cols-1 gap-3 md:hidden">
        <label class="space-y-2">
          <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">省份</span>
          <select
            class="apple-input w-full"
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
            class="apple-input w-full disabled:cursor-not-allowed disabled:opacity-60"
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

        <div class="grid grid-cols-2 gap-3">
          <button
            type="button"
            class="apple-pill-secondary w-full"
            @click="showMobileAdvancedFilters = !showMobileAdvancedFilters"
          >
            {{ showMobileAdvancedFilters ? '收起高级条件' : '高级条件' }}
          </button>
          <button
            type="button"
            class="apple-pill-secondary w-full"
            @click="clearFilters"
          >
            重置
          </button>

        </div>
        <div v-if="showMobileAdvancedFilters" class="grid grid-cols-1 gap-3">
          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">年份</span>
            <select
              class="apple-input w-full"
              :value="query.year ?? ''"
              @change="handleYearChange"
            >
              <option value="">全部年份</option>
              <option v-for="year in filters.years" :key="year" :value="year">
                {{ year }}
              </option>
            </select>
          </label>

          <label class="space-y-2">
            <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">关键词</span>
            <input
              v-model="keywordInput"
              type="text"
              placeholder="搜索省份、城市或年份"
              class="apple-input w-full"
              @keyup.enter="handleKeywordSearch"
            />
          </label>

          <button
            type="button"
            class="apple-pill-primary w-full"
            @click="handleKeywordSearch"
          >
            查询
          </button>
      </div>
      </div>

      <div class="mt-4 hidden gap-3 md:mt-6 md:grid md:grid-cols-2 md:gap-4 xl:grid-cols-5">
        <label class="space-y-2">
          <span class="text-sm font-medium text-slate-700 dark:text-dark-text/80">省份</span>
          <select
            class="apple-input w-full"
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
            class="apple-input w-full disabled:cursor-not-allowed disabled:opacity-60"
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
            class="apple-input w-full"
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
          <div class="flex flex-col gap-3 sm:flex-row">
            <input
              v-model="keywordInput"
              type="text"
              placeholder="搜索省份、城市或年份"
              class="apple-input w-full"
              @keyup.enter="handleKeywordSearch"
            />
            <button
              class="apple-pill-primary w-full sm:w-auto"
              @click="handleKeywordSearch"
            >
              查询
            </button>
            <button
              class="apple-pill-secondary w-full sm:w-auto"
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
      class="grid grid-cols-1 gap-4 xl:grid-cols-2 xl:gap-6"
    >
      <article class="apple-card overflow-hidden p-4 sm:p-6 lg:p-8">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">各省数据量分布</h4>
            <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">展示记录数最高的前 12 个省级区域</p>
          </div>
        </div>
        <div v-if="loading.stats" class="flex h-72 items-center justify-center text-sm text-slate-500 dark:text-dark-text/60 sm:h-80 lg:h-[380px]">
          正在加载省份图表...
        </div>
        <div v-else-if="!hasStatsData" class="flex h-72 items-center justify-center rounded-2xl border border-dashed border-emerald-200/80 bg-white/70 text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60 sm:h-80 lg:h-[380px]">
          暂无省份统计数据
        </div>
        <div v-else ref="provinceChartRef" class="h-72 w-full sm:h-80 lg:h-[380px]"></div>
        <p v-if="hasStatsData" class="mt-4 text-xs font-medium text-slate-400 dark:text-dark-text/50">
          {{ provinceInsight }}
        </p>
      </article>

      <article class="apple-card overflow-hidden p-4 sm:p-6 lg:p-8">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">年份趋势</h4>
            <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">按年份查看记录数量与装机量变化</p>
          </div>
        </div>
        <div v-if="loading.stats" class="flex h-72 items-center justify-center text-sm text-slate-500 dark:text-dark-text/60 sm:h-80 lg:h-[380px]">
          正在加载年份趋势...
        </div>
        <div v-else-if="!hasStatsData" class="flex h-72 items-center justify-center rounded-2xl border border-dashed border-emerald-200/80 bg-white/70 text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60 sm:h-80 lg:h-[380px]">
          暂无年份统计数据
        </div>
        <div v-else ref="trendChartRef" class="h-72 w-full sm:h-80 lg:h-[380px]"></div>
        <p v-if="hasStatsData" class="mt-4 text-xs font-medium text-slate-400 dark:text-dark-text/50">
          {{ trendInsight }}
        </p>
      </article>
    </section>

    <section
      v-if="showTable"
      class="apple-card stable-table-card p-4 sm:p-6 lg:p-8"
    >
      <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h4 class="text-lg font-semibold text-slate-900 dark:text-dark-text">面板数据明细</h4>
          <p class="mt-1 text-sm text-slate-500 dark:text-dark-text/60">
            {{ pageStart }} - {{ pageEnd }} / {{ formatInteger(tableData.total) }} 条</p>
        </div>
        <div class="flex items-center gap-3">
          <label class="text-sm text-slate-500 dark:text-dark-text/60">每页</label>
          <select
            class="apple-input rounded-xl px-3 py-2"
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

      <div class="mt-4 md:hidden">
        <button
          type="button"
          class="apple-pill-secondary w-full justify-center"
          @click="showMobileTable = !showMobileTable"
        >
          {{ showMobileTable ? '收起明细数据' : '查看明细数据' }}
        </button>
      </div>

      <div
        v-if="showMobileTable"
        class="mt-5 max-h-[520px] space-y-3 overflow-y-auto pr-1 md:hidden"
        @touchstart.passive="onMobileTableTouchStart"
        @touchend.passive="onMobileTableTouchEnd"
      >
        <div v-if="loading.list" class="rounded-2xl border border-dashed border-emerald-200/80 bg-white/70 px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60">
          正在加载明细数据...
        </div>
        <div v-else-if="tableData.items.length === 0" class="rounded-2xl border border-dashed border-emerald-200/80 bg-white/70 px-4 py-10 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-dark-text/60">
          当前筛选条件下暂无数据
        </div>
        <template v-else>
          <article
            v-for="item in mobileTableItems"
            :key="`mobile-${item.id}`"
            class="apple-subcard p-4"
          >
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900 dark:text-dark-text">{{ item.province }} {{ item.city }}</p>
                <p class="mt-1 text-xs text-slate-500 dark:text-dark-text/60">{{ item.year }} 年</p>
              </div>
              <span class="inline-flex rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                {{ formatNumber(item.pv_installed_capacity_wan_kw) }} 万千瓦</span>
            </div>

            <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div class="panel-soft-cell">
                <p class="text-xs text-slate-400">人均收入</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ formatNumber(item.disposable_income_per_capita_yuan, 0) }} 元</p>
              </div>
              <div class="panel-soft-cell">
                <p class="text-xs text-slate-400">GDP</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ formatNumber(item.gdp_100m_yuan) }} 亿元</p>
              </div>
              <div class="panel-soft-cell">
                <p class="text-xs text-slate-400">PM2.5</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ formatNumber(item.pm25_annual_avg_ug_per_m3) }}</p>
              </div>
              <div class="panel-soft-cell">
                <p class="text-xs text-slate-400">年份</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">{{ item.year }}</p>
              </div>
            </div>
          </article>

          <div class="apple-subcard flex items-center justify-between gap-3 px-3 py-2">
            <button
              type="button"
              class="panel-page-btn"
              :disabled="!canPrevMobileTablePage"
              @click="prevMobileTablePage"
            >
              上一页</button>
            <span class="text-sm text-slate-500 dark:text-dark-text/60">{{ mobileTablePage + 1 }} / {{ mobileTableTotalPages }}</span>
            <button
              type="button"
              class="panel-page-btn"
              :disabled="!canNextMobileTablePage"
              @click="nextMobileTablePage"
            >
              下一页</button>
          </div>
        </template>
      </div>

      <div class="panel-table-shell stable-table-body touch-scroll hidden md:block">
        <table class="min-w-full divide-y divide-slate-200 text-left text-sm dark:divide-slate-800">
          <thead class="panel-table-head">
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
              class="transition hover:bg-emerald-50/60 dark:hover:bg-slate-900/40"
            >
              <td class="px-4 py-3 font-medium text-slate-900 dark:text-dark-text">{{ item.province }}</td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ item.city }}</td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">{{ item.year }}</td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">
                {{ formatNumber(item.pv_installed_capacity_wan_kw) }} 万千瓦</td>
              <td class="px-4 py-3 text-slate-700 dark:text-dark-text/80">
                {{ formatNumber(item.disposable_income_per_capita_yuan, 0) }} 元</td>
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

      <div class="mt-5 flex flex-col gap-3 border-t border-emerald-100/80 pt-4 sm:flex-row sm:items-center sm:justify-between dark:border-slate-800">
        <p class="text-sm text-slate-500 dark:text-dark-text/60">
          第 {{ query.page }} / {{ totalPages }} 页</p>
        <div class="grid grid-cols-2 gap-3 sm:flex sm:items-center">
          <button
            class="panel-page-btn w-full sm:w-auto"
            :disabled="!canPrevPage"
            @click="goToPage(query.page - 1)"
          >
            上一页</button>
          <button
            class="panel-page-btn w-full sm:w-auto"
            :disabled="!canNextPage"
            @click="goToPage(query.page + 1)"
          >
            下一页</button>
        </div>
      </div>
    </section>

    <section
      v-if="showToolkit"
      class="space-y-8 lg:space-y-10"
    >
      <div>
        <p class="text-sm uppercase tracking-[0.28em] text-teal-600">Toolkit</p>
        <h4 class="mt-2 text-2xl font-semibold tracking-[-0.04em] text-slate-900 dark:text-dark-text lg:text-[2rem]">业务辅助面板</h4>
      </div>

      <div id="tools-mobile-section" class="space-y-4 md:hidden">
        <div v-if="!isMobileToolPanelOpen" class="apple-subcard p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-900 dark:text-dark-text">数据工具</p>
              <p class="apple-compact-copy mt-2">先选择一个工具，再查看表单、结果和应用动作。</p>
            </div>
          </div>

          <div class="mt-4 grid grid-cols-2 gap-3">
            <button
              v-for="tool in mobileToolItems"
              :key="tool.key"
              type="button"
              class="apple-subcard px-4 py-4 text-left transition hover:border-emerald-300 hover:bg-emerald-50/50 dark:hover:bg-slate-900/70"
              @click="selectMobileTool(tool.key)"
            >
              <span class="block text-sm font-medium text-slate-900 dark:text-dark-text">{{ tool.label }}</span>
              <span class="mt-1 block text-xs text-slate-500 dark:text-dark-text/60">{{ tool.caption }}</span>
            </button>
          </div>
        </div>

        <div v-else class="space-y-4">
          <div class="apple-subcard p-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-slate-900 dark:text-dark-text">{{ activeMobileToolMeta.label }}</p>
                <p class="apple-compact-copy mt-2">{{ activeMobileToolMeta.caption }}</p>
              </div>
              <button
                type="button"
                class="apple-pill-secondary min-h-[40px] px-4 py-2"
                @click="closeMobileToolPanel"
              >
                返回工具
              </button>
            </div>
          </div>

          <WeatherRadiationPanel v-if="activeMobileTool === 'weather'" />
          <PovertyPanel v-else-if="activeMobileTool === 'poverty'" />
          <PolicyPanel v-else-if="activeMobileTool === 'policy'" @apply-price="onApplyPrice" />
          <CostPanel v-else-if="activeMobileTool === 'cost'" @apply-cost="onApplyCost" />
          <GenerationPanel v-else />
        </div>
      </div>

      <div class="hidden grid-cols-1 items-start gap-6 md:grid lg:gap-8 xl:grid-cols-2">
        <div class="min-w-0">
          <WeatherRadiationPanel />
        </div>
        <section id="poverty-section" class="min-w-0 scroll-mt-24 sm:scroll-mt-28">
          <PovertyPanel />
        </section>

        <section id="policy-section" class="min-w-0 scroll-mt-24 sm:scroll-mt-28 xl:col-span-2">
          <PolicyPanel @apply-price="onApplyPrice" />
        </section>
        <section id="cost-section" class="min-w-0 scroll-mt-24 sm:scroll-mt-28">
          <CostPanel @apply-cost="onApplyCost" />
        </section>
        <section id="generation-section" class="min-w-0 scroll-mt-24 sm:scroll-mt-28">
          <GenerationPanel />
        </section>
      </div>
    </section>
  </div>
</template>
