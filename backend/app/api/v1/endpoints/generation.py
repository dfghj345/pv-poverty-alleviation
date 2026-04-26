from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.core.logging import get_logger
from app.schemas.generation import GenerationOut, GenerationRecordOut, GenerationSummaryOut
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


@router.get('/generation', response_model=Result[List[GenerationRecordOut]])
async def list_generation(
    province: Optional[str] = Query(default=None),
    city: Optional[str] = Query(default=None),
    county: Optional[str] = Query(default=None),
    year: Optional[int] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
):
    t = get_pipeline_tables().generation_table
    q = select(
        t.c.province,
        t.c.city,
        t.c.county,
        t.c.year,
        t.c.installed_capacity_kw,
        t.c.annual_generation_kwh,
        t.c.annual_income_yuan,
        t.c.utilization_hours,
        t.c.source,
        t.c.remark,
    )
    if province is not None:
        q = q.where(t.c.province == province)
    if city is not None:
        q = q.where(t.c.city == city)
    if county is not None:
        q = q.where(t.c.county == county)
    if year is not None:
        q = q.where(t.c.year == year)
    q = q.order_by(t.c.province, t.c.city, t.c.county, t.c.year).offset(skip).limit(limit)

    engine = get_pipeline_engine()
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(q)).all()
    except Exception as exc:
        logger.exception('list_generation failed')
        raise HTTPException(status_code=503, detail='Failed to load generation_table data') from exc

    out: List[GenerationRecordOut] = []
    for r in rows:
        out.append(
            GenerationRecordOut(
                province=str(r.province) if r.province is not None else '',
                city=r.city,
                county=r.county,
                year=int(r.year) if r.year is not None else 0,
                installed_capacity_kw=float(r.installed_capacity_kw) if r.installed_capacity_kw is not None else None,
                annual_generation_kwh=float(r.annual_generation_kwh) if r.annual_generation_kwh is not None else None,
                annual_income_yuan=float(r.annual_income_yuan) if r.annual_income_yuan is not None else None,
                utilization_hours=float(r.utilization_hours) if r.utilization_hours is not None else None,
                source=str(r.source) if r.source is not None else 'generation',
                remark=r.remark,
            )
        )
    return Result.success(data=out)


@router.get('/generation/summary', response_model=Result[GenerationSummaryOut])
async def generation_summary():
    t = get_pipeline_tables().generation_table
    engine = get_pipeline_engine()

    try:
        async with engine.connect() as conn:
            total_row = await conn.execute(
                select(
                    func.coalesce(func.sum(t.c.installed_capacity_kw), 0),
                    func.coalesce(func.sum(t.c.annual_generation_kwh), 0),
                    func.coalesce(func.sum(t.c.annual_income_yuan), 0),
                )
            )
            total_installed_capacity_kw, total_annual_generation_kwh, total_annual_income_yuan = total_row.one()

            counts_row = await conn.execute(
                select(
                    func.count(func.distinct(t.c.province)),
                    func.count(func.distinct(t.c.city)),
                    func.count(func.distinct(t.c.county)),
                )
            )
            province_count, city_count, county_count = counts_row.one()

            trend_rows = (await conn.execute(
                select(
                    t.c.year,
                    func.coalesce(func.sum(t.c.installed_capacity_kw), 0),
                    func.coalesce(func.sum(t.c.annual_generation_kwh), 0),
                    func.coalesce(func.sum(t.c.annual_income_yuan), 0),
                )
                .where(t.c.year.is_not(None))
                .group_by(t.c.year)
                .order_by(t.c.year)
            )).all()

            province_rows = (await conn.execute(
                select(
                    t.c.province,
                    func.coalesce(func.sum(t.c.installed_capacity_kw), 0),
                )
                .where(t.c.province.is_not(None))
                .group_by(t.c.province)
                .order_by(func.sum(t.c.installed_capacity_kw).desc())
            )).all()
    except Exception as exc:
        logger.exception('generation_summary failed')
        raise HTTPException(status_code=503, detail='Failed to load generation summary') from exc

    return Result.success(
        data=GenerationSummaryOut(
            total_installed_capacity_kw=float(total_installed_capacity_kw or 0),
            total_annual_generation_kwh=float(total_annual_generation_kwh or 0),
            total_annual_income_yuan=float(total_annual_income_yuan or 0),
            province_count=int(province_count or 0),
            city_count=int(city_count or 0),
            county_count=int(county_count or 0),
            yearly_trend=[
                {
                    'year': int(row.year),
                    'installed_capacity_kw': float(row[1] or 0),
                    'annual_generation_kwh': float(row[2] or 0),
                    'annual_income_yuan': float(row[3] or 0),
                }
                for row in trend_rows
                if row.year is not None
            ],
            province_distribution=[
                {'name': str(row.province), 'value': float(row[1] or 0)}
                for row in province_rows
                if row.province is not None
            ],
        )
    )
