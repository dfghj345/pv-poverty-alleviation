from datetime import date
from typing import List
from pydantic import BaseModel, ConfigDict, Field

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    capacity: float = Field(..., gt=0, description="装机容量 (kWp)")
    commissioning_date: date = Field(..., description="投产日期")

class ProjectCreate(ProjectBase):
    longitude: float = Field(..., ge=-180, le=180, description="经度 WGS84")
    latitude: float = Field(..., ge=-90, le=90, description="纬度 WGS84")
    policy_id: int = Field(..., gt=0, description="关联政策 ID")

class ProjectInDB(ProjectBase):
    model_config = ConfigDict(from_attributes=True)
    id: int = Field(..., description="主键")
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")

class ProjectPagination(BaseModel):
    total: int = Field(..., ge=0, description="总条数")
    items: List[ProjectInDB] = Field(default_factory=list, description="当前页项目列表")
