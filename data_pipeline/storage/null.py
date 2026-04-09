from __future__ import annotations

from typing import List, TypeVar

from data_pipeline.base.storage import BaseStorage, StoreResult
from data_pipeline.core.context import RunContext

T = TypeVar("T")


class NullStorage(BaseStorage[T]):
    """
    默认 storage：不做任何持久化。
    主要用于测试/开发阶段不配置 DB 时的安全兜底。
    """

    name = "null"

    async def store(self, items: List[T], ctx: RunContext) -> StoreResult:
        return StoreResult(stored=0, failed=0, error=None, store_errors=[])

