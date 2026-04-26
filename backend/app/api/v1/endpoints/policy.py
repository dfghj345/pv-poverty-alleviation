from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import desc, or_, select

from app.core.logging import get_logger
from app.schemas.policy import EnergyPolicyOut, PolicyTariffOut
from app.schemas.response import Result
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables
from app.services.region_query import province_equals

router = APIRouter()
logger = get_logger(__name__)


@router.get('/policies', response_model=Result[List[PolicyTariffOut]])
async def list_policies(
    province: Optional[str] = Query(default=None, description='Province filter'),
    limit: int = Query(default=200, ge=1, le=2000),
):
    t = get_pipeline_tables().policy_table
    q = (
        select(
            t.c.province,
            t.c.price,
            t.c.subsidy,
            t.c.policy_date,
            t.c.policy_type,
            t.c.source_url,
        )
        .order_by(t.c.province.asc())
        .limit(2000)
    )

    engine = get_pipeline_engine()
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(q)).all()
    except Exception as exc:
        logger.exception('list_policies failed')
        raise HTTPException(status_code=503, detail='Failed to load policy_table data') from exc

    if province:
        rows = [r for r in rows if province_equals(str(r.province) if r.province is not None else None, province)]

    out: List[PolicyTariffOut] = []
    for r in rows[:limit]:
        out.append(
            PolicyTariffOut(
                province=str(r.province),
                benchmark_price_yuan_per_kwh=float(r.price) if r.price is not None else 0.0,
                subsidy_yuan_per_kwh=float(r.subsidy) if r.subsidy is not None else None,
                policy_date=r.policy_date,
                policy_type=r.policy_type,
                source_url=r.source_url,
            )
        )
    return Result.success(data=out)


@router.get('/energy-policies', response_model=Result[List[EnergyPolicyOut]])
async def list_energy_policies(
    keyword: Optional[str] = Query(default=None, description='Title keyword filter'),
    limit: int = Query(default=100, ge=1, le=1000),
):
    t = get_pipeline_tables().energy_policy_table
    q = (
        select(
            t.c.title,
            t.c.url,
            t.c.publish_date,
            t.c.summary,
            t.c.source,
            t.c.source_url,
        )
        .order_by(desc(t.c.publish_date), t.c.id.desc())
        .limit(1000)
    )

    if keyword:
        like = f'%{keyword.strip()}%'
        q = q.where(or_(t.c.title.ilike(like), t.c.summary.ilike(like)))

    engine = get_pipeline_engine()
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(q)).all()
    except Exception as exc:
        logger.exception('list_energy_policies failed')
        raise HTTPException(status_code=503, detail='Failed to load energy_policy_table data') from exc

    out: List[EnergyPolicyOut] = []
    for r in rows[:limit]:
        out.append(
            EnergyPolicyOut(
                title=str(r.title),
                url=str(r.url),
                publish_date=r.publish_date,
                summary=r.summary,
                source=str(r.source) if r.source is not None else 'nea',
                source_url=r.source_url,
            )
        )
    return Result.success(data=out)
