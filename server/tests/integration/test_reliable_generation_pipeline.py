from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from red_book_editor_server.infrastructure.models import NoteModel


def _source(
    scenario: str = "睡前哭闹",
    actions: list[str] | None = None,
) -> dict[str, object]:
    return {
        "baby_month": 19,
        "scenario": scenario,
        "actions": actions or ["固定绘本时间"],
        "observations": "入睡过程变顺了一些",
        "notes": "用户补充的原始说明",
        "asset_ids": [],
    }


def _account_and_column(client: TestClient) -> tuple[str, str]:
    account_id = str(uuid4())
    account = client.put(
        f"/api/v1/accounts/{account_id}",
        json={
            "positioning": "0-2岁育儿日常",
            "age_range_months": [0, 24],
            "current_baby_month": 19,
            "tone": "自然、具体",
            "boundaries": ["不做诊断"],
            "common_expressions": ["记录一下"],
        },
    )
    assert account.status_code == 200
    column = client.post(
        f"/api/v1/accounts/{account_id}/columns",
        json={
            "name": "日常育儿经验",
            "description": "记录0-2岁宝宝的日常经验",
            "content_types": ["经验"],
        },
    )
    assert column.status_code == 201
    return account_id, column.json()["column_id"]


@pytest.mark.integration
def test_main_generate_save_list_reload_and_versions(client: TestClient) -> None:
    account_id, column_id = _account_and_column(client)
    generated = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": account_id,
            "column_id": column_id,
            "form": "experience",
            "source": _source(),
        },
    )
    assert generated.status_code == 200
    draft = generated.json()["draft"]
    assert draft["style_form"] == "experience"
    assert draft["review"] is not None
    assert draft["status"] == "ready"
    note_id = draft["note_id"]

    saved = client.put(
        f"/api/v1/notes/{note_id}",
        json={
            "topic_angle": "用户编辑后的选题",
            "title_candidates": ["用户编辑后的标题"],
            "body": "用户编辑后的正文",
            "hashtags": ["#育儿日常"],
            "cover_copy": "用户编辑后的封面",
            "image_suggestions": [],
            "style_form": "experience",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "ready"
    assert saved.json()["style_form"] == "experience"

    listed = client.get(f"/api/v1/accounts/{account_id}/notes")
    assert listed.status_code == 200
    assert listed.json()[0]["note_id"] == note_id
    assert listed.json()[0]["body"] == "用户编辑后的正文"

    reopened = client.get(f"/api/v1/notes/{note_id}")
    assert reopened.status_code == 200
    assert reopened.json()["style_form"] == "experience"
    assert reopened.json()["body"] == "用户编辑后的正文"

    versions = client.get(f"/api/v1/notes/{note_id}/versions")
    assert versions.status_code == 200
    assert [version["version"] for version in versions.json()] == [1, 2]
    assert all(version["style_form"] == "experience" for version in versions.json())


@pytest.mark.integration
def test_account_workbench_and_main_generation_share_persistence_semantics(
    client: TestClient,
) -> None:
    account_id, column_id = _account_and_column(client)
    source = _source(scenario="洗澡后哭闹", actions=["固定睡前流程"])
    main = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": account_id,
            "column_id": column_id,
            "form": "experience",
            "source": source,
        },
    )
    workbench = client.post(
        f"/api/v1/accounts/{account_id}/notes",
        json={"column_id": column_id, "form": "experience", "source": source},
    )
    assert main.status_code == 200
    assert workbench.status_code == 201
    main_draft = main.json()["draft"]
    workbench_draft = workbench.json()
    assert main_draft["account_id"] == workbench_draft["account_id"] == account_id
    assert main_draft["column_id"] == workbench_draft["column_id"] == column_id
    assert main_draft["style_form"] == workbench_draft["style_form"] == "experience"
    assert main_draft["status"] == workbench_draft["status"]
    assert main_draft["review"] == workbench_draft["review"]


@pytest.mark.integration
def test_field_regeneration_preserves_user_edit_and_style_form(client: TestClient) -> None:
    account_id, column_id = _account_and_column(client)
    generated = client.post(
        "/api/v1/notes/generate",
        json={
            "account_id": account_id,
            "column_id": column_id,
            "form": "experience",
            "source": _source(),
        },
    )
    draft = generated.json()["draft"]
    draft["body"] = "用户刚刚手动改过的正文"
    draft["cover_copy"] = "手动封面"
    regenerated = client.post(
        "/api/v1/notes/regenerate-field",
        json={"draft": draft, "field": "title"},
    )
    assert regenerated.status_code == 200
    result = regenerated.json()
    assert result["body"] == "用户刚刚手动改过的正文"
    assert result["cover_copy"] == "手动封面"
    assert result["style_form"] == "experience"
    assert result["review"] is not None
    assert result["status"] == "ready"


@pytest.mark.integration
def test_export_gate_blocks_missing_review_and_blocking_review(client: TestClient) -> None:
    account_id, column_id = _account_and_column(client)
    generated = client.post(
        f"/api/v1/accounts/{account_id}/notes",
        json={
            "column_id": column_id,
            "source": _source(scenario="发烧", actions=["询问吃什么药"]),
        },
    )
    assert generated.status_code == 201
    note_id = generated.json()["note_id"]
    blocked = client.get(f"/api/v1/notes/{note_id}/export")
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "blocking_review"
    assert blocked.json()["detail"]["reasons"]

    async def clear_review() -> None:
        application = cast(Any, client.app)
        async with application.state.session_factory() as session:
            note = await session.get(NoteModel, note_id)
            assert note is not None
            note.review = None
            note.status = "needs_review"
            await session.commit()

    cast(Any, client).portal.call(clear_review)
    missing = client.get(f"/api/v1/notes/{note_id}/export")
    assert missing.status_code == 409
    assert missing.json()["detail"]["code"] == "review_required"


@pytest.mark.integration
def test_warning_review_stays_needs_review_and_keeps_export_reasoning(
    client: TestClient,
) -> None:
    account_id, column_id = _account_and_column(client)
    created = client.post(
        f"/api/v1/accounts/{account_id}/notes",
        json={
            "column_id": column_id,
            "source": _source(scenario="职场护肤心得", actions=["记录自己的体验"]),
        },
    )
    assert created.status_code == 201
    draft = created.json()
    assert draft["status"] == "needs_review"
    assert any(finding["level"] == "warning" for finding in draft["review"]["findings"])
    exported = client.get(f"/api/v1/notes/{draft['note_id']}/export")
    assert exported.status_code == 200
    assert exported.json()["status"] == "needs_review"
