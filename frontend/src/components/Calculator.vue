<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { useROICalculator } from '@/composables/useROICalculator';
import { useROIChart } from '@/composables/useROIChart';
import { useMobilePager } from '@/composables/useMobilePager';

const {
  form,
  calculating,
  errorMsg,
  result,
  submit,
  hasResult,
  hasAutoFillSelection,
  buttonLabel,
  chartData,
  lastAppliedPolicy,
  lastAppliedWeather,
} = useROICalculator();
const { chartRef, resize } = useROIChart(() => chartData.value);
const mobilePanel = ref<'form' | 'result'>('form');

const irrDisplay = computed(() => (result.value?.irr != null ? (result.value.irr * 100).toFixed(2) + '%' : '—'));
const npvDisplay = computed(() => result.value?.npv?.toFixed(2) ?? '—');
const lcoeDisplay = computed(() => result.value?.lcoe?.toFixed(4) ?? '—');
const annualCashFlowRows = computed(() => {
  const flows = result.value?.annual_cash_flows ?? [];
  let cumulative = 0;

  return flows.map((cashFlow, index) => {
    cumulative += cashFlow;
    return {
      year: index + 1,
      cashFlow,
      cumulative,
    };
  });
});
const {
  page: mobileCashFlowPage,
  totalPages: mobileCashFlowTotalPages,
  pagedItems: mobileCashFlowRows,
  canPrev: canPrevMobileCashFlowPage,
  canNext: canNextMobileCashFlowPage,
  next: nextMobileCashFlowPage,
  prev: prevMobileCashFlowPage,
  onTouchStart: onCashFlowTouchStart,
  onTouchEnd: onCashFlowTouchEnd,
} = useMobilePager(annualCashFlowRows, 1);

async function showResultPanel(): Promise<void> {
  if (window.innerWidth < 768) {
    mobilePanel.value = 'result';
  }

  await nextTick();
  window.setTimeout(() => {
    resize();
  }, 320);
}

async function handleSubmit(): Promise<void> {
  const success = await submit();
  if (!success) {
    return;
  }

  await showResultPanel();
}

function backToForm(): void {
  mobilePanel.value = 'form';
}
</script>

