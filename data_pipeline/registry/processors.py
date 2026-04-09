from __future__ import annotations

from typing import Callable, Dict, Optional, Type, TypeVar

from data_pipeline.base.processor import BaseProcessor

ProcessorT = TypeVar("ProcessorT", bound=BaseProcessor)

_PROCESSOR_FACTORIES: Dict[str, Callable[[], BaseProcessor]] = {}


def register_processor(spider_name: str):
    """
    用法：
      @register_processor("energy_gov")
      class MyProcessor(BaseProcessor[...]): ...
    """

    def _decorator(cls: Type[ProcessorT]) -> Type[ProcessorT]:
        _PROCESSOR_FACTORIES[spider_name] = cls  # type: ignore[assignment]
        return cls

    return _decorator


def get_processor(spider_name: str) -> Optional[BaseProcessor]:
    f = _PROCESSOR_FACTORIES.get(spider_name)
    return f() if f is not None else None


def has_processor(spider_name: str) -> bool:
    return spider_name in _PROCESSOR_FACTORIES

