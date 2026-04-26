import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.models.project import Base

logger = logging.getLogger(__name__)

# Main application database engine.
engine = create_async_engine(
    settings.database_url,
    echo=bool(settings.DB_ECHO),
    future=True,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=int(settings.DB_POOL_SIZE),
    max_overflow=int(settings.DB_MAX_OVERFLOW),
    connect_args={
        'ssl': False,
        'timeout': 10,
        'command_timeout': 60,
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

async def get_db():
    """Dependency for getting async session"""
    async with AsyncSessionLocal() as session:
        yield session


async def initialize_database() -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS postgis;'))
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.warning('main application database initialization skipped', extra={'error': str(exc)})


async def dispose_database() -> None:
    await engine.dispose()
