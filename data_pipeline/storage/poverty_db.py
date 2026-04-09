from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import and_, select

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, PovertyCountyTable
from data_pipeline.db.records import PovertyCountyRecord
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage


@register_storage(data_type='poverty_county')
class PovertyCountyStorage(BaseStorage[PovertyCountyRecord]):
    name = 'poverty_county_db'

    async def ensure_tables(self) -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def store(self, items: List[PovertyCountyRecord], ctx: RunContext) -> StoreResult:
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
                            select(PovertyCountyTable).where(
                                and_(
                                    PovertyCountyTable.province == item.province,
                                    PovertyCountyTable.city == item.city,
                                    PovertyCountyTable.county == item.county,
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
                        log.warning('store poverty item failed', extra={'item_index': idx, 'error': str(exc)})

        return StoreResult(stored=stored, failed=failed, error=None if failed == 0 else f'{failed} items failed', store_errors=errs)


def _to_row(item: PovertyCountyRecord) -> PovertyCountyTable:
    return PovertyCountyTable(
        province=item.province,
        city=item.city,
        county=item.county,
        population=item.population,
        income_per_capita_yuan=_fopt(item.income_per_capita_yuan),
        energy_condition=item.energy_condition,
        tags=item.tags,
        adcode=item.adcode,
        source=item.source,
        source_url=item.source_url,
    )


def _apply_update(row: PovertyCountyTable, item: PovertyCountyRecord) -> None:
    row.population = item.population
    row.income_per_capita_yuan = _fopt(item.income_per_capita_yuan)
    row.energy_condition = item.energy_condition
    row.tags = item.tags
    row.adcode = item.adcode
    row.source = item.source
    row.source_url = item.source_url


def _dedupe(items: Iterable[PovertyCountyRecord]) -> Iterable[PovertyCountyRecord]:
    seen: dict[tuple[str, str | None, str], PovertyCountyRecord] = {}
    for item in items:
        seen[(item.province, item.city, item.county)] = item
    return seen.values()


def _fopt(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None
