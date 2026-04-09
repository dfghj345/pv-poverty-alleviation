from __future__ import annotations

from typing import Any, Dict, List

from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.project import Project

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
    except Exception:
        logger.exception("build_pv_summary failed; fallback to empty summary")
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
    except Exception:
        logger.exception("build_projects_page failed; fallback to empty page")
        return {"total": 0, "items": []}
