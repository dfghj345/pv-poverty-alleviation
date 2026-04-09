from __future__ import annotations

from typing import List, Optional

from sqlalchemy import and_, select

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, GenerationTable
from data_pipeline.db.records import GenerationRecord
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage


@register_storage(data_type="generation")
class GenerationStorage(BaseStorage[GenerationRecord]):
    name = "generation_db"

    async def ensure_tables(self) -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def store(self, items: List[GenerationRecord], ctx: RunContext) -> StoreResult:
        log = get_ctx_logger(__name__, ctx=ctx)
        await self.ensure_tables()

        stored = 0
        failed = 0
        errs: List[ErrorDetail] = []
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for idx, it in enumerate(items):
                    try:
                        existing = await session.execute(
                            select(GenerationTable).where(
                                and_(
                                    GenerationTable.project_name == it.project_name,
                                    GenerationTable.province == it.province,
                                    GenerationTable.effective_date == it.effective_date,
                                    GenerationTable.source == it.source,
                                )
                            )
                        )
                        row = existing.scalar_one_or_none()
                        if row is None:
                            session.add(_to_row(it))
                        else:
                            _apply_update(row, it)
                        stored += 1
                    except Exception as e:
                        failed += 1
                        errs.append(
                            ErrorDetail(
                                stage="store",
                                type=type(e).__name__,
                                message=str(e),
                                url=ctx.url,
                                item_index=idx,
                                traceback_optional=None,
                            )
                        )
                        log.warning("store generation item failed", extra={"item_index": idx, "error": str(e)})

        return StoreResult(stored=stored, failed=failed, error=None if failed == 0 else f"{failed} items failed", store_errors=errs)


def _to_row(it: GenerationRecord) -> GenerationTable:
    return GenerationTable(
        project_name=it.project_name,
        province=it.province,
        capacity_kw=_fopt(it.capacity_kw),
        annual_generation_kwh=_fopt(it.annual_generation_kwh),
        annual_income_yuan=_fopt(it.annual_income_yuan),
        project_type=it.project_type,
        status=it.status,
        effective_date=it.effective_date,
        source=it.source,
        source_url=it.source_url,
    )


def _apply_update(row: GenerationTable, it: GenerationRecord) -> None:
    row.capacity_kw = _fopt(it.capacity_kw)
    row.annual_generation_kwh = _fopt(it.annual_generation_kwh)
    row.annual_income_yuan = _fopt(it.annual_income_yuan)
    row.project_type = it.project_type
    row.status = it.status
    row.source_url = it.source_url


def _fopt(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except Exception:
        return None

