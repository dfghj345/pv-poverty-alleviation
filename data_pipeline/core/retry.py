from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")


async def async_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = 3,
    base_delay_s: float = 0.5,
    max_delay_s: float = 10.0,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Optional[Callable[[int, BaseException, float], None]] = None,
) -> T:
    last_exc: Optional[BaseException] = None
    for attempt in range(retries + 1):
        try:
            return await fn()
        except retry_on as exc:
            last_exc = exc
            if attempt >= retries:
                raise
            delay = min(max_delay_s, base_delay_s * (2**attempt))
            if on_retry is not None:
                try:
                    on_retry(attempt + 1, exc, delay)
                except Exception:
                    # 避免重试回调本身影响重试流程
                    pass
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc

