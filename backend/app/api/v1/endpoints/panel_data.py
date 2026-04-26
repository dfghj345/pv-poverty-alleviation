from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.panel_data import (
    PanelDataFiltersResponse,
    PanelDataMapResponse,
    PanelDataPageResponse,
    PanelDataStatsResponse,
)
from app.services.panel_data import (
    PanelDataServiceError,
    get_panel_data_filters,
    get_panel_data_map,
    get_panel_data_page,
    get_panel_data_stats,
)

router = APIRouter()


@router.get("/panel-data", response_model=PanelDataPageResponse)
async def list_panel_data(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    province: str | None = Query(default=None),
    city: str | None = Query(default=None),
    year: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await get_panel_data_page(
            db,
            page=page,
            page_size=page_size,
            province=province,
            city=city,
            year=year,
            keyword=keyword,
        )
    except PanelDataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PanelDataPageResponse(data=data)


@router.get("/panel-data/filters", response_model=PanelDataFiltersResponse)
async def get_filters(
    province: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await get_panel_data_filters(db, province=province)
    except PanelDataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PanelDataFiltersResponse(data=data)


@router.get("/panel-data/stats", response_model=PanelDataStatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    try:
        data = await get_panel_data_stats(db)
    except PanelDataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PanelDataStatsResponse(data=data)


@router.get("/panel-data/map", response_model=PanelDataMapResponse)
async def get_map(
    province: str | None = Query(default=None),
    city: str | None = Query(default=None),
    year: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await get_panel_data_map(
            db,
            province=province,
            city=city,
            year=year,
            keyword=keyword,
        )
    except PanelDataServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return PanelDataMapResponse(data=data)
