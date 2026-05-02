<script setup lang="ts">
import { defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue';

import heroPhoto from '@/assets/photo.jpg';
import {
  getPanelDataFiltersApi,
  getPanelDataListApi,
  getPanelDataStatsApi,
  type PanelDataFilters,
  type PanelDataItem,
  type PanelDataListParams,
  type PanelDataPage,
  type PanelDataStats,
} from '@/api/panel_data';
import { buildAggregateKey, type PanelDataMapAggregate, useProjectMap } from '@/composables/useProjectMap';

const DataStats = defineAsyncComponent(() => import('@/components/DataStats.vue'));
const MapView = defineAsyncComponent(() => import('@/components/MapView.vue'));
const AutoFillPanel = defineAsyncComponent(() => import('@/components/AutoFillPanel.vue'));
const Calculator = defineAsyncComponent(() => import('@/components/Calculator.vue'));

type QueryState = Required<Pick<PanelDataListParams, 'page' | 'page_size'>> & Omit<PanelDataListParams, 'page' | 'page_size'>;

const {
  mapData,
  mapViewport,
  selectedMapData,
  mapLoading,
  mapError,
  loadMapData,
  selectAggregateItem,
} = useProjectMap();

const isDark = ref(false);
const isMobileNavOpen = ref(false);
const panelStats = ref<PanelDataStats | null>(null);
const panelFilters = ref<PanelDataFilters>({
  provinces: [],
  cities: [],
  years: [],
});
const panelTable = ref<PanelDataPage>({
  items: [],
  total: 0,
  page: 1,
  page_size: 20,
});
const selectedPanelRecord = ref<PanelDataItem | null>(null);
const selectedRecordLoading = ref(false);
const selectedRecordError = ref<string | null>(null);

const query = ref<QueryState>({
  page: 1,
  page_size: 20,
  province: undefined,
  city: undefined,
  year: undefined,
  keyword: undefined,
});

const statsLoading = ref(false);
const filtersLoading = ref(false);
const listLoading = ref(false);

const statsError = ref<string | null>(null);
const filtersError = ref<string | null>(null);
const listError = ref<string | null>(null);
const mobileToolTargets = new Set(['weather-section', 'poverty-section', 'policy-section', 'cost-section', 'generation-section']);
const mobileNavItems: Array<{ label: string; target: string }> = [
  { label: '数据总览', target: 'data-stats' },
  { label: '地图展示', target: 'map-section' },
  { label: '天气与辐射', target: 'weather-section' },
  { label: '自动填参', target: 'autofill-section' },
  { label: '收益测算', target: 'calculator-section' },
  { label: '政策信息', target: 'policy-section' },
  { label: '成本分析', target: 'cost-section' },
  { label: '发电量分析', target: 'generation-section' },
  { label: '贫困地区数据', target: 'poverty-section' },
];

function hasOwn<K extends keyof QueryState>(patch: Partial<QueryState>, key: K): boolean {
  return Object.prototype.hasOwnProperty.call(patch, key);
}

function matchesSelection(item: PanelDataItem, selection: PanelDataMapAggregate): boolean {
  return item.province === selection.province && item.city === selection.city && item.year === selection.year;
}

function toggleTheme(): void {
  isMobileNavOpen.value = false;
  isDark.value = !isDark.value;
  const html = document.documentElement;

  if (isDark.value) {
    html.classList.add('dark');
    localStorage.setItem('theme', 'dark');
    return;
  }

  html.classList.remove('dark');
  localStorage.setItem('theme', 'light');
}

function toggleMobileNav(): void {
  isMobileNavOpen.value = !isMobileNavOpen.value;
}

function closeMobileNav(): void {
  isMobileNavOpen.value = false;
}

function scrollToSection(target: string): void {
  let resolvedTarget = target;
  closeMobileNav();

  if (window.innerWidth < 768 && mobileToolTargets.has(target)) {
    window.dispatchEvent(new CustomEvent('mobile-tool-target', { detail: target }));
    resolvedTarget = 'tools-mobile-section';
  }

  const element = document.getElementById(resolvedTarget);

  if (!element) {
    return;
  }

  window.setTimeout(() => {
    element.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  }, 60);
}

async function loadStats(): Promise<void> {
  statsLoading.value = true;
  statsError.value = null;

  try {
    panelStats.value = await getPanelDataStatsApi();
  } catch (error) {
    statsError.value = error instanceof Error ? error.message : '统计数据加载失败';
    panelStats.value = null;
  } finally {
    statsLoading.value = false;
  }
}

async function loadFilters(province?: string): Promise<void> {
  filtersLoading.value = true;
  filtersError.value = null;

  try {
    panelFilters.value = await getPanelDataFiltersApi({ province });

    if (query.value.city && !panelFilters.value.cities.includes(query.value.city)) {
      query.value = {
        ...query.value,
        city: undefined,
      };
    }

    if (query.value.year && !panelFilters.value.years.includes(query.value.year)) {
      query.value = {
        ...query.value,
        year: undefined,
      };
    }
  } catch (error) {
    filtersError.value = error instanceof Error ? error.message : '筛选项加载失败';
    panelFilters.value = {
      provinces: [],
      cities: [],
      years: [],
    };
  } finally {
    filtersLoading.value = false;
  }
}

async function loadList(): Promise<void> {
  listLoading.value = true;
  listError.value = null;

  try {
    panelTable.value = await getPanelDataListApi({
      page: query.value.page,
      page_size: query.value.page_size,
      province: query.value.province,
      city: query.value.city,
      year: query.value.year,
      keyword: query.value.keyword,
    });
  } catch (error) {
    listError.value = error instanceof Error ? error.message : '列表数据加载失败';
    panelTable.value = {
      items: [],
      total: 0,
      page: query.value.page,
      page_size: query.value.page_size,
    };
  } finally {
    listLoading.value = false;
  }
}

async function loadMap(): Promise<void> {
  await loadMapData({
    province: query.value.province,
    city: query.value.city,
    year: query.value.year,
    keyword: query.value.keyword,
  });
}

async function loadSelectedRecord(selection: PanelDataMapAggregate | null): Promise<void> {
  selectedRecordError.value = null;

  if (!selection) {
    selectedPanelRecord.value = null;
    selectedRecordLoading.value = false;
    return;
  }

  selectedPanelRecord.value =
    panelTable.value.items.find((item) => matchesSelection(item, selection)) ?? null;
  selectedRecordLoading.value = true;

  try {
    const detailPage = await getPanelDataListApi({
      page: 1,
      page_size: 1,
      province: selection.province,
      city: selection.city,
      year: selection.year,
    });
    selectedPanelRecord.value = detailPage.items[0] ?? selectedPanelRecord.value;
  } catch (error) {
    selectedRecordError.value = error instanceof Error ? error.message : '选中数据详情加载失败';
  } finally {
    selectedRecordLoading.value = false;
  }
}

async function initializeDashboard(): Promise<void> {
  await Promise.all([
    loadStats(),
    loadFilters(query.value.province),
    loadList(),
    loadMap(),
  ]);
}

async function handleQueryChange(patch: Partial<QueryState>): Promise<void> {
  const provinceChanged = hasOwn(patch, 'province') && patch.province !== query.value.province;
  const filterChanged =
    provinceChanged ||
    hasOwn(patch, 'city') ||
    hasOwn(patch, 'year') ||
    hasOwn(patch, 'keyword');
  const pageSizeChanged = hasOwn(patch, 'page_size') && patch.page_size !== query.value.page_size;

  const nextQuery: QueryState = {
    ...query.value,
    ...patch,
  };

  if (provinceChanged) {
    nextQuery.city = undefined;
  }

  if ((filterChanged || pageSizeChanged) && !hasOwn(patch, 'page')) {
    nextQuery.page = 1;
  }

  query.value = nextQuery;

  if (provinceChanged) {
    await loadFilters(nextQuery.province);
  }

  await Promise.all([loadList(), loadMap()]);
}

async function reloadPanelData(): Promise<void> {
  await Promise.all([
    loadStats(),
    loadFilters(query.value.province),
    loadList(),
    loadMap(),
  ]);
}

function handleAggregateClick(aggregate: PanelDataMapAggregate): void {
  selectAggregateItem(aggregate);
}

watch(
  () => (selectedMapData.value ? buildAggregateKey(selectedMapData.value) : ''),
  async () => {
    await loadSelectedRecord(selectedMapData.value);
  },
);

watch(isMobileNavOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : '';
});

