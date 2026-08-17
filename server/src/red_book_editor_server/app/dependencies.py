from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from red_book_editor_server.app.config import Settings
from red_book_editor_server.domain.ports import ModelGateway, ModelGatewayError
from red_book_editor_server.infrastructure.llm import DeepSeekModelGateway, StubModelGateway


async def database_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory = request.app.state.session_factory
    async for session in request.app.state.database_session_provider(session_factory):
        yield session


def build_model_gateway(settings: Settings) -> ModelGateway:
    """按配置选择模型网关；stub 仅用于测试和明确的离线开发。"""

    if settings.model_provider == "deepseek":
        if not settings.model_api_key:
            raise ModelGatewayError("model_api_key_missing")
        return _build_deepseek_gateway(
            settings.model_api_key,
            settings.deepseek_model,
            settings.deepseek_base_url,
            settings.model_timeout_seconds,
            settings.model_max_retries,
            settings.model_max_tokens,
        )
    return StubModelGateway()


@lru_cache(maxsize=4)
def _build_deepseek_gateway(
    api_key: str,
    model: str,
    base_url: str,
    timeout_seconds: float,
    max_retries: int,
    max_tokens: int | None,
) -> DeepSeekModelGateway:
    """复用进程内网关，让其响应缓存跨请求生效。"""

    return DeepSeekModelGateway(
        api_key=api_key,
        model=model,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        max_tokens=max_tokens,
    )
