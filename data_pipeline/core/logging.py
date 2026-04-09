from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

from data_pipeline.core.context import RunContext


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class ContextLogger(logging.LoggerAdapter):
    def __init__(self, logger: logging.Logger, *, ctx: Optional[RunContext] = None, base_extra: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(logger, extra={})
        self._ctx = ctx
        self._base_extra = dict(base_extra or {})

    def bind(self, *, ctx: Optional[RunContext] = None, **extra: Any) -> "ContextLogger":
        new = ContextLogger(self.logger, ctx=ctx if ctx is not None else self._ctx, base_extra={**self._base_extra, **extra})
        return new

    def process(self, msg: str, kwargs: Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
        extra = dict(self._base_extra)
        if self._ctx is not None:
            extra.update(self._ctx.log_extra())
        if "extra" in kwargs and isinstance(kwargs["extra"], dict):
            extra.update(kwargs["extra"])
        new_kwargs = dict(kwargs)
        new_kwargs["extra"] = extra
        return msg, new_kwargs


def get_ctx_logger(name: str, *, ctx: Optional[RunContext] = None, **extra: Any) -> ContextLogger:
    return ContextLogger(get_logger(name), ctx=ctx, base_extra=extra)

