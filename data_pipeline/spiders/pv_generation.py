from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, List, Optional

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider


@dataclass(frozen=True, slots=True)
class GenerationRawItem:
    project_name: str
    province: Optional[str] = None
    capacity_kw: Optional[Decimal] = None
    annual_generation_kwh: Optional[Decimal] = None
    annual_income_yuan: Optional[Decimal] = None
    project_type: Optional[str] = None
    status: Optional[str] = None
    effective_date: Optional[str] = None
    source_url: Optional[str] = None


@register_spider("pv_generation")
class PVGenerationSpider(BaseSpider[dict, GenerationRawItem]):
    """
    历史发电/示范项目数据（示例数据源）：
    - 优先对接开放 JSON；你后续可替换为更权威来源（示范项目公示、统计年鉴、地方能源局）。
    - raw 约定为 JSON：{"items":[{...}, ...]} 或直接为 [{...}, ...]
    """

    name = "pv_generation"
    site = "pv_generation"
    data_type = "generation"
    enabled = False
    disabled_reason = "当前站点为统计/交互页面，未适配 API 参数与反爬策略，先降级跳过"

    def __init__(self) -> None:
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> dict:
        if self._http is None or self._request_opt is None or self._site_url is None:
            raise RuntimeError("spider dependencies not injected (runner should set _http/_request_opt/_site_url)")
        return await self._http.get_json(self._site_url, params=None, ctx=ctx, opt=self._request_opt)

    def parse(self, raw: dict, ctx: RunContext) -> List[GenerationRawItem]:
        log = get_ctx_logger(__name__, ctx=ctx)
        items_raw: Any = raw
        if isinstance(raw, dict) and isinstance(raw.get("items"), list):
            items_raw = raw["items"]
        if not isinstance(items_raw, list):
            log.warning("unexpected generation raw format", extra={"type": type(items_raw).__name__})
            return []

        out: List[GenerationRawItem] = []
        for x in items_raw:
            if not isinstance(x, dict):
                continue
            name = str(x.get("project_name") or x.get("name") or "").strip()
            if not name:
                continue
            out.append(
                GenerationRawItem(
                    project_name=name,
                    province=_opt_str(x.get("province")),
                    capacity_kw=_opt_decimal(x.get("capacity_kw")),
                    annual_generation_kwh=_opt_decimal(x.get("annual_generation_kwh")),
                    annual_income_yuan=_opt_decimal(x.get("annual_income_yuan")),
                    project_type=_opt_str(x.get("project_type")),
                    status=_opt_str(x.get("status")),
                    effective_date=_opt_str(x.get("effective_date")),
                    source_url=_opt_str(x.get("source_url")) or ctx.url,
                )
            )
        log.info("parsed generation items", extra={"count": len(out)})
        return out


def _opt_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _opt_decimal(v: Any) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except Exception:
        return None

