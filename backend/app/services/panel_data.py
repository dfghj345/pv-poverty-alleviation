from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import String, cast, desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.panel_data import PanelData
from app.schemas.panel_data import (
    PanelDataFilters,
    PanelDataItem,
    PanelDataMapItem,
    PanelDataPage,
    PanelDataProvinceStat,
    PanelDataStats,
    PanelDataYearStat,
)

logger = get_logger(__name__)


class PanelDataServiceError(RuntimeError):
    pass


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _build_filters(
    *,
    province: str | None = None,
    city: str | None = None,
    year: int | None = None,
    keyword: str | None = None,
) -> list[Any]:
    conditions: list[Any] = []

    if province:
        conditions.append(PanelData.province == province.strip())
    if city:
        conditions.append(PanelData.city == city.strip())
    if year is not None:
        conditions.append(PanelData.year == year)
    if keyword:
        text = keyword.strip()
        if text:
            like = f"%{text}%"
            conditions.append(
                or_(
                    PanelData.province.ilike(like),
                    PanelData.city.ilike(like),
                    PanelData.source_workbook.ilike(like),
                    cast(PanelData.year, String).ilike(like),
                )
            )
    return conditions


async def get_panel_data_page(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    province: str | None = None,
    city: str | None = None,
    year: int | None = None,
    keyword: str | None = None,
) -> PanelDataPage:
    conditions = _build_filters(province=province, city=city, year=year, keyword=keyword)
    offset = (page - 1) * page_size

    try:
        total = int(
            await db.scalar(
                select(func.count(PanelData.id)).where(*conditions)
            )
            or 0
        )
        rows = (
            await db.scalars(
                select(PanelData)
                .where(*conditions)
                .order_by(desc(PanelData.year), PanelData.province.asc(), PanelData.city.asc())
                .offset(offset)
                .limit(page_size)
            )
        ).all()
    except Exception as exc:
        await db.rollback()
        logger.exception("get_panel_data_page failed")
        raise PanelDataServiceError("Panel data is not available right now") from exc

    items = [
        PanelDataItem(
            id=row.id,
            province=row.province,
            city=row.city,
            year=row.year,
            pv_installed_capacity_wan_kw=_to_float(row.pv_installed_capacity_wan_kw) if row.pv_installed_capacity_wan_kw is not None else None,
            disposable_income_per_capita_yuan=_to_float(row.disposable_income_per_capita_yuan) if row.disposable_income_per_capita_yuan is not None else None,
            healthcare_expenditure_per_capita_yuan=_to_float(row.healthcare_expenditure_per_capita_yuan) if row.healthcare_expenditure_per_capita_yuan is not None else None,
            urban_rural_income_ratio=_to_float(row.urban_rural_income_ratio) if row.urban_rural_income_ratio is not None else None,
            mortality_per_mille=_to_float(row.mortality_per_mille) if row.mortality_per_mille is not None else None,
            pm25_annual_avg_ug_per_m3=_to_float(row.pm25_annual_avg_ug_per_m3) if row.pm25_annual_avg_ug_per_m3 is not None else None,
            gdp_100m_yuan=_to_float(row.gdp_100m_yuan) if row.gdp_100m_yuan is not None else None,
            source_sheet=row.source_sheet,
            source_workbook=row.source_workbook,
        )
        for row in rows
    ]

    return PanelDataPage(items=items, total=total, page=page, page_size=page_size)


async def get_panel_data_filters(
    db: AsyncSession,
    *,
    province: str | None = None,
) -> PanelDataFilters:
    city_conditions = _build_filters(province=province)

    try:
        provinces = list(
            (
                await db.scalars(
                    select(distinct(PanelData.province)).order_by(PanelData.province.asc())
                )
            ).all()
        )
        cities = list(
            (
                await db.scalars(
                    select(distinct(PanelData.city))
                    .where(*city_conditions)
                    .order_by(PanelData.city.asc())
                )
            ).all()
        )
        years = list(
            (
                await db.scalars(
                    select(distinct(PanelData.year)).order_by(PanelData.year.asc())
                )
            ).all()
        )
    except Exception as exc:
        await db.rollback()
        logger.exception("get_panel_data_filters failed")
        raise PanelDataServiceError("Panel data filters are not available right now") from exc

    return PanelDataFilters(
        provinces=[item for item in provinces if item],
        cities=[item for item in cities if item],
        years=[int(item) for item in years if item is not None],
    )


async def get_panel_data_stats(db: AsyncSession) -> PanelDataStats:
    try:
        total_count = int(await db.scalar(select(func.count(PanelData.id))) or 0)
        province_count = int(await db.scalar(select(func.count(distinct(PanelData.province)))) or 0)
        city_count = int(await db.scalar(select(func.count(distinct(PanelData.city)))) or 0)
        year_count = int(await db.scalar(select(func.count(distinct(PanelData.year)))) or 0)

        province_rows = (
            await db.execute(
                select(
                    PanelData.province.label("province"),
                    func.count(PanelData.id).label("count"),
                    func.coalesce(func.sum(PanelData.pv_installed_capacity_wan_kw), 0).label("value"),
                )
                .group_by(PanelData.province)
                .order_by(desc("count"), PanelData.province.asc())
            )
        ).all()

        year_rows = (
            await db.execute(
                select(
                    PanelData.year.label("year"),
                    func.count(PanelData.id).label("count"),
                    func.coalesce(func.sum(PanelData.pv_installed_capacity_wan_kw), 0).label("value"),
                )
                .group_by(PanelData.year)
                .order_by(PanelData.year.asc())
            )
        ).all()
    except Exception as exc:
        await db.rollback()
        logger.exception("get_panel_data_stats failed")
        raise PanelDataServiceError("Panel data statistics are not available right now") from exc

    return PanelDataStats(
        total_count=total_count,
        province_count=province_count,
        city_count=city_count,
        year_count=year_count,
        by_province=[
            PanelDataProvinceStat(
                province=str(row.province),
                count=int(row.count or 0),
                value=_to_float(row.value),
            )
            for row in province_rows
        ],
        by_year=[
            PanelDataYearStat(
                year=int(row.year),
                count=int(row.count or 0),
                value=_to_float(row.value),
            )
            for row in year_rows
        ],
    )


async def get_panel_data_map(
    db: AsyncSession,
    *,
    province: str | None = None,
    city: str | None = None,
    year: int | None = None,
    keyword: str | None = None,
) -> list[PanelDataMapItem]:
    conditions = _build_filters(province=province, city=city, year=year, keyword=keyword)

    try:
        rows = (
            await db.execute(
                select(
                    PanelData.province.label("province"),
                    PanelData.city.label("city"),
                    PanelData.year.label("year"),
                    func.coalesce(func.sum(PanelData.pv_installed_capacity_wan_kw), 0).label("value"),
                    func.count(PanelData.id).label("count"),
                )
                .where(*conditions)
                .group_by(PanelData.province, PanelData.city, PanelData.year)
                .order_by(desc(PanelData.year), PanelData.province.asc(), PanelData.city.asc())
            )
        ).all()
    except Exception as exc:
        await db.rollback()
        logger.exception("get_panel_data_map failed")
        raise PanelDataServiceError("Panel data map is not available right now") from exc

    return [
        PanelDataMapItem(
            province=str(row.province),
            city=str(row.city),
            year=int(row.year),
            value=_to_float(row.value),
            count=int(row.count or 0),
        )
        for row in rows
    ]
