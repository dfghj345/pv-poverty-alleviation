from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PolicyTariffOut(BaseModel):
    province: str = Field(..., description="Province")
    benchmark_price_yuan_per_kwh: float = Field(..., description="Benchmark tariff, yuan/kWh")
    subsidy_yuan_per_kwh: Optional[float] = Field(default=None, description="Subsidy, yuan/kWh")
    policy_date: Optional[str] = Field(default=None, description="Policy date")
    policy_type: Optional[str] = Field(default=None, description="Policy type")
    source_url: Optional[str] = Field(default=None, description="Source URL")


class EnergyPolicyOut(BaseModel):
    title: str = Field(..., description="Policy title")
    url: str = Field(..., description="Policy URL")
    publish_date: Optional[str] = Field(default=None, description="Publish date")
    summary: Optional[str] = Field(default=None, description="Summary")
    source: str = Field(..., description="Data source")
    source_url: Optional[str] = Field(default=None, description="Source list URL")
