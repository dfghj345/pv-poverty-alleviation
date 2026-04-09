from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import and_, select

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, CostTable
from data_pipeline.db.records import CostRecord
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage


@register_storage(data_type='cost')
class CostStorage(BaseStorage[CostRecord]):
    name = 'cost_db'

    async def ensure_tables(self) -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def store(self, items: List[CostRecord], ctx: RunContext) -> StoreResult:
        log = get_ctx_logger(__name__, ctx=ctx)
        await self.ensure_tables()

        unique_items = list(_dedupe(items))
        stored = 0
        failed = 0
        errs: List[ErrorDetail] = []
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for idx, item in enumerate(unique_items):
                    try:
                        existing = await session.execute(
                            select(CostTable).where(
                                and_(
                                    CostTable.name == item.name,
                                    CostTable.category == item.category,
                                    CostTable.province == item.province,
                                    CostTable.source == item.source,
                                )
                            )
                        )
                        row = existing.scalar_one_or_none()
                        if row is None:
                            session.add(_to_row(item))
                        else:
                            _apply_update(row, item)
                        stored += 1
                    except Exception as exc:
                        failed += 1
                        errs.append(
                            ErrorDetail(
                                stage='store',
                                type=type(exc).__name__,
                                message=str(exc),
                                url=ctx.url,
                                item_index=idx,
                                traceback_optional=None,
                            )
                        )
                        log.warning('store cost item failed', extra={'item_index': idx, 'error': str(exc)})

        return StoreResult(stored=stored, failed=failed, error=None if failed == 0 else f'{failed} items failed', store_errors=errs)


def _to_row(item: CostRecord) -> CostTable:
    return CostTable(
        name=item.name,
        category=item.category,
        province=item.province,
        unit_cost_yuan_per_kw=_fopt(item.unit_cost_yuan_per_kw),
        component_price_yuan_per_w=_fopt(item.component_price_yuan_per_w),
        effective_date=item.effective_date,
        source=item.source,
        source_url=item.source_url,
    )


def _apply_update(row: CostTable, item: CostRecord) -> None:
    row.unit_cost_yuan_per_kw = _fopt(item.unit_cost_yuan_per_kw)
    row.component_price_yuan_per_w = _fopt(item.component_price_yuan_per_w)
    row.effective_date = item.effective_date
    row.source = item.source
    row.source_url = item.source_url


def _dedupe(items: Iterable[CostRecord]) -> Iterable[CostRecord]:
    seen: dict[tuple[str, str, str | None, str], CostRecord] = {}
    for item in items:
        seen[(item.name, item.category, item.province, item.source)] = item
    return seen.values()


def _fopt(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None
