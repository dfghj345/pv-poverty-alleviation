from __future__ import annotations

import re
from decimal import Decimal
from typing import List, Optional

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.db.records import PovertyCountyRecord
from data_pipeline.registry.processors import register_processor
from data_pipeline.spiders.poverty_regions import PovertyRawItem


_PROVINCE_SUFFIX_RE = re.compile(r"(省|市|自治区|特别行政区)$")


@register_processor("poverty_regions")
class PovertyCleaner(BaseProcessor[PovertyRawItem, PovertyCountyRecord]):
    name = "poverty_cleaner"

    def process(self, items: List[PovertyRawItem], ctx: RunContext) -> List[PovertyCountyRecord]:
        log = get_ctx_logger(__name__, ctx=ctx)
        out: List[PovertyCountyRecord] = []
        for idx, it in enumerate(items):
            try:
                prov = (it.province or "").strip()
                prov2 = _PROVINCE_SUFFIX_RE.sub("", prov) or prov
                county = (it.county or "").strip()
                if not prov2 or not county:
                    continue
                out.append(
                    PovertyCountyRecord(
                        province=prov2,
                        city=_norm_opt(it.city),
                        county=county,
                        population=it.population if (it.population is None or it.population >= 0) else None,
                        income_per_capita_yuan=_nonneg_opt_decimal(it.income_per_capita_yuan),
                        energy_condition=_norm_opt(it.energy_condition),
                        tags=_norm_opt(it.tags),
                        adcode=_norm_opt(it.adcode),
                        source="poverty_dataset",
                        source_url=it.source_url,
                    )
                )
            except Exception as e:
                log.warning("process poverty item failed", extra={"item_index": idx, "error": str(e)})
        return out


def _norm_opt(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = v.strip()
    return s or None


def _nonneg_opt_decimal(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return v if v >= 0 else None
    except Exception:
        return None

