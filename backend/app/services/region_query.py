from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import get_logger
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables

logger = get_logger(__name__)

RegionDomain = str

ALL_PROVINCES: tuple[str, ...] = (
    '北京',
    '天津',
    '上海',
    '重庆',
    '河北',
    '山西',
    '辽宁',
    '吉林',
    '黑龙江',
    '江苏',
    '浙江',
    '安徽',
    '福建',
    '江西',
    '山东',
    '河南',
    '湖北',
    '湖南',
    '广东',
    '海南',
    '四川',
    '贵州',
    '云南',
    '陕西',
    '甘肃',
    '青海',
    '台湾',
    '内蒙古',
    '广西',
    '西藏',
    '宁夏',
    '新疆',
    '香港',
    '澳门',
)


@dataclass(frozen=True, slots=True)
class CityCoordinate:
    province: str
    city: str
    latitude: float
    longitude: float
    source: str = 'fallback'


# Fallback coordinates for common province/city pairs (WGS84).
# Used when city_location_table has not been populated yet.
FALLBACK_CITY_COORDS: tuple[CityCoordinate, ...] = (
    CityCoordinate('北京', '北京', 39.9042, 116.4074),
    CityCoordinate('上海', '上海', 31.2304, 121.4737),
    CityCoordinate('天津', '天津', 39.3434, 117.3616),
    CityCoordinate('重庆', '重庆', 29.5630, 106.5516),
    CityCoordinate('广东', '广州', 23.1291, 113.2644),
    CityCoordinate('广东', '深圳', 22.5431, 114.0579),
    CityCoordinate('浙江', '杭州', 30.2741, 120.1551),
    CityCoordinate('江苏', '南京', 32.0603, 118.7969),
    CityCoordinate('四川', '成都', 30.5728, 104.0668),
    CityCoordinate('湖北', '武汉', 30.5928, 114.3055),
    CityCoordinate('山东', '济南', 36.6512, 117.1201),
    CityCoordinate('河南', '郑州', 34.7466, 113.6254),
    CityCoordinate('河北', '石家庄', 38.0428, 114.5149),
    CityCoordinate('云南', '昆明', 25.0389, 102.7183),
    CityCoordinate('宁夏', '银川', 38.4872, 106.2309),
    CityCoordinate('陕西', '西安', 34.3416, 108.9398),
    CityCoordinate('福建', '福州', 26.0745, 119.2965),
    CityCoordinate('广西', '南宁', 22.8170, 108.3669),
)


def normalize_province(value: str | None) -> str:
    if not value:
        return ''
    v = str(value).strip()
    for suffix in (
        '维吾尔自治区',
        '壮族自治区',
        '回族自治区',
        '自治区',
        '特别行政区',
        '省',
        '市',
    ):
        if v.endswith(suffix):
            v = v[: -len(suffix)]
            break
    return v.strip()


def normalize_city(value: str | None) -> str:
    if not value:
        return ''
    v = str(value).strip()
    for suffix in ('自治州', '地区', '盟', '市'):
        if v.endswith(suffix):
            v = v[: -len(suffix)]
            break
    return v.strip()


def province_equals(a: str | None, b: str | None) -> bool:
    return normalize_province(a) == normalize_province(b)


def city_equals(a: str | None, b: str | None) -> bool:
    return normalize_city(a) == normalize_city(b)


def _clean_items(values: Iterable[object]) -> list[str]:
    out: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        out.add(text)
    return sorted(out)


def _ordered_province_list(provinces: set[str]) -> list[str]:
    normalized = {p.strip() for p in provinces if p and p.strip() and p != 'None'}
    ordered: list[str] = [p for p in ALL_PROVINCES if p in normalized]
    extras = sorted(p for p in normalized if p not in ALL_PROVINCES)
    ordered.extend(extras)
    return ordered


