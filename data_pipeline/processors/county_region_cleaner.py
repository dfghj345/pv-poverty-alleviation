from __future__ import annotations

import re
from decimal import Decimal
from typing import List, Optional

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.db.records import PovertyCountyRecord
from data_pipeline.registry.processors import register_processor
from data_pipeline.spiders.county_region_reference import CountyRegionRawItem

_PROVINCE_SUFFIX_RE = re.compile("(\u7ef4\u543e\u5c14\u81ea\u6cbb\u533a|\u58ee\u65cf\u81ea\u6cbb\u533a|\u56de\u65cf\u81ea\u6cbb\u533a|\u81ea\u6cbb\u533a|\u7279\u522b\u884c\u653f\u533a|\u7701|\u5e02)$")
_CITY_SUFFIX_RE = re.compile("(\u81ea\u6cbb\u5dde|\u5730\u533a|\u76df|\u5e02)$")


@register_processor('county_region_reference')
class CountyRegionCleaner(BaseProcessor[CountyRegionRawItem, PovertyCountyRecord]):
    name = 'county_region_cleaner'

    def process(self, items: List[CountyRegionRawItem], ctx: RunContext) -> List[PovertyCountyRecord]:
        log = get_ctx_logger(__name__, ctx=ctx)
        deduped: dict[tuple[str, str | None, str], PovertyCountyRecord] = {}

        for idx, item in enumerate(items):
            try:
                province = _normalize_province(item.province)
                city = _normalize_city(item.city)
                county = (item.county or '').strip()
                if not province or not county:
                    continue
                record = PovertyCountyRecord(
                    province=province,
                    city=city,
                    county=county,
                    population=item.population if (item.population is None or item.population >= 0) else None,
                    income_per_capita_yuan=_nonneg_opt_decimal(item.income_per_capita_yuan),
                    energy_condition=_norm_opt(item.energy_condition),
                    tags=_norm_opt(item.tags),
                    adcode=_norm_opt(item.adcode),
                    source=(item.source or 'county_region_reference').strip() or 'county_region_reference',
                    source_url=item.source_url,
                )
                deduped[(record.province, record.city, record.county)] = record
            except Exception as exc:
                log.warning('process county region item failed', extra={'item_index': idx, 'error': str(exc)})

        return sorted(deduped.values(), key=lambda x: (x.province, x.city or '', x.county))


def _normalize_province(value: str) -> str:
    text = (value or '').strip()
    if not text:
        return ''
    normalized = _PROVINCE_SUFFIX_RE.sub('', text)
    return normalized or text


def _normalize_city(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    normalized = _CITY_SUFFIX_RE.sub('', text)
    return normalized or text


def _norm_opt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _nonneg_opt_decimal(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return value if value >= 0 else None
    except Exception:
        return None
