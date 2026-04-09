from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from sqlalchemy.dialects.postgresql import insert

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, PolicyTable
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage


@dataclass(slots=True)
class PolicyRow:
    province: str
    price: float
    subsidy: Optional[float] = None
    policy_date: Optional[str] = None
    policy_type: Optional[str] = None
    source_url: Optional[str] = None


@register_storage(data_type='policy')
class PolicyStorage(BaseStorage[PolicyRow]):
    name = 'policy_db'

    async def ensure_tables(self) -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def store(self, items: List[PolicyRow], ctx: RunContext) -> StoreResult:
        log = get_ctx_logger(__name__, ctx=ctx)
        await self.ensure_tables()

        unique_items = list(_dedupe(items))
        if not unique_items:
            return StoreResult(stored=0, failed=0, error=None)

        rows = [
            {
                'province': item.province,
                'price': item.price,
                'subsidy': item.subsidy,
                'policy_date': item.policy_date,
                'policy_type': item.policy_type,
                'source_url': item.source_url,
            }
            for item in unique_items
        ]

        stored = 0
        failed = 0
        errs: List[ErrorDetail] = []

        async with AsyncSessionLocal() as session:
            try:
                async with session.begin():
                    stmt = insert(PolicyTable).values(rows)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['province'],
                        set_={
                            'price': stmt.excluded.price,
                            'subsidy': stmt.excluded.subsidy,
                            'policy_date': stmt.excluded.policy_date,
                            'policy_type': stmt.excluded.policy_type,
                            'source_url': stmt.excluded.source_url,
                        },
                    )
                    await session.execute(stmt)
                stored = len(rows)
            except Exception as exc:
                failed = len(rows)
                errs.append(
                    ErrorDetail(
                        stage='store',
                        type=type(exc).__name__,
                        message=str(exc),
                        url=ctx.url,
                        item_index=None,
                        traceback_optional=None,
                    )
                )
                log.warning('bulk upsert policy items failed', extra={'error': str(exc)})

        return StoreResult(
            stored=stored,
            failed=failed,
            error=None if failed == 0 else f'{failed} items failed',
            store_errors=errs,
        )


def _dedupe(items: Iterable[PolicyRow]) -> Iterable[PolicyRow]:
    seen: dict[str, PolicyRow] = {}
    for item in items:
        seen[item.province] = item
    return seen.values()
