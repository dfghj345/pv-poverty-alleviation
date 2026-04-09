from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext
from data_pipeline.core.logging import get_ctx_logger
from data_pipeline.core.results import ErrorDetail
from data_pipeline.db.models import Base, WeatherRadiationTable
from data_pipeline.db.records import WeatherRadiationRecord
from data_pipeline.db.session import AsyncSessionLocal, get_engine
from data_pipeline.registry.storages import register_storage

_TABLES_READY = False


@register_storage(data_type='weather_radiation')
class WeatherRadiationStorage(BaseStorage[WeatherRadiationRecord]):
    name = 'weather_radiation_db'

    async def ensure_tables(self) -> None:
        global _TABLES_READY
        if _TABLES_READY:
            return
        engine = get_engine()
        try:
            async with engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=[WeatherRadiationTable.__table__]))
        except Exception:
            log = get_ctx_logger(__name__, ctx=None)
            log.warning('ensure_tables failed; continuing (table may already exist)')
        _TABLES_READY = True

    async def store(self, items: List[WeatherRadiationRecord], ctx: RunContext) -> StoreResult:
        log = get_ctx_logger(__name__, ctx=ctx)
        await self.ensure_tables()

        unique_items = list(_dedupe(items))
        rows = [_to_row_dict(item) for item in unique_items]

        stored = 0
        failed = 0
        errs: List[ErrorDetail] = []
        async with AsyncSessionLocal() as session:
            bulk_ok = False
            bulk_err: Optional[str] = None
            if rows:
                try:
                    async with session.begin():
                        stmt = insert(WeatherRadiationTable).values(rows)
                        update_cols = {
                            'shortwave_radiation_sum_kwh_m2': stmt.excluded.shortwave_radiation_sum_kwh_m2,
                            'temperature_mean_c': stmt.excluded.temperature_mean_c,
                            'precipitation_sum_mm': stmt.excluded.precipitation_sum_mm,
                            'wind_speed_mean_m_s': stmt.excluded.wind_speed_mean_m_s,
                            'annual_radiation_sum_kwh_m2': stmt.excluded.annual_radiation_sum_kwh_m2,
                            'equivalent_hours_h': stmt.excluded.equivalent_hours_h,
                            'source_url': stmt.excluded.source_url,
                        }
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['latitude', 'longitude', 'day', 'source'],
                            set_=update_cols,
                        )
                        await session.execute(stmt)
                    stored = len(rows)
                    bulk_ok = True
                except Exception as exc:
                    bulk_err = f'{type(exc).__name__}: {exc}'

            if not bulk_ok:
                if bulk_err:
                    log.warning('bulk upsert failed; fell back to row-by-row', extra={'error': bulk_err})
                async with session.begin():
                    for idx, item in enumerate(unique_items):
                        try:
                            existing = await session.execute(
                                select(WeatherRadiationTable).where(
                                    and_(
                                        WeatherRadiationTable.latitude == item.latitude,
                                        WeatherRadiationTable.longitude == item.longitude,
                                        WeatherRadiationTable.day == item.day,
                                        WeatherRadiationTable.source == item.source,
                                    )
                                )
                            )
                            row = existing.scalar_one_or_none()
                            if row is None:
                                session.add(_to_row(item))
                            else:
                                _apply_update(row, item)
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
                            log.warning('store weather item failed', extra={'item_index': idx, 'error': str(row_exc)})

        log.info('stored weather radiation records', extra={'stored': stored, 'failed': failed})
        return StoreResult(stored=stored, failed=failed, error=None if failed == 0 else f'{failed} items failed', store_errors=errs)


def _dedupe(items: Iterable[WeatherRadiationRecord]) -> Iterable[WeatherRadiationRecord]:
    seen: dict[tuple[float, float, object, str], WeatherRadiationRecord] = {}
    for item in items:
        seen[(float(item.latitude), float(item.longitude), item.day, item.source)] = item
    return seen.values()


def _to_row(item: WeatherRadiationRecord) -> WeatherRadiationTable:
    return WeatherRadiationTable(
        latitude=float(item.latitude),
        longitude=float(item.longitude),
        day=item.day,
        shortwave_radiation_sum_kwh_m2=float(item.shortwave_radiation_sum_kwh_m2),
        temperature_mean_c=_fopt(item.temperature_mean_c),
        precipitation_sum_mm=_fopt(item.precipitation_sum_mm),
        wind_speed_mean_m_s=_fopt(item.wind_speed_mean_m_s),
        annual_radiation_sum_kwh_m2=_fopt(item.annual_radiation_sum_kwh_m2),
        equivalent_hours_h=_fopt(item.equivalent_hours_h),
        source=item.source,
        source_url=item.source_url,
    )


def _to_row_dict(item: WeatherRadiationRecord) -> dict:
    return {
        'latitude': float(item.latitude),
        'longitude': float(item.longitude),
        'day': item.day,
        'shortwave_radiation_sum_kwh_m2': float(item.shortwave_radiation_sum_kwh_m2),
        'temperature_mean_c': _fopt(item.temperature_mean_c),
        'precipitation_sum_mm': _fopt(item.precipitation_sum_mm),
        'wind_speed_mean_m_s': _fopt(item.wind_speed_mean_m_s),
        'annual_radiation_sum_kwh_m2': _fopt(item.annual_radiation_sum_kwh_m2),
        'equivalent_hours_h': _fopt(item.equivalent_hours_h),
        'source': item.source,
        'source_url': item.source_url,
    }


def _apply_update(row: WeatherRadiationTable, item: WeatherRadiationRecord) -> None:
    row.shortwave_radiation_sum_kwh_m2 = float(item.shortwave_radiation_sum_kwh_m2)
    row.temperature_mean_c = _fopt(item.temperature_mean_c)
    row.precipitation_sum_mm = _fopt(item.precipitation_sum_mm)
    row.wind_speed_mean_m_s = _fopt(item.wind_speed_mean_m_s)
    row.annual_radiation_sum_kwh_m2 = _fopt(item.annual_radiation_sum_kwh_m2)
    row.equivalent_hours_h = _fopt(item.equivalent_hours_h)
    row.source_url = item.source_url


def _fopt(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None
