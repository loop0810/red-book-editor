from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import pytest

from red_book_editor_server.domain.agent import (
    AgentFailureCode,
    AgentPhase,
    AgentRunError,
    AgentRuntimeEvent,
    AgentRunStatus,
    AgentRuntime,
    FinalValidation,
    Tool,
)
from red_book_editor_server.modules.content_workflow.styling.tools import build_styling_tools
from tests.unit.fakes import ScriptedGateway, text_response, tool_call


async def _echo(args: dict[str, object]) -> str:
    return json.dumps(args, ensure_ascii=False)


async def _slow_echo(args: dict[str, object]) -> str:
    await asyncio.sleep(0.05)
    return json.dumps(args, ensure_ascii=False)


def _echo_tool() -> Tool:
    return Tool(
        name="echo",
        description="echo tool",
        parameters={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        handler=_echo,
    )


def _slow_tool() -> Tool:
    tool = _echo_tool()
    tool.handler = _slow_echo
    return tool


def _json_validator() -> Callable[[str], FinalValidation]:
    def validate(content: str) -> FinalValidation:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as error:
            return FinalValidation(ok=False, error=str(error))
        return FinalValidation(ok=True, result=parsed)

    return validate


@pytest.mark.asyncio
async def test_tool_calling_round_trip() -> None:
    gateway = ScriptedGateway(
        [
            tool_call("echo", {"value": "hi"}),
            text_response('{"ok": true}'),
        ]
    )
    runtime = AgentRuntime(gateway, max_steps=5)

    result = await runtime.run(
        system="test",
        user="hello",
        tools=[_echo_tool()],
        final_validator=_json_validator(),
    )

    assert result.result == {"ok": True}
    assert [step.kind for step in result.trace] == ["model", "tool", "model"]
    assert result.trace[1].label == "echo"
    assert "hi" in result.trace[1].summary
    assert result.diagnostics.status is AgentRunStatus.COMPLETED
    assert result.diagnostics.steps == 2
    assert result.diagnostics.tool_calls == 1


@pytest.mark.asyncio
async def test_max_steps_raises_with_partial_trace() -> None:
    gateway = ScriptedGateway([tool_call("echo", {"value": "loop"})])
    runtime = AgentRuntime(gateway, max_steps=3)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="loop",
            tools=[_echo_tool()],
            final_validator=_json_validator(),
        )

    assert excinfo.value.args[0] == "agent_max_steps"
    assert len(excinfo.value.trace) == 6
    assert excinfo.value.diagnostics.failure_code is AgentFailureCode.MAX_STEPS
    assert excinfo.value.diagnostics.status is AgentRunStatus.BUDGET_EXHAUSTED


@pytest.mark.asyncio
async def test_malformed_final_output_is_retried() -> None:
    gateway = ScriptedGateway(
        [
            text_response("not json"),
            text_response('{"ok": true}'),
        ]
    )
    runtime = AgentRuntime(gateway, max_steps=5)

    result = await runtime.run(
        system="test",
        user="hello",
        tools=[_echo_tool()],
        final_validator=_json_validator(),
    )

    assert result.result == {"ok": True}
    feedback = gateway.calls[1][0][-1]["content"]
    assert isinstance(feedback, str)
    assert "校验失败" in feedback
    assert result.diagnostics.revisions == 1


@pytest.mark.asyncio
async def test_finalization_failure_after_retry_cap() -> None:
    gateway = ScriptedGateway([text_response("still not json")])
    runtime = AgentRuntime(gateway, max_steps=5, retry_final=2)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="hello",
            tools=[_echo_tool()],
            final_validator=_json_validator(),
        )

    assert excinfo.value.args[0] == "agent_finalization_failed"


@pytest.mark.asyncio
async def test_explicit_revision_budget_has_stable_failure_code() -> None:
    gateway = ScriptedGateway([text_response("still not json")])
    runtime = AgentRuntime(gateway, max_steps=5, max_revisions=1)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="hello",
            tools=[_echo_tool()],
            final_validator=_json_validator(),
        )

    assert excinfo.value.args[0] == "agent_revision_budget_exhausted"
    assert excinfo.value.diagnostics.revisions == 2