async def _distinct_column_values(engine: AsyncEngine, column) -> list[str]:
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(select(column).where(column.is_not(None)).distinct())).all()
        return _clean_items(row[0] for row in rows)
    except Exception:
        logger.exception('distinct query failed', extra={'column': str(column)})
        return []


async def list_provinces(domain: RegionDomain = 'all') -> list[str]:
    domain = (domain or 'all').strip().lower()
    engine = get_pipeline_engine()
    tables = get_pipeline_tables()

    provinces: set[str] = set(ALL_PROVINCES)

    if domain in ('all', 'policy'):
        provinces.update(await _distinct_column_values(engine, tables.policy_table.c.province))

    if domain in ('all', 'poverty'):
        provinces.update(await _distinct_column_values(engine, tables.poverty_county_table.c.province))

    if domain in ('all', 'cost'):
        provinces.update(await _distinct_column_values(engine, tables.cost_table.c.province))

    if domain in ('all', 'generation'):
        provinces.update(await _distinct_column_values(engine, tables.generation_table.c.province))

    if domain in ('all', 'weather'):
        provinces.update(await _distinct_column_values(engine, tables.city_location_table.c.province))
        provinces.update(item.province for item in FALLBACK_CITY_COORDS)

    return _ordered_province_list(provinces)


async def list_cities(*, province: str, domain: RegionDomain = 'all') -> list[str]:
    domain = (domain or 'all').strip().lower()
    province = province.strip()
    if not province:
        return []

    engine = get_pipeline_engine()
    tables = get_pipeline_tables()
    cities: set[str] = set()

    async def _load_rows(column, province_column) -> list[tuple[object, object]]:
        try:
            async with engine.connect() as conn:
                return (await conn.execute(select(province_column, column).where(column.is_not(None)))).all()
        except Exception:
            logger.exception('city list query failed', extra={'column': str(column)})
            return []

    if domain in ('all', 'weather'):
        rows = await _load_rows(tables.city_location_table.c.city, tables.city_location_table.c.province)
        for prov, city in rows:
            if city is None or prov is None:
                continue
            if province_equals(str(prov), province):
                cities.add(str(city).strip())
        for item in FALLBACK_CITY_COORDS:
            if province_equals(item.province, province):
                cities.add(item.city)

    if domain in ('all', 'poverty'):
        rows = await _load_rows(tables.poverty_county_table.c.city, tables.poverty_county_table.c.province)
        for prov, city in rows:
            if city is None or prov is None:
                continue
            if province_equals(str(prov), province):
                cities.add(str(city).strip())

    return sorted(c for c in cities if c and c != 'None')


async def resolve_city_coordinate(*, province: str, city: str) -> Optional[CityCoordinate]:
    province = province.strip()
    city = city.strip()
    if not province or not city:
        return None

    engine = get_pipeline_engine()
    tables = get_pipeline_tables()

    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(
                        tables.city_location_table.c.province,
                        tables.city_location_table.c.city,
                        tables.city_location_table.c.latitude,
                        tables.city_location_table.c.longitude,
                        tables.city_location_table.c.source,
                    )
                )
            ).all()

        for row in rows:
            row_prov = str(row.province) if row.province is not None else ''
            row_city = str(row.city) if row.city is not None else ''
            if not row_prov or not row_city:
                continue
            if province_equals(row_prov, province) and city_equals(row_city, city):
                if row.latitude is None or row.longitude is None:
                    continue
                return CityCoordinate(
                    province=row_prov,
                    city=row_city,
                    latitude=float(row.latitude),
                    longitude=float(row.longitude),
                    source=str(row.source) if row.source else 'city_location_table',
                )
    except Exception:
        logger.exception('resolve_city_coordinate query failed')

    for item in FALLBACK_CITY_COORDS:
        if province_equals(item.province, province) and city_equals(item.city, city):
            return item

    return None


async def list_city_coordinates(*, province: str | None = None, limit: int = 500) -> list[CityCoordinate]:
    items = await _iter_all_city_coordinates()
    if province:
        items = [item for item in items if province_equals(item.province, province)]
    return items[:limit]


