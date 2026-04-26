from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.errors import SkipPipelineError
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider
from data_pipeline.spiders.source_utils import is_placeholder_url


@dataclass(frozen=True, slots=True)
class GenerationRawItem:
    project_name: str
    province: Optional[str] = None
    city: Optional[str] = None
    county: Optional[str] = None
    year: Optional[int] = None
    installed_capacity_kw: Optional[Decimal] = None
    utilization_hours: Optional[Decimal] = None
    annual_generation_kwh: Optional[Decimal] = None
    annual_income_yuan: Optional[Decimal] = None
    project_type: Optional[str] = None
    status: Optional[str] = None
    effective_date: Optional[str] = None
    remark: Optional[str] = None
    source: str = "generation"
    source_url: Optional[str] = None


DEFAULT_GENERATION_SEED_PATH = Path(__file__).resolve().parents[1] / "seeds" / "generation.json"


@register_spider("pv_generation")
class PVGenerationSpider(BaseSpider[dict, GenerationRawItem]):
    name = "pv_generation"
    site = "pv_generation"
    data_type = "generation"

    def __init__(self) -> None:
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> dict:
        log = get_ctx_logger(__name__, ctx=ctx)

        inline_rows = ctx.meta.get("seed_rows")
        if isinstance(inline_rows, list):
            return {"items": inline_rows}

        seed_file = _resolve_seed_file(ctx)
        if seed_file is not None:
            local_items = _load_seed_file(seed_file, log=log, warn_missing=True)
            if local_items:
                return {"items": local_items}

        default_items = _load_seed_file(DEFAULT_GENERATION_SEED_PATH, log=log, warn_missing=True)
        if default_items:
            log.warning(
                "pv_generation structured real source is not configured; using seed fallback",
                extra={"seed_path": str(DEFAULT_GENERATION_SEED_PATH), "url": self._site_url},
            )
            return {"items": default_items}

        if _should_use_seed_fallback(self._site_url):
            raise SkipPipelineError(
                message=f"pv_generation seed fallback is missing: {DEFAULT_GENERATION_SEED_PATH}",
                spider=self.name,
                site=self.site,
                stage=ctx.stage,
                url=self._site_url,
            )

        if self._http is not None and self._request_opt is not None and self._site_url is not None:
            try:
                data = await self._http.get_json(self._site_url, params=None, ctx=ctx, opt=self._request_opt)
                items = _coerce_payload_items(data)
                if items:
                    return {"items": items}
            except Exception as exc:
                log.warning("fetch pv_generation failed, fallback to local seed", extra={"error": str(exc)})

        fallback_items = _load_seed_file(DEFAULT_GENERATION_SEED_PATH, log=log, warn_missing=True)
        if fallback_items:
            return {"items": fallback_items}

        raise SkipPipelineError(
            message=f"pv_generation seed fallback is missing: {DEFAULT_GENERATION_SEED_PATH}",
            spider=self.name,
            site=self.site,
            stage=ctx.stage,
            url=self._site_url,
        )

    def parse(self, raw: dict, ctx: RunContext) -> List[GenerationRawItem]:
        log = get_ctx_logger(__name__, ctx=ctx)
        items_raw = _coerce_payload_items(raw)
        if not isinstance(items_raw, list):
            log.warning("unexpected generation raw format", extra={"type": type(items_raw).__name__})
            return []

        out: List[GenerationRawItem] = []
        for item in items_raw:
            province = _opt_str(item.get("province"))
            city = _opt_str(item.get("city"))
            county = _opt_str(item.get("county"))
            year = _opt_int(item.get("year"))
            project_name = _opt_str(item.get("project_name")) or _build_project_name(province, city, county, year)
            if not project_name or not province or year is None:
                continue

            out.append(
                GenerationRawItem(
                    project_name=project_name,
                    province=province,
                    city=city,
                    county=county,
                    year=year,
                    installed_capacity_kw=_opt_decimal(item.get("installed_capacity_kw") or item.get("capacity_kw")),
                    utilization_hours=_opt_decimal(item.get("utilization_hours")),
                    annual_generation_kwh=_opt_decimal(item.get("annual_generation_kwh")),
                    annual_income_yuan=_opt_decimal(item.get("annual_income_yuan")),
                    project_type=_opt_str(item.get("project_type")),
                    status=_opt_str(item.get("status")),
                    effective_date=_opt_str(item.get("effective_date")) or str(year),
                    remark=_opt_str(item.get("remark")),
                    source=_opt_str(item.get("source")) or "generation",
                    source_url=_opt_str(item.get("source_url")) or ctx.url,
                )
            )

        log.info("parsed generation items", extra={"count": len(out)})
        return out


def _resolve_seed_file(ctx: RunContext) -> Optional[Path]:
    raw = ctx.meta.get("seed_file") or ctx.meta.get("local_file")
    if raw is None:
        return None
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _load_seed_file(path: Path, *, log, warn_missing: bool = False) -> list[dict[str, Any]]:
    if not path.exists():
        if warn_missing:
            log.warning("generation seed file missing", extra={"path": str(path)})
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        items = _coerce_payload_items(payload)
        for item in items:
            if not item.get('source'):
                item['source'] = 'seed_estimated'
        if items:
            log.info("loaded generation seed file", extra={"path": str(path), "count": len(items)})
        return items
    except Exception as exc:
        log.warning("load generation seed file failed", extra={"path": str(path), "error": str(exc)})
        return []


def _coerce_payload_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        maybe_items = payload.get("items")
        if isinstance(maybe_items, list):
            payload = maybe_items
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _should_use_seed_fallback(url: Optional[str]) -> bool:
    if not url:
        return True
    normalized = url.rstrip("/").lower()
    return is_placeholder_url(url) or normalized == "https://data.stats.gov.cn"


def _build_project_name(
    province: Optional[str],
    city: Optional[str],
    county: Optional[str],
    year: Optional[int],
) -> Optional[str]:
    parts = [part for part in (province, city, county) if part]
    if not parts or year is None:
        return None
    return f"{''.join(parts)}光伏扶贫项目-{year}"


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _opt_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _opt_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except Exception:
        return None
