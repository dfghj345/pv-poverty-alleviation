from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class GenerationOut(BaseModel):
    project_name: str = Field(..., description="项目名称")
    province: Optional[str] = Field(default=None, description="省份")
    capacity_kw: Optional[float] = Field(default=None, description="容量(kW)")
    annual_generation_kwh: Optional[float] = Field(default=None, description="年发电量(kWh)")
    annual_income_yuan: Optional[float] = Field(default=None, description="年收益(元)")
    project_type: Optional[str] = Field(default=None, description="项目类型")
    status: Optional[str] = Field(default=None, description="运行状态")
    effective_date: Optional[str] = Field(default=None, description="统计年份/日期")
    source: str = Field(..., description="数据源")
    source_url: Optional[str] = Field(default=None, description="来源链接")

