from __future__ import annotations

from fastapi import APIRouter

from app.schemas.calculator import CalcRequest, CalcResponse
from app.schemas.response import Result
from app.services.calculator import PVFinanceService

router = APIRouter()

@router.post("/estimate", response_model=Result[CalcResponse])
async def calculate_roi(data: CalcRequest):
    raw = await PVFinanceService.calculate_full_lifecycle(
        capacity_kw=data.capacity_kw,
        equivalent_hours=data.equivalent_hours,
        total_investment=data.total_investment,
        electricity_price=data.electricity_price,
        loan_ratio=data.loan_ratio,
        annual_degradation=data.annual_degradation
    )
    return Result.success(data=raw)