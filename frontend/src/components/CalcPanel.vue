<script setup lang="ts">
import { computed } from 'vue';
import { useCalcPanel } from '@/composables/useCalcPanel';

const { formData, isCalculating, handleCalculate, buttonClass, buttonLabel } = useCalcPanel();

const priceDisplay = computed(() => formData.benchmark_price.toFixed(2));
</script>

<template>
  <div class="w-full max-w-2xl mx-auto bg-slate-900/90 backdrop-blur-xl border border-slate-700 rounded-2xl p-6 shadow-2xl text-slate-200">
    <div class="flex items-center gap-2 mb-4">
      <div class="w-1.5 h-5 bg-emerald-500 rounded-full"></div>
      <h2 class="text-lg font-bold">收益仿真推演引擎</h2>
    </div>

    <div class="grid grid-cols-2 gap-6 mb-6">
      <div>
        <div class="flex justify-between text-sm mb-2">
          <label class="text-slate-400">规划装机容量</label>
          <span class="text-emerald-400 font-mono">{{ formData.capacity_kw }} kW</span>
        </div>
        <input
          v-model.number="formData.capacity_kw"
          type="range"
          min="10"
          max="1000"
          step="10"
          class="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>
      <div>
        <div class="flex justify-between text-sm mb-2">
          <label class="text-slate-400">预估上网电价</label>
          <span class="text-emerald-400 font-mono">{{ priceDisplay }} 元/度</span>
        </div>
        <input
          v-model.number="formData.benchmark_price"
          type="range"
          min="0.1"
          max="1.0"
          step="0.01"
          class="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
        />
      </div>
    </div>

    <button
      type="button"
      :disabled="isCalculating"
      class="w-full py-3 rounded-xl font-semibold transition-all flex justify-center items-center gap-2"
      :class="buttonClass"
      @click="handleCalculate"
    >
      <svg v-if="isCalculating" class="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
      {{ buttonLabel }}
    </button>
  </div>
</template>
