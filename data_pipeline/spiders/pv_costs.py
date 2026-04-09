from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, List, Optional

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider


@dataclass(frozen=True, slots=True)
class CostRawItem:
    name: str
    category: str
    province: Optional[str] = None
    unit_cost_yuan_per_kw: Optional[Decimal] = None
    component_price_yuan_per_w: Optional[Decimal] = None
    effective_date: Optional[str] = None
    source: str = 'pv_costs'
    source_url: Optional[str] = None


DEFAULT_COST_SEED_PATH = Path(__file__).resolve().parents[1] / 'seeds' / 'cost' / 'cost_seed.json'

EMBEDDED_COST_ITEMS: tuple[dict[str, object], ...] = ()


@register_spider('pv_costs')
class PVCostSpider(BaseSpider[dict, CostRawItem]):
    name = 'pv_costs'
    site = 'pv_costs'
    data_type = 'cost'
    enabled = False
    disabled_reason = 'online crawl is still placeholder-heavy; use seed import first'

    def __init__(self) -> None:
        self._http: HttpClient | None = None
        self._request_opt: RequestOptions | None = None
        self._site_url: str | None = None

    async def fetch(self, ctx: RunContext) -> dict:
        log = get_ctx_logger(__name__, ctx=ctx)

        inline_rows = ctx.meta.get('seed_rows')
        if isinstance(inline_rows, list):
            return {'items': inline_rows}

        seed_file = _resolve_seed_file(ctx)
        if seed_file is not None:
            local_items = _load_seed_file(seed_file, log=log)
            if local_items:
                return {'items': local_items}

        if self._http is not None and self._request_opt is not None and self._site_url is not None:
            try:
                data = await self._http.get_json(self._site_url, params=None, ctx=ctx, opt=self._request_opt)
                items = _coerce_payload_items(data)
                if items:
                    return {'items': items}
            except Exception as exc:
                log.warning('fetch pv costs failed, fallback to local seed', extra={'error': str(exc)})

        default_items = _load_seed_file(DEFAULT_COST_SEED_PATH, log=log)
        if default_items:
            return {'items': default_items}

        return {'items': list(EMBEDDED_COST_ITEMS)}

    def parse(self, raw: dict, ctx: RunContext) -> List[CostRawItem]:
        log = get_ctx_logger(__name__, ctx=ctx)
        items_raw = _coerce_payload_items(raw)
        if not isinstance(items_raw, list):
            log.warning('unexpected cost raw format', extra={'type': type(items_raw).__name__})
            return []

        out: List[CostRawItem] = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get('name') or '').strip()
            category = str(item.get('category') or '').strip()
            if not name or not category:
                continue
            out.append(
                CostRawItem(
                    name=name,
                    category=category,
                    province=_opt_str(item.get('province')),
                    unit_cost_yuan_per_kw=_opt_decimal(item.get('unit_cost_yuan_per_kw')),
                    component_price_yuan_per_w=_opt_decimal(item.get('component_price_yuan_per_w')),
                    effective_date=_opt_str(item.get('effective_date')),
                    source=_opt_str(item.get('source')) or 'pv_costs',
                    source_url=_opt_str(item.get('source_url')) or ctx.url,
                )
            )
        log.info('parsed pv cost items', extra={'count': len(out)})
        return out


def _resolve_seed_file(ctx: RunContext) -> Optional[Path]:
    raw = ctx.meta.get('seed_file') or ctx.meta.get('local_file')
    if raw is None:
        return None
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _load_seed_file(path: Path, *, log) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding='utf-8-sig'))
        items = _coerce_payload_items(payload)
        if items:
            log.info('loaded cost seed file', extra={'path': str(path), 'count': len(items)})
        return items
    except Exception as exc:
        log.warning('load cost seed file failed', extra={'path': str(path), 'error': str(exc)})
        return []


def _coerce_payload_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        maybe_items = payload.get('items')
        if isinstance(maybe_items, list):
            payload = maybe_items
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _opt_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except Exception:
        return None
