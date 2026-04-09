from __future__ import annotations

import re
from typing import List

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.registry.processors import register_processor
from data_pipeline.spiders.policy_tariff_reference import PolicyTariffRawItem
from data_pipeline.storage.db import PolicyRow

_PROVINCE_SUFFIX_RE = re.compile("(\u7ef4\u543e\u5c14\u81ea\u6cbb\u533a|\u58ee\u65cf\u81ea\u6cbb\u533a|\u56de\u65cf\u81ea\u6cbb\u533a|\u81ea\u6cbb\u533a|\u7279\u522b\u884c\u653f\u533a|\u7701|\u5e02)$")


@register_processor('policy_tariff_reference')
class PolicyTariffCleaner(BaseProcessor[PolicyTariffRawItem, PolicyRow]):
    name = 'policy_tariff_cleaner'

    def process(self, items: List[PolicyTariffRawItem], ctx: RunContext) -> List[PolicyRow]:
        log = get_ctx_logger(__name__, ctx=ctx)
        deduped: dict[str, PolicyRow] = {}
        for idx, item in enumerate(items):
            try:
                province = _normalize_province(item.province)
                price = float(item.benchmark_price_yuan_per_kwh)
                subsidy = float(item.subsidy_yuan_per_kwh) if item.subsidy_yuan_per_kwh is not None else None
                if not province or price < 0:
                    continue
                deduped[province] = PolicyRow(
                    province=province,
                    price=price,
                    subsidy=subsidy,
                    policy_date=item.policy_date,
                    policy_type=item.policy_type or 'seed_baseline',
                    source_url=item.source_url,
                )
            except Exception as exc:
                log.warning('process policy tariff item failed', extra={'item_index': idx, 'error': str(exc)})
        return [deduped[key] for key in sorted(deduped)]


def _normalize_province(value: str) -> str:
    text = (value or '').strip()
    if not text:
        return ''
    normalized = _PROVINCE_SUFFIX_RE.sub('', text)
    return normalized or text
