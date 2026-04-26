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
from data_pipeline.spiders.source_utils import is_placeholder_url


@dataclass(frozen=True, slots=True)
class PolicyTariffRawItem:
    province: str
    benchmark_price_yuan_per_kwh: Decimal
    subsidy_yuan_per_kwh: Optional[Decimal] = None
    policy_date: Optional[str] = None
    policy_type: Optional[str] = None
    source: str = 'policy_tariff_reference'
    source_url: Optional[str] = None


DEFAULT_POLICY_TARIFF_SEED_PATH = (
    Path(__file__).resolve().parents[1] / 'seeds' / 'policy_tariff' / 'policy_tariff_seed.json'
)

EMBEDDED_POLICY_ITEMS: tuple[dict[str, object], ...] = ()


@register_spider('policy_tariff_reference')
class PolicyTariffReferenceSpider(BaseSpider[dict, PolicyTariffRawItem]):
    name = 'policy_tariff_reference'
    site = 'policy_tariff_reference'
    data_type = 'policy'

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
            local_items = _load_seed_file(seed_file, log=log, warn_missing=True)
            if local_items:
                return {'items': local_items}

        if is_placeholder_url(self._site_url):
            default_items = _load_seed_file(DEFAULT_POLICY_TARIFF_SEED_PATH, log=log, warn_missing=True)
            if default_items:
                log.warning(
                    'policy_table real data source is not configured; using seed fallback',
                    extra={'seed_path': str(DEFAULT_POLICY_TARIFF_SEED_PATH), 'url': self._site_url},
                )
                return {'items': default_items}
            log.warning('policy_table seed fallback is missing', extra={'seed_path': str(DEFAULT_POLICY_TARIFF_SEED_PATH), 'url': self._site_url})
            return {'items': []}

        if self._http is not None and self._request_opt is not None and self._site_url is not None:
            try:
                data = await self._http.get_json(self._site_url, params=None, ctx=ctx, opt=self._request_opt)
                items = _coerce_payload_items(data)
                if items:
                    return {'items': items}
            except Exception as exc:
                log.warning('fetch policy tariff failed, fallback to local seed', extra={'error': str(exc)})

        default_items = _load_seed_file(DEFAULT_POLICY_TARIFF_SEED_PATH, log=log, warn_missing=True)
        if default_items:
            return {'items': default_items}

        log.warning('policy_table seed fallback is missing', extra={'seed_path': str(DEFAULT_POLICY_TARIFF_SEED_PATH)})
        return {'items': list(EMBEDDED_POLICY_ITEMS)}

    def parse(self, raw: dict, ctx: RunContext) -> List[PolicyTariffRawItem]:
        log = get_ctx_logger(__name__, ctx=ctx)
        items_raw = _coerce_payload_items(raw)
        if not isinstance(items_raw, list):
            log.warning('unexpected policy tariff raw format', extra={'type': type(items_raw).__name__})
            return []

        out: List[PolicyTariffRawItem] = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            province = str(item.get('province') or '').strip()
            price = _opt_decimal(item.get('benchmark_price_yuan_per_kwh') or item.get('price'))
            if not province or price is None:
                continue
            out.append(
                PolicyTariffRawItem(
                    province=province,
                    benchmark_price_yuan_per_kwh=price,
                    subsidy_yuan_per_kwh=_opt_decimal(item.get('subsidy_yuan_per_kwh') or item.get('subsidy')),
                    policy_date=_opt_str(item.get('policy_date')),
                    policy_type=_opt_str(item.get('policy_type')),
                    source=_opt_str(item.get('source')) or 'policy_tariff_reference',
                    source_url=_opt_str(item.get('source_url')) or ctx.url,
                )
            )

        log.info('parsed policy tariff items', extra={'count': len(out)})
        return out


def _resolve_seed_file(ctx: RunContext) -> Optional[Path]:
    raw = ctx.meta.get('seed_file') or ctx.meta.get('local_file')
    if raw is None:
        return None
    path = Path(str(raw)).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _load_seed_file(path: Path, *, log, warn_missing: bool = False) -> list[dict[str, Any]]:
    if not path.exists():
        if warn_missing:
            log.warning('policy tariff seed file missing', extra={'path': str(path)})
        return []
    try:
        payload = json.loads(path.read_text(encoding='utf-8-sig'))
        items = _coerce_payload_items(payload)
        if items:
            log.info('loaded policy tariff seed file', extra={'path': str(path), 'count': len(items)})
        return items
    except Exception as exc:
        log.warning('load policy tariff seed file failed', extra={'path': str(path), 'error': str(exc)})
        return []


def _coerce_payload_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        maybe_items = payload.get('items')
        if isinstance(maybe_items, list):
            payload = maybe_items
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _opt_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value).strip())
    except Exception:
        return None


def _opt_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
