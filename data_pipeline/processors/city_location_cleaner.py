from __future__ import annotations

import re
from decimal import Decimal
from typing import List

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.db.records import CityLocationRecord
from data_pipeline.registry.processors import register_processor
from data_pipeline.spiders.city_location_reference import CityLocationRawItem

_PROVINCE_SUFFIX_RE = re.compile(r'(维吾尔自治区|壮族自治区|回族自治区|自治区|特别行政区|省|市)$')
_CITY_SUFFIX_RE = re.compile(r'(自治州|地区|盟|市)$')

_DIRECT_CONTROLLED = {'北京', '上海', '天津', '重庆', '香港', '澳门'}


@register_processor('city_location_reference')
class CityLocationCleaner(BaseProcessor[CityLocationRawItem, CityLocationRecord]):
    name = 'city_location_cleaner'

    def process(self, items: List[CityLocationRawItem], ctx: RunContext) -> List[CityLocationRecord]:
        log = get_ctx_logger(__name__, ctx=ctx)
        deduped: dict[tuple[str, str], CityLocationRecord] = {}

        for idx, item in enumerate(items):
            try:
                province = _normalize_province(item.province)
                city = _normalize_city(item.city)
                if not province:
                    continue
                if not city:
                    city = province
                latitude = Decimal(str(item.latitude))
                longitude = Decimal(str(item.longitude))
                if not _valid_coordinate(latitude=float(latitude), longitude=float(longitude)):
                    continue

                record = CityLocationRecord(
                    province=province,
                    city=_canonical_city_name(province, city),
                    latitude=latitude,
                    longitude=longitude,
                    source=(item.source or 'city_location_reference').strip() or 'city_location_reference',
                    source_url=item.source_url,
                )
                deduped[(record.province, record.city)] = record
            except Exception as exc:
                log.warning('process city location item failed', extra={'item_index': idx, 'error': str(exc)})

        return sorted(deduped.values(), key=lambda x: (x.province, x.city))


def _normalize_province(value: str) -> str:
    text = (value or '').strip()
    if not text:
        return ''
    normalized = _PROVINCE_SUFFIX_RE.sub('', text)
    return normalized or text


def _normalize_city(value: str) -> str:
    text = (value or '').strip()
    if not text:
        return ''
    normalized = _CITY_SUFFIX_RE.sub('', text)
    return normalized or text


def _canonical_city_name(province: str, city: str) -> str:
    if province in _DIRECT_CONTROLLED:
        return province
    return city


def _valid_coordinate(*, latitude: float, longitude: float) -> bool:
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return False
    if latitude == 0 and longitude == 0:
        return False
    return True
