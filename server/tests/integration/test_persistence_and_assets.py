from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _source() -> dict[str, object]:
    return {
        "baby_month": 19,
        "scenario": "睡前哭闹",
        "actions": ["固定绘本时间"],
        "observations": "入睡过程变顺了一些",
        "notes": "补充说明",
        "asset_ids": [],
    }


def _create_account_with_column(client: TestClient, account_id: object) -> str:
    profile = client.put(
        f"/api/v1/accounts/{account_id}",
        json={
            "positioning": "0-2岁育儿日常",
            "age_range_months": [0, 24],
            "current_baby_month": 19,
            "tone": "自然、具体",
        },
    )
    assert profile.status_code == 200
    column = client.post(
        f"/api/v1/accounts/{account_id}/columns",
        json={
            "name": "日常育儿经验",
            "description": "记录0-2岁宝宝的日常经验",
            "content_types": ["经验"],
        },
    )
    assert column.status_code == 201
    return str(column.json()["column_id"])


def _create_note(client: TestClient, account_id: object, column_id: object) -> str:
    response = client.post(
        f"/api/v1/accounts/{account_id}/notes",
        json={"column_id": str(column_id), "source": _source()},
    )
    assert response.status_code == 201
    return str(response.json()["note_id"])


@pytest.mark.integration
def test_create_and_reload_note(client: TestClient) -> None:
    account_id = uuid4()
    column_id = _create_account_with_column(client, account_id)
    note_id = _create_note(client, account_id, column_id)

    loaded = client.get(f"/api/v1/notes/{note_id}")
    assert loaded.status_code == 200
    payload = loaded.json()
    assert payload["note_id"] == note_id
    assert payload["source"]["scenario"] == "睡前哭闹"
    assert payload["source"]["asset_ids"] == []


@pytest.mark.integration
def test_save_draft_records_version_history(client: TestClient) -> None:
    account_id = uuid4()
    column_id = _create_account_with_column(client, account_id)
    note_id = _create_note(client, account_id, column_id)

    updated = client.put(
        f"/api/v1/notes/{note_id}",
        json={
            "topic_angle": "改过的选题",
            "title_candidates": ["改过的标题"],
            "body": "改过的正文",
            "hashtags": ["#育儿日常"],
            "cover_copy": "封面",
            "image_suggestions": [],
        },
    )
    assert updated.status_code == 200
    assert updated.json()["body"] == "改过的正文"

    versions = client.get(f"/api/v1/notes/{note_id}/versions")
    assert versions.status_code == 200
    payload = versions.json()
    assert [version["version"] for version in payload] == [1, 2]
    assert payload[1]["body"] == "改过的正文"


@pytest.mark.integration
def test_list_account_notes_is_account_scoped(client: TestClient) -> None:
    account_a, account_b = uuid4(), uuid4()
    column_a = _create_account_with_column(client, account_a)
    _create_account_with_column(client, account_b)
    _create_note(client, account_a, column_a)
    _create_note(client, account_a, column_a)

    listed = client.get(f"/api/v1/accounts/{account_a}/notes")
    assert listed.status_code == 200
    assert len(listed.json()) == 2

    listed_b = client.get(f"/api/v1/accounts/{account_b}/notes")
    assert listed_b.status_code == 200
    assert listed_b.json() == []


@pytest.mark.integration
def test_export_blocks_note_with_medication_review(client: TestClient) -> None:
    account_id = uuid4()
    column_id = _create_account_with_column(client, account_id)
    response = client.post(
        f"/api/v1/accounts/{account_id}/notes",
        json={
            "column_id": str(column_id),
            "source": {
                "baby_month": 12,
                "scenario": "发烧",
                "actions": ["询问用什么药"],
                "asset_ids": [],
            },
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "needs_review"
    note_id = response.json()["note_id"]

    export = client.get(f"/api/v1/notes/{note_id}/export")
    assert export.status_code == 409
    assert export.json()["detail"]["code"] == "blocking_review"
    assert export.json()["detail"]["reasons"]


@pytest.mark.integration
def test_asset_upload_list_reorder_download_delete(client: TestClient) -> None:
    account_a, account_b = uuid4(), uuid4()
    _create_account_with_column(client, account_a)
    _create_account_with_column(client, account_b)
    image = b"\xff\xd8\xff\xe0fakejpeg"

    upload_a = client.post(
        f"/api/v1/accounts/{account_a}/assets",
        files={"file": ("a.jpg", image, "image/jpeg")},
    )
    assert upload_a.status_code == 201
    asset_a = upload_a.json()["asset_id"]
    upload_b = client.post(
        f"/api/v1/accounts/{account_a}/assets",
        files={"file": ("b.jpg", image, "image/jpeg")},
    )
    asset_b = upload_b.json()["asset_id"]
    client.post(
        f"/api/v1/accounts/{account_b}/assets",
        files={"file": ("c.jpg", image, "image/jpeg")},
    )

    listed_a = client.get(f"/api/v1/accounts/{account_a}/assets")
    assert listed_a.status_code == 200
    assert {asset["asset_id"] for asset in listed_a.json()} == {asset_a, asset_b}

    reordered = client.put(
        f"/api/v1/accounts/{account_a}/assets/order",
        json={"asset_ids": [asset_b, asset_a]},
    )
    assert reordered.status_code == 200
    assert [asset["asset_id"] for asset in reordered.json()] == [asset_b, asset_a]

    downloaded = client.get(f"/api/v1/assets/{asset_a}")
    assert downloaded.status_code == 200
    assert downloaded.content == image

    deleted = client.delete(f"/api/v1/assets/{asset_a}")
    assert deleted.status_code == 204
    after = client.get(f"/api/v1/accounts/{account_a}/assets")
    assert [asset["asset_id"] for asset in after.json()] == [asset_b]


@pytest.mark.integration
def test_upload_rejects_non_image_without_touching_existing_assets(
    client: TestClient,
) -> None:
    account_id = uuid4()
    _create_account_with_column(client, account_id)
    image = b"\xff\xd8\xff\xe0fakejpeg"
    client.post(
        f"/api/v1/accounts/{account_id}/assets",
        files={"file": ("ok.jpg", image, "image/jpeg")},
    )

    rejected = client.post(
        f"/api/v1/accounts/{account_id}/assets",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert rejected.status_code == 415
    listed = client.get(f"/api/v1/accounts/{account_id}/assets")
    assert len(listed.json()) == 1
