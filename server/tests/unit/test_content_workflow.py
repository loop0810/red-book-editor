from __future__ import annotations

import pytest
from datetime import UTC, datetime
from uuid import UUID

from red_book_editor_server.domain.contracts import (
    NoteDraftDto,
    NoteStatus,
    RiskLevel,
    SourceExperienceDto,
)
from red_book_editor_server.modules.content_workflow import (
    DeterministicContentReviewer,
    ModelAssistedContentReviewer,
    StubContentGenerator,
    review_draft,
)


@pytest.mark.asyncio
async def test_stub_generator_preserves_source_facts() -> None:
    source = SourceExperienceDto(baby_month=19, scenario="睡前哭闹", actions=["固定绘本时间"])
    draft = await StubContentGenerator().generate(source)
    assert draft.source == source
    assert "睡前哭闹" in draft.body


def test_reviewer_allows_common_care_experience() -> None:
    draft = NoteDraftDto(
        note_id=UUID("00000000-0000-0000-0000-000000000001"),
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        column_id=UUID("00000000-0000-0000-0000-000000000003"),
        status=NoteStatus.DRAFT,
        body="宝宝有点发烧时，我们记录了状态并按自己的习惯照顾。",
        source=SourceExperienceDto(baby_month=19, scenario="发烧", actions=["记录状态"]),
        updated_at=datetime(2026, 8, 5, tzinfo=UTC),
    )
    result = DeterministicContentReviewer().review(draft)
    assert result.passed


def test_reviewer_blocks_medication_advice() -> None:
    draft = NoteDraftDto(
        note_id=UUID("00000000-0000-0000-0000-000000000001"),
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        column_id=UUID("00000000-0000-0000-0000-000000000003"),
        status=NoteStatus.DRAFT,
        body="一岁宝宝发烧应该吃什么药？",
        source=SourceExperienceDto(baby_month=12, scenario="发烧", actions=["询问用药"]),
        updated_at=datetime(2026, 8, 5, tzinfo=UTC),
    )
    result = DeterministicContentReviewer().review(draft)
    assert not result.passed
    assert result.findings[0].level is RiskLevel.BLOCKING


def _draft(body: str) -> NoteDraftDto:
    return NoteDraftDto(
        note_id=UUID("00000000-0000-0000-0000-000000000001"),
        account_id=UUID("00000000-0000-0000-0000-000000000002"),
        column_id=UUID("00000000-0000-0000-0000-000000000003"),
        status=NoteStatus.DRAFT,
        body=body,
        source=SourceExperienceDto(baby_month=19, scenario="睡前哭闹", actions=["固定绘本时间"]),
        updated_at=datetime(2026, 8, 5, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_model_assisted_reviewer_blocks_unsupported_claim() -> None:
    result = await ModelAssistedContentReviewer().review(
        _draft("研究表明这样做一定有效，宝宝很快就睡整觉了。")
    )
    assert not result.passed
    assert any(
        finding.code == "unsupported_claim" and finding.level is RiskLevel.BLOCKING
        for finding in result.findings
    )


@pytest.mark.asyncio
async def test_model_assisted_reviewer_warns_out_of_account_scope() -> None:
    result = await ModelAssistedContentReviewer().review(_draft("今天聊聊职场里的护肤心得"))
    assert result.passed
    assert any(
        finding.code == "account_scope" and finding.level is RiskLevel.WARNING
        for finding in result.findings
    )


@pytest.mark.asyncio
async def test_model_assisted_reviewer_warns_anxiety_language() -> None:
    result = await ModelAssistedContentReviewer().review(_draft("千万不要再拖延，否则会出事"))
    assert result.passed
    assert any(
        finding.code == "anxiety_language" and finding.level is RiskLevel.WARNING
        for finding in result.findings
    )


@pytest.mark.asyncio
async def test_review_draft_merges_deterministic_and_model_checks() -> None:
    result = await review_draft(_draft("宝宝发烧应该吃什么药？研究表明用药三天一定好。"))
    assert not result.passed
    codes = {finding.code for finding in result.findings}
    assert "medication" in codes
    assert "unsupported_claim" in codes
