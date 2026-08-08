from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from red_book_editor_server.domain.ports import ModelGatewayError
from red_book_editor_server.infrastructure.llm.deepseek import DeepSeekModelGateway


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5)


def _completion(
    content: str | None = None,
    tool_calls: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    message: dict[str, object] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message}]}


@pytest.mark.asyncio
async def test_chat_parses_tool_calls() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_completion(
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "echo", "arguments": '{"value":"hi"}'},
                    }
                ]
            ),
        )

    gateway = DeepSeekModelGateway(api_key="sk-test-123", http_client=_client(handler))
    response = await gateway.chat([{"role": "user", "content": "hello"}])

    assert response.tool_calls is not None
    assert response.tool_calls[0].name == "echo"
    assert json.loads(response.tool_calls[0].arguments) == {"value": "hi"}
    assert response.content is None


@pytest.mark.asyncio
async def test_chat_returns_plain_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion(content="plain answer"))

    gateway = DeepSeekModelGateway(api_key="sk-test-123", http_client=_client(handler))
    response = await gateway.chat([{"role": "user", "content": "hello"}])

    assert response.content == "plain answer"
    assert response.tool_calls is None


@pytest.mark.asyncio
async def test_chat_caches_successful_response() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=_completion(content="cached answer"))

    gateway = DeepSeekModelGateway(api_key="sk-test-123", http_client=_client(handler))
    first = await gateway.chat([{"role": "user", "content": "hello"}])
    second = await gateway.chat([{"role": "user", "content": "hello"}])

    assert calls == 1
    assert first == second


@pytest.mark.asyncio
async def test_chat_retries_timeout_then_succeeds() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ReadTimeout("boom")
        return httpx.Response(200, json=_completion(content="ok"))

    gateway = DeepSeekModelGateway(
        api_key="sk-test-123",
        max_retries=2,
        http_client=_client(handler),
    )
    response = await gateway.chat([{"role": "user", "content": "hello"}])

    assert attempts == 3
    assert response.content == "ok"


@pytest.mark.asyncio
async def test_chat_does_not_retry_4xx_and_never_leaks_key() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(400, json={"error": "bad request"})

    gateway = DeepSeekModelGateway(
        api_key="sk-test-123",
        max_retries=2,
        http_client=_client(handler),
    )

    with pytest.raises(ModelGatewayError) as excinfo:
        await gateway.chat([{"role": "user", "content": "hello"}])

    assert attempts == 1
    assert "sk-test-123" not in str(excinfo.value)


@pytest.mark.asyncio
async def test_chat_raises_after_retries_exhausted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network down")

    gateway = DeepSeekModelGateway(
        api_key="sk-test-123",
        max_retries=1,
        http_client=_client(handler),
    )

    with pytest.raises(ModelGatewayError):
        await gateway.chat([{"role": "user", "content": "hello"}])
