from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from data_pipeline.core.config import pipeline_settings

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is not None:
        return _engine
    if pipeline_settings.PIPELINE_DATABASE_URL is None:
        raise RuntimeError("PIPELINE_DATABASE_URL is not configured; cannot create db engine")

    _engine = create_async_engine(
        str(pipeline_settings.PIPELINE_DATABASE_URL),
        echo=False,
        future=True,
        # Windows + asyncpg：避免 stale connection / 复用死连接
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=1,
        max_overflow=0,
        connect_args={
            # asyncpg 不支持 ssl="disable"；用 False 显式禁用 SSL 协商
            "ssl": False,
            "timeout": 10,
            "command_timeout": 60,
        },
    )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is not None:
        return _sessionmaker
    engine = get_engine()
    _sessionmaker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return _sessionmaker


def AsyncSessionLocal() -> AsyncSession:
    return get_sessionmaker()()


engine = None  # type: ignore[assignment]