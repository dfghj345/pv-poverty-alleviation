<script setup lang="ts">
import { defineAsyncComponent, onMounted, ref, watch } from 'vue';

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

function hasOwn<K extends keyof QueryState>(patch: Partial<QueryState>, key: K): boolean {
  return Object.prototype.hasOwnProperty.call(patch, key);
}

function matchesSelection(item: PanelDataItem, selection: PanelDataMapAggregate): boolean {
  return item.province === selection.province && item.city === selection.city && item.year === selection.year;
}

function toggleTheme(): void {
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

onMounted(() => {
  if (localStorage.getItem('theme') === 'dark') {
    isDark.value = true;
    document.documentElement.classList.add('dark');
  }

  void initializeDashboard();
});
</script>

<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 transition-colors duration-300 dark:bg-dark-bg dark:text-dark-text">
    <nav class="fixed left-0 right-0 top-0 z-50 border-b border-white/60 bg-white/85 shadow-sm backdrop-blur-sm transition-all duration-300 dark:border-slate-800 dark:bg-dark-card/90">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="text-lg font-semibold text-slate-900 dark:text-dark-text">光伏扶贫数据平台</span>
          </div>
          <div class="hidden items-center gap-2 md:flex">
            <a href="#home" class="rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-emerald-500 dark:text-dark-text/70">首页</a>
            <a href="#dashboard" class="rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-emerald-500 dark:text-dark-text/70">看板</a>
            <a href="#map" class="rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-emerald-500 dark:text-dark-text/70">地图</a>
            <a href="#calculator" class="rounded-full px-4 py-2 text-sm font-medium text-slate-600 transition hover:text-emerald-500 dark:text-dark-text/70">测算</a>
            <button
              class="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:text-emerald-600 dark:border-slate-700 dark:text-dark-text/80 dark:hover:border-emerald-400 dark:hover:text-emerald-300"
              @click="toggleTheme"
            >
              {{ isDark ? '浅色' : '深色' }}
            </button>
          </div>
        </div>
      </div>
    </nav>

    <section id="home" class="bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.18),_transparent_36%),linear-gradient(135deg,_rgba(14,165,233,0.08),_rgba(255,255,255,0.4))] pt-28 dark:bg-[radial-gradient(circle_at_top_left,_rgba(16,185,129,0.18),_transparent_36%),linear-gradient(135deg,_rgba(15,23,42,0.9),_rgba(2,6,23,0.98))]">
      <div class="container mx-auto px-4 pb-20 sm:px-6 lg:px-8">
        <div class="grid items-center gap-10 lg:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-emerald-600 dark:text-emerald-300">光伏扶贫数据平台</p>
            <h1 class="mt-5 max-w-3xl text-4xl font-semibold leading-tight text-slate-950 dark:text-dark-text md:text-5xl lg:text-6xl">
              阳光变成收益
              <br />
              光伏助力乡村振兴
            </h1>
            <p class="mt-6 max-w-2xl text-lg leading-8 text-slate-600 dark:text-dark-text/75">
              基于真实政策、电价、天气辐射和区域数据，联动地图展示、数据看板与收益测算，帮助我们快速验证光伏扶贫项目的落点与回报。
            </p>
            <div class="mt-8 flex flex-wrap gap-4">
              <a href="#dashboard" class="rounded-full bg-emerald-500 px-6 py-3 text-sm font-medium text-white shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-600">
                查看数据看板
              </a>
              <a href="#map" class="rounded-full border border-slate-300 bg-white/70 px-6 py-3 text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:text-emerald-600 dark:border-slate-700 dark:bg-slate-900/40 dark:text-dark-text/80">
                浏览地图聚合
              </a>
            </div>
          </div>

          <div class="relative">
            <div class="absolute -left-6 -top-6 h-32 w-32 rounded-full bg-emerald-400/20 blur-2xl"></div>
            <div class="absolute -bottom-8 right-0 h-36 w-36 rounded-full bg-cyan-400/20 blur-2xl"></div>
            <img
              :src="heroPhoto"
              alt="光伏扶贫项目"
              class="relative h-[340px] w-full rounded-[32px] object-cover shadow-2xl shadow-slate-900/10 ring-1 ring-white/60"
            />
          </div>
        </div>
      </div>
    </section>

    <section id="dashboard" class="py-16">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="mb-10 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-slate-400">Overview</p>
            <h2 class="mt-2 text-3xl font-semibold text-slate-950 dark:text-dark-text">顶部统计与筛选</h2>
          </div>
          <p class="max-w-2xl text-sm leading-7 text-slate-500 dark:text-dark-text/60">
            先看总体规模，再按省份、城市、年份和关键词联动筛选，后续地图、自动填参和收益测算会同步更新。
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

    <section id="map" class="pb-16">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="mb-10 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-slate-400">Spatial View</p>
            <h2 class="mt-2 text-3xl font-semibold text-slate-950 dark:text-dark-text">地图与聚合列表</h2>
          </div>
          <p class="max-w-2xl text-sm leading-7 text-slate-500 dark:text-dark-text/60">
            左侧展示地图点位，右侧展示省市聚合数据。即使后端没有经纬度，也会保留可选的聚合列表，不会中断页面。
          </p>
        </div>

        <div class="rounded-[32px] border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-dark-card">
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

    <section id="autofill" class="pb-16">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <AutoFillPanel
          :selected-data="selectedMapData"
          :selected-record="selectedPanelRecord"
          :detail-loading="selectedRecordLoading"
          :detail-error="selectedRecordError"
        />
      </div>
    </section>

    <section id="calculator" class="pb-16">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="mb-10 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-slate-400">Simulator</p>
            <h2 class="mt-2 text-3xl font-semibold text-slate-950 dark:text-dark-text">收益仿真测算</h2>
          </div>
          <p class="max-w-2xl text-sm leading-7 text-slate-500 dark:text-dark-text/60">
            自动填参同步过来的装机量、电价、成本与利用小时会直接带入测算表单，便于继续做投资收益验证。
          </p>
        </div>
        <Calculator />
      </div>
    </section>

    <section id="analytics" class="pb-16">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="mb-10 flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm uppercase tracking-[0.32em] text-slate-400">Analytics</p>
            <h2 class="mt-2 text-3xl font-semibold text-slate-950 dark:text-dark-text">图表与明细</h2>
          </div>
          <p class="max-w-2xl text-sm leading-7 text-slate-500 dark:text-dark-text/60">
            保留各省柱状图、年份趋势、分页表格和业务辅助面板，同时删除历史发电模块，避免页面重复。
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

    <footer class="border-t border-slate-200 bg-slate-950 py-10 text-white dark:border-slate-800">
      <div class="container mx-auto px-4 text-center">
        <div class="flex items-center justify-center gap-2">
          <span class="text-2xl font-semibold text-emerald-400">PV</span>
          <span class="text-lg font-semibold tracking-wide">光伏扶贫数据平台</span>
        </div>
        <p class="mt-3 text-sm text-slate-400">真实 panel_data 数据驱动的前端展示与分析页面</p>
      </div>
    </footer>
  </div>
</template>
