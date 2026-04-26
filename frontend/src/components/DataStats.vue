<script setup lang="ts">
import { markRaw, onMounted, onUnmounted, ref, computed } from 'vue';
import * as echarts from 'echarts';

import {
  getGenerationSummaryApi,
  type GenerationSummary,
} from '@/api/generation';
import AutoFillPanel from '@/components/AutoFillPanel.vue';
import CostPanel from '@/components/CostPanel.vue';
import GenerationPanel from '@/components/GenerationPanel.vue';
import PolicyPanel from '@/components/PolicyPanel.vue';
import PovertyPanel from '@/components/PovertyPanel.vue';
import WeatherRadiationPanel from '@/components/WeatherRadiationPanel.vue';
import { useProjectStore } from '@/store/project';

const stats = ref<GenerationSummary>({
  total_installed_capacity_kw: 0,
  total_annual_generation_kwh: 0,
  total_annual_income_yuan: 0,
  province_count: 0,
  city_count: 0,
  county_count: 0,
  yearly_trend: [],
  province_distribution: [],
});

const loading = ref(false);
const errorMsg = ref<string | null>(null);
const lineChartRef = ref<HTMLElement | null>(null);
const pieChartRef = ref<HTMLElement | null>(null);
const charts: echarts.ECharts[] = [];
const isDarkTheme = ref(document.documentElement.classList.contains('dark'));
const projectStore = useProjectStore();

const noGenerationData = computed(
  () =>
    stats.value.total_installed_capacity_kw === 0 &&
    stats.value.total_annual_generation_kwh === 0 &&
    stats.value.total_annual_income_yuan === 0,
);

let observer: MutationObserver | null = null;

function onApplyPrice(payload: { province: string; electricity_price: number }): void {
  projectStore.setAppliedPolicy(payload);
}

function onApplyCost(payload: { province: string | null; unit_cost_yuan_per_kw: number }): void {
  projectStore.setAppliedCost(payload);
}

async function fetchDashboardData(): Promise<void> {
  loading.value = true;
  errorMsg.value = null;
  try {
    const data = await getGenerationSummaryApi();
    stats.value = data;
    initCharts();
  } catch (error) {
    console.error('加载发电摘要数据失败', error);
    errorMsg.value = error instanceof Error ? error.message : '加载发电摘要数据失败';
  } finally {
    loading.value = false;
  }
}

function initCharts(): void {
  charts.forEach((chart) => chart.dispose());
  charts.length = 0;

  if (noGenerationData.value) {
    return;
  }

  const textColor = isDarkTheme.value ? '#F9FAFB' : '#1F2937';
  const splitLineColor = isDarkTheme.value ? '#374151' : '#E5E7EB';

  const years = stats.value.yearly_trend.map((item) => item.year);
  const installedData = stats.value.yearly_trend.map((item) => item.installed_capacity_kw);
  const generationData = stats.value.yearly_trend.map((item) => item.annual_generation_kwh);
  const incomeData = stats.value.yearly_trend.map((item) => item.annual_income_yuan / 100000000);

  if (lineChartRef.value) {
    const chart = markRaw(echarts.init(lineChartRef.value));
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: {
        top: '8%',
        textStyle: { color: textColor },
      },
      grid: { left: '5%', right: '10%', bottom: '12%', top: '18%', containLabel: true },
      xAxis: {
        type: 'category',
        data: years,
        axisLabel: { color: textColor },
        axisLine: { lineStyle: { color: splitLineColor } },
      },
      yAxis: [
        {
          type: 'value',
          name: '装机(kW)/发电(kWh)',
          axisLabel: { color: textColor },
          splitLine: { lineStyle: { color: splitLineColor } },
        },
        {
          type: 'value',
          name: '年收益(亿元)',
          axisLabel: { color: textColor },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '装机容量(kW)',
          data: installedData,
          type: 'line',
          smooth: true,
          color: '#10b981',
        },
        {
          name: '年发电量(kWh)',
          data: generationData,
          type: 'line',
          smooth: true,
          color: '#06b6d4',
        },
        {
          name: '年收益(亿元)',
          data: incomeData,
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          color: '#f59e0b',
        },
      ],
    });
    charts.push(chart);
  }

  if (pieChartRef.value) {
    const chart = markRaw(echarts.init(pieChartRef.value));
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item' },
      legend: { top: '5%', left: 'center', textStyle: { color: textColor } },
      series: [
        {
          name: '省份装机',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['50%', '60%'],
          itemStyle: {
            borderRadius: 8,
            borderColor: isDarkTheme.value ? '#374151' : '#ffffff',
            borderWidth: 2,
          },
          data: stats.value.province_distribution,
        },
      ],
    });
    charts.push(chart);
  }
}

function handleResize(): void {
  charts.forEach((chart) => chart.resize());
}

onMounted(() => {
  window.addEventListener('resize', handleResize);
  observer = new MutationObserver(() => {
    const currentTheme = document.documentElement.classList.contains('dark');
    if (isDarkTheme.value !== currentTheme) {
      isDarkTheme.value = currentTheme;
      initCharts();
    }
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  void fetchDashboardData();
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  observer?.disconnect();
  charts.forEach((chart) => chart.dispose());
});
</script>

<template>
  <div class="w-full">
    <div v-if="errorMsg" class="mb-6 text-sm text-red-600 dark:text-red-400">
      {{ errorMsg }}
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-6 shadow-sm border border-emerald-100 dark:border-emerald-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">总装机容量</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">
          {{ (stats.total_installed_capacity_kw / 1000).toFixed(2) }}<span class="text-lg text-emerald-500 ml-1">MW</span>
        </h3>
      </div>
      <div class="bg-cyan-50 dark:bg-cyan-900/20 rounded-xl p-6 shadow-sm border border-cyan-100 dark:border-cyan-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">年发电量</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">
          {{ (stats.total_annual_generation_kwh / 100000000).toFixed(2) }}<span class="text-lg text-cyan-500 ml-1">亿度</span>
        </h3>
      </div>
      <div class="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-6 shadow-sm border border-amber-100 dark:border-amber-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">年收益</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">
          {{ (stats.total_annual_income_yuan / 100000000).toFixed(2) }}<span class="text-lg text-amber-500 ml-1">亿元</span>
        </h3>
      </div>
      <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-6 shadow-sm border border-emerald-100 dark:border-emerald-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">覆盖省份</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">
          {{ stats.province_count }}<span class="text-lg text-emerald-500 ml-1">个</span>
        </h3>
      </div>
    </div>

    <div v-if="loading" class="mb-6 text-sm text-gray-500 dark:text-dark-text/60">
      正在加载发电摘要数据...
    </div>

    <div v-if="!loading && noGenerationData" class="mb-6 text-sm text-gray-500 dark:text-dark-text/60">
      暂无发电测算数据，请运行 data_pipeline 并确认 /v1/generation/summary 接口可用。
    </div>

    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text mb-2">年度发电趋势</h3>
        <div ref="lineChartRef" class="w-full h-72"></div>
      </div>
      <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text mb-2">省份装机分布</h3>
        <div ref="pieChartRef" class="w-full h-72"></div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
      <WeatherRadiationPanel />
      <PovertyPanel />
    </div>

    <div class="mt-8">
      <PolicyPanel @apply-price="onApplyPrice" />
    </div>

    <div class="mt-8">
      <CostPanel @apply-cost="onApplyCost" />
    </div>

    <div class="mt-8">
      <AutoFillPanel />
    </div>

    <div class="mt-8">
      <GenerationPanel />
    </div>
  </div>
</template>
