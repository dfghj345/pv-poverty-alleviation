from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple, Type, TypeVar

from data_pipeline.base.storage import BaseStorage

StorageT = TypeVar("StorageT", bound=BaseStorage)


@dataclass(frozen=True, slots=True)
class StorageKey:
    spider: Optional[str] = None
    site: Optional[str] = None
    data_type: Optional[str] = None


_FACTORIES: Dict[StorageKey, Callable[[], BaseStorage]] = {}


def register_storage(*, spider: Optional[str] = None, site: Optional[str] = None, data_type: Optional[str] = None):
    """
    支持按 spider/site/data_type 注册不同 storage。

    用法：
      @register_storage(spider="energy_gov", data_type="policy")
      class PolicyStorage(BaseStorage[...]): ...
    """

    def _decorator(cls: Type[StorageT]) -> Type[StorageT]:
        key = StorageKey(spider=spider, site=site, data_type=data_type)
        _FACTORIES[key] = cls  # type: ignore[assignment]
        return cls

    return _decorator


def _score(key: StorageKey, *, spider: str, site: str, data_type: str) -> Optional[int]:
    if key.spider is not None and key.spider != spider:
        return None
    if key.site is not None and key.site != site:
        return None
    if key.data_type is not None and key.data_type != data_type:
        return None

    # 匹配越具体得分越高
    score = 0
    score += 4 if key.spider is not None else 0
    score += 2 if key.site is not None else 0
    score += 1 if key.data_type is not None else 0
    return score


def get_storage(*, spider: str, site: str, data_type: str) -> Optional[BaseStorage]:
    best: Tuple[int, Callable[[], BaseStorage]] | None = None
    for k, f in _FACTORIES.items():
        s = _score(k, spider=spider, site=site, data_type=data_type)
        if s is None:
            continue
        if best is None or s > best[0]:
            best = (s, f)
    return best[1]() if best is not None else None

