from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """服务端运行时配置。"""

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://red_book_editor:red_book_editor-local-only@127.0.0.1:5432/red_book_editor_development"
    storage_root: Path = Path("./storage")
    model_provider: str = "stub"
    model_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=None, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
