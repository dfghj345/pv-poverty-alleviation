from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.schemas.poverty import PovertyCountyOut
from app.schemas.response import Result
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables
from app.services.region_query import city_equals, province_equals

router = APIRouter()


@router.get('/poverty/counties', response_model=Result[List[PovertyCountyOut]])
async def list_poverty_counties(
    province: Optional[str] = Query(default=None, description='Province filter'),
    city: Optional[str] = Query(default=None, description='City filter'),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=2000),
):
    t = get_pipeline_tables().poverty_county_table
    q = (
        select(
            t.c.province,
            t.c.city,
            t.c.county,
            t.c.population,
            t.c.income_per_capita_yuan,
            t.c.energy_condition,
            t.c.tags,
            t.c.adcode,
            t.c.source,
            t.c.source_url,
        )
        .order_by(t.c.province.asc(), t.c.city.asc(), t.c.county.asc())
        .limit(5000)
    )

    engine = get_pipeline_engine()
    async with engine.connect() as conn:
        rows = (await conn.execute(q)).all()

    if province:
        rows = [r for r in rows if province_equals(str(r.province) if r.province is not None else None, province)]
    if city:
        rows = [r for r in rows if city_equals(str(r.city) if r.city is not None else None, city)]

    rows = rows[skip : skip + limit]

    out: List[PovertyCountyOut] = []
    for r in rows:
        out.append(
            PovertyCountyOut(
                province=str(r.province),
                city=r.city,
                county=str(r.county),
                population=int(r.population) if r.population is not None else None,
                income_per_capita_yuan=float(r.income_per_capita_yuan) if r.income_per_capita_yuan is not None else None,
                energy_condition=r.energy_condition,
                tags=r.tags,
                adcode=r.adcode,
                source=str(r.source),
                source_url=r.source_url,
            )
        )

    return Result.success(data=out)
