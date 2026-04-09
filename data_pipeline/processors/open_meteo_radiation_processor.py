from __future__ import annotations

from decimal import Decimal
from typing import List

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.registry.processors import register_processor
from data_pipeline.db.records import WeatherRadiationRecord


@register_processor("open_meteo_radiation")
class OpenMeteoRadiationProcessor(BaseProcessor[WeatherRadiationRecord, WeatherRadiationRecord]):
    """
    轻量标准化：
    - 保证数值字段非负（辐射/降水/风速）
    - 保持类型稳定，便于落库与后端查询
    """

    name = "open_meteo_radiation_processor"

    def process(self, items: List[WeatherRadiationRecord], ctx: RunContext) -> List[WeatherRadiationRecord]:
        out: List[WeatherRadiationRecord] = []
        for it in items:
            out.append(
                WeatherRadiationRecord(
                    latitude=it.latitude,
                    longitude=it.longitude,
                    day=it.day,
                    shortwave_radiation_sum_kwh_m2=_nonneg(it.shortwave_radiation_sum_kwh_m2),
                    temperature_mean_c=it.temperature_mean_c,
                    precipitation_sum_mm=_nonneg_opt(it.precipitation_sum_mm),
                    wind_speed_mean_m_s=_nonneg_opt(it.wind_speed_mean_m_s),
                    annual_radiation_sum_kwh_m2=_nonneg_opt(it.annual_radiation_sum_kwh_m2),
                    equivalent_hours_h=_nonneg_opt(it.equivalent_hours_h),
                    source=it.source,
                    source_url=it.source_url,
                )
            )
        return out


def _nonneg(v: Decimal) -> Decimal:
    try:
        return v if v >= 0 else Decimal("0")
    except Exception:
        return Decimal("0")


def _nonneg_opt(v: Decimal | None) -> Decimal | None:
    if v is None:
        return None
    return _nonneg(v)

