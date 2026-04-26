from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2.functions import ST_X, ST_Y
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.project import Policy, Project
from app.schemas.project_detail import ProjectDetailOut
from app.schemas.response import Result
from app.services.projects import build_projects_page, build_pv_summary

router = APIRouter()
logger = get_logger(__name__)


@router.get("/summary", response_model=Result[dict[str, Any]])
async def get_pv_summary(db: AsyncSession = Depends(get_db)):
    real_data = await build_pv_summary(db)
    return Result.success(data=real_data)


@router.get("/dashboard-stats", response_model=Result[dict[str, Any]])
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    # Keep the historical frontend path compatible.
    real_data = await build_pv_summary(db)
    return Result.success(data=real_data)


@router.get("/", response_model=Result[dict[str, Any]])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    data = await build_projects_page(db, skip=skip, limit=limit)
    return Result.success(data=data)


@router.get("/{project_id}", response_model=Result[ProjectDetailOut])
async def get_project_detail(project_id: int, db: AsyncSession = Depends(get_db)):
    query = (
        select(
            Project.id,
            Project.name,
            Project.capacity,
            Project.commissioning_date,
            ST_X(Project.location).label("longitude"),
            ST_Y(Project.location).label("latitude"),
            Policy.province.label("province"),
        )
        .join(Policy, Project.policy_id == Policy.id)
        .where(Project.id == project_id)
    )

    try:
        result = await db.execute(query)
        row = result.first()
    except Exception as exc:
        await db.rollback()
        logger.warning('project detail query failed', extra={'project_id': project_id, 'error': str(exc)})
        raise HTTPException(status_code=503, detail='Project detail data is not available') from exc

    if row is None:
        raise HTTPException(status_code=404, detail='Project not found')

    return Result.success(
        data=ProjectDetailOut(
            id=int(row.id),
            name=str(row.name),
            capacity_kw=float(row.capacity),
            commissioning_date=row.commissioning_date,
            longitude=float(row.longitude),
            latitude=float(row.latitude),
            province=str(row.province),
        )
    )
