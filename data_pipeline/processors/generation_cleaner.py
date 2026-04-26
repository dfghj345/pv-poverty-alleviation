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
        for idx, item in enumerate(items):
            try:
                year = item.year
                out.append(
                    GenerationRecord(
                        project_name=item.project_name.strip(),
                        province=_norm_opt(item.province),
                        city=_norm_opt(item.city),
                        county=_norm_opt(item.county),
                        year=year,
                        installed_capacity_kw=_nonneg_opt(item.installed_capacity_kw),
                        utilization_hours=_nonneg_opt(item.utilization_hours),
                        capacity_kw=_nonneg_opt(item.installed_capacity_kw),
                        annual_generation_kwh=_nonneg_opt(item.annual_generation_kwh),
                        annual_income_yuan=_nonneg_opt(item.annual_income_yuan),
                        project_type=_norm_opt(item.project_type),
                        status=_norm_opt(item.status),
                        effective_date=_norm_opt(item.effective_date) or (str(year) if year is not None else None),
                        source=_norm_opt(item.source) or "generation",
                        remark=_norm_opt(item.remark),
                        source_url=item.source_url,
                    )
                )
            except Exception as exc:
                log.warning("process generation item failed", extra={"item_index": idx, "error": str(exc)})
        return out


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
