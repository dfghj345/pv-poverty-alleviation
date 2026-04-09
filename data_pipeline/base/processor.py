from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

from data_pipeline.core.context import RunContext

InT = TypeVar("InT")
OutT = TypeVar("OutT")


class BaseProcessor(ABC, Generic[InT, OutT]):
    """
    Processor 负责清洗/标准化/字段映射。
    设计为可单测的纯逻辑单元（尽量无 I/O）。
    """

    name: str

    @abstractmethod
    def process(self, items: List[InT], ctx: RunContext) -> List[OutT]:
        raise NotImplementedError

