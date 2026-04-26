from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(slots=True)
class PipelineError(Exception):
    message: str
    spider: str = ""
    site: str = ""
    stage: str = ""
    url: Optional[str] = None
    item_index: Optional[int] = None
    cause: Optional[BaseException] = None
    extra: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        bits = [self.message]
        if self.stage:
            bits.append(f"stage={self.stage}")
        if self.spider:
            bits.append(f"spider={self.spider}")
        if self.site:
            bits.append(f"site={self.site}")
        if self.url:
            bits.append(f"url={self.url}")
        if self.item_index is not None:
            bits.append(f"item_index={self.item_index}")
        if self.cause is not None:
            bits.append(f"cause={type(self.cause).__name__}: {self.cause}")
        return " | ".join(bits)


class FetchError(PipelineError): ...


class ParseError(PipelineError): ...


class ProcessError(PipelineError): ...


class StoreError(PipelineError): ...


class SkipPipelineError(PipelineError): ...

