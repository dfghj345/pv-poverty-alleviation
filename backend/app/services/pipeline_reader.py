from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import Column, Date, DateTime, Integer, MetaData, Numeric, String, Table
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class PipelineTables:
    metadata: MetaData
    policy_table: Table
    weather_radiation_table: Table
    city_location_table: Table
    poverty_county_table: Table
    cost_table: Table
    generation_table: Table


_engine: Optional[AsyncEngine] = None
_tables: Optional[PipelineTables] = None


def _resolve_pipeline_dsn() -> str:
    # Priority:
    # 1) explicit runtime env PIPELINE_DATABASE_URL
    # 2) parsed settings.PIPELINE_DATABASE_URL
    # 3) fallback to main DATABASE_URL (same DB deployment)
    env_dsn = os.getenv('PIPELINE_DATABASE_URL')
    if env_dsn:
        return env_dsn

    if settings.PIPELINE_DATABASE_URL is not None:
        return str(settings.PIPELINE_DATABASE_URL)

    return str(settings.DATABASE_URL)


def get_pipeline_engine() -> AsyncEngine:
    """
    Read-only engine for data_pipeline tables.
    """
    global _engine
    if _engine is not None:
        return _engine

    dsn = _resolve_pipeline_dsn()
    _engine = create_async_engine(dsn, echo=False, future=True)
    return _engine


def get_pipeline_tables() -> PipelineTables:
    global _tables
    if _tables is not None:
        return _tables

    md = MetaData()
    policy_table = Table(
        'policy_table',
        md,
        Column('id', Integer, primary_key=True),
        Column('province', String(50)),
        Column('price', Numeric(10, 4)),
        Column('subsidy', Numeric(10, 4)),
        Column('policy_date', String(100)),
        Column('policy_type', String(100)),
        Column('source_url', String(500)),
        Column('created_at', DateTime),
    )

    weather_radiation_table = Table(
        'weather_radiation_table',
        md,
        Column('id', Integer, primary_key=True),
        Column('latitude', Numeric(9, 6)),
        Column('longitude', Numeric(9, 6)),
        Column('day', Date),
        Column('shortwave_radiation_sum_kwh_m2', Numeric(12, 6)),
        Column('temperature_mean_c', Numeric(8, 3)),
        Column('precipitation_sum_mm', Numeric(10, 3)),
        Column('wind_speed_mean_m_s', Numeric(10, 3)),
        Column('annual_radiation_sum_kwh_m2', Numeric(12, 6)),
        Column('equivalent_hours_h', Numeric(10, 3)),
        Column('source', String(50)),
        Column('source_url', String(500)),
        Column('created_at', DateTime),
    )

    city_location_table = Table(
        'city_location_table',
        md,
        Column('id', Integer, primary_key=True),
        Column('province', String(50)),
        Column('city', String(100)),
        Column('latitude', Numeric(9, 6)),
        Column('longitude', Numeric(9, 6)),
        Column('source', String(50)),
        Column('source_url', String(500)),
        Column('created_at', DateTime),
    )

    poverty_county_table = Table(
        'poverty_county_table',
        md,
        Column('id', Integer, primary_key=True),
        Column('province', String(50)),
        Column('city', String(100)),
        Column('county', String(100)),
        Column('population', Integer),
        Column('income_per_capita_yuan', Numeric(12, 2)),
        Column('energy_condition', String(200)),
        Column('tags', String(500)),
        Column('adcode', String(50)),
        Column('source', String(50)),
        Column('source_url', String(500)),
        Column('created_at', DateTime),
    )

    cost_table = Table(
        'cost_table',
        md,
        Column('id', Integer, primary_key=True),
        Column('name', String(200)),
        Column('category', String(50)),
        Column('province', String(50)),
        Column('unit_cost_yuan_per_kw', Numeric(12, 2)),
        Column('component_price_yuan_per_w', Numeric(12, 4)),
        Column('effective_date', String(100)),
        Column('source', String(50)),
        Column('source_url', String(500)),
        Column('created_at', DateTime),
    )

    generation_table = Table(
        'generation_table',
        md,
        Column('id', Integer, primary_key=True),
        Column('project_name', String(200)),
        Column('province', String(50)),
        Column('capacity_kw', Numeric(14, 3)),
        Column('annual_generation_kwh', Numeric(18, 3)),
        Column('annual_income_yuan', Numeric(18, 2)),
        Column('project_type', String(100)),
        Column('status', String(50)),
        Column('effective_date', String(100)),
        Column('source', String(50)),
        Column('source_url', String(500)),
        Column('created_at', DateTime),
    )

    _tables = PipelineTables(
        metadata=md,
        policy_table=policy_table,
        weather_radiation_table=weather_radiation_table,
        city_location_table=city_location_table,
        poverty_county_table=poverty_county_table,
        cost_table=cost_table,
        generation_table=generation_table,
    )
    return _tables


async def dispose_pipeline_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