onMounted(() => {
  if (localStorage.getItem('theme') === 'dark') {
    isDark.value = true;
    document.documentElement.classList.add('dark');
  }

  void initializeDashboard();
});

onUnmounted(() => {
  document.body.style.overflow = '';
});
</script>

<template>
  <div class="min-h-screen overflow-x-clip bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),_transparent_34%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.14),_transparent_32%),linear-gradient(180deg,_#effcf3_0%,_#ecfeff_46%,_#f8fafc_100%)] text-slate-900 transition-colors duration-300 dark:bg-dark-bg dark:text-dark-text">
    <nav class="sticky top-0 z-50 border-b border-emerald-100/80 bg-white/85 shadow-[0_8px_24px_rgba(15,118,110,0.08)] backdrop-blur-xl transition-all duration-300 dark:border-slate-800 dark:bg-dark-card/90">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <button
              type="button"
              class="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-2xl border border-emerald-100 bg-white/90 p-2 text-slate-700 shadow-[0_8px_24px_rgba(15,118,110,0.1)] transition hover:border-emerald-300 hover:bg-emerald-50/80 hover:text-emerald-700 dark:border-slate-700 dark:bg-dark-card dark:text-dark-text md:hidden"
              :aria-expanded="isMobileNavOpen"
              aria-controls="mobile-nav-drawer"
              aria-label="切换导航"
              @click="toggleMobileNav"
            >
              <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </button>
            <span class="text-base font-semibold tracking-[-0.02em] text-slate-800 dark:text-dark-text sm:text-lg">光伏扶贫数据平台</span>
          </div>
          <div class="hidden items-center gap-1 md:flex lg:gap-2">
            <a href="#home" class="rounded-full px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-emerald-50 hover:text-emerald-700 dark:text-dark-text/70">首页</a>
            <a href="#data-stats" class="rounded-full px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-emerald-50 hover:text-emerald-700 dark:text-dark-text/70">数据总览</a>
            <a href="#map-section" class="rounded-full px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-emerald-50 hover:text-emerald-700 dark:text-dark-text/70">地图展示</a>
            <a href="#calculator-section" class="rounded-full px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-emerald-50 hover:text-emerald-700 dark:text-dark-text/70">收益测算</a>
            <a href="#analytics-section" class="rounded-full px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-emerald-50 hover:text-emerald-700 dark:text-dark-text/70">数据工具</a>
            <button
              class="apple-pill-secondary min-h-[40px] px-4 py-2"
              @click="toggleTheme"
            >
              {{ isDark ? '浅色' : '深色' }}
            </button>
          </div>
        </div>
      </div>
    </nav>

    <div
      v-if="isMobileNavOpen"
      class="fixed inset-0 z-[60] md:hidden"
      aria-modal="true"
      role="dialog"
    >
      <button
        type="button"
        class="absolute inset-0 h-full w-full bg-slate-900/30 backdrop-blur-sm"
        aria-label="关闭导航菜单"
        @click="closeMobileNav"
      ></button>
      <aside
        id="mobile-nav-drawer"
        class="touch-scroll absolute left-0 top-0 flex h-full w-[min(86vw,360px)] max-w-full flex-col overflow-y-auto border-r border-emerald-100/80 bg-[linear-gradient(180deg,rgba(255,255,255,0.97),rgba(240,253,250,0.94))] px-5 pb-6 pt-20 shadow-[0_20px_40px_rgba(15,118,110,0.14)] dark:border-slate-800 dark:bg-dark-card"
      >
        <div class="flex items-start justify-between gap-4 border-b border-emerald-100/80 pb-5 dark:border-slate-800">
          <div>
            <p class="text-xs uppercase tracking-[0.28em] text-emerald-600 dark:text-emerald-300">Quick Menu</p>
            <h2 class="mt-2 text-xl font-semibold text-slate-900 dark:text-dark-text">模块导航</h2>
            <p class="mt-2 text-sm text-slate-500 dark:text-dark-text/60">点击后会平滑滚动到对应模块。</p>
          </div>
          <button
            type="button"
            class="inline-flex min-h-[40px] min-w-[40px] items-center justify-center rounded-full border border-emerald-100 bg-white/90 text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-700 dark:border-slate-700 dark:bg-dark-card dark:text-dark-text/80"
            aria-label="关闭导航"
            @click="closeMobileNav"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 6l12 12M18 6 6 18" />
            </svg>
          </button>
        </div>

        <div class="mt-5 grid gap-3">
          <button
            v-for="item in mobileNavItems"
            :key="item.target"
            type="button"
            class="min-h-[48px] rounded-2xl border border-emerald-100/80 bg-white/90 px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50/80 hover:text-emerald-700 dark:border-slate-700 dark:bg-slate-900/50 dark:text-dark-text/80 dark:hover:bg-slate-900/70"
            @click="scrollToSection(item.target)"
          >
            {{ item.label }}
          </button>
        </div>

        <div class="mt-6 grid gap-3 border-t border-emerald-100/80 pt-5 dark:border-slate-800">
          <button
            type="button"
            class="min-h-[48px] rounded-full bg-emerald-600 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-emerald-700"
            @click="scrollToSection('home')"
          >
            返回首页首屏
          </button>
          <button
            type="button"
            class="min-h-[48px] rounded-full border border-emerald-200 bg-white/90 px-4 py-3 text-left text-sm font-medium text-emerald-700 transition hover:border-emerald-300 hover:bg-emerald-50 dark:border-slate-700 dark:bg-dark-card dark:text-dark-text/80 dark:hover:border-slate-600 dark:hover:text-dark-text"
            @click="toggleTheme"
          >
            切换到{{ isDark ? '浅色' : '深色' }}模式
          </button>
        </div>
      </aside>
    </div>

    <section id="home" class="bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),_transparent_34%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.14),_transparent_32%),linear-gradient(180deg,_#effcf3_0%,_#ecfeff_46%,_#f8fafc_100%)] pt-8 dark:bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.16),_transparent_34%),radial-gradient(circle_at_top_right,_rgba(14,165,233,0.16),_transparent_32%),linear-gradient(180deg,_rgba(15,23,42,0.95)_0%,_rgba(15,118,110,0.16)_100%)] sm:pt-10 md:pt-14 lg:pt-16">
      <div class="mx-auto max-w-7xl px-4 pb-12 sm:px-6 sm:pb-20 lg:px-8 lg:pb-28">
        <div class="mx-auto max-w-md md:hidden">
          <div class="relative overflow-hidden rounded-[28px] border border-emerald-200/40 bg-[linear-gradient(135deg,rgba(15,118,110,0.94),rgba(14,165,233,0.76))] shadow-[0_22px_56px_rgba(15,118,110,0.18)]">
            <!-- 放大后的照片 -->
            <img
              :src="heroPhoto"
              alt="光伏扶贫项目"
              class="h-[470px] w-full object-cover object-center"
            />

            <!-- 图片遮罩，保证文字清晰 -->
            <div class="absolute inset-0 bg-gradient-to-b from-emerald-950/44 via-slate-900/10 to-slate-950/34"></div>

            <!-- 顶部文字 -->
            <div class="absolute inset-x-0 top-0 px-6 pt-8 text-center">
              <p class="text-[11px] font-medium tracking-[0.12em] text-white/70">
                光伏扶贫数据平台
              </p>

              <h1 class="mt-4 text-[2.35rem] font-semibold leading-[1.08] tracking-[-0.02em] text-white drop-shadow-[0_6px_18px_rgba(0,0,0,0.26)]">
              阳光变成收益
              <br />
              光伏助力乡村振兴
              </h1>
            </div>

            <!-- 底部说明文字 -->
            <div class="absolute inset-x-0 bottom-0 px-5 pb-5">
              <div class="rounded-2xl border border-white/24 bg-white/16 px-4 py-3.5 text-center text-white shadow-[0_14px_36px_rgba(0,0,0,0.14)] backdrop-blur-xl">
                <p class="text-[13px] leading-6 text-white/88">
                基于真实政策、电价、天气辐射和区域数据，联动地图展示、数据看板与收益测算，快速验证光伏扶贫项目的落点与回报。
                </p>

              <div class="mt-3 flex items-center justify-center gap-2 text-[10px] text-white/68">
                <span>数据驱动</span>
                <span class="h-1 w-1 rounded-full bg-white/50"></span>
                <span>地图联动</span>
                <span class="h-1 w-1 rounded-full bg-white/50"></span>
                <span>收益测算</span>
              </div>
            </div>
          </div>
        </div>
      </div>

        <div class="hidden items-center gap-10 md:grid lg:grid-cols-[minmax(0,1fr)_minmax(380px,0.92fr)] lg:gap-16 xl:gap-20">
          <div>
            <p class="text-sm font-semibold uppercase tracking-[0.3em] text-emerald-600 dark:text-emerald-300">光伏扶贫数据平台</p>
            <h1 class="mt-5 max-w-4xl text-5xl font-semibold leading-[0.96] tracking-[-0.04em] text-slate-900 dark:text-dark-text xl:text-6xl">
              阳光变成收益
              <br />
              光伏助力乡村振兴
            </h1>
            <p class="mt-6 max-w-xl text-lg leading-8 text-slate-600 dark:text-dark-text/72">
              基于真实政策、电价、天气辐射和区域数据，联动地图展示、数据看板与收益测算，帮助快速验证光伏扶贫项目的落点与回报。
            </p>
            <div class="mt-10 hidden gap-4 md:flex md:flex-wrap">
              <a href="#data-stats" class="apple-pill-primary px-6">
                查看数据看板
              </a>
              <a href="#map-section" class="apple-pill-secondary px-6">
                浏览地图聚合
              </a>
            </div>
          </div>

          <div class="relative mx-auto w-full max-w-xl lg:mx-0 lg:max-w-none">
            <div class="absolute -left-8 top-10 h-36 w-36 rounded-full bg-emerald-400/16 blur-3xl"></div>
            <div class="absolute -bottom-8 right-2 h-40 w-40 rounded-full bg-cyan-400/16 blur-3xl"></div>
            <div class="apple-card relative overflow-hidden p-4 lg:p-5">
              <div class="relative aspect-[3/2] w-full overflow-hidden rounded-2xl ring-1 ring-emerald-100/80">
                <img
                :src="heroPhoto"
                alt="光伏扶贫项目"
                class="h-full w-full object-cover"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="data-stats" class="scroll-mt-24 py-14 sm:scroll-mt-28 sm:py-16 lg:py-24">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="mb-8 flex flex-col gap-4 lg:mb-12 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-emerald-600">Overview</p>
            <h2 class="apple-section-title mt-2">顶部统计与筛选</h2>
          </div>
          <p class="apple-section-copy apple-compact-copy max-w-2xl">
            按省份、城市、年份与关键词联动筛选，地图和测算会同步更新。
          </p>
        </div>

        <DataStats
          :stats="panelStats"
          :filters="panelFilters"
          :table-data="panelTable"
          :query="query"
          :loading="{ stats: statsLoading, filters: filtersLoading, list: listLoading }"
          :errors="{ stats: statsError, filters: filtersError, list: listError }"
          :show-charts="false"
          :show-table="false"
          :show-toolkit="false"
          @query-change="handleQueryChange"
          @reload="reloadPanelData"
        />
      </div>
    </section>

    <section id="map-section" class="scroll-mt-24 pb-14 sm:scroll-mt-28 sm:pb-16 lg:pb-24">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="mb-8 flex flex-col gap-4 lg:mb-12 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-cyan-600">Spatial View</p>
            <h2 class="apple-section-title mt-2">地图与聚合列表</h2>
          </div>
          <p class="apple-section-copy apple-compact-copy max-w-2xl">
            查看地图点位与省市聚合，快速定位可分析区域。
          </p>
        </div>

        <div class="apple-card overflow-hidden p-4 sm:p-6 lg:p-8">
          <MapView
            :items="mapData"
            :selected-key="selectedMapData ? buildAggregateKey(selectedMapData) : null"
            :viewport="mapViewport"
            :loading="mapLoading"
            :error-message="mapError"
            @aggregate-click="handleAggregateClick"
          />
        </div>
      </div>
    </section>

    <section id="autofill-section" class="scroll-mt-24 pb-14 sm:scroll-mt-28 sm:pb-16 lg:pb-24">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="mb-8 flex flex-col gap-4 lg:mb-12 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-teal-600">Workflow</p>
            <h2 class="apple-section-title mt-2">自动填参</h2>
          </div>
          <p class="apple-section-copy apple-compact-copy max-w-2xl">
            把地图、政策、天气和成本参数一键同步到测算。
          </p>
        </div>
        <AutoFillPanel
          :selected-data="selectedMapData"
          :selected-record="selectedPanelRecord"
          :detail-loading="selectedRecordLoading"
          :detail-error="selectedRecordError"
        />
      </div>
    </section>

    <section id="calculator-section" class="scroll-mt-24 pb-14 sm:scroll-mt-28 sm:pb-16 lg:pb-24">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="mb-8 flex flex-col gap-4 lg:mb-12 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-emerald-600">Simulator</p>
            <h2 class="apple-section-title mt-2">收益仿真测算</h2>
          </div>
          <p class="apple-section-copy apple-compact-copy max-w-2xl">
            带入装机量、电价、成本与利用小时，快速验证项目收益。
          </p>
        </div>
        <Calculator />
      </div>
    </section>

    <section id="analytics-section" class="pb-16 sm:pb-20 lg:pb-24">
      <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div class="mb-8 flex flex-col gap-4 lg:mb-12 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-cyan-600">Analytics</p>
            <h2 class="apple-section-title mt-2">图表与明细</h2>
          </div>
          <p class="apple-section-copy apple-compact-copy max-w-2xl">
            集中查看图表、分页明细和政策成本等辅助数据。
          </p>
        </div>

        <DataStats
          :stats="panelStats"
          :filters="panelFilters"
          :table-data="panelTable"
          :query="query"
          :loading="{ stats: statsLoading, filters: filtersLoading, list: listLoading }"
          :errors="{ stats: statsError, filters: filtersError, list: listError }"
          :show-summary="false"
          :show-filters="false"
          @query-change="handleQueryChange"
          @reload="reloadPanelData"
        />
      </div>
    </section>

    <footer class="border-t border-emerald-200/60 bg-[linear-gradient(135deg,#0f766e_0%,#0f172a_100%)] py-10 text-white dark:border-slate-800">
      <div class="container mx-auto px-4 text-center">
        <div class="flex items-center justify-center gap-2">
          <span class="text-2xl font-semibold text-emerald-400">PV</span>
          <span class="text-lg font-semibold tracking-wide">光伏扶贫数据平台</span>
        </div>
        <p class="mt-3 text-sm text-slate-400">由真实 panel_data 数据驱动的前端展示与分析页面</p>
      </div>
    </footer>
  </div>
</template>
