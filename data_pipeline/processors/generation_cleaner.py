from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.db.records import GenerationRecord
from data_pipeline.registry.processors import register_processor
from data_pipeline.spiders.pv_generation import GenerationRawItem


@register_processor("pv_generation")
class GenerationCleaner(BaseProcessor[GenerationRawItem, GenerationRecord]):
    name = "generation_cleaner"

    def process(self, items: List[GenerationRawItem], ctx: RunContext) -> List[GenerationRecord]:
        log = get_ctx_logger(__name__, ctx=ctx)
        out: List[GenerationRecord] = []
        for idx, it in enumerate(items):
            try:
                out.append(
                    GenerationRecord(
                        project_name=it.project_name.strip(),
                        province=_norm_opt(it.province),
                        capacity_kw=_nonneg_opt(it.capacity_kw),
                        annual_generation_kwh=_nonneg_opt(it.annual_generation_kwh),
                        annual_income_yuan=_nonneg_opt(it.annual_income_yuan),
                        project_type=_norm_opt(it.project_type),
                        status=_norm_opt(it.status),
                        effective_date=_norm_opt(it.effective_date),
                        source="generation",
                        source_url=it.source_url,
                    )
                )
            except Exception as e:
                log.warning("process generation item failed", extra={"item_index": idx, "error": str(e)})
        return out


def _norm_opt(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    s = v.strip()
    return s or None


def _nonneg_opt(v: Optional[Decimal]) -> Optional[Decimal]:
    if v is None:
        return None
    try:
        return v if v >= 0 else None
    except Exception:
        return None

