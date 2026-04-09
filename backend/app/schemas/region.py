from __future__ import annotations

from pydantic import BaseModel, Field


class RegionLocationOut(BaseModel):
    province: str = Field(..., description='Province name')
    city: str = Field(..., description='City name')
    latitude: float = Field(..., description='Latitude')
    longitude: float = Field(..., description='Longitude')
    source: str = Field(..., description='Coordinate source')
