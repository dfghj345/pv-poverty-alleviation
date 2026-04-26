<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';

import heroPhoto from '@/assets/photo.jpg';
import { getEnergyPoliciesApi, getPoliciesApi, type EnergyPolicyItem } from '@/api/policy';
import Calculator from '@/components/Calculator.vue';
import DataStats from '@/components/DataStats.vue';
import MapView from '@/components/MapView.vue';
import { useProjectMap } from '@/composables/useProjectMap';

const { mapData, handlePointClick, handleLocationPicked, handleLocationCleared } = useProjectMap();

const isDark = ref(false);
const highlightError = ref<string | null>(null);
const policyCount = ref(0);
const policyProvinceCount = ref(0);
const energyPolicyCount = ref(0);
const latestEnergyPolicy = ref<EnergyPolicyItem | null>(null);

const provinceCount = computed(() => {
  const provinces = new Set(
    mapData.value.features
      .map((feature) => feature.properties.province)
      .filter((value): value is string => Boolean(value)),
  );
  return provinces.size;
});

const mapHighlights = computed(() => [
  {
    title: '城市坐标点位',
    value: `${mapData.value.features.length} 个`,
    description:
      provinceCount.value > 0
        ? `来自 city_location_table，覆盖 ${provinceCount.value} 个省级区域`
        : '等待地图点位接口返回数据',
    accent: 'text-emerald-500',
  },
  {
    title: '政策电价记录',
    value: `${policyCount.value} 条`,
    description:
      policyProvinceCount.value > 0
        ? `policy_table 已覆盖 ${policyProvinceCount.value} 个省级样本`
        : 'policy_table 暂无可用记录',
    accent: 'text-cyan-500',
  },
  {
    title: '能源局政策动态',
    value: `${energyPolicyCount.value} 条`,
    description: latestEnergyPolicy.value
      ? `${latestEnergyPolicy.value.publish_date ?? '未知日期'} · ${latestEnergyPolicy.value.title}`
      : 'energy_policy_table 暂无可用记录',
    accent: 'text-amber-500',
  },
]);

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

async function loadMapHighlights(): Promise<void> {
  highlightError.value = null;
  try {
    const [policies, energyPolicies] = await Promise.all([
      getPoliciesApi({ limit: 2000 }),
      getEnergyPoliciesApi({ limit: 1000 }),
    ]);

    policyCount.value = policies.length;
    policyProvinceCount.value = new Set(policies.map((item) => item.province)).size;
    energyPolicyCount.value = energyPolicies.length;
    latestEnergyPolicy.value = energyPolicies[0] ?? null;
  } catch (error) {
    highlightError.value = error instanceof Error ? error.message : '地图摘要加载失败';
  }
}

onMounted(() => {
  if (localStorage.getItem('theme') === 'dark') {
    isDark.value = true;
    document.documentElement.classList.add('dark');
  }
  void loadMapHighlights();
});
</script>

<template>
  <div class="min-h-screen bg-gray-50 text-gray-800 dark:bg-dark-bg dark:text-dark-text transition-colors duration-300 font-sans">
    <nav class="fixed top-0 left-0 right-0 bg-white/90 dark:bg-dark-card/90 backdrop-blur-sm shadow-sm z-50 transition-all duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <span class="text-emerald-500 text-2xl mr-2">PV</span>
            <span class="text-xl font-bold text-gray-900 dark:text-dark-text">光伏扶贫决策系统</span>
          </div>
          <div class="hidden md:flex items-baseline space-x-4">
            <a href="#home" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">首页</a>
            <a href="#map" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">地图</a>
            <a href="#dashboard" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">数据看板</a>
            <a href="#calculator" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">收益测算</a>
            <button @click="toggleTheme" class="px-3 py-2 rounded-md hover:text-emerald-500 transition-colors text-xl">
              {{ isDark ? '深色' : '浅色' }}
            </button>
          </div>
        </div>
      </div>
    </nav>

    <section id="home" class="pt-28 pb-16 bg-gradient-to-br from-emerald-500/5 to-cyan-500/5 dark:from-emerald-500/10 dark:to-cyan-500/10">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col md:flex-row items-center">
          <div class="md:w-1/2 mb-8 md:mb-0">
            <h1 class="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 dark:text-dark-text leading-tight text-shadow">
              阳光变成收益
              <br />
              <span class="text-emerald-500">光伏助力乡村振兴</span>
            </h1>
            <p class="mt-4 text-lg text-gray-700 dark:text-dark-text/80 max-w-lg">
              基于真实政策、电价、天气辐射和区域数据，联动地图展示、数据看板与收益测算，帮助我们快速验证光伏扶贫项目的落点与回报。
            </p>
            <div class="mt-8 flex gap-4">
              <a href="#dashboard" class="px-6 py-3 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 shadow-md transition-colors">查看数据看板</a>
              <a href="#calculator" class="px-6 py-3 bg-white dark:bg-dark-card text-emerald-600 dark:text-emerald-400 border border-emerald-500 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-dark-bg shadow-md transition-colors">进入收益测算</a>
            </div>
          </div>
          <div class="md:w-1/2 w-full">
            <img :src="heroPhoto" alt="光伏项目航拍图" class="rounded-xl shadow-2xl w-full h-64 md:h-80 object-cover" />
          </div>
        </div>
      </div>
    </section>

    <section id="map" class="py-16 bg-white dark:bg-dark-card transition-colors duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center text-gray-900 dark:text-dark-text mb-12">全国点位分布</h2>
        <div class="bg-gray-50 dark:bg-dark-bg rounded-xl shadow-lg p-6 border border-gray-100 dark:border-gray-800">
          <div class="mb-6 rounded-xl overflow-hidden shadow-inner border border-gray-200 dark:border-gray-700">
            <MapView
              :points="mapData"
              @point-click="handlePointClick"
              @location-picked="handleLocationPicked"
              @location-cleared="handleLocationCleared"
            />
          </div>

          <div v-if="highlightError" class="mb-4 text-sm text-red-600 dark:text-red-400">
            {{ highlightError }}
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div
              v-for="item in mapHighlights"
              :key="item.title"
              class="bg-white dark:bg-dark-card rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700 card-hover"
            >
              <h3 class="font-bold mb-2" :class="item.accent">{{ item.title }}</h3>
              <p class="text-2xl font-semibold text-gray-900 dark:text-dark-text">{{ item.value }}</p>
              <p class="mt-2 text-gray-600 dark:text-dark-text/70 text-sm leading-relaxed">
                {{ item.description }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="dashboard" class="py-16 bg-gray-50 dark:bg-dark-bg transition-colors duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center text-gray-900 dark:text-dark-text mb-12">核心数据看板</h2>
        <DataStats />
      </div>
    </section>

    <section id="calculator" class="py-16 bg-white dark:bg-dark-card transition-colors duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center text-gray-900 dark:text-dark-text mb-12">收益仿真测算</h2>
        <div class="max-w-6xl mx-auto">
          <Calculator />
        </div>
      </div>
    </section>

    <footer class="bg-gray-900 text-white py-10">
      <div class="container mx-auto px-4 text-center">
        <div class="flex items-center justify-center mb-4">
          <span class="text-emerald-500 text-2xl mr-2">PV</span>
          <span class="text-xl font-bold tracking-wider">光伏扶贫数据平台</span>
        </div>
        <p class="text-gray-400 text-sm">2026 光伏扶贫项目演示环境</p>
      </div>
    </footer>
  </div>
</template>

<style>
html {
  scroll-behavior: smooth;
}

.card-hover {
  transition: all 0.3s ease;
}

.card-hover:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
}
</style>
