from __future__ import annotations

import json
from collections.abc import Sequence

from red_book_editor_server.domain.ports import ModelResponse, ToolCall


class ScriptedGateway:
    """按脚本顺序返回响应的假网关；超出脚本长度时重复最后一条。"""

    def __init__(self, responses: Sequence[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[list[dict[str, object]], list[dict[str, object]] | None]] = []

    async def chat(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]] | None = None,
    ) -> ModelResponse:
        self.calls.append((list(messages), tools))
        return self._responses[min(len(self.calls) - 1, len(self._responses) - 1)]


def tool_call(name: str, arguments: dict[str, object] | None = None) -> ModelResponse:
    return ModelResponse(
        content=None,
        tool_calls=[
            ToolCall(
                id=f"call_{name}",
                name=name,
                arguments=json.dumps(arguments or {}),
            )
        ],
    )


def text_response(content: str) -> ModelResponse:
    return ModelResponse(content=content)
