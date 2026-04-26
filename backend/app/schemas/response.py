from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool = Field(default=True, alias="success")
    code: int = 200
    message: str = "success"
    data: Optional[T] = None

    @classmethod
    def success(cls, data: T | None = None, message: str = "success") -> "Result[T]":
        return cls(ok=True, code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int = 500, message: str = "error") -> "Result[Any]":
        return cls(ok=False, code=code, message=message, data=None)
