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
  const calculating = ref(false);
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
    form.electricity_price = toFiniteNumber(payload.electricity_price, defaultForm.electricity_price);
    lastAppliedPolicy.value = payload;
  }

  function applyEquivalentHours(payload: {
    latitude: number;
    longitude: number;
    equivalent_hours: number;
    province?: string | null;
    city?: string | null;
  }): void {
    form.equivalent_hours = toFiniteNumber(payload.equivalent_hours, defaultForm.equivalent_hours);
    lastAppliedWeather.value = payload;
  }

  function toFiniteNumber(value: unknown, fallback = 0): number {
    const numeric = Number(value);
    return Number.isFinite(numeric) ? numeric : fallback;
  }

  function buildPayload(): CalcRequest {
    return {
      capacity_kw: toFiniteNumber(form.capacity_kw, 0),
      equivalent_hours: toFiniteNumber(form.equivalent_hours, 0),
      total_investment: toFiniteNumber(form.total_investment, 0),
      electricity_price: toFiniteNumber(form.electricity_price, 0),
      loan_ratio: toFiniteNumber(form.loan_ratio, 0),
      annual_degradation: toFiniteNumber(form.annual_degradation, defaultForm.annual_degradation ?? 0),
    };
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
      form.total_investment = toFiniteNumber(form.capacity_kw, 0) * toFiniteNumber(cost.unit_cost_yuan_per_kw, 0);
    },
    { immediate: true, deep: true }
  );

  watch(
    () => projectStore.appliedProject,
    (project) => {
      if (!project) return;
      form.capacity_kw = toFiniteNumber(project.capacity_kw, defaultForm.capacity_kw);
    },
    { immediate: true, deep: true }
  );

  async function submit(): Promise<boolean> {
    calculating.value = true;
    errorMsg.value = null;

    try {
      const response = await estimateCalc(buildPayload());
      result.value = {
        npv: toFiniteNumber(response?.npv, 0),
        irr: toFiniteNumber(response?.irr, 0),
        lcoe: toFiniteNumber(response?.lcoe, 0),
        annual_cash_flows: Array.isArray(response?.annual_cash_flows)
          ? response.annual_cash_flows.map((value) => toFiniteNumber(value, 0))
          : [],
      };
      return true;
    } catch (error) {
      console.error('ROI calculation API request failed', error);
      errorMsg.value = error instanceof Error ? error.message : '收益测算接口请求失败';
      return false;
    } finally {
      calculating.value = false;
    }
  }

  const hasResult = computed(() => result.value !== null);
  const buttonLabel = computed(() => (calculating.value ? '计算中...' : '开始收益测算'));
  const hasAutoFillSelection = computed(() => Boolean(projectStore.selectedStation || projectStore.appliedProject));

  const chartData = computed(() => {
    const cashFlows = result.value?.annual_cash_flows;
    if (!cashFlows || cashFlows.length === 0) return null;

    let cumulativeSum = 0;
    const cumulative = cashFlows.map((value) => {
      cumulativeSum += toFiniteNumber(value, 0);
      return cumulativeSum;
    });

    return {
      years: cashFlows.map((_, index) => `第${index + 1}年`),
      profits: cashFlows.map((value) => toFiniteNumber(value, 0)),
      cumulative
    };
  });

  return {
    form,
    calculating,
    errorMsg,
    result,
    submit,
    hasResult,
    hasAutoFillSelection,
    buttonLabel,
    chartData,
    applyElectricityPrice,
    applyEquivalentHours,
    lastAppliedPolicy,
    lastAppliedWeather
  };
}
