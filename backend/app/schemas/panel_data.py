from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PanelDataItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    province: str
    city: str
    year: int
    pv_installed_capacity_wan_kw: float | None = None
    disposable_income_per_capita_yuan: float | None = None
    healthcare_expenditure_per_capita_yuan: float | None = None
    urban_rural_income_ratio: float | None = None
    mortality_per_mille: float | None = None
    pm25_annual_avg_ug_per_m3: float | None = None
    gdp_100m_yuan: float | None = None
    source_sheet: str | None = None
    source_workbook: str | None = None


class PanelDataPage(BaseModel):
    items: list[PanelDataItem] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1)


class PanelDataPageResponse(BaseModel):
    status: Literal["success"] = "success"
    data: PanelDataPage


class PanelDataFilters(BaseModel):
    provinces: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    years: list[int] = Field(default_factory=list)


class PanelDataFiltersResponse(BaseModel):
    status: Literal["success"] = "success"
    data: PanelDataFilters


class PanelDataProvinceStat(BaseModel):
    province: str
    count: int
    value: float


class PanelDataYearStat(BaseModel):
    year: int
    count: int
    value: float


class PanelDataStats(BaseModel):
    total_count: int = Field(default=0, ge=0)
    province_count: int = Field(default=0, ge=0)
    city_count: int = Field(default=0, ge=0)
    year_count: int = Field(default=0, ge=0)
    by_province: list[PanelDataProvinceStat] = Field(default_factory=list)
    by_year: list[PanelDataYearStat] = Field(default_factory=list)


class PanelDataStatsResponse(BaseModel):
    status: Literal["success"] = "success"
    data: PanelDataStats


class PanelDataMapItem(BaseModel):
    province: str
    city: str
    year: int
    value: float
    count: int
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)


class PanelDataMapResponse(BaseModel):
    status: Literal["success"] = "success"
    data: list[PanelDataMapItem] = Field(default_factory=list)
