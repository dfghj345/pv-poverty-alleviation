from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.functions import ST_X, ST_Y

from app.db.session import get_db
from app.models.project import Project, Policy
from app.schemas.project_detail import ProjectDetailOut
from app.schemas.response import Result
from app.services.projects import build_projects_page, build_pv_summary

router = APIRouter()

@router.get("/summary")
async def get_pv_summary(db: AsyncSession = Depends(get_db)):
    real_data = await build_pv_summary(db)
    return Result.success(data=real_data)

# 前端历史路径兼容（frontend/src/api/project.ts 使用 /projects/dashboard-stats）
@router.get("/dashboard-stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    real_data = await build_pv_summary(db)
    return Result.success(data=real_data)

@router.get("/")
async def list_projects(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    data = await build_projects_page(db, skip=skip, limit=limit)
    return Result.success(data=data)


@router.get("/{project_id}", response_model=Result[ProjectDetailOut])
async def get_project_detail(project_id: int, db: AsyncSession = Depends(get_db)):
    q = (
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
    r = await db.execute(q)
    row = r.first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
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
