from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = 'PV_Poverty_Alleviation_API'

    DEBUG: bool = False

    # Database
    DATABASE_URL: PostgresDsn
    PIPELINE_DATABASE_URL: Optional[PostgresDsn] = None
    REDIS_URL: RedisDsn

    # Optional PostgreSQL parts (used to derive PIPELINE_DATABASE_URL)
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
        # Build PIPELINE_DATABASE_URL automatically when only POSTGRES_* is provided.
        if self.PIPELINE_DATABASE_URL is not None:
            return
        if not (self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB):
            return

        dsn = (
            f'postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}'
            f'@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}'
        )
        try:
            self.PIPELINE_DATABASE_URL = PostgresDsn(dsn)  # type: ignore[assignment]
        except Exception:
            # Keep startup non-blocking; real engine creation will raise a clear error later.
            return

    # App Config
    _BACKEND_DIR = Path(__file__).resolve().parents[2]
    model_config = SettingsConfigDict(
        # Always load backend/.env regardless of current working directory.
        env_file=str(_BACKEND_DIR / '.env'),
        case_sensitive=True,
        extra='ignore'
    )


settings = Settings()
