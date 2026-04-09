from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Mapping, MutableMapping, Optional
from uuid import uuid4


Stage = str  # fetch | parse | process | store | crawl | test


@dataclass(slots=True)
class RunContext:
    run_id: str = field(default_factory=lambda: uuid4().hex)
    spider: str = ""
    site: str = ""
    stage: Stage = "crawl"
    url: Optional[str] = None
    meta: MutableMapping[str, Any] = field(default_factory=dict)
    _t0: float = field(default_factory=perf_counter, repr=False)

    def with_stage(self, stage: Stage, *, url: Optional[str] = None, **meta: Any) -> "RunContext":
        new = RunContext(
            run_id=self.run_id,
            spider=self.spider,
            site=self.site,
            stage=stage,
            url=url if url is not None else self.url,
            meta={**self.meta, **meta},
        )
        return new

    def elapsed_ms(self) -> int:
        return int((perf_counter() - self._t0) * 1000)

    def log_extra(self) -> Mapping[str, Any]:
        return {
            "run_id": self.run_id,
            "spider": self.spider,
            "site": self.site,
            "stage": self.stage,
            "url": self.url,
            **self.meta,
        }

