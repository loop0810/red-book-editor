from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_CASE_FIELDS = {
    "case_id",
    "form",
    "content_brief",
    "source",
    "expected_behavior",
    "must_preserve",
    "unknown_facts",
    "forbidden_inferences",
}
REQUIRED_SOURCE_FIELDS = {"baby_month", "scenario", "actions", "observations", "notes"}
REQUIRED_BRIEF_FIELDS = {"focus", "raw_material", "domain_context"}
SENSITIVE_KEYS = {"api_key", "authorization", "access_token", "secret", "token"}
REQUIRED_DIAGNOSTIC_FIELDS = {
    "status",
    "phase",
    "steps",
    "revisions",
    "tool_calls",
    "repeated_errors",
    "failure_code",
}
REQUIRED_EVALUATION_CONTEXT_FIELDS = {
    "manifest_version",
    "manifest_sha256",
    "model_provider",
    "model",
    "model_max_tokens",
    "scorecard_version",
    "prompt_version",
    "profile_version",
    "agent_runtime_version",
    "agent_config_version",
    "cases_sha256",
    "scorecard_sha256",
    "prompt_sha256",
    "profile_sha256",
    "agent_config_sha256",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Agent evaluation inputs and run records")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("evals/agent_baseline/cases.json"),
    )
    parser.add_argument("--run", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_cases(cases: Any) -> set[str]:
    if not isinstance(cases, list) or len(cases) < 5:
        raise ValueError("cases must be a JSON array containing at least 5 cases")
    case_ids: set[str] = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("each case must be an object")
        missing = REQUIRED_CASE_FIELDS - case.keys()
        if missing:
            raise ValueError(f"case is missing fields: {sorted(missing)}")
        case_id = case["case_id"]
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise ValueError(f"invalid or duplicate case_id: {case_id!r}")
        case_ids.add(case_id)
        source = case["source"]
        if not isinstance(source, dict) or REQUIRED_SOURCE_FIELDS - source.keys():
            raise ValueError(f"{case_id}: source fields are incomplete")
        if not isinstance(source["actions"], list) or not source["actions"]:
            raise ValueError(f"{case_id}: source.actions must not be empty")
        brief = case["content_brief"]
        if not isinstance(brief, dict) or REQUIRED_BRIEF_FIELDS - brief.keys():
            raise ValueError(f"{case_id}: content_brief fields are incomplete")
        if not isinstance(brief["focus"], str) or not brief["focus"].strip():
            raise ValueError(f"{case_id}: content_brief.focus must not be empty")
        if not isinstance(brief["raw_material"], str) or not brief["raw_material"].strip():
            raise ValueError(f"{case_id}: content_brief.raw_material must not be empty")
    return case_ids


def validate_no_sensitive_keys(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in SENSITIVE_KEYS:
                raise ValueError(f"sensitive key is not allowed in evaluation data: {path}.{key}")
            validate_no_sensitive_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_no_sensitive_keys(child, f"{path}[{index}]")


def validate_run(run: Any, case_ids: set[str]) -> None:
    if not isinstance(run, dict):
        raise ValueError("run record must be an object")
    for field in ("schema_version", "run_id", "model_provider", "model", "records"):
        if field not in run:
            raise ValueError(f"run record is missing {field}")
    records = run["records"]
    if not isinstance(records, list):
        raise ValueError("run.records must be an array")
    seen: set[tuple[str, int]] = set()
    schema_version = run["schema_version"]
    if not isinstance(schema_version, int) or schema_version < 1:
        raise ValueError("run.schema_version must be a positive integer")
    if schema_version >= 4:
        context = run.get("evaluation_context")
        if not isinstance(context, dict):
            raise ValueError("schema 4 run requires evaluation_context")
        missing_context = REQUIRED_EVALUATION_CONTEXT_FIELDS - context.keys()
        if missing_context:
            raise ValueError(f"evaluation_context is missing fields: {sorted(missing_context)}")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each run record must be an object")
        case_id = record.get("case_id")
        attempt = record.get("attempt")
        if case_id not in case_ids or not isinstance(attempt, int) or attempt < 1:
            raise ValueError(f"invalid run record identity: {case_id!r}/{attempt!r}")
        identity = (case_id, attempt)
        if identity in seen:
            raise ValueError(f"duplicate run record: {identity}")
        seen.add(identity)
        if schema_version >= 3:
            diagnostics = record.get("agent_diagnostics")
            if not isinstance(diagnostics, dict):
                raise ValueError(f"{identity}: agent_diagnostics must be an object")
            missing = REQUIRED_DIAGNOSTIC_FIELDS - diagnostics.keys()
            if missing:
                raise ValueError(f"{identity}: diagnostics missing fields: {sorted(missing)}")
            for field in ("steps", "revisions", "tool_calls", "repeated_errors"):
                if not isinstance(diagnostics[field], int) or diagnostics[field] < 0:
                    raise ValueError(f"{identity}: diagnostics.{field} must be non-negative")
        if schema_version >= 4:
            diagnostics = record["agent_diagnostics"]
            for field in (
                "model_calls",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
            ):
                if not isinstance(diagnostics[field], int) or diagnostics[field] < 0:
                    raise ValueError(f"{identity}: diagnostics.{field} must be non-negative")
            if not isinstance(diagnostics["usage_available"], bool):
                raise ValueError(f"{identity}: diagnostics.usage_available must be boolean")
            fact = record.get("fact_coverage")
            if not isinstance(fact, dict) or not isinstance(fact.get("ratio"), (int, float)):
                raise ValueError(f"{identity}: fact_coverage must contain numeric ratio")
            cost = record.get("estimated_cost_usd")
            if cost is not None and (not isinstance(cost, (int, float)) or cost < 0):
                raise ValueError(f"{identity}: estimated_cost_usd must be non-negative or null")
    validate_no_sensitive_keys(run)


def main() -> None:
    args = parse_args()
    cases = load_json(args.cases)
    case_ids = validate_cases(cases)
    validate_no_sensitive_keys(cases)
    if args.run:
        validate_run(load_json(args.run), case_ids)
        print(f"Valid evaluation run: {args.run}")
    print(f"Valid evaluation cases: {len(case_ids)}")


if __name__ == "__main__":
    main()
