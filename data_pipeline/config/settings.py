from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


def _build_postgres_async_dsn(
    *,
    user: Optional[str],
    password: Optional[str],
    host: str,
    port: int,
    database: Optional[str],
) -> Optional[PostgresDsn]:
    if not (user and password and database):
        return None

    dsn = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
    try:
        return PostgresDsn(dsn)
    except Exception:
        return None


class PipelineSettings(BaseSettings):
    DATABASE_URL: Optional[PostgresDsn] = None
    PIPELINE_DATABASE_URL: Optional[PostgresDsn] = None

    # Optional PostgreSQL parts (used to derive DATABASE_URL / PIPELINE_DATABASE_URL)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432

    TASKIQ_BROKER_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    HTTP_TRUST_ENV: bool = False

    _PROJECT_ROOT = Path(__file__).resolve().parents[2]
    model_config = SettingsConfigDict(
        env_file=(
            str(_PROJECT_ROOT / ".env"),
            str(_PROJECT_ROOT / "backend" / ".env"),
        ),
        case_sensitive=True,
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        derived_database_url = _build_postgres_async_dsn(
            user=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )

        if self.DATABASE_URL is None and derived_database_url is not None:
            self.DATABASE_URL = derived_database_url

        if self.PIPELINE_DATABASE_URL is None:
            self.PIPELINE_DATABASE_URL = self.DATABASE_URL

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL is None:
            raise RuntimeError("DATABASE_URL is not configured")
        return str(self.DATABASE_URL)

    @property
    def pipeline_database_url(self) -> str:
        if self.PIPELINE_DATABASE_URL is not None:
            return str(self.PIPELINE_DATABASE_URL)
        if self.DATABASE_URL is not None:
            return str(self.DATABASE_URL)
        raise RuntimeError("PIPELINE_DATABASE_URL is not configured")


pipeline_settings = PipelineSettings()
