from __future__ import annotations

from decimal import Decimal, getcontext
from math import isnan
from typing import Any, Dict, List

import numpy_financial as npf

# 设置全局精度，建议 18 位以上
getcontext().prec = 28

class PVFinanceService:
    """
    光伏项目财务分析服务
    """
    
    @staticmethod
    async def calculate_full_lifecycle(
        capacity_kw: Decimal,
        equivalent_hours: Decimal,
        total_investment: Decimal,
        electricity_price: Decimal,
        loan_ratio: Decimal = Decimal("0.7"),
        annual_degradation: Decimal = Decimal("0.008"),  # 默认 0.8%
        discount_rate: Decimal = Decimal("0.06"),       # 折现率 6%
        op_years: int = 20
    ) -> Dict[str, Any]:
        """
        计算全生命周期财务指标
        """
        
        # 1. 初始计算
        annual_flows = []
        total_generation_lifecycle = Decimal("0")
        discounted_costs = total_investment  # 初始投资作为第0年折现成本
        
        # 第 0 年：初始投资现金流（负值）
        annual_flows.append(float(-total_investment))
        
        # 2. 逐年计算 (Year 1 to op_years)
        for year in range(1, op_years + 1):
            # 考虑衰减后的年发电量 = 容量 * 小时 * (1 - 衰减)^n
            year_gen = capacity_kw * equivalent_hours * ((Decimal("1") - annual_degradation) ** (year - 1))
            year_revenue = year_gen * electricity_price
            
            # 简化模型：假设运维费用为投资额的 1%
            year_opex = total_investment * Decimal("0.01")
            year_cash_flow = year_revenue - year_opex
            
            annual_flows.append(float(year_cash_flow))
            
            # 用于 LCOE 计算：总发电量折现与总成本折现
            total_generation_lifecycle += year_gen / ((1 + discount_rate) ** year)
            discounted_costs += year_opex / ((1 + discount_rate) ** year)

        # 3. 核心财务指标计算
        # 使用 numpy-financial 计算 IRR (内部收益率)
        irr_val = float(npf.irr(annual_flows))
        irr = None if isnan(irr_val) else irr_val
        
        # 计算 NPV (净现值)
        npv = npf.npv(float(discount_rate), annual_flows)
        
        # 计算 LCOE (平准化度电成本) = 总成本折现 / 总发电量折现
        lcoe = discounted_costs / total_generation_lifecycle if total_generation_lifecycle > 0 else Decimal("0")

        return {
            "npv": round(Decimal(str(npv)), 2),
            "irr": round(Decimal(str(irr)), 4) if irr is not None else None,
            "lcoe": round(lcoe, 4),
            "annual_cash_flows": [round(Decimal(str(f)), 2) for f in annual_flows],
            "total_generation_discounted": round(total_generation_lifecycle, 2)
        }