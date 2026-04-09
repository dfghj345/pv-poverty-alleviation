from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, List, Optional

from data_pipeline.base.spider import BaseSpider
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.request import HttpClient, RequestOptions
from data_pipeline.registry.spiders import register_spider


@dataclass(frozen=True, slots=True)
class CityLocationRawItem:
    province: str
    city: str
    latitude: Decimal
    longitude: Decimal
    source: str = 'city_location_reference'
    source_url: Optional[str] = None


DEFAULT_CITY_LOCATION_SEED_PATH = (
    Path(__file__).resolve().parents[1] / 'seeds' / 'city_location' / 'city_location_seed.json'
)

EMBEDDED_FALLBACK_ITEMS: tuple[dict[str, object], ...] = (
    {'province': '北京市', 'city': '北京市', 'latitude': 39.9042, 'longitude': 116.4074, 'source': 'embedded_fallback'},
    {'province': '上海市', 'city': '上海市', 'latitude': 31.2304, 'longitude': 121.4737, 'source': 'embedded_fallback'},
    {'province': '广东省', 'city': '广州市', 'latitude': 23.1291, 'longitude': 113.2644, 'source': 'embedded_fallback'},
    {'province': '江苏省', 'city': '南京市', 'latitude': 32.0603, 'longitude': 118.7969, 'source': 'embedded_fallback'},
    {'province': '四川省', 'city': '成都市', 'latitude': 30.5728, 'longitude': 104.0668, 'source': 'embedded_fallback'},
)


@register_spider('city_location_reference')
class CityLocationReferenceSpider(BaseSpider[dict, CityLocationRawItem]):
    """
    Province-city to coordinate mapping source for region/weather lookup.

    Priority:
    1. ctx.meta['seed_rows'] inline seed payload
    2. ctx.meta['seed_file'] local JSON file
    3. remote JSON source configured in sites.py
    4. default seed file under data_pipeline/seeds/city_location/
    5. embedded fallback items
    """

    name = 'city_location_reference'
    site = 'city_location_reference'
    data_type = 'city_location'

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
                log.warning('fetch city location failed, fallback to local seed', extra={'error': str(exc)})

        default_items = _load_seed_file(DEFAULT_CITY_LOCATION_SEED_PATH, log=log)
        if default_items:
            return {'items': default_items}

        return {'items': list(EMBEDDED_FALLBACK_ITEMS)}

    def parse(self, raw: dict, ctx: RunContext) -> List[CityLocationRawItem]:
        log = get_ctx_logger(__name__, ctx=ctx)
        items_raw = _coerce_payload_items(raw)
        if not isinstance(items_raw, list):
            log.warning('unexpected city location format', extra={'type': type(items_raw).__name__})
            return []

        out: List[CityLocationRawItem] = []
        for item in items_raw:
            if not isinstance(item, dict):
                continue
            province = str(item.get('province') or '').strip()
            city = str(item.get('city') or '').strip()
            latitude = _opt_decimal(item.get('latitude'))
            longitude = _opt_decimal(item.get('longitude'))
            if not province or not city or latitude is None or longitude is None:
                continue
            out.append(
                CityLocationRawItem(
                    province=province,
                    city=city,
                    latitude=latitude,
                    longitude=longitude,
                    source=str(item.get('source') or 'city_location_reference').strip() or 'city_location_reference',
                    source_url=str(item.get('source_url') or ctx.url or '').strip() or None,
                )
            )

        log.info('parsed city location items', extra={'count': len(out)})
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
            log.info('loaded city location seed file', extra={'path': str(path), 'count': len(items)})
        return items
    except Exception as exc:
        log.warning('load city location seed file failed', extra={'path': str(path), 'error': str(exc)})
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
