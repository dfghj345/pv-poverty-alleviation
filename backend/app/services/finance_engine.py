from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional
import numpy_financial as npf  # 建议在 requirements.txt 中补充此库

class PVCalculator:
    """
    光伏收益分析引擎 (Financial Engine for PV Poverty Alleviation)
    负责处理 20 年全生命周期的财务建模、电量衰减及核心指标计算。
    """

    def __init__(
        self,
        annual_degradation: Decimal = Decimal("0.005"),  # 年衰减率 0.5%
        op_cost_ratio: Decimal = Decimal("0.05")         # 运维成本占年收益比例
    ):
        self.annual_degradation = annual_degradation
        self.op_cost_ratio = op_cost_ratio

    def calculate_20year_return(
        self,
        capacity_kw: Decimal,
        sunshine_hours: Decimal,
        total_investment: Decimal,
        benchmark_price: Decimal,
        subsidy: Decimal = Decimal("0.0"),
        discount_rate: Decimal = Decimal("0.06")  # 折现率用于 NPV 计算
    ) -> Dict[str, Any]:
        """
        计算 20 年收益回报情况。
        
        Args:
            capacity_kw: 装机容量 (kW)
            sunshine_hours: 年等效利用小时数 (h)
            total_investment: 总投资额 (元)
            benchmark_price: 标杆上网电价 (元/kWh)
            subsidy: 政策补贴 (元/kWh)
            discount_rate: 社会折现率 (默认 6%)
            
        Returns:
            包含年度利润流、累计收益、NPV、IRR、回本周期的综合字典。
        """
        
        annual_metrics = []
        cash_flows: List[float] = [float(-total_investment)]  # 用于 IRR 计算的现金流数组
        
        cumulative_profit = Decimal("0.0")
        payback_period: Optional[float] = None
        
        unit_revenue = benchmark_price + subsidy
        
        for year in range(1, 21):
            # 1. 计算当年发电量：容量 * 利用小时 * (1 - 衰减率^年数)
            # 考虑到第一年通常视为 100% 效率，公式调整为 (1 - deg)^(year-1)
            efficiency = (Decimal("1.0") - self.annual_degradation) ** (year - 1)
            annual_generation = capacity_kw * sunshine_hours * efficiency
            
            # 2. 计算年度收益与成本
            gross_revenue = (annual_generation * unit_revenue).quantize(Decimal("0.01"), ROUND_HALF_UP)
            maintenance_fee = (gross_revenue * self.op_cost_ratio).quantize(Decimal("0.01"), ROUND_HALF_UP)
            net_profit = gross_revenue - maintenance_fee
            
            # 3. 累计数据统计
            cumulative_profit += net_profit
            cash_flows.append(float(net_profit))
            
            # 4. 回本周期判定（动态）
            if cumulative_profit >= total_investment and payback_period is None:
                # 简单估算：前一年余项 / 当年利润（线性插值简化处理）
                prev_cumulative = cumulative_profit - net_profit
                gap = total_investment - prev_cumulative
                payback_period = round(float(year - 1) + float(gap / net_profit), 2)

            annual_metrics.append({
                "year": year,
                "generation_kwh": float(annual_generation.quantize(Decimal("0.01"))),
                "net_profit": float(net_profit),
                "cumulative_profit": float(cumulative_profit)
            })

        # 5. 核心财务指标分析
        # NPV: 净现值
        npv_val = npf.npv(float(discount_rate), cash_flows)
        # IRR: 内部收益率
        try:
            irr_val = npf.irr(cash_flows)
        except Exception:
            irr_val = 0.0

        return {
            "summary": {
                "total_investment": float(total_investment),
                "total_20y_profit": float(cumulative_profit),
                "npv": round(float(npv_val), 2),
                "irr": round(float(irr_val), 4) if irr_val else None,
                "payback_period": payback_period or 20.0,
                "is_viable": irr_val > float(discount_rate) if irr_val else False
            },
            "yearly_details": annual_metrics
        }