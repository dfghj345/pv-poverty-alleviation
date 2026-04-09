from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider


@dataclass(frozen=True, slots=True)
class PovertyRawItem:
    province: str
    city: Optional[str]
    county: str
    population: Optional[int] = None
    income_per_capita_yuan: Optional[Decimal] = None
    energy_condition: Optional[str] = None
    tags: Optional[str] = None
    adcode: Optional[str] = None
    source_url: Optional[str] = None


@register_spider("poverty_regions")
class PovertyRegionsSpider(BaseSpider[dict, PovertyRawItem]):
    """
    贫困县/乡村振兴区域基础数据：
    - 优先对接开放数据的 JSON（或由你后续替换为更权威来源/文件下载）。
    - raw 约定为 JSON：{"items":[{...}, ...]} 或直接为 [{...}, ...]
    """

    name = "poverty_regions"
    site = "poverty_regions"
    data_type = "poverty_county"
    enabled = False
    disabled_reason = "当前链路优先打通 Open-Meteo 入库；贫困区域数据先降级避免全量运行噪音"

    def __init__(self) -> None:
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> dict:
        if self._http is None or self._request_opt is None or self._site_url is None:
            raise RuntimeError("spider dependencies not injected (runner should set _http/_request_opt/_site_url)")
        return await self._http.get_json(self._site_url, params=None, ctx=ctx, opt=self._request_opt)

    def parse(self, raw: dict, ctx: RunContext) -> List[PovertyRawItem]:
        log = get_ctx_logger(__name__, ctx=ctx)
        items_raw: Any = raw
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            items_raw = raw["items"]

        if not isinstance(items_raw, list):
            log.warning("unexpected poverty raw format", extra={"type": type(items_raw).__name__})
            return []

        out: List[PovertyRawItem] = []
        for x in items_raw:
            if not isinstance(x, dict):
                continue
            prov = str(x.get("province") or "").strip()
            county = str(x.get("county") or x.get("district") or "").strip()
            if not prov or not county:
                continue
            out.append(
                PovertyRawItem(
                    province=prov,
                    city=_opt_str(x.get("city")),
                    county=county,
                    population=_opt_int(x.get("population")),
                    income_per_capita_yuan=_opt_decimal(x.get("income_per_capita_yuan")),
                    energy_condition=_opt_str(x.get("energy_condition")),
                    tags=_opt_str(x.get("tags")),
                    adcode=_opt_str(x.get("adcode")),
                    source_url=_opt_str(x.get("source_url")) or ctx.url,
                )
            )

        log.info("parsed poverty region items", extra={"count": len(out)})
        return out


def _opt_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _opt_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        return None


def _opt_decimal(v: Any) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None

