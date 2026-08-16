from __future__ import annotations

import pytest

from red_book_editor_server.infrastructure.llm.stub import StubModelGateway
from scripts.run_agent_eval import load_cases, run_case
from scripts.validate_agent_eval import validate_run


def _record() -> dict[str, object]:
    return {
        "case_id": "case-1",
        "attempt": 1,
        "status": "failed",
        "agent_diagnostics": {
            "status": "budget_exhausted",
            "phase": "revise",
            "steps": 4,
            "revisions": 2,
            "tool_calls": 1,
            "repeated_errors": 2,
            "failure_code": "agent_repeated_error",
        },
    }


def test_schema_three_requires_runtime_diagnostics() -> None:
    validate_run(
        {
            "schema_version": 3,
            "run_id": "run-1",
            "model_provider": "stub",
            "model": "stub",
            "records": [_record()],
        },
        {"case-1"},
    )


def test_legacy_run_without_diagnostics_remains_readable() -> None:
    validate_run(
        {
            "schema_version": 2,
            "run_id": "legacy",
            "model_provider": "deepseek",
            "model": "deepseek-chat",
            "records": [{"case_id": "case-1", "attempt": 1}],
        },
        {"case-1"},
    )


def test_schema_three_rejects_missing_diagnostics() -> None:
    with pytest.raises(ValueError, match="agent_diagnostics"):
        validate_run(
            {
                "schema_version": 3,
                "run_id": "run-1",
                "model_provider": "stub",
                "model": "stub",
                "records": [{"case_id": "case-1", "attempt": 1}],
            },
            {"case-1"},
        )


@pytest.mark.asyncio
async def test_runner_records_runtime_diagnostics_for_failed_stub_run() -> None:
    case = load_cases(["case-01-fever-care"])[0]
    record = await run_case(StubModelGateway(), case, 1)

    diagnostics = record["agent_diagnostics"]
    assert isinstance(diagnostics, dict)
    assert diagnostics["status"] == "budget_exhausted"
    assert diagnostics["failure_code"] == "agent_repeated_error"
    assert record["automatic_hard_failures"] == ["agent_run_failed"]
