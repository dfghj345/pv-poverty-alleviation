from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CostOut(BaseModel):
    name: str = Field(..., description="条目名称")
    category: str = Field(..., description="类别：module/inverter/mounting/construction/opex/total")
    province: Optional[str] = Field(default=None, description="省份（可为空表示全国）")
    unit_cost_yuan_per_kw: Optional[float] = Field(default=None, description="单位造价(元/kW)")
    component_price_yuan_per_w: Optional[float] = Field(default=None, description="组件等单价(元/W)")
    effective_date: Optional[str] = Field(default=None, description="生效日期")
    source: str = Field(..., description="数据源")
    source_url: Optional[str] = Field(default=None, description="来源链接")

