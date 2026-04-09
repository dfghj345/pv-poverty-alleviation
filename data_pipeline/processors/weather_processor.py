from __future__ import annotations

from decimal import Decimal
from typing import List

from data_pipeline.base.processor import BaseProcessor
from data_pipeline.core.context import RunContext
from data_pipeline.registry.processors import register_processor


@register_processor("weather_data")
class WeatherProcessor(BaseProcessor[Decimal, Decimal]):
    """
    最小 processor：保持业务不变（原本 parse 已兜底返回 Decimal）。
    后续如需单位/范围/缺失值策略，可在此扩展并保持可单测。
    """

    name = "weather_processor"

    def process(self, items: List[Decimal], ctx: RunContext) -> List[Decimal]:
        out: List[Decimal] = []
        for x in items:
            try:
                out.append(Decimal(x))
            except Exception:
                # 兜底：保持健壮性
                out.append(Decimal("1200"))
        return out

