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
def test_first_use_can_create_account_and_default_column(client: TestClient) -> None:
    account = client.post(
        "/api/v1/accounts",
        json={
            "positioning": "记录真实育儿生活",
            "tone": "真实、自然",
            "current_baby_month": 0,
        },
    )
    assert account.status_code == 201
    account_id = account.json()["account_id"]

    column = client.post(
        f"/api/v1/accounts/{account_id}/columns",
        json={
            "name": "日常分享",
            "description": "记录真实经历与实用经验",
            "content_types": ["note"],
        },
    )
    assert column.status_code == 201
    assert column.json()["account_id"] == account_id
    assert (
        client.get(f"/api/v1/accounts/{account_id}/columns").json()[0]["column_id"]
        == column.json()["column_id"]
    )


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
    assert draft["content_brief"]["focus"] == _source()["scenario"]
    assert "review" not in draft
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
    assert all(version["review"] is not None for version in versions.json())


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
    assert main_draft["content_brief"] == workbench_draft["content_brief"]
    assert "review" not in main_draft
    assert "review" not in workbench_draft


@pytest.mark.integration
def test_field_regeneration_returns_target_field_suggestion(client: TestClient) -> None:
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
    assert result["field"] == "title"
    assert isinstance(result["value"], list)
    assert result["value"]
    assert result["base_field_digest"]
    assert result["base_content_digest"]
    assert result["review"] is not None
    assert "body" not in result
    assert "cover_copy" not in result
    assert "style_form" not in result


@pytest.mark.integration
def test_field_suggestion_history_persists_and_marks_stale(client: TestClient) -> None:
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
    note_id = draft["note_id"]

    regenerated = client.post(
        "/api/v1/notes/regenerate-field",
        json={"draft": draft, "field": "title"},
    )
    assert regenerated.status_code == 200
    suggestion = regenerated.json()
    listed = client.get(f"/api/v1/notes/{note_id}/suggestions")
    assert listed.status_code == 200
    assert listed.json()[0]["suggestion_id"] == suggestion["suggestion_id"]
    assert listed.json()[0]["status"] == "pending"

    resolved = client.patch(
        f"/api/v1/notes/{note_id}/suggestions/{suggestion['suggestion_id']}",
        json={"status": "rejected"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "rejected"
    unchanged = client.get(f"/api/v1/notes/{note_id}")
    assert unchanged.status_code == 200
    assert unchanged.json()["title_candidates"] == draft["title_candidates"]

    regenerated_again = client.post(
        "/api/v1/notes/regenerate-field",
        json={"draft": draft, "field": "body"},
    )
    assert regenerated_again.status_code == 200
    changed = {
        "topic_angle": draft["topic_angle"],
        "title_candidates": draft["title_candidates"],
        "body": "用户改过的正文",
        "hashtags": draft["hashtags"],
        "cover_copy": draft["cover_copy"],
        "image_suggestions": draft["image_suggestions"],
        "style_form": draft["style_form"],
    }
    saved = client.put(f"/api/v1/notes/{note_id}", json=changed)
    assert saved.status_code == 200
    after_edit = client.get(f"/api/v1/notes/{note_id}/suggestions")
    assert after_edit.status_code == 200
    body_suggestion = next(
        item
        for item in after_edit.json()
        if item["suggestion_id"] == regenerated_again.json()["suggestion_id"]
    )
    assert body_suggestion["status"] == "stale"


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
def test_warning_review_is_ready_without_an_irrelevant_user_warning(
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
    assert draft["status"] == "ready"
    assert "review" not in draft
    exported = client.get(f"/api/v1/notes/{draft['note_id']}/export")
    assert exported.status_code == 200
    assert exported.json()["status"] == "ready"
    assert "review" not in exported.json()


@pytest.mark.integration
def test_export_rejects_stale_review_after_out_of_band_content_change(client: TestClient) -> None:
    account_id, column_id = _account_and_column(client)
    created = client.post(
        f"/api/v1/accounts/{account_id}/notes",
        json={"column_id": column_id, "source": _source()},
    )
    assert created.status_code == 201
    note_id = created.json()["note_id"]

    async def change_content_without_review() -> None:
        application = cast(Any, client.app)
        async with application.state.session_factory() as session:
            note = await session.get(NoteModel, note_id)
            assert note is not None
            note.content = {**note.content, "body": "未经审核的外部新增内容"}
            await session.commit()

    cast(Any, client).portal.call(change_content_without_review)
    exported = client.get(f"/api/v1/notes/{note_id}/export")
    assert exported.status_code == 409
    assert exported.json()["detail"]["code"] == "review_required"


@pytest.mark.integration
def test_legacy_review_is_readable_but_cannot_remain_ready(client: TestClient) -> None:
    account_id, column_id = _account_and_column(client)
    created = client.post(
        f"/api/v1/accounts/{account_id}/notes",
        json={"column_id": column_id, "source": _source()},
    )
    assert created.status_code == 201
    note_id = created.json()["note_id"]

    async def replace_with_legacy_review() -> None:
        application = cast(Any, client.app)
        async with application.state.session_factory() as session:
            note = await session.get(NoteModel, note_id)
            assert note is not None
            note.review = {"passed": True, "findings": []}
            note.status = "ready"
            await session.commit()

    cast(Any, client).portal.call(replace_with_legacy_review)
    reopened = client.get(f"/api/v1/notes/{note_id}")
    assert reopened.status_code == 200
    assert "review" not in reopened.json()
    assert reopened.json()["status"] == "needs_review"

    exported = client.get(f"/api/v1/notes/{note_id}/export")
    assert exported.status_code == 409
    assert exported.json()["detail"]["code"] == "review_required"
