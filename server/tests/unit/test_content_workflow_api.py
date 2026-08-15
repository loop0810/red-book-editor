from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from red_book_editor_server.domain.contracts import (
    NoteDraftDto,
    NoteStatus,
    SourceExperienceDto,
    StyleForm,
)
from red_book_editor_server.modules.content_workflow.generator import (
    ContentGenerationError,
    generate_with_retry,
)
from red_book_editor_server.modules.content_workflow.service import ContentWorkflowService


def _source_payload(
    scenario: str = "睡前哭闹",
    actions: list[str] | None = None,
) -> dict[str, object]:
    return {
        "baby_month": 19,
        "scenario": scenario,
        "actions": actions or ["固定绘本时间"],
    }


def _draft_payload() -> dict[str, object]:
    return {
        "note_id": str(uuid4()),
        "account_id": str(uuid4()),
        "column_id": str(uuid4()),
        "status": "ready",
        "topic_angle": "19个月宝宝的出门记录",
        "title_candidates": ["原来的标题"],
        "body": "原来的正文",
        "hashtags": ["#育儿日常"],
        "cover_copy": "原来的封面",
        "image_suggestions": ["场景照片"],
        "source": _source_payload(scenario="出门", actions=["准备清单"]),
        "style_form": "experience",
        "review": {"passed": True, "findings": []},
        "updated_at": "2026-08-05T00:00:00Z",
    }


@pytest.mark.asyncio
async def test_generate_service_returns_reviewed_draft_with_style_form() -> None:
    account_id = uuid4()
    column_id = uuid4()
    result = await ContentWorkflowService().generate(
        account_id=account_id,
        column_id=column_id,
        form=StyleForm.EXPERIENCE,
        source=SourceExperienceDto.model_validate(_source_payload(actions=["固定绘本时间"])),
    )
    assert result.draft.status == NoteStatus.READY
    assert result.draft.review is not None
    assert result.draft.style_form is StyleForm.EXPERIENCE
    assert result.draft.account_id == account_id
    assert result.agent_trace[0].label == "stub_fallback"


def test_generate_note_requires_form(client: TestClient) -> None:
    response = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": str(uuid4()),
            "column_id": str(uuid4()),
            "source": _source_payload(),
        },
    )
    assert response.status_code == 422


def test_generate_note_rejects_unknown_form(client: TestClient) -> None:
    response = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": str(uuid4()),
            "column_id": str(uuid4()),
            "form": "unknown",
            "source": _source_payload(),
        },
    )
    assert response.status_code == 422


def test_restyle_note_returns_draft_and_trace(client: TestClient) -> None:
    draft = _draft_payload()
    response = client.post(
        "/api/v1/notes/style",
        json={"draft": draft, "form": "popular_science"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["draft"]["note_id"] == draft["note_id"]
    assert payload["agent_trace"][0]["label"] == "stub_fallback"
    assert payload["draft"]["review"] is not None


def test_regenerate_field_preserves_other_fields(client: TestClient) -> None:
    draft = _draft_payload()
    old_body = draft["body"]
    regenerated = client.post(
        "/api/v1/notes/regenerate-field",
        json={"draft": draft, "field": "title"},
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["body"] == old_body
    assert regenerated.json()["status"] == "ready"
    assert regenerated.json()["review"] is not None


def test_generate_note_rejects_invalid_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": str(uuid4()),
            "column_id": str(uuid4()),
            "form": "experience",
            "source": {"baby_month": 19, "scenario": "", "actions": []},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_generation_retries_timeout_and_preserves_source() -> None:
    source = SourceExperienceDto(baby_month=19, scenario="发烧", actions=["记录体温"])
    calls = 0

    class FlakyGenerator:
        async def generate(
            self,
            received: SourceExperienceDto,
            *,
            account_id: UUID | None = None,
            column_id: UUID | None = None,
        ) -> NoteDraftDto:
            nonlocal calls
            calls += 1
            assert received == source
            if calls == 1:
                raise TimeoutError
            assert account_id is not None
            assert column_id is not None
            return NoteDraftDto(
                note_id=uuid4(),
                account_id=account_id,
                column_id=column_id,
                status=NoteStatus.DRAFT,
                source=received,
                updated_at=datetime(2026, 8, 5, tzinfo=UTC),
            )

    result = await generate_with_retry(
        FlakyGenerator(),
        source,
        account_id=uuid4(),
        column_id=uuid4(),
    )
    assert result.source.scenario == "发烧"
    assert calls == 2


@pytest.mark.asyncio
async def test_generation_failure_is_normalized_after_retries() -> None:
    class BrokenGenerator:
        async def generate(
            self,
            source: SourceExperienceDto,
            *,
            account_id: UUID | None = None,
            column_id: UUID | None = None,
        ) -> NoteDraftDto:
            raise ValueError("malformed")

    with pytest.raises(ContentGenerationError):
        await generate_with_retry(
            BrokenGenerator(),
            SourceExperienceDto(baby_month=19, scenario="出门", actions=["准备清单"]),
            account_id=uuid4(),
            column_id=uuid4(),
        )
