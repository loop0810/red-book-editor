from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, NoReturn, TypeVar

from pydantic import BaseModel

from red_book_editor_server.domain.ports import ModelGateway, ToolCall

AGENT_RUNTIME_VERSION = "agent-runtime-v1"

T = TypeVar("T")


class AgentPhase(StrEnum):
    COLLECT_CONTEXT = "collect_context"
    DRAFT = "draft"
    CRITIQUE = "critique"
    REVISE = "revise"
    SAFETY_REVIEW = "safety_review"
    FINALIZE = "finalize"


class AgentRunStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    BUDGET_EXHAUSTED = "budget_exhausted"
    CANCELLED = "cancelled"


class AgentFailureCode(StrEnum):
    MAX_STEPS = "agent_max_steps"
    FINALIZATION_FAILED = "agent_finalization_failed"
    REVISION_BUDGET_EXHAUSTED = "agent_revision_budget_exhausted"
    TOOL_BUDGET_EXHAUSTED = "agent_tool_budget_exhausted"
    REPEATED_ERROR = "agent_repeated_error"
    STAGE_TIMEOUT = "agent_stage_timeout"
    MODEL_ERROR = "agent_model_error"
    INPUT_ERROR = "agent_input_error"
    UNEXPECTED_ERROR = "agent_unexpected_error"
    CANCELLED = "agent_cancelled"


class AgentRunDiagnostics(BaseModel):
    status: AgentRunStatus
    phase: AgentPhase
    steps: int = 0
    revisions: int = 0
    tool_calls: int = 0
    repeated_errors: int = 0
    model_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    usage_available: bool = False
    failure_code: AgentFailureCode | None = None


class AgentTraceStep(BaseModel):
    """agent 运行过程中的一个可展示步骤。"""

    order: int
    kind: Literal["model", "tool", "phase"]
    label: str
    summary: str
    phase: AgentPhase | None = None


class AgentRuntimeEvent(BaseModel):
    """Runtime 发给应用层的有界事件，不包含完整模型消息。"""

    order: int
    kind: Literal["model", "tool", "phase", "terminal"]
    label: str
    summary: str
    phase: AgentPhase | None = None
    status: AgentRunStatus | None = None
    failure_code: AgentFailureCode | None = None


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
    phase: AgentPhase = AgentPhase.DRAFT
    transition: Callable[[str], AgentPhase | None] | None = None


class AgentRunResult(BaseModel):
    """agent 运行结果：校验通过的结构化输出、trace 和运行诊断。"""

    result: Any
    trace: list[AgentTraceStep]
    diagnostics: AgentRunDiagnostics


