from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class WeatherRadiationOut(BaseModel):
    latitude: float = Field(..., description='Latitude')
    longitude: float = Field(..., description='Longitude')
    province: Optional[str] = Field(default=None, description='Resolved province when queried by province/city')
    city: Optional[str] = Field(default=None, description='Resolved city when queried by province/city')
    location_source: Optional[str] = Field(default=None, description='Location resolve source')

    day: date = Field(..., description='Date')

    shortwave_radiation_sum_kwh_m2: float = Field(..., description='Daily shortwave radiation sum (kWh/m^2)')
    temperature_mean_c: Optional[float] = Field(default=None, description='Daily mean temperature (degC)')
    precipitation_sum_mm: Optional[float] = Field(default=None, description='Daily precipitation (mm)')
    wind_speed_mean_m_s: Optional[float] = Field(default=None, description='Daily mean wind speed (m/s)')

    annual_radiation_sum_kwh_m2: Optional[float] = Field(default=None, description='Annual radiation sum (kWh/m^2)')
    equivalent_hours_h: Optional[float] = Field(default=None, description='Equivalent full-load hours (h)')

    source: str = Field(..., description='Data source')
    source_url: Optional[str] = Field(default=None, description='Source URL')
