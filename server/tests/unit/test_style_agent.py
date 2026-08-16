from __future__ import annotations

import json

import pytest

from red_book_editor_server.domain.agent import AgentRunError
from red_book_editor_server.domain.contracts import SourceExperienceDto, StyleForm
from red_book_editor_server.modules.content_workflow.styling.agent import (
    _extract_json,
    style_draft,
)
from red_book_editor_server.modules.content_workflow.styling.models import FinalizeArgs
from red_book_editor_server.modules.content_workflow.styling.tools import critique_draft_tool
from tests.unit.fakes import ScriptedGateway, text_response, tool_call


def _source() -> SourceExperienceDto:
    return SourceExperienceDto(
        baby_month=19,
        scenario="宝宝半夜发烧",
        actions=["温水擦身", "记录体温"],
        observations="第二天退烧了",
    )


def _draft_payload() -> dict[str, object]:
    return {
        "topic_angle": "19个月宝宝半夜发烧的真实复盘",
        "title_candidates": [
            "19个月宝宝半夜发烧，我是这样做的",
            "宝宝半夜发烧，别慌，先看这个",
        ],
        "body": (
            "当时真的吓坏了。\n"
            "1. 发现发烧：19个月宝宝半夜体温38.5度。\n"
            "2. 我做了什么：温水擦身、记录体温。\n"
            "3. 结果：第二天退烧了。\n\n"
            "希望所有宝宝都健健康康。"
        ),
        "hashtags": ["#育儿日常", "#宝妈分享", "#宝宝发烧", "#新手宝妈"],
        "cover_copy": "19个月宝宝半夜发烧 | 真实复盘",
    }


def _final_payload() -> dict[str, object]:
    return {
        "form": "experience",
        "draft": _draft_payload(),
        "image_suggestions": ["体温记录照片", "退烧后的状态照"],
    }


@pytest.mark.asyncio
async def test_golden_path_produces_styled_draft_with_trace() -> None:
    gateway = ScriptedGateway(
        [
            tool_call("load_style_profile", {"form": "experience"}),
            tool_call(
                "critique_draft",
                {
                    "form": "experience",
                    "draft": _draft_payload(),
                    "source": _source().model_dump(mode="json"),
                },
            ),
            tool_call("finalize_note", _final_payload()),
            text_response(json.dumps(_final_payload(), ensure_ascii=False)),
        ]
    )

    result = await style_draft(
        gateway,
        source=_source(),
        neutral_draft=None,
        form=StyleForm.EXPERIENCE,
    )

    finalized = result.result
    assert isinstance(finalized, FinalizeArgs)
    assert finalized.draft.title_candidates
    assert finalized.draft.body
    assert finalized.draft.hashtags
    labels = [step.label for step in result.trace]
    assert "load_style_profile" in labels
    assert "critique_draft" in labels
    assert "finalize_note" in labels
    assert result.trace[0].phase == "collect_context"
    assert result.trace[1].phase == "collect_context"
    assert any(step.phase == "critique" for step in result.trace)
    assert any(step.phase == "finalize" for step in result.trace)
    assert [step.kind for step in result.trace] == [
        "model",
        "tool",
        "model",
        "tool",
        "model",
        "tool",
        "model",
    ]


@pytest.mark.asyncio
async def test_fact_violation_triggers_revision_loop() -> None:
    missing_facts = json.loads(json.dumps(_final_payload()))
    missing_facts["draft"]["body"] = "宝宝晚上有点闹，我陪了一会儿就睡着了。"
    valid = _final_payload()
    gateway = ScriptedGateway(
        [
            text_response(json.dumps(missing_facts, ensure_ascii=False)),
            text_response(json.dumps(valid, ensure_ascii=False)),
        ]
    )

    result = await style_draft(
        gateway,
        source=_source(),
        neutral_draft=None,
        form=StyleForm.EXPERIENCE,
    )

    assert isinstance(result.result, FinalizeArgs)
    feedback = gateway.calls[1][0][-1]["content"]
    assert isinstance(feedback, str)
    assert "校验失败" in feedback or "事实缺失" in feedback


def test_extract_json_accepts_markdown_fence() -> None:
    assert _extract_json('已确认：\n```json\n{"form":"experience"}\n```') == (
        '{"form":"experience"}'
    )


@pytest.mark.asyncio
async def test_revision_cap_raises_agent_error() -> None:
    gateway = ScriptedGateway([text_response("not json at all")])

    with pytest.raises(AgentRunError):
        await style_draft(
            gateway,
            source=_source(),
            neutral_draft=None,
            form=StyleForm.EXPERIENCE,
        )


@pytest.mark.asyncio
async def test_critique_tool_flags_missing_facts_and_out_of_range_tags() -> None:
    from red_book_editor_server.modules.content_workflow.styling.tools import (
        critique_draft_tool,
    )

    payload: dict[str, object] = {
        "form": "experience",
        "draft": {
            "topic_angle": "记录一次",
            "title_candidates": ["记录一次宝宝的情况"],
            "body": "记录一下。",
            "hashtags": ["#育儿"],
            "cover_copy": "记录",
        },
        "source": _source().model_dump(mode="json"),
    }
    raw = await critique_draft_tool(payload)
    result = json.loads(raw)
    assert result["passed"] is False
    assert result["scores"]["facts"] < 5
    assert any("话题数量" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_critique_accepts_experience_narrative_paragraphs() -> None:
    payload: dict[str, object] = {
        "form": "experience",
        "draft": {
            **_draft_payload(),
            "body": (
                "周末出门时，19个月宝宝准备绘本和水杯。\n\n"
                "孩子更愿意自己整理物品，我当时真的很惊喜。\n\n"
                "后来出门顺利完成，希望所有宝宝都健健康康。"
            ),
        },
        "source": _source().model_dump(mode="json"),
    }
    result = json.loads(await critique_draft_tool(payload))
    assert result["scores"]["structure"] == 3
