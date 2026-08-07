from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from red_book_editor_server.domain.contracts import NoteDraftDto, NoteStatus, SourceExperienceDto
from red_book_editor_server.modules.content_workflow.generator import (
    ContentGenerationError,
    generate_with_retry,
)


def test_generate_note_returns_structured_ready_draft(client: TestClient) -> None:
    account_id = uuid4()
    column_id = uuid4()
    response = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": str(account_id),
            "column_id": str(column_id),
            "source": {
                "baby_month": 19,
                "scenario": "睡前哭闹",
                "actions": ["固定绘本时间"],
                "observations": "入睡过程变顺了一些",
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["review"]["passed"] is True
    assert payload["account_id"] == str(account_id)


def test_generate_note_marks_medication_content_for_review(client: TestClient) -> None:
    response = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": str(uuid4()),
            "column_id": str(uuid4()),
            "source": {
                "baby_month": 19,
                "scenario": "发烧",
                "actions": ["询问用什么药"],
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "needs_review"


def test_regenerate_field_preserves_other_fields(client: TestClient) -> None:
    account_id = uuid4()
    column_id = uuid4()
    draft_response = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": str(account_id),
            "column_id": str(column_id),
            "source": {"baby_month": 19, "scenario": "出门", "actions": ["准备清单"]},
        },
    )
    draft = draft_response.json()
    old_body = draft["body"]
    regenerated = client.post(
        "/api/v1/notes/regenerate-field",
        json={"draft": draft, "field": "title"},
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["body"] == old_body


def test_generate_note_rejects_invalid_source(client: TestClient) -> None:
    response = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": str(uuid4()),
            "column_id": str(uuid4()),
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
