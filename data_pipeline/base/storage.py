from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, List, Optional, TypeVar

from data_pipeline.core.context import RunContext
from data_pipeline.core.results import ErrorDetail

ItemT = TypeVar("ItemT")


@dataclass(slots=True)
class StoreResult:
    stored: int
    failed: int = 0
    error: Optional[str] = None
    store_errors: List[ErrorDetail] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.store_errors is None:
            self.store_errors = []


class BaseStorage(ABC, Generic[ItemT]):
    name: str

    @abstractmethod
    async def store(self, items: List[ItemT], ctx: RunContext) -> StoreResult:
        raise NotImplementedError

