from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from fastapi import HTTPException
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.logging import get_logger
from app.models.project import Project
from app.schemas.calculator import CalcROIResponse
from app.services.calculator import PVFinanceService

logger = get_logger(__name__)


async def calculate_project_roi(db: AsyncSession, project_id: int) -> CalcROIResponse:
    row = await _get_project_with_coords(db, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="未找到该电站项目")

    project, lon, lat = row
    if not project.policy:
        raise HTTPException(status_code=400, detail="该项目尚未关联当地电价政策")

    dynamic_hours = Decimal(str(settings.DEFAULT_EQUIVALENT_HOURS))
    logger.info("project roi uses default equivalent hours", extra={"project_id": project_id})

    capacity_kw = Decimal(str(project.capacity))
    total_investment = capacity_kw * Decimal(str(settings.UNIT_COST_PER_KW))
    electricity_price = Decimal(str(project.policy.electricity_price))
    annual_degradation = Decimal(str(settings.DEFAULT_DEGRADATION))

    raw = await PVFinanceService.calculate_full_lifecycle(
        capacity_kw=capacity_kw,
        equivalent_hours=dynamic_hours,
        total_investment=total_investment,
        electricity_price=electricity_price,
        annual_degradation=annual_degradation,
    )
    return CalcROIResponse(
        **raw,
        source_equivalent_hours=float(dynamic_hours),
        location={"lon": float(lon), "lat": float(lat)},
    )


async def _get_project_with_coords(
    db: AsyncSession, project_id: int
) -> Optional[Tuple[Project, float, float]]:
    q = (
        select(
            Project,
            ST_X(Project.location).label("lon"),
            ST_Y(Project.location).label("lat"),
        )
        .options(joinedload(Project.policy))
        .where(Project.id == project_id)
    )
    r = await db.execute(q)
    return r.first()
