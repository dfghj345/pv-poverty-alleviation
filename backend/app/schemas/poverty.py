from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PovertyCountyOut(BaseModel):
    province: str = Field(..., description="省份")
    city: Optional[str] = Field(default=None, description="市/州")
    county: str = Field(..., description="县/区")

    population: Optional[int] = Field(default=None, description="人口")
    income_per_capita_yuan: Optional[float] = Field(default=None, description="人均收入(元)")
    energy_condition: Optional[str] = Field(default=None, description="能源条件/电网情况")
    tags: Optional[str] = Field(default=None, description="标签")
    adcode: Optional[str] = Field(default=None, description="行政区划代码")

    source: str = Field(..., description="数据源")
    source_url: Optional[str] = Field(default=None, description="源链接")

