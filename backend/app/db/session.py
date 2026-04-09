from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# 确保 DATABASE_URL 使用 postgresql+asyncpg:// 协议
engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=bool(settings.DB_ECHO),
    future=True,
    pool_size=int(settings.DB_POOL_SIZE),
    max_overflow=int(settings.DB_MAX_OVERFLOW),
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