from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from red_book_editor_server.domain.agent import (
    AgentRunError,
    AgentRuntime,
    FinalValidation,
    Tool,
)
from red_book_editor_server.modules.content_workflow.styling.tools import build_styling_tools
from tests.unit.fakes import ScriptedGateway, text_response, tool_call


async def _echo(args: dict[str, object]) -> str:
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
