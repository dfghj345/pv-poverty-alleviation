from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy import select

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, EnergyPolicyTable
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage

_TABLES_READY = False


@dataclass(slots=True, frozen=True)
class EnergyPolicyRow:
    title: str
    url: str
    publish_date: Optional[str] = None
    summary: Optional[str] = None
    source: str = "nea"
    source_url: Optional[str] = None


@register_storage(spider="energy_gov", site="energy_gov", data_type="energy_policy")
class EnergyPolicyStorage(BaseStorage[EnergyPolicyRow]):
    name = "energy_policy_db"

    async def ensure_tables(self) -> None:
        global _TABLES_READY
        if _TABLES_READY:
            return
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[EnergyPolicyTable.__table__]))
        _TABLES_READY = True

    async def store(self, items: List[EnergyPolicyRow], ctx: RunContext) -> StoreResult:
        log = get_ctx_logger(__name__, ctx=ctx)
        await self.ensure_tables()

        stored = 0
        failed = 0
        errs: List[ErrorDetail] = []
        async with AsyncSessionLocal() as session:
            async with session.begin():
                for idx, it in enumerate(items):
                    try:
                        existing = await session.execute(select(EnergyPolicyTable).where(EnergyPolicyTable.url == it.url))
                        row = existing.scalar_one_or_none()
                        if row is None:
                            session.add(
                                EnergyPolicyTable(
                                    title=it.title,
                                    url=it.url,
                                    publish_date=it.publish_date,
                                    summary=it.summary,
                                    source=it.source,
                                    source_url=it.source_url,
                                )
                            )
                        else:
                            row.title = it.title
                            row.publish_date = it.publish_date
                            row.summary = it.summary
                            row.source = it.source
                            row.source_url = it.source_url
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
                        log.warning("store policy item failed", extra={"item_index": idx, "error": str(e)})

        return StoreResult(stored=stored, failed=failed, error=None if failed == 0 else f"{failed} items failed", store_errors=errs)