async def resolve_nearest_weather_coordinate(*, province: str, city: str) -> Optional[CityCoordinate]:
    """
    Resolve province/city to weather-table coordinates.

    1) Resolve province/city -> reference coordinate
    2) Try exact coordinate in weather table
    3) Fallback to nearest available coordinate
    """
    ref = await resolve_city_coordinate(province=province, city=city)
    if ref is None:
        return None

    engine = get_pipeline_engine()
    tables = get_pipeline_tables()

    try:
        async with engine.connect() as conn:
            exact = (
                await conn.execute(
                    select(
                        tables.weather_radiation_table.c.latitude,
                        tables.weather_radiation_table.c.longitude,
                    )
                    .where(
                        tables.weather_radiation_table.c.latitude == ref.latitude,
                        tables.weather_radiation_table.c.longitude == ref.longitude,
                    )
                    .limit(1)
                )
            ).first()

            if exact:
                return CityCoordinate(
                    province=ref.province,
                    city=ref.city,
                    latitude=float(exact.latitude),
                    longitude=float(exact.longitude),
                    source=ref.source,
                )

            nearest = (
                await conn.execute(
                    select(
                        tables.weather_radiation_table.c.latitude,
                        tables.weather_radiation_table.c.longitude,
                    )
                    .distinct(
                        tables.weather_radiation_table.c.latitude,
                        tables.weather_radiation_table.c.longitude,
                    )
                    .order_by(
                        func.abs(tables.weather_radiation_table.c.latitude - ref.latitude)
                        + func.abs(tables.weather_radiation_table.c.longitude - ref.longitude)
                    )
                    .limit(1)
                )
            ).first()

        if nearest:
            return CityCoordinate(
                province=ref.province,
                city=ref.city,
                latitude=float(nearest.latitude),
                longitude=float(nearest.longitude),
                source='nearest_weather_grid',
            )
    except Exception:
        logger.exception('resolve_nearest_weather_coordinate failed')

    return None


async def _iter_all_city_coordinates() -> list[CityCoordinate]:
    engine = get_pipeline_engine()
    tables = get_pipeline_tables()
    out: list[CityCoordinate] = []

    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    select(
                        tables.city_location_table.c.province,
                        tables.city_location_table.c.city,
                        tables.city_location_table.c.latitude,
                        tables.city_location_table.c.longitude,
                        tables.city_location_table.c.source,
                    )
                    .where(
                        tables.city_location_table.c.province.is_not(None),
                        tables.city_location_table.c.city.is_not(None),
                        tables.city_location_table.c.latitude.is_not(None),
                        tables.city_location_table.c.longitude.is_not(None),
                    )
                )
            ).all()

        for row in rows:
            out.append(
                CityCoordinate(
                    province=str(row.province).strip(),
                    city=str(row.city).strip(),
                    latitude=float(row.latitude),
                    longitude=float(row.longitude),
                    source=str(row.source) if row.source else 'city_location_table',
                )
            )
    except Exception:
        logger.exception('load city locations failed')

    # Add fallback when city_location table is empty / partially missing.
    if not out:
        out.extend(FALLBACK_CITY_COORDS)
    else:
        existed = {(normalize_province(x.province), normalize_city(x.city)) for x in out}
        for item in FALLBACK_CITY_COORDS:
            key = (normalize_province(item.province), normalize_city(item.city))
            if key not in existed:
                out.append(item)

    return out


async def resolve_city_by_coordinate(*, latitude: float, longitude: float) -> Optional[CityCoordinate]:
    """Map a coordinate to nearest known city location."""
    candidates = await _iter_all_city_coordinates()
    if not candidates:
        return None

    best: CityCoordinate | None = None
    best_score: float | None = None
    for item in candidates:
        score = abs(item.latitude - latitude) + abs(item.longitude - longitude)
        if best_score is None or score < best_score:
            best = item
            best_score = score

    return best