@pytest.mark.asyncio
async def test_tool_budget_stops_before_next_tool_execution() -> None:
    gateway = ScriptedGateway(
        [tool_call("echo", {"value": "first"}), tool_call("echo", {"value": "second"})]
    )
    runtime = AgentRuntime(gateway, max_steps=5, max_tool_calls=1)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="hello",
            tools=[_echo_tool()],
            final_validator=_json_validator(),
        )

    assert excinfo.value.args[0] == "agent_tool_budget_exhausted"
    assert excinfo.value.diagnostics.tool_calls == 1


@pytest.mark.asyncio
async def test_repeated_validation_error_is_circuit_broken() -> None:
    gateway = ScriptedGateway([text_response("bad")])
    runtime = AgentRuntime(gateway, max_steps=8, max_revisions=5, max_same_error=2)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="hello",
            tools=[_echo_tool()],
            final_validator=_json_validator(),
        )

    assert excinfo.value.args[0] == "agent_repeated_error"
    assert excinfo.value.diagnostics.repeated_errors == 2


@pytest.mark.asyncio
async def test_different_validation_errors_do_not_share_repeat_count() -> None:
    gateway = ScriptedGateway(
        [text_response("bad-one"), text_response("bad-two"), text_response("bad-two")]
    )
    runtime = AgentRuntime(gateway, max_steps=8, max_revisions=5, max_same_error=2)

    def validate_with_content(content: str) -> FinalValidation:
        return FinalValidation(ok=False, error=content)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="hello",
            tools=[_echo_tool()],
            final_validator=validate_with_content,
        )

    assert excinfo.value.args[0] == "agent_repeated_error"
    assert excinfo.value.diagnostics.revisions == 3


@pytest.mark.asyncio
async def test_stage_timeout_returns_partial_trace() -> None:
    gateway = ScriptedGateway([tool_call("echo", {"value": "slow"})])
    runtime = AgentRuntime(gateway, max_steps=3, stage_timeout_seconds=0.01)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="hello",
            tools=[_slow_tool()],
            final_validator=_json_validator(),
        )

    assert excinfo.value.args[0] == "agent_stage_timeout"
    assert excinfo.value.trace
    assert excinfo.value.diagnostics.phase is AgentPhase.DRAFT


@pytest.mark.asyncio
async def test_trace_summaries_are_bounded() -> None:
    gateway = ScriptedGateway([text_response("x" * 2_000)])
    runtime = AgentRuntime(gateway, max_steps=1)

    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="test",
            user="hello",
            tools=[_echo_tool()],
            final_validator=_json_validator(),
        )

    assert len(gateway.calls) == 1
    assert len(excinfo.value.trace[0].summary) <= 400


@pytest.mark.asyncio
async def test_runtime_emits_safe_events_and_observes_cancellation() -> None:
    events: list[AgentRuntimeEvent] = []
    cancelled = False

    async def cancel_check() -> bool:
        return cancelled

    async def event_sink(event: AgentRuntimeEvent) -> None:
        nonlocal cancelled
        events.append(event)
        if event.kind == "model":
            cancelled = True

    runtime = AgentRuntime(ScriptedGateway([text_response("敏感用户正文")]), max_steps=3)
    with pytest.raises(AgentRunError) as excinfo:
        await runtime.run(
            system="system",
            user="user",
            tools=[],
            final_validator=lambda _: FinalValidation(ok=True, result={}),
            cancel_check=cancel_check,
            event_sink=event_sink,
        )

    assert excinfo.value.args[0] == "agent_cancelled"
    assert excinfo.value.diagnostics.status is AgentRunStatus.CANCELLED
    assert [event.order for event in events] == sorted(event.order for event in events)
    assert all("敏感用户正文" not in event.summary for event in events)


def test_runtime_rejects_invalid_budget_configuration() -> None:
    with pytest.raises(ValueError, match="max_steps"):
        AgentRuntime(ScriptedGateway([text_response("ok")]), max_steps=0)
    with pytest.raises(ValueError, match="stage_timeout_seconds"):
        AgentRuntime(ScriptedGateway([text_response("ok")]), stage_timeout_seconds=0)


def test_styling_tool_schemas_are_deepseek_compatible() -> None:
    tools = build_styling_tools()
    assert {tool.name for tool in tools} == {
        "load_style_profile",
        "suggest_tags",
        "critique_draft",
        "finalize_note",
    }
    for tool in tools:
        assert tool.parameters["type"] == "object"
        assert tool.description
