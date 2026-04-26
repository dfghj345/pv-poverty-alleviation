from __future__ import annotations

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
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

PROVINCE_SUFFIXES = (
    "维吾尔自治区",
    "壮族自治区",
    "回族自治区",
    "自治区",
    "特别行政区",
    "省",
    "市",
)

CITY_SUFFIXES = ("自治州", "地区", "盟", "市")

CITY_COORDINATE_FILE = Path(__file__).resolve().parents[1] / "static" / "city_coordinates.json"


class PanelDataServiceError(RuntimeError):
    pass


def _to_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    return float(value)


def _normalize_province(value: str | None) -> str:
    if not value:
        return ""
    normalized = str(value).strip()
    for suffix in PROVINCE_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized.strip()


def _normalize_city(value: str | None) -> str:
    if not value:
        return ""
    normalized = str(value).strip()
    for suffix in CITY_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
            break
    return normalized.strip()


def _coordinate_key(province: str, city: str | None) -> str:
    return f"{province.strip()}|{(city or '').strip()}"


def _normalized_coordinate_key(province: str, city: str | None) -> str:
    normalized_province = _normalize_province(province)
    normalized_city = _normalize_city(city) or normalized_province
    return f"{normalized_province}|{normalized_city}"


@lru_cache(maxsize=1)
def _load_coordinate_indexes() -> tuple[dict[str, tuple[float, float]], dict[str, tuple[float, float]]]:
    if not CITY_COORDINATE_FILE.exists():
        logger.warning("panel_data coordinate file not found: %s", CITY_COORDINATE_FILE)
        return {}, {}

    raw_payload = json.loads(CITY_COORDINATE_FILE.read_text(encoding="utf-8"))
    exact_index: dict[str, tuple[float, float]] = {}
    normalized_index: dict[str, tuple[float, float]] = {}

    for key, value in raw_payload.items():
        longitude = float(value["longitude"])
        latitude = float(value["latitude"])
        exact_index[str(key)] = (longitude, latitude)

        province, _, city = str(key).partition("|")
        normalized_index[_normalized_coordinate_key(province, city)] = (longitude, latitude)

    return exact_index, normalized_index


@lru_cache(maxsize=1)
def _load_province_centers() -> dict[str, tuple[float, float]]:
    exact_index, _ = _load_coordinate_indexes()
    buckets: dict[str, list[tuple[float, float]]] = {}

    for key, coordinate in exact_index.items():
        province, _, _ = key.partition("|")
        normalized_province = _normalize_province(province)
        buckets.setdefault(normalized_province, []).append(coordinate)

    centers: dict[str, tuple[float, float]] = {}
    for normalized_province, coordinates in buckets.items():
        longitude = sum(item[0] for item in coordinates) / len(coordinates)
        latitude = sum(item[1] for item in coordinates) / len(coordinates)
        centers[normalized_province] = (longitude, latitude)

    return centers


def _resolve_map_coordinate(
    *,
    province: str,
    city: str | None,
    db_longitude: float | Decimal | None = None,
    db_latitude: float | Decimal | None = None,
) -> tuple[float, float] | None:
    if db_longitude is not None and db_latitude is not None:
        return float(db_longitude), float(db_latitude)

    exact_index, normalized_index = _load_coordinate_indexes()

    coordinate = exact_index.get(_coordinate_key(province, city))
    if coordinate is not None:
        return coordinate

    coordinate = normalized_index.get(_normalized_coordinate_key(province, city))
    if coordinate is not None:
        return coordinate

    if not city:
        return _load_province_centers().get(_normalize_province(province))

    return None


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
    longitude_column = getattr(PanelData, "longitude", None)
    latitude_column = getattr(PanelData, "latitude", None)
    select_fields = [
        PanelData.province.label("province"),
        PanelData.city.label("city"),
        PanelData.year.label("year"),
        func.coalesce(func.sum(PanelData.pv_installed_capacity_wan_kw), 0).label("value"),
        func.count(PanelData.id).label("count"),
    ]

    if longitude_column is not None and latitude_column is not None:
        select_fields.extend(
            [
                func.avg(longitude_column).label("longitude"),
                func.avg(latitude_column).label("latitude"),
            ]
        )

    try:
        rows = (
            await db.execute(
                select(*select_fields)
                .where(*conditions)
                .group_by(PanelData.province, PanelData.city, PanelData.year)
                .order_by(desc(PanelData.year), PanelData.province.asc(), PanelData.city.asc())
            )
        ).all()
    except Exception as exc:
        await db.rollback()
        logger.exception("get_panel_data_map failed")
        raise PanelDataServiceError("Panel data map is not available right now") from exc

    items: list[PanelDataMapItem] = []
    skipped: list[str] = []

    for row in rows:
        row_province = str(row.province)
        row_city = str(row.city)
        coordinate = _resolve_map_coordinate(
            province=row_province,
            city=row_city,
            db_longitude=getattr(row, "longitude", None),
            db_latitude=getattr(row, "latitude", None),
        )
        if coordinate is None:
            skipped.append(f"{row_province}|{row_city}|{int(row.year)}")
            continue

        longitude, latitude = coordinate
        items.append(
            PanelDataMapItem(
                province=row_province,
                city=row_city,
                year=int(row.year),
                value=_to_float(row.value),
                count=int(row.count or 0),
                longitude=longitude,
                latitude=latitude,
            )
        )

    if skipped:
        logger.warning(
            "panel_data map skipped %s row(s) without coordinates: %s",
            len(skipped),
            ", ".join(skipped[:10]),
        )

    return items
