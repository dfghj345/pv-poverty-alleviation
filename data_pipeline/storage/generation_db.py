from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import and_, select, text

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, GenerationTable, PolicyTable
from data_pipeline.db.records import GenerationRecord
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage


DEFAULT_FEED_IN_TARIFF = Decimal("0.35")


@register_storage(data_type="generation")
class GenerationStorage(BaseStorage[GenerationRecord]):
    name = "generation_db"

    async def ensure_tables(self) -> None:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("ALTER TABLE generation_table ADD COLUMN IF NOT EXISTS city VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE generation_table ADD COLUMN IF NOT EXISTS county VARCHAR(100)"))
            await conn.execute(text("ALTER TABLE generation_table ADD COLUMN IF NOT EXISTS year INTEGER"))
            await conn.execute(text("ALTER TABLE generation_table ADD COLUMN IF NOT EXISTS installed_capacity_kw NUMERIC(14, 3)"))
            await conn.execute(text("ALTER TABLE generation_table ADD COLUMN IF NOT EXISTS utilization_hours NUMERIC(10, 3)"))
            await conn.execute(text("ALTER TABLE generation_table ADD COLUMN IF NOT EXISTS remark VARCHAR(1000)"))
            await conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_generation_region_year_unique "
                    "ON generation_table (province, city, county, year)"
                )
            )

    async def store(self, items: List[GenerationRecord], ctx: RunContext) -> StoreResult:
        log = get_ctx_logger(__name__, ctx=ctx)
        await self.ensure_tables()

        stored = 0
        failed = 0
        errors: List[ErrorDetail] = []

        async with AsyncSessionLocal() as session:
            tariff_map = await _load_feed_in_tariffs(session)
            async with session.begin():
                for idx, item in enumerate(items):
                    try:
                        hydrated = _hydrate_record(item, tariff_map)
                        existing = await session.execute(
                            select(GenerationTable).where(
                                and_(
                                    GenerationTable.province == hydrated.province,
                                    GenerationTable.city == hydrated.city,
                                    GenerationTable.county == hydrated.county,
                                    GenerationTable.year == hydrated.year,
                                )
                            )
                        )
                        row = existing.scalar_one_or_none()
                        if row is None:
                            session.add(_to_row(hydrated))
                        else:
                            _apply_update(row, hydrated)
                        stored += 1
                    except Exception as exc:
                        failed += 1
                        errors.append(
                            ErrorDetail(
                                stage="store",
                                type=type(exc).__name__,
                                message=str(exc),
                                url=ctx.url,
                                item_index=idx,
                                traceback_optional=None,
                            )
                        )
                        log.warning("store generation item failed", extra={"item_index": idx, "error": str(exc)})

        log.info("stored generation items", extra={"stored": stored, "failed": failed})
        return StoreResult(
            stored=stored,
            failed=failed,
            error=None if failed == 0 else f"{failed} items failed",
            store_errors=errors,
        )


async def _load_feed_in_tariffs(session) -> dict[str, Decimal]:
    result = await session.execute(select(PolicyTable.province, PolicyTable.price, PolicyTable.subsidy))
    tariffs: dict[str, Decimal] = {}
    for province, price, subsidy in result.all():
        normalized = _normalize_province(province)
        if not normalized or price is None:
            continue
        base = Decimal(str(price))
        extra = Decimal(str(subsidy)) if subsidy is not None else Decimal("0")
        tariffs[normalized] = base + extra
    return tariffs


def _hydrate_record(item: GenerationRecord, tariff_map: dict[str, Decimal]) -> GenerationRecord:
    installed_capacity_kw = item.installed_capacity_kw or item.capacity_kw
    annual_generation_kwh = item.annual_generation_kwh
    annual_income_yuan = item.annual_income_yuan
    utilization_hours = item.utilization_hours
    remark = item.remark

    if annual_generation_kwh is None and installed_capacity_kw is not None and utilization_hours is not None:
        annual_generation_kwh = installed_capacity_kw * utilization_hours

    if annual_income_yuan is None and annual_generation_kwh is not None:
        province_key = _normalize_province(item.province)
        tariff = tariff_map.get(province_key, DEFAULT_FEED_IN_TARIFF)
        annual_income_yuan = annual_generation_kwh * tariff
        if province_key not in tariff_map:
            remark = _append_remark(remark, "缺少政策电价，按0.35元/kWh估算年收益")

    return GenerationRecord(
        project_name=item.project_name,
        province=item.province,
        city=item.city,
        county=item.county,
        year=item.year,
        installed_capacity_kw=installed_capacity_kw,
        utilization_hours=utilization_hours,
        capacity_kw=installed_capacity_kw,
        annual_generation_kwh=annual_generation_kwh,
        annual_income_yuan=annual_income_yuan,
        project_type=item.project_type,
        status=item.status,
        effective_date=item.effective_date or (str(item.year) if item.year is not None else None),
        source=item.source,
        remark=remark,
        source_url=item.source_url,
    )


def _to_row(item: GenerationRecord) -> GenerationTable:
    return GenerationTable(
        project_name=item.project_name,
        province=item.province,
        city=item.city,
        county=item.county,
        year=item.year,
        installed_capacity_kw=_fopt(item.installed_capacity_kw or item.capacity_kw),
        utilization_hours=_fopt(item.utilization_hours),
        capacity_kw=_fopt(item.installed_capacity_kw or item.capacity_kw),
        annual_generation_kwh=_fopt(item.annual_generation_kwh),
        annual_income_yuan=_fopt(item.annual_income_yuan),
        project_type=item.project_type,
        status=item.status,
        effective_date=item.effective_date,
        source=item.source,
        remark=item.remark,
        source_url=item.source_url,
    )


def _apply_update(row: GenerationTable, item: GenerationRecord) -> None:
    row.project_name = item.project_name
    row.province = item.province
    row.city = item.city
    row.county = item.county
    row.year = item.year
    row.installed_capacity_kw = _fopt(item.installed_capacity_kw or item.capacity_kw)
    row.utilization_hours = _fopt(item.utilization_hours)
    row.capacity_kw = _fopt(item.installed_capacity_kw or item.capacity_kw)
    row.annual_generation_kwh = _fopt(item.annual_generation_kwh)
    row.annual_income_yuan = _fopt(item.annual_income_yuan)
    row.project_type = item.project_type
    row.status = item.status
    row.effective_date = item.effective_date
    row.source = item.source
    row.remark = item.remark
    row.source_url = item.source_url


def _append_remark(current: Optional[str], extra: str) -> str:
    if not current:
        return extra
    if extra in current:
        return current
    return f"{current}；{extra}"


def _normalize_province(value: Optional[str]) -> str:
    if not value:
        return ""
    text = str(value).strip()
    for suffix in ("维吾尔自治区", "壮族自治区", "回族自治区", "自治区", "特别行政区", "省", "市"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text.strip()


def _fopt(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None
