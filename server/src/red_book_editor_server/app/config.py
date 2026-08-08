from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """服务端运行时配置。"""

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://red_book_editor:red_book_editor-local-only@127.0.0.1:5432/red_book_editor_development"
    storage_root: Path = Path("./storage")
    model_provider: str = "stub"
    model_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "MODEL_API_KEY"),
    )
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    model_timeout_seconds: float = 60.0
    model_max_retries: int = 2

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    @model_validator(mode="after")
    def _validate_model_provider(self) -> Settings:
        if self.model_provider == "deepseek" and not self.model_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required when MODEL_PROVIDER=deepseek")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
