from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider
from data_pipeline.db.records import WeatherRadiationRecord


@dataclass(frozen=True, slots=True)
class OpenMeteoQuery:
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    performance_ratio: Decimal = Decimal("0.82")


@register_spider("open_meteo_radiation")
class OpenMeteoRadiationSpider(BaseSpider[dict, WeatherRadiationRecord]):
    """
    Open-Meteo Archive API：拉取按日的短波辐射/温度/降水/风速，并计算年辐射与等效利用小时数。

    - 输入参数通过 ctx.meta['query'] 传入 OpenMeteoQuery；缺省则默认取最近 365 天、(0,0) 坐标仅用于测试。
    - 不改变现有 weather_data spider 行为，作为结构化增强新增 spider。
    """

    name = "open_meteo_radiation"
    site = "weather_data"  # 复用现有 SiteConfig（URL 指向 open-meteo archive）
    data_type = "weather_radiation"

    def __init__(self) -> None:
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> dict:
        if self._http is None or self._request_opt is None or self._site_url is None:
            raise RuntimeError("spider dependencies not injected (runner should set _http/_request_opt/_site_url)")

        q = _get_query(ctx)
        if ctx.meta.get("query") is None and float(q.latitude) == 0.0 and float(q.longitude) == 0.0:
            get_ctx_logger(__name__, ctx=ctx).warning(
                "using default test coordinates (0,0); pass ctx.meta['query']=OpenMeteoQuery for real location",
                extra={"start_date": q.start_date.isoformat(), "end_date": q.end_date.isoformat()},
            )
        params = {
            "latitude": q.latitude,
            "longitude": q.longitude,
            "start_date": q.start_date.isoformat(),
            "end_date": q.end_date.isoformat(),
            "daily": ",".join(
                [
                    "shortwave_radiation_sum",
                    "temperature_2m_mean",
                    "precipitation_sum",
                    "windspeed_10m_mean",
                ]
            ),
            "timezone": "auto",
        }
        get_ctx_logger(__name__, ctx=ctx).info(
            "open-meteo request params",
            extra={
                "latitude": q.latitude,
                "longitude": q.longitude,
                "start_date": q.start_date.isoformat(),
                "end_date": q.end_date.isoformat(),
                "timezone": "auto",
            },
        )
        return await self._http.get_json(self._site_url, params=params, ctx=ctx, opt=self._request_opt)

    def parse(self, raw: dict, ctx: RunContext) -> List[WeatherRadiationRecord]:
        log = get_ctx_logger(__name__, ctx=ctx)
        q = _get_query(ctx)

        daily = raw.get("daily") or {}
        times = daily.get("time") or []
        rad_mj_m2 = daily.get("shortwave_radiation_sum") or []
        t_mean = daily.get("temperature_2m_mean") or []
        prcp = daily.get("precipitation_sum") or []
        wind = daily.get("windspeed_10m_mean") or []

        n = min(len(times), len(rad_mj_m2))
        if n == 0:
            log.warning("open-meteo returned empty daily arrays")
            return []

        # Open-Meteo shortwave_radiation_sum：MJ/m^2；换算 kWh/m^2：* 0.2778
        kwh_values: List[Decimal] = []
        for i in range(n):
            v = rad_mj_m2[i]
            if v is None:
                continue
            kwh_values.append(Decimal(str(v)) * Decimal("0.2778"))
        annual_sum = sum(kwh_values) if kwh_values else Decimal("0")
        equivalent_hours = (annual_sum * q.performance_ratio).quantize(Decimal("0.01")) if annual_sum > 0 else None

        out: List[WeatherRadiationRecord] = []
        for i in range(n):
            day = _parse_day(times[i])
            if day is None:
                continue
            rad_kwh = Decimal(str(rad_mj_m2[i] or 0)) * Decimal("0.2778")
            out.append(
                WeatherRadiationRecord(
                    latitude=float(q.latitude),
                    longitude=float(q.longitude),
                    day=day,
                    shortwave_radiation_sum_kwh_m2=rad_kwh,
                    temperature_mean_c=_opt_decimal(t_mean, i),
                    precipitation_sum_mm=_opt_decimal(prcp, i),
                    wind_speed_mean_m_s=_opt_decimal(wind, i),
                    annual_radiation_sum_kwh_m2=annual_sum if i == n - 1 else None,
                    equivalent_hours_h=equivalent_hours if i == n - 1 else None,
                    source="open_meteo",
                    source_url=ctx.url,
                )
            )

        log.info("parsed weather radiation records", extra={"count": len(out), "annual_sum_kwh_m2": float(annual_sum)})
        return out


def _get_query(ctx: RunContext) -> OpenMeteoQuery:
    q = ctx.meta.get("query")
    if isinstance(q, OpenMeteoQuery):
        return q
    end = date.today()
    start = end - timedelta(days=365)
    return OpenMeteoQuery(latitude=0.0, longitude=0.0, start_date=start, end_date=end)


def _parse_day(v: Any) -> Optional[date]:
    if isinstance(v, date):
        return v
    if not isinstance(v, str) or not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except Exception:
        return None


def _opt_decimal(arr: list, idx: int) -> Optional[Decimal]:
    try:
        v = arr[idx]
    except Exception:
        return None
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None

