from __future__ import annotations

from typing import Any, Dict, List

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.project import Project
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables

logger = get_logger(__name__)


def _empty_summary() -> Dict[str, Any]:
    return {
        "total_capacity_mw": 0.0,
        "annual_generation_yi": 0.0,
        "farmers_benefited": 0,
        "carbon_reduction_wt": 0.0,
        "revenue_years": ["1年", "5年", "10年", "15年", "20年"],
        "revenue_data": [0, 0, 0, 0, 0],
        "province_distribution": [],
    }


async def build_pv_summary(db: AsyncSession) -> Dict[str, Any]:
    project_count = 0
    try:
        project_count = int(await db.scalar(select(func.count(Project.id))) or 0)
    except Exception as exc:
        await db.rollback()
        logger.warning("project count query failed; using pipeline summary", extra={"error": str(exc)})

    if project_count <= 0:
        return await build_pipeline_summary()

    try:
        total_capacity = await db.scalar(select(func.sum(Project.capacity))) or 0
        total_gen = await db.scalar(select(func.sum(Project.annual_generation))) or 0
        farmers = await db.scalar(select(func.sum(Project.farmers_benefited))) or 0
        carbon = await db.scalar(select(func.sum(Project.carbon_reduction))) or 0

        # Province distribution depends on a projects->policies FK relation.
        # For environments without policy data, keep it empty instead of failing.
        province_distribution: List[Dict[str, Any]] = []

        return {
            "total_capacity_mw": round(float(total_capacity) / 1000, 2),
            "annual_generation_yi": round(float(total_gen) / 100000000, 2),
            "farmers_benefited": int(farmers),
            "carbon_reduction_wt": round(float(carbon) / 10000, 2),
            "revenue_years": ["1年", "5年", "10年", "15年", "20年"],
            "revenue_data": [round(float(total_capacity) * 1.5 * i, 2) for i in [1, 5, 10, 15, 20]],
            "province_distribution": province_distribution,
        }
    except Exception as exc:
        await db.rollback()
        logger.warning("build_pv_summary failed; using pipeline summary", extra={"error": str(exc)})
        return await build_pipeline_summary()


async def build_pipeline_summary() -> Dict[str, Any]:
    engine = get_pipeline_engine()
    tables = get_pipeline_tables()

    try:
        async with engine.connect() as conn:
            total_capacity_kw = await conn.scalar(select(func.coalesce(func.sum(tables.generation_table.c.capacity_kw), 0)))
            total_generation_kwh = await conn.scalar(
                select(func.coalesce(func.sum(tables.generation_table.c.annual_generation_kwh), 0))
            )
            total_income_yuan = await conn.scalar(select(func.coalesce(func.sum(tables.generation_table.c.annual_income_yuan), 0)))
            poverty_population = await conn.scalar(select(func.coalesce(func.sum(tables.poverty_county_table.c.population), 0)))

            province_count = func.count(tables.poverty_county_table.c.county).label("value")
            province_rows = (
                await conn.execute(
                    select(
                        tables.poverty_county_table.c.province,
                        province_count,
                    )
                    .where(tables.poverty_county_table.c.province.is_not(None))
                    .group_by(tables.poverty_county_table.c.province)
                    .order_by(desc(province_count))
                    .limit(10)
                )
            ).all()

            annual_income = float(total_income_yuan or 0)
            revenue_data = [round(annual_income * i / 10000, 2) for i in [1, 5, 10, 15, 20]]
            total_generation = float(total_generation_kwh or 0)

        return {
            "total_capacity_mw": round(float(total_capacity_kw or 0) / 1000, 2),
            "annual_generation_yi": round(total_generation / 100000000, 2),
            "farmers_benefited": int(poverty_population or 0),
            "carbon_reduction_wt": round(total_generation * 0.0005703 / 10000, 2),
            "revenue_years": ["1年", "5年", "10年", "15年", "20年"],
            "revenue_data": revenue_data,
            "province_distribution": [{"name": str(row.province), "value": int(row.value)} for row in province_rows],
        }
    except Exception:
        logger.exception("build_pipeline_summary failed; fallback to empty summary")
        return _empty_summary()


async def build_projects_page(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> Dict[str, Any]:
    try:
        total = await db.scalar(select(func.count(Project.id))) or 0
        query = (
            select(
                Project.id,
                Project.name,
                Project.capacity,
                Project.commissioning_date,
                ST_X(Project.location).label("longitude"),
                ST_Y(Project.location).label("latitude"),
            )
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)

        items: List[Dict[str, Any]] = []
        for row in result.all():
            items.append(
                {
                    "id": int(row.id),
                    "name": str(row.name),
                    "capacity": float(row.capacity) if row.capacity is not None else 0.0,
                    "commissioning_date": str(row.commissioning_date) if row.commissioning_date is not None else "",
                    "longitude": float(row.longitude) if row.longitude is not None else 0.0,
                    "latitude": float(row.latitude) if row.latitude is not None else 0.0,
                }
            )

        return {"total": int(total), "items": items}
    except Exception as exc:
        await db.rollback()
        logger.warning("build_projects_page failed; fallback to empty page", extra={"error": str(exc)})
        return {"total": 0, "items": []}
