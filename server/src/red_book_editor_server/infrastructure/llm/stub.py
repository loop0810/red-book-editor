from __future__ import annotations

from red_book_editor_server.domain.ports import ModelResponse


class StubModelGateway:
    """本地开发与测试用网关：不调用真实模型，仅返回固定文本。"""

    async def chat(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]] | None = None,
    ) -> ModelResponse:
        return ModelResponse(content="stub response")
