from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GenerationRecordOut(BaseModel):
    province: str = Field(..., description="Province name")
    city: Optional[str] = Field(default=None, description="City name")
    county: Optional[str] = Field(default=None, description="County name")
    year: int = Field(..., description="Statistics year")
    installed_capacity_kw: Optional[float] = Field(default=None, description="Installed capacity (kW)")
    annual_generation_kwh: Optional[float] = Field(default=None, description="Annual generation (kWh)")
    annual_income_yuan: Optional[float] = Field(default=None, description="Annual income (yuan)")
    utilization_hours: Optional[float] = Field(default=None, description="Equivalent utilization hours")
    source: str = Field(..., description="Data source")
    remark: Optional[str] = Field(default=None, description="Notes")


class GenerationTrendItemOut(BaseModel):
    year: int = Field(..., description="Statistics year")
    installed_capacity_kw: float = Field(..., description="Installed capacity (kW)")
    annual_generation_kwh: float = Field(..., description="Annual generation (kWh)")
    annual_income_yuan: float = Field(..., description="Annual income (yuan)")


class GenerationProvinceDistributionItemOut(BaseModel):
    name: str = Field(..., description="Province name")
    value: float = Field(..., description="Installed capacity share value")


class GenerationSummaryOut(BaseModel):
    total_installed_capacity_kw: float = Field(..., description="Total installed capacity (kW)")
    total_annual_generation_kwh: float = Field(..., description="Total annual generation (kWh)")
    total_annual_income_yuan: float = Field(..., description="Total annual income (yuan)")
    province_count: int = Field(..., description="Distinct province count")
    city_count: int = Field(..., description="Distinct city count")
    county_count: int = Field(..., description="Distinct county count")
    yearly_trend: list[GenerationTrendItemOut] = Field(default_factory=list, description="Yearly trend items")
    province_distribution: list[GenerationProvinceDistributionItemOut] = Field(
        default_factory=list,
        description="Installed capacity distribution by province",
    )
