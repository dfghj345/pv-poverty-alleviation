import { computed, reactive, ref, watch } from 'vue';
import { estimateCalc } from '@/api/calc';
import type { CalcRequest, CalcResponse } from '@/api/types';
import { useProjectStore } from '@/store/project';

const defaultForm: CalcRequest = {
  capacity_kw: 150.5,
  equivalent_hours: 1200,
  total_investment: 450000,
  electricity_price: 0.38,
  loan_ratio: 0.7,
  annual_degradation: 0.008
};

export function useROICalculator() {
  const projectStore = useProjectStore();
  const loading = ref(false);
  const errorMsg = ref<string | null>(null);
  const form = reactive<CalcRequest>({ ...defaultForm });
  const result = ref<CalcResponse | null>(null);
  const lastAppliedPolicy = ref<{ province: string; electricity_price: number } | null>(null);
  const lastAppliedWeather = ref<{
    latitude: number;
    longitude: number;
    equivalent_hours: number;
    province?: string | null;
    city?: string | null;
  } | null>(null);

  function applyElectricityPrice(payload: { province: string; electricity_price: number }): void {
    form.electricity_price = payload.electricity_price;
    lastAppliedPolicy.value = payload;
  }

  function applyEquivalentHours(payload: {
    latitude: number;
    longitude: number;
    equivalent_hours: number;
    province?: string | null;
    city?: string | null;
  }): void {
    form.equivalent_hours = payload.equivalent_hours;
    lastAppliedWeather.value = payload;
  }

  watch(
    () => projectStore.appliedPolicy,
    (policy) => {
      if (policy) applyElectricityPrice(policy);
    },
    { immediate: true, deep: true }
  );

  watch(
    () => projectStore.appliedWeather,
    (weather) => {
      if (weather) applyEquivalentHours(weather);
    },
    { immediate: true, deep: true }
  );

  watch(
    () => projectStore.appliedCost,
    (cost) => {
      if (!cost) return;
      form.total_investment = Number((form.capacity_kw ?? 0) * cost.unit_cost_yuan_per_kw);
    },
    { immediate: true, deep: true }
  );

  watch(
    () => projectStore.appliedProject,
    (project) => {
      if (!project) return;
      form.capacity_kw = project.capacity_kw;
    },
    { immediate: true, deep: true }
  );

  async function submit(): Promise<void> {
    loading.value = true;
    errorMsg.value = null;
    result.value = null;

    try {
      result.value = await estimateCalc(form);
    } catch (error) {
      console.error('ROI calculation API request failed', error);
      errorMsg.value = error instanceof Error ? error.message : '收益测算接口请求失败';
    } finally {
      loading.value = false;
    }
  }

  const hasResult = computed(() => result.value !== null);
  const buttonLabel = computed(() => (loading.value ? '计算中...' : '开始收益测算'));

  const chartData = computed(() => {
    const cashFlows = result.value?.annual_cash_flows;
    if (!cashFlows || cashFlows.length === 0) return null;

    let cumulativeSum = 0;
    const cumulative = cashFlows.map((value) => {
      cumulativeSum += Number(value);
      return cumulativeSum;
    });

    return {
      years: cashFlows.map((_, index) => `第${index}年`),
      profits: cashFlows.map(Number),
      cumulative
    };
  });

  return {
    form,
    loading,
    errorMsg,
    result,
    submit,
    hasResult,
    buttonLabel,
    chartData,
    applyElectricityPrice,
    applyEquivalentHours,
    lastAppliedPolicy,
    lastAppliedWeather
  };
}