<template>
  <div class="min-w-0 apple-card overflow-hidden bg-white dark:bg-dark-card">
    <div
      class="flex w-[200%] transition-transform duration-300 ease-out md:block md:w-full md:transition-none lg:grid lg:grid-cols-12 lg:gap-8"
      :class="mobilePanel === 'result' ? '-translate-x-1/2 md:translate-x-0' : 'translate-x-0'"
    >
      <div class="min-w-0 w-1/2 shrink-0 space-y-5 p-4 sm:p-6 md:w-full lg:col-span-5 lg:p-9">
      <div class="mb-6 flex items-center gap-2">
        <div class="w-2 h-6 bg-emerald-500 rounded-full"></div>
        <h2 class="text-xl font-bold tracking-[-0.03em] text-gray-900 dark:text-dark-text lg:text-[2rem]">参数配置</h2>
      </div>

      <div
        v-if="!hasAutoFillSelection"
        class="rounded-xl border border-dashed border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 dark:border-slate-700 dark:bg-dark-card dark:text-dark-text/60"
      >
        请选择地图聚合数据后可自动填参，也可以手动输入参数进行测算。
      </div>

      <form class="grid grid-cols-1 gap-4 sm:grid-cols-2" @submit.prevent="handleSubmit">
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">装机容量 (kW)</label>
          <input v-model.number="form.capacity_kw" type="number" class="apple-input w-full text-base" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">利用小时 (h)</label>
          <input v-model.number="form.equivalent_hours" type="number" class="apple-input w-full text-base" />
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
        <div class="sm:col-span-2">
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">总投资额 (元)</label>
          <input v-model.number="form.total_investment" type="number" class="apple-input w-full text-base" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">电价 (元/kWh)</label>
          <input v-model.number="form.electricity_price" type="number" step="0.01" class="apple-input w-full text-base" />
          <p v-if="lastAppliedPolicy" class="mt-1 text-xs text-gray-500 dark:text-dark-text/60">
            已应用政策：{{ lastAppliedPolicy.province }}，电价={{ lastAppliedPolicy.electricity_price }}
          </p>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 dark:text-dark-text/80 mb-1">贷款比例</label>
          <input v-model.number="form.loan_ratio" type="number" step="0.1" class="apple-input w-full text-base" />
        </div>

        <button type="submit" :disabled="calculating" class="apple-pill-primary mt-2 flex w-full items-center gap-2 text-base sm:col-span-2">
        <svg v-if="calculating" class="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        {{ buttonLabel }}
        </button>
      </form>

      <div v-if="errorMsg" class="mt-3 text-sm text-red-600 dark:text-red-400">
        {{ errorMsg }}
      </div>
      <button
        v-if="hasResult"
        type="button"
        class="apple-pill-secondary w-full md:hidden"
        @click="showResultPanel"
      >
        查看测算结果
      </button>
      </div>

      <div class="flex min-h-[320px] min-w-0 w-1/2 shrink-0 flex-col border-l border-gray-200 p-4 dark:border-gray-700 sm:min-h-[420px] sm:p-6 md:w-full md:border-l-0 lg:col-span-7 lg:min-h-[450px] lg:border-l lg:p-9">
        <div class="mb-4 flex items-center justify-between gap-3">
          <h3 class="text-lg font-bold tracking-[-0.03em] text-gray-900 dark:text-dark-text lg:text-[1.75rem]">决策分析视图</h3>
          <button
            type="button"
          class="apple-pill-secondary min-h-[40px] px-4 py-2 md:hidden"
            @click="backToForm"
          >
            返回修改参数
          </button>
        </div>

        <p class="mb-4 text-sm text-slate-500 dark:text-dark-text/60 md:hidden">
          核心收益指标与收益曲线会在当前卡片位置展示，你可以返回继续修改参数后重新计算。
        </p>

        <div v-if="hasResult" class="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div class="apple-subcard border-emerald-100 bg-emerald-50 p-4 dark:border-emerald-800/30 dark:bg-emerald-900/20">
            <p class="text-sm text-gray-600 dark:text-dark-text/80">内部收益率 (IRR)</p>
            <p class="mt-2 font-mono text-xl font-bold text-emerald-500">{{ irrDisplay }}</p>
          </div>
          <div class="apple-subcard border-cyan-100 bg-cyan-50 p-4 dark:border-cyan-800/30 dark:bg-cyan-900/10">
            <p class="text-sm text-gray-600 dark:text-dark-text/80">净现值 (NPV)</p>
            <p class="mt-2 font-mono text-xl font-bold text-cyan-500">¥{{ npvDisplay }}</p>
          </div>
          <div class="apple-subcard p-4">
            <p class="text-sm text-gray-600 dark:text-dark-text/80">平准化度电成本 (LCOE)</p>
            <p class="mt-2 font-mono text-xl font-bold text-slate-700 dark:text-dark-text">{{ lcoeDisplay }}</p>
          </div>
        </div>

        <div class="relative mt-4 flex-1 w-full min-h-[260px] overflow-hidden rounded-[24px] border border-black/[0.04] bg-[#fbfbfd] dark:border-slate-700 dark:bg-dark-card sm:min-h-[320px] lg:min-h-[350px]">
          <div
            ref="chartRef"
            class="absolute inset-0 transition-opacity duration-500"
            :style="{ opacity: hasResult ? 1 : 0, zIndex: hasResult ? 10 : 0 }"
          ></div>

          <div
            v-if="!hasResult"
            class="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white px-6 text-center text-gray-400 dark:bg-dark-card dark:text-gray-500"
          >
            <div class="mb-4 text-5xl">📊</div>
            <p>请输入左侧参数并点击计算以生成图表</p>
          </div>
        </div>

        <div
          v-if="hasResult && annualCashFlowRows.length > 0"
          class="mt-4 space-y-3 md:hidden"
          @touchstart.passive="onCashFlowTouchStart"
          @touchend.passive="onCashFlowTouchEnd"
        >
          <article
            v-for="item in mobileCashFlowRows"
            :key="`cashflow-${item.year}`"
            class="apple-subcard p-4"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="text-sm font-semibold text-slate-900 dark:text-dark-text">第 {{ item.year }} 年现金流</p>
              <span class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
                年度明细
              </span>
            </div>
            <div class="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div class="rounded-[18px] bg-white px-3 py-2 dark:bg-slate-900/40">
                <p class="text-xs text-slate-500 dark:text-dark-text/60">年度现金流</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">¥{{ item.cashFlow.toFixed(2) }}</p>
              </div>
              <div class="rounded-[18px] bg-white px-3 py-2 dark:bg-slate-900/40">
                <p class="text-xs text-slate-500 dark:text-dark-text/60">累计现金流</p>
                <p class="mt-1 font-medium text-slate-900 dark:text-dark-text">¥{{ item.cumulative.toFixed(2) }}</p>
              </div>
            </div>
          </article>

          <div class="apple-subcard flex items-center justify-between gap-3 px-3 py-2">
            <button
              type="button"
              class="min-h-[40px] rounded-lg px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
              :disabled="!canPrevMobileCashFlowPage"
              @click="prevMobileCashFlowPage"
            >
              上一页
            </button>
            <span class="text-sm text-slate-500 dark:text-dark-text/60">{{ mobileCashFlowPage + 1 }} / {{ mobileCashFlowTotalPages }}</span>
            <button
              type="button"
              class="min-h-[40px] rounded-lg px-3 text-sm font-medium text-slate-700 transition disabled:opacity-40 dark:text-dark-text/80"
              :disabled="!canNextMobileCashFlowPage"
              @click="nextMobileCashFlowPage"
            >
              下一页
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
