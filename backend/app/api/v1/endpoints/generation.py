from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.logging import get_logger
from app.schemas.generation import GenerationOut
from app.schemas.response import Result
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables
from app.services.region_query import province_equals

router = APIRouter()
logger = get_logger(__name__)


@router.get('/generations', response_model=Result[List[GenerationOut]])
async def list_generations(
    province: Optional[str] = Query(default=None),
    project_type: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
):
    t = get_pipeline_tables().generation_table
    q = select(
        t.c.project_name,
        t.c.province,
        t.c.capacity_kw,
        t.c.annual_generation_kwh,
        t.c.annual_income_yuan,
        t.c.project_type,
        t.c.status,
        t.c.effective_date,
        t.c.source,
        t.c.source_url,
    ).limit(5000)

    engine = get_pipeline_engine()
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(q)).all()
    except Exception as exc:
        logger.exception('list_generations failed')
        raise HTTPException(status_code=503, detail='Failed to load generation_table data') from exc

    if province:
        rows = [r for r in rows if province_equals(str(r.province) if r.province is not None else None, province)]
    if project_type:
        rows = [r for r in rows if str(r.project_type) == project_type]

    out: List[GenerationOut] = []
    for r in rows[:limit]:
        out.append(
            GenerationOut(
                project_name=str(r.project_name),
                province=r.province,
                capacity_kw=float(r.capacity_kw) if r.capacity_kw is not None else None,
                annual_generation_kwh=float(r.annual_generation_kwh) if r.annual_generation_kwh is not None else None,
                annual_income_yuan=float(r.annual_income_yuan) if r.annual_income_yuan is not None else None,
                project_type=r.project_type,
                status=r.status,
                effective_date=r.effective_date,
                source=str(r.source) if r.source is not None else 'generation',
                source_url=r.source_url,
            )
        )
    return Result.success(data=out)
