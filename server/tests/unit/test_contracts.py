from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from red_book_editor_server.domain.contracts import (
    ContentBriefDto,
    EditableField,
    FieldSuggestionDto,
    NoteDraftDto,
    NoteStatus,
    ReviewFindingDto,
    ReviewResultDto,
    RiskLevel,
    SourceExperienceDto,
    SuggestionStatus,
    UserResultResponseDto,
)


def test_source_experience_requires_a_scenario_and_action() -> None:
    source = SourceExperienceDto(baby_month=19, scenario="睡前哭闹", actions=["固定绘本时间"])
    assert source.baby_month == 19


def test_source_experience_rejects_empty_actions() -> None:
    with pytest.raises(ValidationError):
        SourceExperienceDto(baby_month=19, scenario="睡前哭闹", actions=[])


def test_source_experience_accepts_asset_ids() -> None:
    source = SourceExperienceDto(
        baby_month=19,
        scenario="出门",
        actions=["准备随身物品"],
        asset_ids=[uuid4()],
    )
    assert len(source.asset_ids) == 1


def test_field_suggestion_contract_round_trips_target_value() -> None:
    suggestion = FieldSuggestionDto.model_validate(
        {
            "suggestion_id": str(uuid4()),
            "note_id": str(uuid4()),
            "field": "hashtags",
            "value": ["#育儿日常", "#睡前流程"],
            "base_field_digest": "field-digest",
            "base_content_digest": "content-digest",
            "created_at": "2026-08-16T00:00:00Z",
        }
    )

    assert suggestion.field is EditableField.HASHTAGS
    assert suggestion.value == ["#育儿日常", "#睡前流程"]
    assert suggestion.status is SuggestionStatus.PENDING
    assert "body" not in suggestion.model_dump(mode="json")


def test_review_finding_accepts_legacy_payload_without_field() -> None:
    finding = ReviewFindingDto.model_validate(
        {
            "level": RiskLevel.WARNING,
            "code": "legacy",
            "message": "旧审核结果",
            "matched_text": "旧文本",
        }
    )

    assert finding.field is None
    assert finding.matched_text == "旧文本"


def test_content_brief_is_the_generic_input_and_public_result_hides_review() -> None:
    brief = ContentBriefDto(
        focus="宝宝周岁宴",
        raw_material="不办大型酒宴，只和家人吃顿饭。",
        domain_context={"baby_month": 12},
    )
    draft = NoteDraftDto(
        note_id=uuid4(),
        account_id=uuid4(),
        column_id=uuid4(),
        status=NoteStatus.READY,
        content_brief=brief,
        title_candidates=["宝宝周岁宴：和家人吃顿饭"],
        body="记录这次简单的周岁宴。",
        review=ReviewResultDto(passed=True),
        updated_at=datetime(2026, 8, 16, tzinfo=UTC),
    )

    payload = UserResultResponseDto.from_draft(draft).model_dump(mode="json")

    assert payload["draft"]["content_brief"]["focus"] == "宝宝周岁宴"
    assert "review" not in payload["draft"]
    assert "agent_trace" not in payload
