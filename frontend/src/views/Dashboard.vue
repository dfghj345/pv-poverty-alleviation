<script setup lang="ts">
import { ref, onMounted } from 'vue';
import MapView from '@/components/MapView.vue';
import DataStats from '@/components/DataStats.vue';
import Calculator from '@/components/Calculator.vue';
import { useProjectMap } from '@/composables/useProjectMap';

const { mapData, handlePointClick } = useProjectMap();

// 深色模式切换逻辑
const isDark = ref(false);
const toggleTheme = () => {
  isDark.value = !isDark.value;
  const html = document.documentElement;
  if (isDark.value) {
    html.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  } else {
    html.classList.remove('dark');
    localStorage.setItem('theme', 'light');
  }
};

onMounted(() => {
  if (localStorage.getItem('theme') === 'dark') {
    isDark.value = true;
    document.documentElement.classList.add('dark');
  }
});
</script>

<template>
  <div class="min-h-screen bg-gray-50 text-gray-800 dark:bg-dark-bg dark:text-dark-text transition-colors duration-300 font-sans">
    
    <nav class="fixed top-0 left-0 right-0 bg-white/90 dark:bg-dark-card/90 backdrop-blur-sm shadow-sm z-50 transition-all duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <div class="flex items-center">
            <span class="text-emerald-500 text-2xl mr-2">☀️</span>
            <span class="text-xl font-bold text-gray-900 dark:text-dark-text">光伏扶贫决策系统</span>
          </div>
          <div class="hidden md:flex items-baseline space-x-4">
            <a href="#home" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">首页</a>
            <a href="#map" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">全国布局</a>
            <a href="#dashboard" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">核心数据</a>
            <a href="#calculator" class="px-3 py-2 rounded-md font-medium text-gray-700 dark:text-dark-text/80 hover:text-emerald-500 transition-colors">收益推演</a>
            <button @click="toggleTheme" class="px-3 py-2 rounded-md hover:text-emerald-500 transition-colors text-xl">
              {{ isDark ? '🌞' : '🌙' }}
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
              阳光变黄金<br>
              <span class="text-emerald-500">光伏助力乡村振兴</span>
            </h1>
            <p class="mt-4 text-lg text-gray-700 dark:text-dark-text/80 max-w-lg">
              光伏扶贫是创新的扶贫模式，通过在农村建设光伏发电站，将清洁能源转化为稳定收益，帮助贫困地区实现可持续发展。
            </p>
            <div class="mt-8 flex gap-4">
              <a href="#dashboard" class="px-6 py-3 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 shadow-md transition-colors">核心数据分析</a>
              <a href="#calculator" class="px-6 py-3 bg-white dark:bg-dark-card text-emerald-600 dark:text-emerald-400 border border-emerald-500 rounded-lg font-medium hover:bg-gray-50 dark:hover:bg-dark-bg shadow-md transition-colors">投资收益推演</a>
            </div>
          </div>
          <div class="md:w-1/2 w-full">
            <img 
              src="@/assets/photo.jpg" 
              alt="光伏航拍图" 
              class="rounded-xl shadow-2xl w-full h-64 md:h-80 object-cover" 
            />
          </div>
        </div>
      </div>
    </section>

    <section id="map" class="py-16 bg-white dark:bg-dark-card transition-colors duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center text-gray-900 dark:text-dark-text mb-12">全国项目分布</h2>
        <div class="bg-gray-50 dark:bg-dark-bg rounded-xl shadow-lg p-6 border border-gray-100 dark:border-gray-800">
          <div class="mb-6 rounded-xl overflow-hidden shadow-inner border border-gray-200 dark:border-gray-700">
            <MapView :points="mapData" @point-click="handlePointClick" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div class="bg-white dark:bg-dark-card rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700 card-hover">
              <h3 class="font-bold text-emerald-500 mb-2">云南光伏扶贫</h3>
              <p class="text-gray-600 dark:text-dark-text/70 text-sm leading-relaxed">总装机容量突破1947.8兆瓦，年发电量约33.5亿度，年产值达8.2亿元。</p>
            </div>
            <div class="bg-white dark:bg-dark-card rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700 card-hover">
              <h3 class="font-bold text-cyan-500 mb-2">山东沂南</h3>
              <p class="text-gray-600 dark:text-dark-text/70 text-sm leading-relaxed">全县44.9兆瓦项目全面并网，覆盖256处电站，惠及1.1万户困难家庭。</p>
            </div>
            <div class="bg-white dark:bg-dark-card rounded-lg p-5 shadow-sm border border-gray-100 dark:border-gray-700 card-hover">
              <h3 class="font-bold text-amber-500 mb-2">宁夏固原</h3>
              <p class="text-gray-600 dark:text-dark-text/70 text-sm leading-relaxed">建成并网分布式光伏16.5万千瓦，形成产业转型、农户增收的发展格局。</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="dashboard" class="py-16 bg-gray-50 dark:bg-dark-bg transition-colors duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center text-gray-900 dark:text-dark-text mb-12">核心数据分析</h2>
        <DataStats />
      </div>
    </section>

    <section id="calculator" class="py-16 bg-white dark:bg-dark-card transition-colors duration-300">
      <div class="container mx-auto px-4 sm:px-6 lg:px-8">
        <h2 class="text-3xl font-bold text-center text-gray-900 dark:text-dark-text mb-12">收益仿真推演引擎</h2>
        <div class="max-w-6xl mx-auto">
          <Calculator />
        </div>
      </div>
    </section>

    <footer class="bg-gray-900 text-white py-10">
      <div class="container mx-auto px-4 text-center">
        <div class="flex items-center justify-center mb-4">
          <span class="text-emerald-500 text-2xl mr-2">☀️</span>
          <span class="text-xl font-bold tracking-wider">企业级光伏扶贫决策系统</span>
        </div>
        <p class="text-gray-400 text-sm">© 2026 光伏扶贫数据平台 - 让阳光照亮乡村振兴之路</p>
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
  box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
}
</style>