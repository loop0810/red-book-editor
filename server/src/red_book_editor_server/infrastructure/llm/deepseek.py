from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

import httpx

from red_book_editor_server.domain.ports import (
    ModelGatewayError,
    ModelResponse,
    ToolCall,
)


class DeepSeekModelGateway:
    """OpenAI 兼容的 DeepSeek 聊天适配器（deepseek-chat）。"""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        http_client: httpx.AsyncClient | None = None,
        cache_ttl_seconds: float = 300.0,
        cache_max_entries: int = 128,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(0, max_retries)
        self._http_client = http_client
        self._cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self._cache_max_entries = max(0, cache_max_entries)
        self._response_cache: OrderedDict[str, tuple[float, ModelResponse]] = OrderedDict()

    async def chat(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]] | None = None,
    ) -> ModelResponse:
        # AgentRuntime 只依赖 ModelGateway，不知道这里具体是 DeepSeek。
        # 适配器把统一的 messages/tools 转成供应商的 HTTP 请求。
        cache_key = self._cache_key(messages, tools)
        cached = self._get_cached(cache_key)
        if cached is not None:
            # 相同请求直接复用成功响应，减少重复点击造成的成本。
            # 评测 runner 会主动关闭缓存，避免把重复实验误当成独立采样。
            return cached

        url = f"{self._base_url}/chat/completions"
        payload: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools is not None:
            payload["tools"] = tools
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                # 每次尝试只在这里跨越网络边界；后面的 Agent 逻辑不处理 HTTP 细节。
                if self._http_client is not None:
                    response = await self._http_client.post(url, headers=headers, json=payload)
                else:
                    async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                        response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                parsed = self._parse_response(response.json())
                self._put_cached(cache_key, parsed)
                return parsed
            except httpx.HTTPStatusError as error:
                last_error = error
                if 400 <= error.response.status_code < 500:
                    break
            except httpx.TimeoutException as error:
                last_error = error
            except httpx.HTTPError as error:
                last_error = error
        raise ModelGatewayError(
            f"model_request_failed: {type(last_error).__name__ if last_error else 'unknown'}"
        ) from last_error

    def _cache_key(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]] | None,
    ) -> str:
        payload = json.dumps(
            {"model": self._model, "messages": messages, "tools": tools},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _get_cached(self, key: str) -> ModelResponse | None:
        if self._cache_ttl_seconds <= 0 or self._cache_max_entries <= 0:
            return None
        item = self._response_cache.get(key)
        if item is None:
            return None
        created_at, response = item
        if time.monotonic() - created_at >= self._cache_ttl_seconds:
            self._response_cache.pop(key, None)
            return None
        self._response_cache.move_to_end(key)
        return response.model_copy(deep=True)

    def _put_cached(self, key: str, response: ModelResponse) -> None:
        if self._cache_ttl_seconds <= 0 or self._cache_max_entries <= 0:
            return
        self._response_cache[key] = (time.monotonic(), response.model_copy(deep=True))
        self._response_cache.move_to_end(key)
        while len(self._response_cache) > self._cache_max_entries:
            self._response_cache.popitem(last=False)

    @staticmethod
    def _parse_response(data: dict[str, Any]) -> ModelResponse:
        message = data["choices"][0]["message"]
        content = message.get("content")
        tool_calls = [
            ToolCall(
                id=call["id"],
                name=call["function"]["name"],
                arguments=call["function"].get("arguments") or "{}",
            )
            for call in message.get("tool_calls") or []
        ]
        return ModelResponse(content=content, tool_calls=tool_calls or None)
