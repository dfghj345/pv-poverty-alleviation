<script setup lang="ts">
import { markRaw, onMounted, onUnmounted, ref } from 'vue';
import * as echarts from 'echarts';

import { getDashboardStatsApi, type DashboardStats } from '@/api/project';
import AutoFillPanel from '@/components/AutoFillPanel.vue';
import CostPanel from '@/components/CostPanel.vue';
import GenerationPanel from '@/components/GenerationPanel.vue';
import PolicyPanel from '@/components/PolicyPanel.vue';
import PovertyPanel from '@/components/PovertyPanel.vue';
import WeatherRadiationPanel from '@/components/WeatherRadiationPanel.vue';
import { useProjectStore } from '@/store/project';

const stats = ref<DashboardStats>({
  total_capacity_mw: 0,
  annual_generation_yi: 0,
  farmers_benefited: 0,
  carbon_reduction_wt: 0,
  revenue_years: ['1年', '5年', '10年', '15年', '20年'],
  revenue_data: [0, 0, 0, 0, 0],
  province_distribution: [],
});

const loading = ref(false);
const errorMsg = ref<string | null>(null);
const lineChartRef = ref<HTMLElement | null>(null);
const pieChartRef = ref<HTMLElement | null>(null);
const charts: echarts.ECharts[] = [];
const isDarkTheme = ref(document.documentElement.classList.contains('dark'));
const projectStore = useProjectStore();

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
    const data = await getDashboardStatsApi();
    stats.value = data;
    initCharts();
  } catch (error) {
    console.error('加载看板统计数据失败', error);
    errorMsg.value = error instanceof Error ? error.message : '加载看板统计数据失败';
  } finally {
    loading.value = false;
  }
}

function initCharts(): void {
  charts.forEach((chart) => chart.dispose());
  charts.length = 0;

  const textColor = isDarkTheme.value ? '#F9FAFB' : '#1F2937';
  const splitLineColor = isDarkTheme.value ? '#374151' : '#E5E7EB';

  if (lineChartRef.value) {
    const chart = markRaw(echarts.init(lineChartRef.value));
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      grid: { left: '5%', right: '5%', bottom: '10%', top: '15%', containLabel: true },
      xAxis: {
        type: 'category',
        data: stats.value.revenue_years,
        axisLabel: { color: textColor },
        axisLine: { lineStyle: { color: splitLineColor } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: textColor },
        splitLine: { lineStyle: { color: splitLineColor } },
      },
      series: [
        {
          data: stats.value.revenue_data,
          type: 'line',
          smooth: true,
          color: '#10b981',
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
              { offset: 1, color: 'rgba(16, 185, 129, 0.05)' },
            ]),
          },
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
          name: '省份占比',
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
          {{ stats.total_capacity_mw }}<span class="text-lg text-emerald-500 ml-1">MW</span>
        </h3>
      </div>
      <div class="bg-cyan-50 dark:bg-cyan-900/20 rounded-xl p-6 shadow-sm border border-cyan-100 dark:border-cyan-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">年发电量</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">
          {{ stats.annual_generation_yi }}<span class="text-lg text-cyan-500 ml-1">亿度</span>
        </h3>
      </div>
      <div class="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-6 shadow-sm border border-amber-100 dark:border-amber-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">覆盖人口</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">
          {{ stats.farmers_benefited }}<span class="text-lg text-amber-500 ml-1">人</span>
        </h3>
      </div>
      <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-6 shadow-sm border border-emerald-100 dark:border-emerald-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">年减排量</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">
          {{ stats.carbon_reduction_wt }}<span class="text-lg text-emerald-500 ml-1">万吨</span>
        </h3>
      </div>
    </div>

    <div v-if="loading" class="mb-6 text-sm text-gray-500 dark:text-dark-text/60">
      正在加载看板数据...
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text mb-2">20 年收益走势</h3>
        <div ref="lineChartRef" class="w-full h-72"></div>
      </div>
      <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text mb-2">省份分布</h3>
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
