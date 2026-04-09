import { ref, reactive, computed } from 'vue';
import { useProjectStore } from '@/store/project';
import { estimateCalc } from '@/api/calc';
import type { CalcRequest, CalcROIResponse } from '@/api/types';

export function useCalcPanel() {
  const projectStore = useProjectStore();
  const isCalculating = ref(false);
  const formData = reactive({
    capacity_kw: 150,
    benchmark_price: 0.38,
    loan_ratio: 30
  });

  async function handleCalculate(): Promise<void> {
    isCalculating.value = true;
    try {
      const payload: CalcRequest = {
        capacity_kw: formData.capacity_kw,
        equivalent_hours: 1200,
        total_investment: formData.capacity_kw * 3000,
        electricity_price: formData.benchmark_price,
        loan_ratio: formData.loan_ratio / 100,
        annual_degradation: 0.008
      };
      const res = await estimateCalc(payload);
      const roiResponse: CalcROIResponse = {
        ...res,
        source_equivalent_hours: 1200,
        location: { lon: 0, lat: 0 },
        total_generation_discounted: 0
      };
      projectStore.setCalcResults(roiResponse);
    } catch (e) {
      console.error('计算请求失败', e);
    } finally {
      isCalculating.value = false;
    }
  }

  const buttonClass = computed(() =>
    isCalculating.value
      ? 'bg-slate-700 text-slate-400 cursor-not-allowed'
      : 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white shadow-lg shadow-emerald-900/50'
  );
  const buttonLabel = computed(() => (isCalculating.value ? '引擎推演中...' : '生成投资决策报告'));

  return { formData, isCalculating, handleCalculate, buttonClass, buttonLabel };
}
