from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.schemas.policy import PolicyTariffOut
from app.schemas.response import Result
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables
from app.services.region_query import province_equals

router = APIRouter()


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
    async with engine.connect() as conn:
        rows = (await conn.execute(q)).all()

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
