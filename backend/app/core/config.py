from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
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

    dsn = f'postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}'
    try:
        return PostgresDsn(dsn)
    except Exception:
        return None


class Settings(BaseSettings):
    PROJECT_NAME: str = 'PV_Poverty_Alleviation_API'

    DEBUG: bool = False

    # Database
    DATABASE_URL: Optional[PostgresDsn] = None
    PIPELINE_DATABASE_URL: Optional[PostgresDsn] = None
    REDIS_URL: RedisDsn

    # Optional PostgreSQL parts (used to derive DATABASE_URL / PIPELINE_DATABASE_URL)
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: str = '127.0.0.1'
    POSTGRES_PORT: int = 5432

    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # Security
    SECRET_KEY: str
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Business defaults (keep behavior consistent)
    DEFAULT_EQUIVALENT_HOURS: float = 1200.0
    UNIT_COST_PER_KW: float = 3500.0
    DEFAULT_DEGRADATION: float = 0.008

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            'http://localhost:5173',
            'http://127.0.0.1:5173',
            'http://localhost:8080',
        ]
    )

    # Logging
    LOG_LEVEL: str = 'INFO'

    @field_validator('DEBUG', mode='before')
    @classmethod
    def normalize_debug(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            truthy = {'1', 'true', 'yes', 'on', 'debug', 'dev', 'development'}
            falsy = {'0', 'false', 'no', 'off', 'release', 'prod', 'production', ''}
            if normalized in truthy:
                return True
            if normalized in falsy:
                return False
        raise ValueError('DEBUG must be a boolean-like value')

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def normalize_cors_origins(cls, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []

            # Support JSON array string: ["http://a", "http://b"]
            if raw.startswith('['):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass

            # Support comma-separated string: http://a,http://b
            return [item.strip() for item in raw.split(',') if item.strip()]

        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]

        raise ValueError('CORS_ORIGINS must be a list or comma-separated string')

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
            raise RuntimeError('DATABASE_URL is not configured')
        return str(self.DATABASE_URL)

    @property
    def pipeline_database_url(self) -> str:
        if self.PIPELINE_DATABASE_URL is not None:
            return str(self.PIPELINE_DATABASE_URL)
        if self.DATABASE_URL is not None:
            return str(self.DATABASE_URL)
        raise RuntimeError('PIPELINE_DATABASE_URL is not configured')

    # App Config
    _PROJECT_ROOT = Path(__file__).resolve().parents[3]
    _BACKEND_DIR = Path(__file__).resolve().parents[2]
    model_config = SettingsConfigDict(
        # Support both repo-root .env and backend/.env. Environment variables still win.
        env_file=(
            str(_PROJECT_ROOT / '.env'),
            str(_BACKEND_DIR / '.env'),
        ),
        case_sensitive=True,
        extra='ignore'
    )


settings = Settings()
