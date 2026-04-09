from __future__ import annotations

from typing import Dict, List, Type, TypeVar

from data_pipeline.base.spider import BaseSpider

SpiderT = TypeVar("SpiderT", bound=BaseSpider)

_SPIDERS: Dict[str, Type[BaseSpider]] = {}


def register_spider(name: str):
    def _decorator(cls: Type[SpiderT]) -> Type[SpiderT]:
        _SPIDERS[name] = cls
        return cls

    return _decorator


def get_spider(name: str) -> Type[BaseSpider]:
    try:
        return _SPIDERS[name]
    except KeyError as e:
        raise KeyError(f"unknown spider: {name}. available={list(_SPIDERS.keys())}") from e


def list_spiders() -> List[str]:
    return sorted(_SPIDERS.keys())

