from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, desc, select

from app.schemas.response import Result
from app.schemas.weather import WeatherRadiationOut
from app.services.pipeline_reader import get_pipeline_engine, get_pipeline_tables
from app.services.region_query import resolve_nearest_weather_coordinate

router = APIRouter()


@router.get('/weather/radiation', response_model=Result[List[WeatherRadiationOut]])
async def get_weather_radiation(
    latitude: Optional[float] = Query(default=None, ge=-90, le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
    province: Optional[str] = Query(default=None, description='Province name for location-based query'),
    city: Optional[str] = Query(default=None, description='City name for location-based query'),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    limit: int = Query(default=366, ge=1, le=2000),
):
    """
    Query weather/radiation daily records.

    Supported modes:
    1) province + city (preferred by frontend)
    2) latitude + longitude (kept for backward compatibility)
    """

    resolved_lat: float
    resolved_lon: float
    resolved_province: Optional[str] = None
    resolved_city: Optional[str] = None
    location_source: Optional[str] = None

    province_text = (province or '').strip()
    city_text = (city or '').strip()

    if province_text or city_text:
        if not province_text or not city_text:
            raise HTTPException(status_code=400, detail='province and city must be provided together')

        mapped = await resolve_nearest_weather_coordinate(province=province_text, city=city_text)
        if mapped is None:
            return Result.success(data=[], message='No weather data mapping found for this province/city')

        resolved_lat = mapped.latitude
        resolved_lon = mapped.longitude
        resolved_province = mapped.province
        resolved_city = mapped.city
        location_source = mapped.source
    else:
        if latitude is None and longitude is None:
            raise HTTPException(status_code=400, detail='Either (province, city) or (latitude, longitude) is required')
        if latitude is None or longitude is None:
            raise HTTPException(status_code=400, detail='latitude and longitude must be provided together')

        resolved_lat = latitude
        resolved_lon = longitude

    t = get_pipeline_tables().weather_radiation_table
    conds = [t.c.latitude == resolved_lat, t.c.longitude == resolved_lon]
    if start_date is not None:
        conds.append(t.c.day >= start_date)
    if end_date is not None:
        conds.append(t.c.day <= end_date)

    q = (
        select(
            t.c.latitude,
            t.c.longitude,
            t.c.day,
            t.c.shortwave_radiation_sum_kwh_m2,
            t.c.temperature_mean_c,
            t.c.precipitation_sum_mm,
            t.c.wind_speed_mean_m_s,
            t.c.annual_radiation_sum_kwh_m2,
            t.c.equivalent_hours_h,
            t.c.source,
            t.c.source_url,
        )
        .where(and_(*conds))
        .order_by(desc(t.c.day))
        .limit(limit)
    )

    engine = get_pipeline_engine()
    async with engine.connect() as conn:
        rows = (await conn.execute(q)).all()

    out: List[WeatherRadiationOut] = []
    for r in rows:
        out.append(
            WeatherRadiationOut(
                latitude=float(r.latitude),
                longitude=float(r.longitude),
                province=resolved_province,
                city=resolved_city,
                location_source=location_source,
                day=r.day,
                shortwave_radiation_sum_kwh_m2=float(r.shortwave_radiation_sum_kwh_m2)
                if r.shortwave_radiation_sum_kwh_m2 is not None
                else 0.0,
                temperature_mean_c=float(r.temperature_mean_c) if r.temperature_mean_c is not None else None,
                precipitation_sum_mm=float(r.precipitation_sum_mm) if r.precipitation_sum_mm is not None else None,
                wind_speed_mean_m_s=float(r.wind_speed_mean_m_s) if r.wind_speed_mean_m_s is not None else None,
                annual_radiation_sum_kwh_m2=float(r.annual_radiation_sum_kwh_m2)
                if r.annual_radiation_sum_kwh_m2 is not None
                else None,
                equivalent_hours_h=float(r.equivalent_hours_h) if r.equivalent_hours_h is not None else None,
                source=str(r.source),
                source_url=r.source_url,
            )
        )

    return Result.success(data=out)
