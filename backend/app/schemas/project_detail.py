from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ProjectDetailOut(BaseModel):
    id: int = Field(..., description="项目ID")
    name: str = Field(..., description="项目名称")
    capacity_kw: float = Field(..., description="装机容量(kW)")
    commissioning_date: date = Field(..., description="投产日期")
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")
    province: str = Field(..., description="省份（来自关联政策）")