class AgentRunError(RuntimeError):
    """agent 未能产出通过校验的结果，并保留失败诊断和部分 trace。"""

    def __init__(
        self,
        message: str,
        trace: list[AgentTraceStep],
        *,
        diagnostics: AgentRunDiagnostics | None = None,
        partial_result: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.trace = trace
        self.diagnostics = diagnostics or AgentRunDiagnostics(
            status=AgentRunStatus.FAILED,
            phase=AgentPhase.COLLECT_CONTEXT,
            failure_code=_failure_code_from_message(message),
        )
        self.partial_result = partial_result


class AgentRuntime:
    """手写的有限状态 agent 循环：模型决策 → 工具执行 → 结果回填 → 再决策。"""

    def __init__(
        self,
        gateway: ModelGateway,
        *,
        max_steps: int = 12,
        retry_final: int = 2,
        summary_limit: int = 400,
        max_revisions: int | None = None,
        max_tool_calls: int = 24,
        max_same_error: int = 0,
        stage_timeout_seconds: float | None = None,
        phase_timeouts: Mapping[AgentPhase, float] | None = None,
    ) -> None:
        self._gateway = gateway
        self._max_steps = _positive_int(max_steps, "max_steps")
        self._retry_final = _nonnegative_int(retry_final, "retry_final")
        self._summary_limit = max(20, summary_limit)
        self._revision_budget_explicit = max_revisions is not None
        self._max_revisions = (
            self._retry_final
            if max_revisions is None
            else _nonnegative_int(max_revisions, "max_revisions")
        )
        self._max_tool_calls = _nonnegative_int(max_tool_calls, "max_tool_calls")
        self._max_same_error = _nonnegative_int(max_same_error, "max_same_error")
        if stage_timeout_seconds is not None and stage_timeout_seconds <= 0:
            raise ValueError("stage_timeout_seconds must be positive")
        self._stage_timeout_seconds = stage_timeout_seconds
        self._phase_timeouts = dict(phase_timeouts or {})
        for phase, timeout in self._phase_timeouts.items():
            if timeout <= 0:
                raise ValueError(f"phase timeout for {phase} must be positive")

    async def run(
        self,
        *,
        system: str,
        user: str,
        tools: list[Tool],
        final_validator: Callable[[str], FinalValidation],
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
        event_sink: Callable[[AgentRuntimeEvent], Awaitable[None]] | None = None,
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
        event_order = 0
        steps = 0
        revisions = 0
        tool_calls = 0
        repeated_errors = 0
        model_calls = 0
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        usage_available = False
        last_error: str | None = None
        current_phase = AgentPhase.COLLECT_CONTEXT
        phase_started = time.monotonic()
        partial_result: Any | None = None
        # diagnostics 在整个循环中累加，失败时也原样带出；这让上层能够区分
        # 模型不可用、预算耗尽、用户取消和最终校验失败，而不是只看到一个 500。

        def diagnostics(
            status: AgentRunStatus,
            failure_code: AgentFailureCode | None = None,
        ) -> AgentRunDiagnostics:
            return AgentRunDiagnostics(
                status=status,
                phase=current_phase,
                steps=steps,
                revisions=revisions,
                tool_calls=tool_calls,
                repeated_errors=repeated_errors,
                model_calls=model_calls,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                usage_available=usage_available,
                failure_code=failure_code,
            )

        def fail(code: AgentFailureCode, status: AgentRunStatus) -> NoReturn:
            raise AgentRunError(
                code.value,
                trace,
                diagnostics=diagnostics(status, code),
                partial_result=partial_result,
            )

        def set_phase(next_phase: AgentPhase) -> None:
            nonlocal current_phase, phase_started
            if current_phase != next_phase:
                current_phase = next_phase
                phase_started = time.monotonic()

        async def emit(
            kind: Literal["model", "tool", "phase", "terminal"],
            label: str,
            summary: str,
            *,
            status: AgentRunStatus | None = None,
            failure_code: AgentFailureCode | None = None,
        ) -> None:
            nonlocal event_order
            if event_sink is None:
                return
            event_order += 1
            await event_sink(
                AgentRuntimeEvent(
                    order=event_order,
                    kind=kind,
                    label=label,
                    summary=self._summarize(summary),
                    phase=current_phase,
                    status=status,
                    failure_code=failure_code,
                )
            )

        async def check_cancelled() -> None:
            if cancel_check is not None and await cancel_check():
                fail(AgentFailureCode.CANCELLED, AgentRunStatus.CANCELLED)

        def record_error(error: str) -> None:
            nonlocal last_error, repeated_errors
            normalized = _normalize_error(error, self._summary_limit)
            if normalized == last_error:
                repeated_errors += 1
            else:
                last_error = normalized
                repeated_errors = 1

        async def invoke(factory: Callable[[], Awaitable[T]]) -> T:
            await check_cancelled()
            timeout = self._phase_timeouts.get(current_phase, self._stage_timeout_seconds)
            if timeout is None:
                return await factory()
            remaining = timeout - (time.monotonic() - phase_started)
            if remaining <= 0:
                fail(AgentFailureCode.STAGE_TIMEOUT, AgentRunStatus.BUDGET_EXHAUSTED)
            try:
                # 每个阶段都使用剩余预算计算超时，避免一次慢模型调用吞掉整条 Agent 运行的预算。
                return await asyncio.wait_for(factory(), timeout=remaining)
            except asyncio.TimeoutError:
                fail(AgentFailureCode.STAGE_TIMEOUT, AgentRunStatus.BUDGET_EXHAUSTED)

        await emit("phase", current_phase.value, f"进入阶段：{current_phase.value}")
        for _ in range(self._max_steps):
            # 一轮循环只允许模型决策、白名单工具执行、再回填上下文；
            # max_steps/max_tool_calls/max_revisions 是服务端保险丝，不由模型自行修改。
            steps += 1
            await check_cancelled()
            # 一轮循环只有两种结果：模型要求工具，或模型尝试提交最终答案。
            # max_steps 是保险丝，独立预算负责防止特定类型的循环。
            response = await invoke(lambda: self._gateway.chat(messages, tools=tool_schemas))
            model_calls += 1
            # usage 只累加计数，不保存供应商原始响应，既服务于成本统计也保持隐私边界。
            if response.usage is not None:
                usage_available = True
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens
                total_tokens += response.usage.total_tokens
            order += 1
            trace.append(
                AgentTraceStep(
                    order=order,
                    kind="model",
                    label="model",
                    summary=self._summarize(response.content or ""),
                    phase=current_phase,
                )
            )
            await emit(
                "model",
                "model",
                "模型调用完成",
            )

            if response.tool_calls:
                # 工具调用先在本地执行，结果再以 role=tool 回填给模型。
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
                    if tool_calls >= self._max_tool_calls:
                        fail(
                            AgentFailureCode.TOOL_BUDGET_EXHAUSTED, AgentRunStatus.BUDGET_EXHAUSTED
                        )
                    tool_calls += 1
                    tool = tool_map.get(call.name)
                    if tool is not None:
                        set_phase(tool.phase)
                        await emit("phase", current_phase.value, f"进入阶段：{current_phase.value}")
                    result_text = await invoke(lambda: self._execute_tool(tool_map, call))
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
                            phase=current_phase,
                        )
                    )
                    await emit(
                        "tool",
                        call.name,
                        "工具调用失败" if result_text.startswith("error:") else "工具调用完成",
                    )
                    if result_text.startswith("error:"):
                        record_error(result_text)
                        if self._max_same_error and repeated_errors >= self._max_same_error:
                            fail(AgentFailureCode.REPEATED_ERROR, AgentRunStatus.BUDGET_EXHAUSTED)
                    else:
                        last_error = None
                        repeated_errors = 0
                    if tool is not None and tool.transition is not None:
                        next_phase = tool.transition(result_text)
                        if next_phase is not None:
                            set_phase(next_phase)
                            await emit(
                                "phase", current_phase.value, f"进入阶段：{current_phase.value}"
                            )
                continue

            # 没有工具调用，说明模型尝试结束本轮；最终结果必须经过 validator。
            await check_cancelled()
            set_phase(AgentPhase.FINALIZE)
            await emit("phase", current_phase.value, f"进入阶段：{current_phase.value}")
            validation = final_validator(response.content or "")
            if validation.ok:
                # 只有领域 validator 通过，模型输出才会离开 AgentRuntime 成为业务对象。
                await emit(
                    "terminal",
                    AgentRunStatus.COMPLETED.value,
                    "Agent 运行完成",
                    status=AgentRunStatus.COMPLETED,
                )
                return AgentRunResult(
                    result=validation.result,
                    trace=trace,
                    diagnostics=diagnostics(AgentRunStatus.COMPLETED),
                )
            partial_result = validation.result or partial_result
            revisions += 1
            # 结构化校验失败会进入有限修订循环；超过预算直接失败，避免无限重复生成。
            record_error(validation.error)
            set_phase(AgentPhase.REVISE)
            if self._max_same_error and repeated_errors >= self._max_same_error:
                fail(AgentFailureCode.REPEATED_ERROR, AgentRunStatus.BUDGET_EXHAUSTED)
            if revisions > self._max_revisions:
                if self._revision_budget_explicit:
                    fail(
                        AgentFailureCode.REVISION_BUDGET_EXHAUSTED,
                        AgentRunStatus.BUDGET_EXHAUSTED,
                    )
                fail(AgentFailureCode.FINALIZATION_FAILED, AgentRunStatus.FAILED)
            # 校验失败也继续 loop, 但只增加一条修正提示，不重复执行已完成工具。
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"最终输出校验失败：{validation.error}。"
                        "请修正后重新输出完整结果，不要重复调用已执行过的工具。"
                    ),
                }
            )

        # max_steps 是保险丝：防止模型一直调用工具或一直无法产出合法结果。
        fail(AgentFailureCode.MAX_STEPS, AgentRunStatus.BUDGET_EXHAUSTED)

    async def _execute_tool(self, tool_map: dict[str, Tool], call: ToolCall) -> str:
        # 模型只能提交工具名和 JSON 参数；这里负责把请求路由到白名单 handler。
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
        max_length = limit or self._summary_limit
        return f"{compact[: max_length - 1]}…"


def _positive_int(value: int, name: str) -> int:
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _nonnegative_int(value: int, name: str) -> int:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")
    return value


def _normalize_error(value: str, limit: int) -> str:
    return " ".join(value.split())[:limit]


def _failure_code_from_message(message: str) -> AgentFailureCode | None:
    try:
        return AgentFailureCode(message)
    except ValueError:
        return None
