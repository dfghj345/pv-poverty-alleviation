<script setup lang="ts">
import { computed } from 'vue';
import { useROICalculator } from '@/composables/useROICalculator';
import { useROIChart } from '@/composables/useROIChart';

const { form, loading, errorMsg, result, submit, hasResult, buttonLabel, chartData, lastAppliedPolicy, lastAppliedWeather } = useROICalculator();
const { chartRef } = useROIChart(() => chartData.value);

const irrDisplay = computed(() => (result.value?.irr != null ? (result.value.irr * 100).toFixed(2) + '%' : '—'));
const npvDisplay = computed(() => result.value?.npv?.toFixed(2) ?? '—');
</script>

<template>
  <div class="bg-gray-50 dark:bg-dark-bg rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 p-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
    
    <div class="lg:col-span-5 space-y-5">
      <div class="flex items-center gap-2 mb-6">
        <div class="w-2 h-6 bg-emerald-500 rounded-full"></div>
        <h2 class="text-xl font-bold text-gray-900 dark:text-dark-text">参数配置</h2>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">装机容量 (kW)</label>
          <input v-model.number="form.capacity_kw" type="number" class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-colors bg-white dark:bg-dark-card dark:text-dark-text" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">利用小时 (h)</label>
          <input v-model.number="form.equivalent_hours" type="number" class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-colors bg-white dark:bg-dark-card dark:text-dark-text" />
          <p v-if="lastAppliedWeather" class="mt-1 text-xs text-gray-500 dark:text-dark-text/60">
            已应用天气：
            <span v-if="lastAppliedWeather.province || lastAppliedWeather.city">
              {{ lastAppliedWeather.province ?? '-' }} {{ lastAppliedWeather.city ?? '-' }}
            </span>
            <span v-else>
              ({{ lastAppliedWeather.latitude }}, {{ lastAppliedWeather.longitude }})
            </span>
            ，利用小时={{ lastAppliedWeather.equivalent_hours }}
          </p>
        </div>
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">总投资额 (元)</label>
          <input v-model.number="form.total_investment" type="number" class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-colors bg-white dark:bg-dark-card dark:text-dark-text" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">电价 (元/kWh)</label>
          <input v-model.number="form.electricity_price" type="number" step="0.01" class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-colors bg-white dark:bg-dark-card dark:text-dark-text" />
          <p v-if="lastAppliedPolicy" class="mt-1 text-xs text-gray-500 dark:text-dark-text/60">
            已应用政策：{{ lastAppliedPolicy.province }}，电价={{ lastAppliedPolicy.electricity_price }}
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">贷款比例</label>
          <input v-model.number="form.loan_ratio" type="number" step="0.1" class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-colors bg-white dark:bg-dark-card dark:text-dark-text" />
        </div>
      </div>

      <button :disabled="loading" @click="submit" class="mt-6 w-full py-3 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-600 transition-colors shadow-md flex justify-center items-center gap-2 disabled:opacity-70">
        <svg v-if="loading" class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        {{ buttonLabel }}
      </button>

      <div v-if="errorMsg" class="mt-3 text-sm text-red-600 dark:text-red-400">
        {{ errorMsg }}
      </div>

      <div v-if="hasResult" class="mt-6 p-4 bg-emerald-50 dark:bg-emerald-900/20 rounded-xl border border-emerald-100 dark:border-emerald-800/30">
        <div class="flex justify-between mb-2">
          <span class="text-gray-600 dark:text-dark-text/80">内部收益率 (IRR)</span>
          <span class="text-emerald-500 font-mono font-bold">{{ irrDisplay }}</span>
        </div>
        <div class="flex justify-between">
          <span class="text-gray-600 dark:text-dark-text/80">净现值 (NPV)</span>
          <span class="text-cyan-500 font-mono font-bold">¥{{ npvDisplay }}</span>
        </div>
      </div>
    </div>

    <div class="lg:col-span-7 bg-white dark:bg-dark-card rounded-xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 flex flex-col min-h-[450px]">
      <h3 class="text-lg font-bold text-gray-900 dark:text-dark-text mb-4">决策分析视图</h3>
      
      <div class="relative flex-1 w-full min-h-[350px]">
        
        <div 
          ref="chartRef" 
          class="absolute inset-0 transition-opacity duration-500"
          :style="{ opacity: hasResult ? 1 : 0, zIndex: hasResult ? 10 : 0 }"
        ></div>
        
        <div 
          v-if="!hasResult" 
          class="absolute inset-0 z-20 flex flex-col items-center justify-center text-gray-400 dark:text-gray-500 bg-white dark:bg-dark-card"
        >
          <div class="text-5xl mb-4">📊</div>
          <p>请输入左侧参数并点击计算以生成图表</p>
        </div>

      </div>
    </div>

  </div>
</template>
