from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True, slots=True)
class WeatherRadiationRecord:
    """
    统一的天气/辐射记录（面向存储与后端查询）。

    约定：
    - radiation_* 单位：kWh/m^2
    - temperature 单位：°C
    - precipitation 单位：mm
    - wind_speed 单位：m/s
    """

    latitude: float
    longitude: float
    day: date

    shortwave_radiation_sum_kwh_m2: Decimal
    temperature_mean_c: Optional[Decimal] = None
    precipitation_sum_mm: Optional[Decimal] = None
    wind_speed_mean_m_s: Optional[Decimal] = None

    # 便于直接用于收益计算/地图展示的派生字段
    annual_radiation_sum_kwh_m2: Optional[Decimal] = None
    equivalent_hours_h: Optional[Decimal] = None

    source: str = "open_meteo"
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CityLocationRecord:
    province: str
    city: str
    latitude: Decimal
    longitude: Decimal
    source: str = "city_location_reference"
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class PolicyTariffRecord:
    """
    统一的政策/电价记录（面向存储与后端查询）。
    """

    province: str
    benchmark_price_yuan_per_kwh: Decimal
    subsidy_yuan_per_kwh: Optional[Decimal] = None

    policy_date: Optional[str] = None
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    policy_type: Optional[str] = None
    source_url: Optional[str] = None
    source: str = "energy_gov"


@dataclass(frozen=True, slots=True)
class PovertyCountyRecord:
    """
    统一的贫困县/乡村振兴区域基础数据记录。
    """

    province: str
    city: Optional[str]
    county: str

    population: Optional[int] = None
    income_per_capita_yuan: Optional[Decimal] = None
    energy_condition: Optional[str] = None
    tags: Optional[str] = None

    # 可选：若未来接入行政区划代码/边界，可扩展
    adcode: Optional[str] = None
    source: str = "poverty_dataset"
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CostRecord:
    """
    统一的光伏成本记录（面向存储与后端查询）。

    约定：
    - unit_cost_yuan_per_kw：元/kW（用于快速估算总投资）
    - component_price_*：元/W（若有）
    """

    name: str
    category: str  # module | inverter | mounting | construction | opex | total
    province: Optional[str]

    unit_cost_yuan_per_kw: Optional[Decimal] = None
    component_price_yuan_per_w: Optional[Decimal] = None

    effective_date: Optional[str] = None
    source: str = "pv_costs"
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class GridAccessRecord:
    province: str
    access_capacity_mw: Optional[Decimal] = None
    curtailment_rate: Optional[Decimal] = None
    consumption_capacity_score: Optional[Decimal] = None
    effective_date: Optional[str] = None
    source: str = "grid_access"
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    project_name: str
    province: Optional[str]
    capacity_kw: Optional[Decimal] = None
    annual_generation_kwh: Optional[Decimal] = None
    annual_income_yuan: Optional[Decimal] = None
    project_type: Optional[str] = None
    status: Optional[str] = None
    effective_date: Optional[str] = None
    source: str = "generation"
    source_url: Optional[str] = None


@dataclass(frozen=True, slots=True)
class CarbonReductionRecord:
    province: Optional[str]
    year: Optional[int]
    carbon_reduction_ton: Optional[Decimal] = None
    method: Optional[str] = None
    source: str = "carbon"
    source_url: Optional[str] = None

