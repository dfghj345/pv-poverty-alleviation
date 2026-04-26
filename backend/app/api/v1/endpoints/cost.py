from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.core.logging import get_logger
from app.schemas.cost import CostOut
from app.schemas.response import Result
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables
from app.services.region_query import province_equals

router = APIRouter()
logger = get_logger(__name__)


@router.get('/costs', response_model=Result[List[CostOut]])
async def list_costs(
    category: Optional[str] = Query(default=None, description='Cost category filter'),
    province: Optional[str] = Query(default=None, description='Province filter'),
    limit: int = Query(default=200, ge=1, le=2000),
):
    t = get_pipeline_tables().cost_table
    q = select(
        t.c.name,
        t.c.category,
        t.c.province,
        t.c.unit_cost_yuan_per_kw,
        t.c.component_price_yuan_per_w,
        t.c.effective_date,
        t.c.source,
        t.c.source_url,
    ).limit(5000)

    engine = get_pipeline_engine()
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(q)).all()
    except Exception as exc:
        logger.exception('list_costs failed')
        raise HTTPException(status_code=503, detail='Failed to load cost_table data') from exc

    if category:
        rows = [r for r in rows if str(r.category) == category]
    if province:
        rows = [r for r in rows if province_equals(str(r.province) if r.province is not None else None, province)]

    out: List[CostOut] = []
    for r in rows[:limit]:
        out.append(
            CostOut(
                name=str(r.name),
                category=str(r.category),
                province=r.province,
                unit_cost_yuan_per_kw=float(r.unit_cost_yuan_per_kw) if r.unit_cost_yuan_per_kw is not None else None,
                component_price_yuan_per_w=float(r.component_price_yuan_per_w)
                if r.component_price_yuan_per_w is not None
                else None,
                effective_date=r.effective_date,
                source=str(r.source) if r.source is not None else 'pv_costs',
                source_url=r.source_url,
            )
        )
    return Result.success(data=out)
