from __future__ import annotations

import asyncio
import time
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from red_book_editor_server.modules.content_workflow.service import ContentWorkflowService


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


def _wait_for_terminal(client: TestClient, run_id: str) -> dict[str, Any]:
    for _ in range(40):
        response = client.get(f"/api/v1/agent-runs/{run_id}")
        assert response.status_code == 200
        payload = cast(dict[str, Any], response.json())
        if payload["status"] in {"completed", "failed", "cancelled", "interrupted"}:
            return payload
        time.sleep(0.03)
    raise AssertionError("agent run did not reach a terminal state")


@pytest.mark.integration
def test_agent_run_persists_progress_and_supports_sse_cursor(client: TestClient) -> None:
    account_id, column_id = _account_and_column(client)
    created = client.post(
        "/api/v1/agent-runs",
        json={
            "account_id": account_id,
            "column_id": column_id,
            "form": "experience",
            "source": {
                "baby_month": 19,
                "scenario": "睡前哭闹",
                "actions": ["固定绘本时间"],
                "observations": "入睡过程变顺了一些",
                "notes": "用户补充的原始说明",
                "asset_ids": [],
            },
        },
    )
    assert created.status_code == 202
    run = created.json()
    terminal = _wait_for_terminal(client, run["run_id"])
    assert terminal["status"] == "completed"
    assert terminal["note_id"] == run["note_id"]
    assert terminal["diagnostics"]["phase"] == "safety_review"

    draft = client.get(f"/api/v1/notes/{run['note_id']}")
    assert draft.status_code == 200
    assert "review" not in draft.json()
    assert draft.json()["status"] == "ready"

    events = client.get(f"/api/v1/agent-runs/{run['run_id']}/events")
    assert events.status_code == 200
    lines = events.text.splitlines()
    ids = [int(line.removeprefix("id: ")) for line in lines if line.startswith("id: ")]
    names = [line.removeprefix("event: ") for line in lines if line.startswith("event: ")]
    assert ids == sorted(ids)
    assert "run.created" in names
    assert names[-1] == "run.completed"

    resumed = client.get(f"/api/v1/agent-runs/{run['run_id']}/events?after={ids[0]}")
    resumed_ids = [
        int(line.removeprefix("id: "))
        for line in resumed.text.splitlines()
        if line.startswith("id: ")
    ]
    assert resumed_ids
    assert min(resumed_ids) > ids[0]


@pytest.mark.integration
def test_agent_run_can_cancel_and_resume_from_persisted_note(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    original_generate = ContentWorkflowService.generate

    async def delayed_generate(self: ContentWorkflowService, *args: Any, **kwargs: Any) -> Any:
        await asyncio.sleep(0.3)
        return await original_generate(self, *args, **kwargs)

    monkeypatch.setattr(ContentWorkflowService, "generate", delayed_generate)
    account_id, column_id = _account_and_column(client)
    created = client.post(
        "/api/v1/agent-runs",
        json={
            "account_id": account_id,
            "column_id": column_id,
            "form": "experience",
            "source": {
                "baby_month": 19,
                "scenario": "夜醒",
                "actions": ["记录时间"],
                "asset_ids": [],
            },
        },
    )
    assert created.status_code == 202
    run_id = created.json()["run_id"]
    cancelled = client.post(f"/api/v1/agent-runs/{run_id}/cancel")
    assert cancelled.status_code == 200
    terminal = _wait_for_terminal(client, run_id)
    assert terminal["status"] == "cancelled"
    assert terminal["failure_code"] == "agent_cancelled"

    resumed = client.post(f"/api/v1/agent-runs/{run_id}/resume")
    assert resumed.status_code == 202
    assert resumed.json()["attempt"] == 2
    completed = _wait_for_terminal(client, run_id)
    assert completed["status"] == "completed"
    assert completed["attempt"] == 2
