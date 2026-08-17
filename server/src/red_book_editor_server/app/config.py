from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_SERVER_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """服务端运行时配置。"""

    app_env: str = "development"
    # 8000 is reserved by the Godot AI MCP backend during Godot work.
    server_port: int = 8100
    database_url: str = "postgresql+asyncpg://red_book_editor:red_book_editor-local-only@127.0.0.1:5432/red_book_editor_development"
    storage_root: Path = Path("./storage")
    # stub 只用于测试和明确的离线开发，真实运行默认走 DeepSeek。
    model_provider: str = "deepseek"
    model_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DEEPSEEK_API_KEY", "MODEL_API_KEY"),
    )
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com"
    model_timeout_seconds: float = 60.0
    model_max_retries: int = 2
    model_max_tokens: int | None = None

    model_config = SettingsConfigDict(
        # 无论从仓库根目录还是 server/ 目录启动，都读取同一份本地配置。
        env_file=(_SERVER_ROOT / ".env", Path(".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def _validate_model_provider(self) -> Settings:
        self.model_provider = self.model_provider.strip().lower()
        if self.model_provider not in {"stub", "deepseek"}:
            raise ValueError("MODEL_PROVIDER must be one of: deepseek, stub")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
