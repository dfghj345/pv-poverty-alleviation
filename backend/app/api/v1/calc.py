from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Dict, Any

from app.services.finance_engine import PVCalculator

router = APIRouter(prefix="/calc", tags=["Decision Support - 决策支持"])

# --- 1. 定义 Pydantic 模型 ---

class CalcRequest(BaseModel):
    """光伏收益计算请求参数"""
    capacity_kw: Decimal = Field(..., gt=0, description="装机容量 (kW)，必须大于0", example=150.5)
    sunshine_hours: Decimal = Field(..., gt=0, description="年等效利用小时数 (h)", example=1200)
    total_investment: Decimal = Field(..., gt=0, description="总投资额 (元)", example=450000.0)
    benchmark_price: Decimal = Field(..., ge=0, description="标杆上网电价 (元/kWh)", example=0.38)
    subsidy: Decimal = Field(default=Decimal("0.0"), ge=0, description="政策补贴 (元/kWh)")
    discount_rate: Decimal = Field(default=Decimal("0.06"), ge=0, le=1, description="折现率 (0-1)")

    @field_validator('benchmark_price', 'subsidy')
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("价格或补贴不能为负数")
        return v

class CalcResponse(BaseModel):
    """光伏收益计算响应结果"""
    summary: Dict[str, Any] = Field(..., description="核心财务摘要 (NPV, IRR, 回本周期等)")
    yearly_details: list[Dict[str, Any]] = Field(..., description="20年年度详细收益流")

# --- 2. 路由接口实现 ---

@router.post(
    "/calculate", 
    response_model=CalcResponse,
    status_code=status.HTTP_200_OK,
    summary="执行光伏扶贫收益计算",
    description="基于容量、投资额和电价，通过 PVCalculator 引擎生成 20 年全生命周期的财务分析报告。"
)
async def perform_calculation(payload: CalcRequest):
    """
    核心决策支持接口：
    1. 接收前端 Vite 提交的参数
    2. 调用 Finance Engine 进行高精度计算
    3. 返回符合决策看板要求的 JSON 数据
    """
    try:
        # 初始化引擎（此处可根据需要注入不同的衰减率配置）
        engine = PVCalculator()
        
        # 执行计算
        result = engine.calculate_20year_return(
            capacity_kw=payload.capacity_kw,
            sunshine_hours=payload.sunshine_hours,
            total_investment=payload.total_investment,
            benchmark_price=payload.benchmark_price,
            subsidy=payload.subsidy,
            discount_rate=payload.discount_rate
        )
        
        return result

    except ValueError as ve:
        # 捕获计算层可能的逻辑错误
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"计算逻辑错误: {str(ve)}"
        )
    except Exception as e:
        # 捕获未预见的系统错误
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部计算错误，请联系系统管理员"
        )

# --- 3. 补充说明 ---
# 该模块会自动集成到 FastAPI 的 /docs (Swagger UI) 中，
# 所有的 Field description 将作为前端开发者的 API 文档参考。