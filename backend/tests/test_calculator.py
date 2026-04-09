import pytest
from decimal import Decimal
from app.services.calculator import PVFinanceService

@pytest.mark.asyncio
async def test_calculate_full_lifecycle_standard():
    # 测试标准 1MW 项目
    result = await PVFinanceService.calculate_full_lifecycle(
        capacity_kw=Decimal("1000"),
        equivalent_hours=Decimal("1200"),
        total_investment=Decimal("3500000"), # 350万
        electricity_price=Decimal("0.4")     # 0.4元/度
    )
    
    assert "npv" in result
    assert result["irr"] > 0
    assert result["lcoe"] < Decimal("0.4") # LCOE 应低于电价才有盈利空间
    assert len(result["annual_cash_flows"]) == 21 # 0-20年

@pytest.mark.asyncio
async def test_calculate_zero_generation():
    # 测试极端情况：无发电量
    result = await PVFinanceService.calculate_full_lifecycle(
        capacity_kw=Decimal("1000"),
        equivalent_hours=Decimal("0"),
        total_investment=Decimal("3500000"),
        electricity_price=Decimal("0.4")
    )
    assert result["irr"] is None or result["irr"] < 0
    assert result["npv"] < 0