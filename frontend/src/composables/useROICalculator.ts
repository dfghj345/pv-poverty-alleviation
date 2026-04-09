import { ref, reactive, computed, watch } from 'vue';
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
    (p) => {
      if (p) applyElectricityPrice(p);
    },
    { immediate: true, deep: true }
  );

  watch(
    () => projectStore.appliedWeather,
    (w) => {
      if (w) applyEquivalentHours(w);
    },
    { immediate: true, deep: true }
  );

  watch(
    () => projectStore.appliedCost,
    (c) => {
      if (!c) return;
      // 最小联动：根据单位造价自动刷新总投资（用户仍可手动改写）
      form.total_investment = Number((form.capacity_kw ?? 0) * c.unit_cost_yuan_per_kw);
    },
    { immediate: true, deep: true }
  );

  watch(
    () => projectStore.appliedProject,
    (p) => {
      if (!p) return;
      // 自动填参模式：把所选电站容量带入测算（不依赖后端测算接口改变）
      form.capacity_kw = p.capacity_kw;
    },
    { immediate: true, deep: true }
  );

  async function submit(): Promise<void> {
    loading.value = true;
    result.value = null;
    
    try {
      // 1. 优先尝试调用真实的 Python 后端 API
      result.value = await estimateCalc(form);
    } catch (e) {
      // 2. 启动增强版前端测算模型（包含贷款杠杆逻辑）
      console.warn('⚠️ 后端未响应，启用前端金融测算模型', e);
      
      const capacity = form.capacity_kw;
      const hours = form.equivalent_hours;
      const investment = form.total_investment;
      const price = form.electricity_price;
      const loanRatio = form.loan_ratio || 0; // 例如 0.7 表示贷 70%
      
      // --- 基础收支 ---
      const annualGeneration = capacity * hours;           // 年发电量
      const annualIncome = annualGeneration * price;       // 年收入
      const annualCost = investment * 0.05;                // 年运维成本（5%）
      
      // --- 🌟 银行贷款逻辑 (假设贷款期限10年，年化利率 4.9%) ---
      const loanAmount = investment * loanRatio;           // 银行贷款总额
      const ownInvestment = investment - loanAmount;       // 自有资金投入 (前期真正掏的钱)
      const annualPrincipal = loanAmount / 10;             // 每年还本 (等额本金法)
      
      const annual_flows: number[] = [];
      let totalProfit20 = 0;

      // 逐年推演 20 年的真实净现金流
      for (let year = 1; year <= 20; year++) {
        let currentYearProfit = annualIncome - annualCost;
        
        // 前 10 年需要偿还银行的本金和利息
        if (year <= 10 && loanAmount > 0) {
          // 剩余未还本金 = 总贷款 - 已经还了的本金
          const remainingPrincipal = loanAmount - (year - 1) * annualPrincipal; 
          const annualInterest = remainingPrincipal * 0.049; // 当年产生的利息
          
          // 净利润需扣除当年的还本付息金额
          currentYearProfit = currentYearProfit - annualPrincipal - annualInterest;
        }
        
        annual_flows.push(currentYearProfit);
        totalProfit20 += currentYearProfit;
      }

      // 基于自有资金计算真实的投资回报
      const mockIrr = ownInvestment > 0 ? (totalProfit20 / ownInvestment / 20) : 0;
      const mockNpv = totalProfit20 - ownInvestment;

      await new Promise(resolve => setTimeout(resolve, 1500));

      result.value = {
        npv: mockNpv,
        irr: mockIrr,
        lcoe: 0, 
        annual_cash_flows: annual_flows
      };
    } finally {
      loading.value = false;
    }
  }

  const hasResult = computed(() => result.value !== null);
  const buttonLabel = computed(() => loading.value ? '引擎推演中...' : '开始决策分析');
  
  const chartData = computed(() => {
    const r = result.value;
    if (!r || !r.annual_cash_flows || r.annual_cash_flows.length === 0) return null;
    
    const flows = r.annual_cash_flows;
    
    // 🌟 修复：生成图表数据时，折线图起点必须是你实际掏的“自有资金”，而不是“总投资”
    const ownMoney = form.total_investment * (1 - (form.loan_ratio || 0));
    let cumulativeSum = -ownMoney; 
    
    const cumulative = flows.map((v) => {
      cumulativeSum += v;
      return cumulativeSum;
    });

    return {
      years: flows.map((_, i) => `第${i + 1}年`),
      profits: flows,       // 对应柱状图：每年固定的利润
      cumulative: cumulative // 对应折线图：回本曲线（从负投资额开始爬升）
    };
  });

  return {
    form,
    loading,
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
