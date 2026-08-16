from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.agent_baseline.hard_failures import automatic_hard_failures
from red_book_editor_server.app.config import get_settings
from red_book_editor_server.app.dependencies import build_model_gateway
from red_book_editor_server.domain.agent import (
    AgentFailureCode,
    AgentRunDiagnostics,
    AgentPhase,
    AgentRunError,
    AgentRunStatus,
    AgentTraceStep,
)
from red_book_editor_server.domain.contracts import SourceExperienceDto, StyleForm
from red_book_editor_server.domain.ports import ModelGatewayError
from red_book_editor_server.infrastructure.llm import DeepSeekModelGateway
from red_book_editor_server.modules.content_workflow.styling.agent import style_draft

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "agent_baseline" / "cases.json"
RUNS_DIR = ROOT / "evals" / "agent_baseline" / "runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the red book editor Agent baseline cases")
    parser.add_argument("--run-id", default=_default_run_id())
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument(
        "--allow-stub",
        action="store_true",
        help="Allow MODEL_PROVIDER=stub for local plumbing checks; not a real baseline",
    )
    return parser.parse_args()


def _default_run_id() -> str:
    return datetime.now(UTC).strftime("baseline-%Y%m%d-%H%M%S")


def load_cases(case_ids: list[str] | None) -> list[dict[str, Any]]:
    raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("cases.json must contain a JSON array")
    cases = [case for case in raw if isinstance(case, dict)]
    if len(cases) != len(raw):
        raise ValueError("every evaluation case must be a JSON object")
    if case_ids:
        selected = [case for case in cases if case.get("case_id") in case_ids]
        missing = sorted(set(case_ids) - {case["case_id"] for case in selected})
        if missing:
            raise ValueError(f"unknown case_id: {', '.join(missing)}")
        return selected
    return cases


async def run_case(
    gateway: object,
    case: dict[str, Any],
    attempt: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    trace: list[AgentTraceStep] = []
    try:
        source = SourceExperienceDto.model_validate(case["source"])
        form = StyleForm(case["form"])
        result = await style_draft(gateway, source=source, neutral_draft=None, form=form)  # type: ignore[arg-type]
        trace = result.trace
        return _annotate_record(
            case,
            {
                "case_id": case["case_id"],
                "attempt": attempt,
                "status": "succeeded",
                "elapsed_ms": round((time.perf_counter() - started) * 1000),
                "draft": result.result.model_dump(mode="json"),
                "agent_trace": [_trace_record(step) for step in trace],
                "agent_diagnostics": _diagnostics_record(result.diagnostics),
                "error": None,
            },
        )
    except AgentRunError as error:
        trace = error.trace
        return _failed_record(case, attempt, started, str(error), trace, error.diagnostics)
    except ModelGatewayError as error:
        return _failed_record(
            case,
            attempt,
            started,
            type(error).__name__,
            trace,
            failure_code=AgentFailureCode.MODEL_ERROR,
        )
    except (ValueError, TypeError, KeyError) as error:
        return _failed_record(
            case,
            attempt,
            started,
            type(error).__name__,
            trace,
            failure_code=AgentFailureCode.INPUT_ERROR,
        )
    except Exception as error:  # pragma: no cover - protects a whole baseline run
        return _failed_record(
            case,
            attempt,
            started,
            type(error).__name__,
            trace,
            failure_code=AgentFailureCode.UNEXPECTED_ERROR,
        )


def _failed_record(
    case: dict[str, Any],
    attempt: int,
    started: float,
    error: str,
    trace: list[AgentTraceStep],
    diagnostics: AgentRunDiagnostics | None = None,
    failure_code: AgentFailureCode | None = None,
) -> dict[str, Any]:
    return _annotate_record(
        case,
        {
            "case_id": case["case_id"],
            "attempt": attempt,
            "status": "failed",
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
            "draft": None,
            "agent_trace": [_trace_record(step) for step in trace],
            "agent_diagnostics": _diagnostics_record(
                diagnostics
                or AgentRunDiagnostics(
                    status=AgentRunStatus.FAILED,
                    phase=AgentPhase.COLLECT_CONTEXT,
                    failure_code=failure_code,
                )
            ),
            "error": error,
        },
    )


def _annotate_record(case: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    record["automatic_hard_failures"] = automatic_hard_failures(case, record)
    return record


def _trace_record(step: AgentTraceStep) -> dict[str, Any]:
    return {
        "order": step.order,
        "kind": step.kind,
        "label": step.label,
        "summary": step.summary[:400],
        "phase": step.phase.value if step.phase else None,
    }


def _diagnostics_record(diagnostics: AgentRunDiagnostics) -> dict[str, Any]:
    return {
        "status": diagnostics.status.value,
        "phase": diagnostics.phase.value,
        "steps": diagnostics.steps,
        "revisions": diagnostics.revisions,
        "tool_calls": diagnostics.tool_calls,
        "repeated_errors": diagnostics.repeated_errors,
        "failure_code": diagnostics.failure_code.value if diagnostics.failure_code else None,
    }


def build_eval_gateway(settings: Any) -> object:
    """Build a gateway without response caching for independent attempts."""

    if settings.model_provider == "deepseek":
        if not settings.model_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for a real baseline")
        return DeepSeekModelGateway(
            api_key=settings.model_api_key,
            model=settings.deepseek_model,
            base_url=settings.deepseek_base_url,
            timeout_seconds=settings.model_timeout_seconds,
            max_retries=settings.model_max_retries,
            cache_ttl_seconds=0,
            cache_max_entries=0,
        )
    return build_model_gateway(settings)


async def main(args: argparse.Namespace) -> Path:
    if args.repetitions < 1:
        raise ValueError("--repetitions must be at least 1")
    settings = get_settings()
    if settings.model_provider != "deepseek" and not args.allow_stub:
        raise ValueError(
            "a real baseline requires MODEL_PROVIDER=deepseek; "
            "use --allow-stub only for plumbing checks"
        )

    cases = load_cases(args.case_ids)
    gateway = build_eval_gateway(settings)
    records: list[dict[str, Any]] = []
    for case in cases:
        for attempt in range(1, args.repetitions + 1):
            records.append(await run_case(gateway, case, attempt))

    payload = {
        "schema_version": 3,
        "run_id": args.run_id,
        "started_at": datetime.now(UTC).isoformat(),
        "model_provider": settings.model_provider,
        "model": settings.deepseek_model if settings.model_provider == "deepseek" else "stub",
        "repetitions": args.repetitions,
        "case_count": len(cases),
        "records": records,
    }
    output_path = RUNS_DIR / f"{args.run_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return output_path


if __name__ == "__main__":
    output = asyncio.run(main(parse_args()))
    print(f"Wrote evaluation run: {output}")
