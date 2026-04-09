from __future__ import annotations

from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, CityLocationTable
from data_pipeline.db.records import CityLocationRecord
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage

_TABLES_READY = False


@register_storage(data_type='city_location')
class CityLocationStorage(BaseStorage[CityLocationRecord]):
    name = 'city_location_db'

    async def ensure_tables(self) -> None:
        global _TABLES_READY
        if _TABLES_READY:
            return
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[CityLocationTable.__table__]))
        _TABLES_READY = True

    async def store(self, items: List[CityLocationRecord], ctx: RunContext) -> StoreResult:
        log = get_ctx_logger(__name__, ctx=ctx)
        await self.ensure_tables()

        unique_items = list(_dedupe(items))
        if not unique_items:
            return StoreResult(stored=0, failed=0, error=None)

        rows = [
            {
                'province': item.province,
                'city': item.city,
                'latitude': float(item.latitude),
                'longitude': float(item.longitude),
                'source': item.source,
                'source_url': item.source_url,
            }
            for item in unique_items
        ]

        stored = 0
        failed = 0
        errs: List[ErrorDetail] = []

        async with AsyncSessionLocal() as session:
            if rows:
                try:
                    async with session.begin():
                        stmt = insert(CityLocationTable).values(rows)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['province', 'city'],
                            set_={
                                'latitude': stmt.excluded.latitude,
                                'longitude': stmt.excluded.longitude,
                                'source': stmt.excluded.source,
                                'source_url': stmt.excluded.source_url,
                            },
                        )
                        await session.execute(stmt)
                    stored = len(rows)
                except Exception as exc:
                    log.warning('bulk upsert city_location failed; fallback row-by-row', extra={'error': str(exc)})
                    async with session.begin():
                        for idx, item in enumerate(unique_items):
                            try:
                                existing = await session.execute(
                                    select(CityLocationTable).where(
                                        CityLocationTable.province == item.province,
                                        CityLocationTable.city == item.city,
                                    )
                                )
                                row = existing.scalar_one_or_none()
                                if row is None:
                                    session.add(
                                        CityLocationTable(
                                            province=item.province,
                                            city=item.city,
                                            latitude=float(item.latitude),
                                            longitude=float(item.longitude),
                                            source=item.source,
                                            source_url=item.source_url,
                                        )
                                    )
                                else:
                                    row.latitude = float(item.latitude)
                                    row.longitude = float(item.longitude)
                                    row.source = item.source
                                    row.source_url = item.source_url
                                stored += 1
                            except Exception as row_exc:
                                failed += 1
                                errs.append(
                                    ErrorDetail(
                                        stage='store',
                                        type=type(row_exc).__name__,
                                        message=str(row_exc),
                                        url=ctx.url,
                                        item_index=idx,
                                        traceback_optional=None,
                                    )
                                )

        return StoreResult(
            stored=stored,
            failed=failed,
            error=None if failed == 0 else f'{failed} items failed',
            store_errors=errs,
        )


def _dedupe(items: Iterable[CityLocationRecord]) -> Iterable[CityLocationRecord]:
    seen: dict[tuple[str, str], CityLocationRecord] = {}
    for item in items:
        seen[(item.province, item.city)] = item
    return seen.values()
