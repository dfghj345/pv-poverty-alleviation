from __future__ import annotations

import re
from decimal import Decimal
from typing import List, Optional

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.db.records import CostRecord
from data_pipeline.registry.processors import register_processor
from data_pipeline.spiders.pv_costs import CostRawItem

_PROVINCE_SUFFIX_RE = re.compile("(\u7ef4\u543e\u5c14\u81ea\u6cbb\u533a|\u58ee\u65cf\u81ea\u6cbb\u533a|\u56de\u65cf\u81ea\u6cbb\u533a|\u81ea\u6cbb\u533a|\u7279\u522b\u884c\u653f\u533a|\u7701|\u5e02)$")


@register_processor('pv_costs')
class CostCleaner(BaseProcessor[CostRawItem, CostRecord]):
    name = 'cost_cleaner'

    def process(self, items: List[CostRawItem], ctx: RunContext) -> List[CostRecord]:
        log = get_ctx_logger(__name__, ctx=ctx)
        deduped: dict[tuple[str, str, str | None, str], CostRecord] = {}
        for idx, item in enumerate(items):
            try:
                name = item.name.strip()
                category = item.category.strip()
                province = _normalize_province(item.province)
                if not name or not category:
                    continue
                record = CostRecord(
                    name=name,
                    category=category,
                    province=province,
                    unit_cost_yuan_per_kw=_nonneg_opt(item.unit_cost_yuan_per_kw),
                    component_price_yuan_per_w=_nonneg_opt(item.component_price_yuan_per_w),
                    effective_date=_norm_opt(item.effective_date),
                    source=(item.source or 'pv_costs').strip() or 'pv_costs',
                    source_url=item.source_url,
                )
                deduped[(record.name, record.category, record.province, record.source)] = record
            except Exception as exc:
                log.warning('process cost item failed', extra={'item_index': idx, 'error': str(exc)})
        return sorted(deduped.values(), key=lambda x: (x.category, x.province or '', x.name, x.source))


def _normalize_province(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    normalized = _PROVINCE_SUFFIX_RE.sub('', text)
    return normalized or text


def _norm_opt(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _nonneg_opt(value: Optional[Decimal]) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return value if value >= 0 else None
    except Exception:
        return None
