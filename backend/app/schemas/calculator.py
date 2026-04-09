from decimal import Decimal
from typing import Dict, List
from pydantic import BaseModel, Field

class CalcRequest(BaseModel):
    capacity_kw: Decimal = Field(..., gt=0, description="装机容量 (kW)")
    equivalent_hours: Decimal = Field(..., gt=0, description="年等效利用小时数 (h)")
    total_investment: Decimal = Field(..., gt=0, description="总投资额 (元)")
    electricity_price: Decimal = Field(..., ge=0, description="上网电价 (元/kWh)")
    loan_ratio: Decimal = Field(default=Decimal("0.7"), ge=0, le=1, description="贷款比例")
    annual_degradation: Decimal = Field(default=Decimal("0.008"), ge=0, lt=1, description="年衰减率")

class CalcResponse(BaseModel):
    npv: Decimal = Field(..., description="净现值 (元)")
    irr: float = Field(..., description="内部收益率")
    lcoe: Decimal = Field(..., description="平准化度电成本 (元/kWh)")
    annual_cash_flows: List[Decimal] = Field(default_factory=list, description="年度现金流")

class CalcROIResponse(CalcResponse):
    source_equivalent_hours: float = Field(default=1200.0, description="实际采用的等效小时数")
    location: Dict[str, float] = Field(default_factory=dict, description="计算所用坐标 lon/lat")
    total_generation_discounted: float = Field(default=0.0, description="折后总发电量")
