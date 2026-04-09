from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PolicyTariffOut(BaseModel):
    province: str = Field(..., description="省份")
    benchmark_price_yuan_per_kwh: float = Field(..., description="上网电价(元/kWh)")
    subsidy_yuan_per_kwh: Optional[float] = Field(default=None, description="补贴(元/kWh)")
    policy_date: Optional[str] = Field(default=None, description="政策发布时间/日期")
    policy_type: Optional[str] = Field(default=None, description="政策类型")
    source_url: Optional[str] = Field(default=None, description="来源链接")

