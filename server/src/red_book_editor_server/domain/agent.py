from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from red_book_editor_server.domain.ports import ModelGateway, ToolCall


class AgentTraceStep(BaseModel):
    """agent 运行过程中的一个可展示步骤。"""

    order: int
    kind: Literal["model", "tool", "phase"]
    label: str
    summary: str


class FinalValidation(BaseModel):
    """最终结构化输出的校验结果。"""

    ok: bool
    result: Any | None = None
    error: str = ""


@dataclass
class Tool:
    """agent 可调用工具的注册项。"""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[str]]


class AgentRunResult(BaseModel):
    """agent 运行结果：校验通过的结构化输出 + 完整 trace。"""

    result: Any
    trace: list[AgentTraceStep]


class AgentRunError(RuntimeError):
    """agent 未能产出通过校验的结果（达到最大步数或重试耗尽）。"""

    def __init__(self, message: str, trace: list[AgentTraceStep]) -> None:
        super().__init__(message)
        self.trace = trace


class AgentRuntime:
    """手写的最小 agent 循环：模型决策 → 工具执行 → 结果回填 → 再决策。

    固定骨架由调用方通过系统提示与最终校验器约束；本类只负责调度与 trace。
    """

    def __init__(
        self,
        gateway: ModelGateway,
        *,
        max_steps: int = 12,
        retry_final: int = 2,
        summary_limit: int = 400,
    ) -> None:
        self._gateway = gateway
        self._max_steps = max(1, max_steps)
        self._retry_final = max(0, retry_final)
        self._summary_limit = max(20, summary_limit)

    async def run(
        self,
        *,
        system: str,
        user: str,
        tools: list[Tool],
        final_validator: Callable[[str], FinalValidation],
    ) -> AgentRunResult:
        # messages 是 Agent 的“短期记忆”：每次模型调用都会看到完整历史，
        # 包括用户事实、模型上一次的工具请求，以及工具返回的结果。
        # Agent 不会自动拥有长期记忆；需要持久化的内容必须由业务层显式传入。
        messages: list[dict[str, object]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        trace: list[AgentTraceStep] = []
        # 工具 schema 发给模型，tool_map 留在服务端；模型只能提出调用请求，
        # 真正执行哪个 Python handler 仍由服务端控制。
        tool_schemas = [self._tool_schema(tool) for tool in tools]
        tool_map = {tool.name: tool for tool in tools}
        order = 0
        final_attempts = 0

        for _ in range(self._max_steps):
            # 一轮循环只有两种结果：模型要求工具，或模型尝试提交最终答案。
            # max_steps 是保险丝，防止模型一直调用工具或反复修订。
            # 一轮 loop = 给模型当前上下文 -> 等模型决定下一步。
            # 模型可能要求工具, 也可能认为已经完成并直接返回最终 JSON。
            response = await self._gateway.chat(messages, tools=tool_schemas)
            order += 1
            trace.append(
                AgentTraceStep(
                    order=order,
                    kind="model",
                    label="model",
                    summary=self._summarize(response.content or ""),
                )
            )

            if response.tool_calls:
                # 工具调用先在本地执行，结果再以 role=tool 回填给模型，
                # 下一轮模型才能根据工具结果继续决策。
                # 先把 assistant 的工具请求写回历史。下一次模型调用时,
                # 模型才知道自己刚才要求了什么工具。
                messages.append(
                    {
                        "role": "assistant",
                        "content": response.content or "",
                        "tool_calls": [
                            self._tool_call_payload(call) for call in response.tool_calls
                        ],
                    }
                )
                for call in response.tool_calls:
                    order += 1
                    # 工具在本地执行, 不再经过模型。执行结果随后以 role=tool
                    # 回填 messages，形成“决策 -> 执行 -> 结果回填”的闭环。
                    result_text = await self._execute_tool(tool_map, call)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "content": result_text,
                        }
                    )
                    trace.append(
                        AgentTraceStep(
                            order=order,
                            kind="tool",
                            label=call.name,
                            summary=self._summarize(
                                f"args={self._summarize(call.arguments, 160)} -> {result_text}"
                            ),
                        )
                    )
                continue

            # 没有工具调用，说明模型尝试结束本轮。这里不能直接相信文本，
            # 必须交给业务方提供的 validator 做 JSON、字段和事实校验。
            validation = final_validator(response.content or "")
            if validation.ok:
                return AgentRunResult(result=validation.result, trace=trace)
            final_attempts += 1
            if final_attempts > self._retry_final:
                raise AgentRunError("agent_finalization_failed", trace=trace)
            # 校验失败也继续 loop, 但只增加一条修正提示; 不重复执行已经完成的工具。
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"最终输出校验失败：{validation.error}。"
                        "请修正后重新输出完整结果，不要重复调用已执行过的工具。"
                    ),
                }
            )

        # max_steps 是保险丝: 防止模型一直调用工具或一直无法产出合法结果。
        raise AgentRunError("agent_max_steps", trace=trace)

    async def _execute_tool(self, tool_map: dict[str, Tool], call: ToolCall) -> str:
        # 模型只能提交工具名和 JSON 参数；这里负责把请求路由到白名单 handler，
        # 并把参数错误/handler 异常转换成模型可以理解的文本结果。
        tool = tool_map.get(call.name)
        if tool is None:
            return f'error: unknown tool "{call.name}"'
        try:
            args = json.loads(call.arguments or "{}")
            if not isinstance(args, dict):
                raise ValueError("arguments must be a JSON object")
        except (json.JSONDecodeError, ValueError) as error:
            return f"error: invalid tool arguments: {error}"
        try:
            return await tool.handler(args)
        except Exception as error:  # pragma: no cover - exercised by integration/model drift
            return f"error: tool {call.name} failed: {type(error).__name__}: {error}"

    @staticmethod
    def _tool_schema(tool: Tool) -> dict[str, object]:
        # schema 发给模型用于“决定要不要调用”，handler 不会随 schema 暴露给模型。
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    @staticmethod
    def _tool_call_payload(call: ToolCall) -> dict[str, object]:
        return {
            "id": call.id,
            "type": "function",
            "function": {"name": call.name, "arguments": call.arguments},
        }

    def _summarize(self, text: str, limit: int | None = None) -> str:
        # trace 只保存压缩摘要，避免把完整 prompt、用户正文或模型响应写入调试结果。
        compact = " ".join(text.split())
        if len(compact) <= (limit or self._summary_limit):
            return compact
        return f"{compact[: limit or self._summary_limit]}…"
