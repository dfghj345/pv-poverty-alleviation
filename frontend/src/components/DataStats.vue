<script setup lang="ts">
import { ref, onMounted, onUnmounted, markRaw } from 'vue';
import * as echarts from 'echarts';
import { getDashboardStatsApi } from '@/api/project';
import type { DashboardStats } from '@/api/project';
import WeatherRadiationPanel from '@/components/WeatherRadiationPanel.vue';
import PovertyPanel from '@/components/PovertyPanel.vue';
import PolicyPanel from '@/components/PolicyPanel.vue';
import CostPanel from '@/components/CostPanel.vue';
import GenerationPanel from '@/components/GenerationPanel.vue';
import AutoFillPanel from '@/components/AutoFillPanel.vue';
import { useProjectStore } from '@/store/project';

// 响应式 KPI 数据 (初始给 0)
const stats = ref<DashboardStats>({
  total_capacity_mw: 0,
  annual_generation_yi: 0,
  farmers_benefited: 0,
  carbon_reduction_wt: 0,
  revenue_years: ['1年', '5年', '10年', '15年', '20年'],
  revenue_data: [0, 0, 0, 0, 0],
  province_distribution: []
});

const lineChartRef = ref<HTMLElement | null>(null);
const pieChartRef = ref<HTMLElement | null>(null);
const charts: echarts.ECharts[] = [];
const isDarkTheme = ref(document.documentElement.classList.contains('dark'));
const projectStore = useProjectStore();

function onApplyPrice(payload: { province: string; electricity_price: number }): void {
  projectStore.setAppliedPolicy(payload);
}

function onApplyCost(payload: { province: string | null; unit_cost_yuan_per_kw: number }): void {
  projectStore.setAppliedCost(payload);
}

// 获取后端数据
const fetchDashboardData = async () => {
  try {
    const data = await getDashboardStatsApi();
    stats.value = data;
    // 数据拿到后，重绘图表
    initCharts();
  } catch (error) {
    console.error('加载大屏统计数据失败', error);
    // 失败时可以在此填充 mock 数据保证 UI 不空白
  }
};

const initCharts = () => {
  charts.forEach(chart => chart.dispose());
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
        data: stats.value.revenue_years, // 接入真实年份
        axisLabel: { color: textColor },
        axisLine: { lineStyle: { color: splitLineColor } }
      },
      yAxis: { type: 'value', axisLabel: { color: textColor }, splitLine: { lineStyle: { color: splitLineColor } } },
      series: [{ 
        data: stats.value.revenue_data,  // 接入真实预测数据
        type: 'line', smooth: true, color: '#10b981',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.05)' }
          ])
        }
      }]
    });
    charts.push(chart);
  }

  if (pieChartRef.value) {
    const chart = markRaw(echarts.init(pieChartRef.value));
    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item' },
      legend: { top: '5%', left: 'center', textStyle: { color: textColor } },
      series: [{
        name: '装机容量省份占比',
        type: 'pie', radius: ['40%', '70%'], center: ['50%', '60%'],
        itemStyle: { borderRadius: 8, borderColor: isDarkTheme.value ? '#374151' : '#ffffff', borderWidth: 2 },
        data: stats.value.province_distribution // 接入真实饼图数据
      }]
    });
    charts.push(chart);
  }
};

onMounted(() => {
  fetchDashboardData();
  const handleResize = () => charts.forEach(chart => chart.resize());
  window.addEventListener('resize', handleResize);
  
  const observer = new MutationObserver(() => {
    const currentTheme = document.documentElement.classList.contains('dark');
    if (isDarkTheme.value !== currentTheme) {
      isDarkTheme.value = currentTheme;
      initCharts();
    }
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

  onUnmounted(() => {
    window.removeEventListener('resize', handleResize);
    observer.disconnect();
  });
});
</script>

<template>
  <div class="w-full">
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-6 shadow-sm border border-emerald-100 dark:border-emerald-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">总装机容量</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">{{ stats.total_capacity_mw }}<span class="text-lg text-emerald-500 ml-1">MW</span></h3>
      </div>
      <div class="bg-cyan-50 dark:bg-cyan-900/20 rounded-xl p-6 shadow-sm border border-cyan-100 dark:border-cyan-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">年发电量</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">{{ stats.annual_generation_yi }}<span class="text-lg text-cyan-500 ml-1">亿度</span></h3>
      </div>
      <div class="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-6 shadow-sm border border-amber-100 dark:border-amber-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">惠及农户</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">{{ stats.farmers_benefited }}<span class="text-lg text-amber-500 ml-1">户</span></h3>
      </div>
      <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-6 shadow-sm border border-emerald-100 dark:border-emerald-800/30 card-hover">
        <p class="text-gray-600 dark:text-dark-text/70 text-sm font-medium">年减排量 (CO₂)</p>
        <h3 class="text-3xl font-bold text-gray-900 dark:text-dark-text mt-2">{{ stats.carbon_reduction_wt }}<span class="text-lg text-emerald-500 ml-1">万吨</span></h3>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text mb-2">20年收益预测</h3>
        <div ref="lineChartRef" class="w-full h-72"></div>
      </div>
      <div class="bg-white dark:bg-dark-card rounded-xl p-6 shadow-md border border-gray-100 dark:border-gray-800">
        <h3 class="text-xl font-bold text-gray-900 dark:text-dark-text mb-2">装机容量省份占比</h3>
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