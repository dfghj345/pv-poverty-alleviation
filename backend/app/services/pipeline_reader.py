from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import MetaData, Table
from sqlalchemy.ext.asyncio import AsyncEngine

from data_pipeline.db.models import (
    Base as PipelineBase,
    CityLocationTable,
    CostTable,
    GenerationTable,
    PolicyTable,
    PovertyCountyTable,
    WeatherRadiationTable,
)
from data_pipeline.db.session import dispose_engine as dispose_pipeline_db_engine
from data_pipeline.db.session import get_engine as get_pipeline_db_engine


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


def get_pipeline_engine() -> AsyncEngine:
    """Read-only engine for data_pipeline tables."""
    global _engine
    if _engine is not None:
        return _engine

    _engine = get_pipeline_db_engine()
    return _engine


def get_pipeline_tables() -> PipelineTables:
    global _tables
    if _tables is not None:
        return _tables

    _tables = PipelineTables(
        metadata=PipelineBase.metadata,
        policy_table=PolicyTable.__table__,
        weather_radiation_table=WeatherRadiationTable.__table__,
        city_location_table=CityLocationTable.__table__,
        poverty_county_table=PovertyCountyTable.__table__,
        cost_table=CostTable.__table__,
        generation_table=GenerationTable.__table__,
    )
    return _tables


async def dispose_pipeline_engine() -> None:
    global _engine
    await dispose_pipeline_db_engine()
    _engine = None
