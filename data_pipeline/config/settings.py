from __future__ import annotations

from typing import Optional

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class PipelineSettings(BaseSettings):
    """
    工程化 settings：
    - 允许只跑 parse/process 测试时不配置 DB/Broker（保持可测试性）
    - 忽略 .env 中与本 pipeline 无关的变量（避免 extra_forbidden）
    """

    PIPELINE_DATABASE_URL: Optional[PostgresDsn] = None
    # 兼容已有项目 .env（仅提供 POSTGRES_*），自动拼接 PIPELINE_DATABASE_URL
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432

    TASKIQ_BROKER_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    HTTP_TRUST_ENV: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        # 若未显式配置 PIPELINE_DATABASE_URL，则从 POSTGRES_* 组合
        if self.PIPELINE_DATABASE_URL is not None:
            return
        if not (self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB):
            return
        dsn = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        try:
            self.PIPELINE_DATABASE_URL = PostgresDsn(dsn)  # type: ignore[assignment]
        except Exception:
            # 不阻断启动：后续真正建 engine 时会给出清晰错误
            return


pipeline_settings = PipelineSettings()

