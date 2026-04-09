from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, List, Mapping, Optional, Sequence, TypeVar

from data_pipeline.core.context import RunContext

RawT = TypeVar("RawT")
ParsedT = TypeVar("ParsedT")


class BaseSpider(ABC, Generic[RawT, ParsedT]):
    """
    Spider 只负责采集与解析：fetch + parse。
    清洗/标准化/字段映射交给 Processor。
    """

    name: str
    site: str
    enabled: bool = True
    disabled_reason: str = ""

    def start_urls(self) -> Sequence[str]:
        return ()

    def request_headers(self) -> Mapping[str, str]:
        return {}

    @abstractmethod
    async def fetch(self, ctx: RunContext) -> RawT:
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: RawT, ctx: RunContext) -> List[ParsedT]:
        raise NotImplementedError

    def validate_items(self, items: Iterable[ParsedT], ctx: RunContext) -> None:
        # 默认不做；如需可覆写（例如字段必填校验）
        return None

