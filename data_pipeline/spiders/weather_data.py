from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider


@register_spider("weather_data")
class WeatherDataSpider(BaseSpider[dict, Decimal]):
    name = "weather_data"
    site = "weather_data"
    # 工程定位：仅用于验证 Open-Meteo Archive API 可用性/兼容性，不参与默认入库链路
    enabled = False
    disabled_reason = "职责与 open_meteo_radiation 重叠；作为接口测试 spider 默认跳过 store"

    def __init__(self) -> None:
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> dict:
        if self._http is None or self._request_opt is None or self._site_url is None:
            raise RuntimeError("spider dependencies not injected (runner should set _http/_request_opt/_site_url)")
        params = ctx.meta.get("params")
        if not isinstance(params, dict) or not params:
            # Open-Meteo Archive API 必须带完整参数；否则可能 200 但返回非 JSON（HTML/空内容）
            end = date.today()
            start = end - timedelta(days=365)
            params = {
                "latitude": 0.0,
                "longitude": 0.0,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "daily": "shortwave_radiation_sum",
                "timezone": "auto",
            }
        return await self._http.get_json(self._site_url, params=params, ctx=ctx, opt=self._request_opt)

    def parse(self, raw: dict, ctx: RunContext) -> list[Decimal]:
        """
        根据经纬度获取该地区过去一年的等效利用小时数
        """
        log = get_ctx_logger(__name__, ctx=ctx)
        try:
            daily_radiation = raw.get("daily", {}).get("shortwave_radiation_sum", [])
            if not daily_radiation:
                return [Decimal("1200")]

            annual_mj_sum = sum([r for r in daily_radiation if r is not None])
            annual_kwh_m2 = Decimal(str(annual_mj_sum)) * Decimal("0.2778")
            performance_ratio = Decimal("0.82")
            equivalent_hours = round(annual_kwh_m2 * performance_ratio, 2)
            return [equivalent_hours]
        except Exception as e:
            log.warning("weather parse failed; fallback", extra={"error": str(e)})
            return [Decimal("1200")]