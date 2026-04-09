from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal


@dataclass(slots=True)
class ErrorDetail:
    stage: str
    type: str
    message: str
    url: Optional[str] = None
    item_index: Optional[int] = None
    traceback_optional: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "type": self.type,
            "message": self.message,
            "url": self.url,
            "item_index": self.item_index,
            "traceback_optional": self.traceback_optional,
        }


@dataclass(slots=True)
class StageErrors:
    fetch_errors: List[ErrorDetail] = field(default_factory=list)
    parse_errors: List[ErrorDetail] = field(default_factory=list)
    process_errors: List[ErrorDetail] = field(default_factory=list)
    store_errors: List[ErrorDetail] = field(default_factory=list)

    def all(self) -> List[ErrorDetail]:
        return self.fetch_errors + self.parse_errors + self.process_errors + self.store_errors

    def any(self) -> bool:
        return bool(self.all())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fetch_errors": [e.to_dict() for e in self.fetch_errors],
            "parse_errors": [e.to_dict() for e in self.parse_errors],
            "process_errors": [e.to_dict() for e in self.process_errors],
            "store_errors": [e.to_dict() for e in self.store_errors],
        }


@dataclass(slots=True)
class PipelineSummary:
    run_id: str
    spider: str
    site: str
    url: Optional[str]
    stage: str
    items_count: int
    duration_ms: int
    status: Literal["ok", "fail", "skipped"]
    skipped_reason: Optional[str] = None

    def is_ok(self) -> bool:
        return self.status == "ok"

    def is_skipped(self) -> bool:
        return self.status == "skipped"


@dataclass(slots=True)
class PipelineDetails:
    stage_durations_ms: Dict[str, int] = field(default_factory=dict)
    errors: StageErrors = field(default_factory=StageErrors)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineReport:
    summary: PipelineSummary
    details: PipelineDetails

