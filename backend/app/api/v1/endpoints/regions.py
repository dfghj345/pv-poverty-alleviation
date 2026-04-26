from __future__ import annotations

from typing import List

from fastapi import APIRouter, Query

from app.schemas.region import RegionLocationOut
from app.schemas.response import Result
from app.services.region_query import (
    list_cities,
    list_city_coordinates,
    list_provinces,
    resolve_city_by_coordinate,
    resolve_city_coordinate,
    resolve_nearest_weather_coordinate,
)

router = APIRouter()


@router.get('/regions/provinces', response_model=Result[List[str]])
async def get_provinces(
    domain: str = Query(default='all', description='all|weather|policy|poverty|cost|generation'),
):
    provinces = await list_provinces(domain=domain)
    return Result.success(data=provinces)


@router.get('/regions/cities', response_model=Result[List[str]])
async def get_cities(
    province: str = Query(..., min_length=1),
    domain: str = Query(default='all', description='all|weather|poverty'),
):
    cities = await list_cities(province=province, domain=domain)
    return Result.success(data=cities)


@router.get('/regions/location', response_model=Result[RegionLocationOut | None])
async def get_city_location(
    province: str = Query(..., min_length=1),
    city: str = Query(..., min_length=1),
):
    resolved = await resolve_city_coordinate(province=province, city=city)
    if resolved is None:
        return Result.success(data=None, message='No coordinate mapping found for this province/city')
    return Result.success(
        data=RegionLocationOut(
            province=resolved.province,
            city=resolved.city,
            latitude=resolved.latitude,
            longitude=resolved.longitude,
            source=resolved.source,
        )
    )


@router.get('/regions/locations', response_model=Result[List[RegionLocationOut]])
async def list_locations(
    province: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=2000),
):
    locations = await list_city_coordinates(province=province, limit=limit)
    return Result.success(
        data=[
            RegionLocationOut(
                province=item.province,
                city=item.city,
                latitude=item.latitude,
                longitude=item.longitude,
                source=item.source,
            )
            for item in locations
        ]
    )


@router.get('/regions/weather-location', response_model=Result[RegionLocationOut | None])
async def get_weather_location(
    province: str = Query(..., min_length=1),
    city: str = Query(..., min_length=1),
):
    resolved = await resolve_nearest_weather_coordinate(province=province, city=city)
    if resolved is None:
        return Result.success(data=None, message='No weather-grid coordinate found for this province/city')
    return Result.success(
        data=RegionLocationOut(
            province=resolved.province,
            city=resolved.city,
            latitude=resolved.latitude,
            longitude=resolved.longitude,
            source=resolved.source,
        )
    )


@router.get('/regions/reverse', response_model=Result[RegionLocationOut | None])
async def reverse_city(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    resolved = await resolve_city_by_coordinate(latitude=latitude, longitude=longitude)
    if resolved is None:
        return Result.success(data=None, message='No nearby city mapping found')
    return Result.success(
        data=RegionLocationOut(
            province=resolved.province,
            city=resolved.city,
            latitude=resolved.latitude,
            longitude=resolved.longitude,
            source=resolved.source,
        )
    )
