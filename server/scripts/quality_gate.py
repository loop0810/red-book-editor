from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TypeGuard

from evals.agent_baseline.evaluation_metadata import (
    MANIFEST_PATH,
    load_manifest,
    sha256_json,
)
from evals.agent_baseline.hard_failures import automatic_hard_failures, fact_coverage
from scripts.validate_agent_eval import load_json, validate_cases

# 质量门禁故意是 fail-closed：版本、运行、人工评分和成本任一证据缺失，
# 即使平均分看起来不错，也不能生成“通过”的结论。
ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "evals" / "agent_baseline" / "cases.json"
RUNS_DIR = ROOT / "evals" / "agent_baseline" / "runs"
REPORTS_DIR = ROOT / "evals" / "agent_baseline" / "reports"
SCORE_DIMENSIONS = (
    "focus_alignment",
    "account_style_fit",
    "factual_fidelity",
    "safety",
    "structure",
    "naturalness",
    "usefulness",
    "edit_cost",
)


def _identity(value: dict[str, Any]) -> tuple[str, int]:
    return (str(value.get("case_id")), int(value.get("attempt", 0)))


def _identity_label(identity: tuple[str, int]) -> str:
    return f"{identity[0]}/{identity[1]}"


def _numeric(value: Any) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _run_records(run: dict[str, Any]) -> list[dict[str, Any]]:
    records = run.get("records")
    return [record for record in records if isinstance(record, dict)] if isinstance(records, list) else []


def _expected_identities(cases: list[dict[str, Any]], repetitions: int) -> set[tuple[str, int]]:
    return {
        (str(case["case_id"]), attempt)
        for case in cases
        for attempt in range(1, repetitions + 1)
    }


def validate_manifest_binding(
    run: dict[str, Any], manifest: dict[str, Any], cases: list[dict[str, Any]]
) -> list[str]:
    # 先验证这批数据是不是“当前这套评测”的产物，再计算指标；
    # 否则旧 prompt/案例集的好成绩可能被错误地当成新版本证据。
    issues: list[str] = []
    context = run.get("evaluation_context")
    if run.get("schema_version", 0) < 4 or not isinstance(context, dict):
        return ["run must use schema 4 with evaluation_context"]

    expected = manifest.get("expected_digests")
    if not isinstance(expected, dict):
        issues.append("manifest.expected_digests is missing")
        expected = {}
    for key in (
        "manifest_version",
        "scorecard_version",
        "model_provider",
        "model",
        "model_max_tokens",
        "prompt_version",
        "profile_version",
        "agent_runtime_version",
        "agent_config_version",
    ):
        manifest_value = manifest.get(key)
        if manifest_value is not None and context.get(key) != manifest_value:
            issues.append(f"evaluation_context.{key} does not match manifest")
    for key in (
        "cases_sha256",
        "scorecard_sha256",
        "prompt_sha256",
        "profile_sha256",
        "agent_config_sha256",
    ):
        if not isinstance(expected.get(key), str) or not expected.get(key):
            issues.append(f"manifest.expected_digests.{key} is missing")
        elif context.get(key) != expected[key]:
            issues.append(f"evaluation_context.{key} does not match manifest")
    if context.get("manifest_sha256") != sha256_json(manifest):
        issues.append("evaluation_context.manifest_sha256 does not match manifest")

    records = _run_records(run)
    repetitions = run.get("repetitions")
    min_repetitions = manifest.get("min_repetitions", 2)
    if not isinstance(repetitions, int) or repetitions < min_repetitions:
        issues.append(f"run.repetitions must be at least {min_repetitions}")
    if run.get("case_count") != len(cases):
        issues.append("run.case_count does not match cases.json")
    if isinstance(repetitions, int) and repetitions >= 1:
        actual = [_identity(record) for record in records]
        if len(actual) != len(set(actual)):
            issues.append("run.records contains duplicate case_id/attempt identities")
        missing = _expected_identities(cases, repetitions) - set(actual)
        extra = set(actual) - _expected_identities(cases, repetitions)
        if missing:
            issues.append(f"run.records missing identities: {sorted(map(_identity_label, missing))}")
        if extra:
            issues.append(f"run.records has unexpected identities: {sorted(map(_identity_label, extra))}")

    require_usage = manifest.get("require_usage") is True
    require_cost = manifest.get("require_cost") is True
    if require_usage or require_cost:
        input_rate = context.get("input_rate_usd_per_million_tokens")
        output_rate = context.get("output_rate_usd_per_million_tokens")
        if require_cost and (not _numeric(input_rate) or not _numeric(output_rate)):
            issues.append("cost rates are required for the quality gate")
        for record in records:
            identity = _identity_label(_identity(record))
            diagnostics = record.get("agent_diagnostics")
            if not isinstance(diagnostics, dict):
                issues.append(f"{identity}: agent_diagnostics is missing")
                continue
            if require_usage and diagnostics.get("usage_available") is not True:
                issues.append(f"{identity}: model usage is missing")
            if require_cost and record.get("estimated_cost_usd") is None:
                issues.append(f"{identity}: estimated_cost_usd is missing")
    return issues


def validate_scores(
    run: dict[str, Any], scores: dict[str, Any]
) -> tuple[list[str], dict[tuple[str, int], dict[str, Any]]]:
    issues: list[str] = []
    if scores.get("run_id") != run.get("run_id"):
        issues.append("scores.run_id does not match run.run_id")
    if scores.get("scorecard_version") != run.get("evaluation_context", {}).get("scorecard_version"):
        issues.append("scores.scorecard_version does not match evaluation_context")
    raw_records = scores.get("records")
    if not isinstance(raw_records, list):
        return ["scores.records must be an array"], {}
    indexed: dict[tuple[str, int], dict[str, Any]] = {}
    for raw in raw_records:
        if not isinstance(raw, dict):
            issues.append("each score record must be an object")
            continue
        identity = _identity(raw)
        if identity in indexed:
            issues.append(f"duplicate score identity: {_identity_label(identity)}")
        indexed[identity] = raw
        score_values = raw.get("scores")
        if not isinstance(score_values, dict):
            issues.append(f"{_identity_label(identity)}: scores is missing")
            continue
        if set(score_values) != set(SCORE_DIMENSIONS):
            issues.append(f"{_identity_label(identity)}: score dimensions are incomplete")
        for dimension in SCORE_DIMENSIONS:
            value = score_values.get(dimension)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 2:
                issues.append(f"{_identity_label(identity)}: invalid score {dimension}")
        total = raw.get("total")
        if isinstance(total, int) and all(isinstance(score_values.get(d), int) for d in SCORE_DIMENSIONS):
            expected_total = sum(int(score_values[d]) for d in SCORE_DIMENSIONS)
            if total != expected_total:
                issues.append(f"{_identity_label(identity)}: total does not match scores")
        else:
            issues.append(f"{_identity_label(identity)}: total is missing")
        for field in ("hard_failures", "failure_reason", "final_edited_draft", "reviewer_note"):
            if field not in raw:
                issues.append(f"{_identity_label(identity)}: {field} is missing")
        if not isinstance(raw.get("hard_failures"), list) or not all(
            isinstance(value, str) for value in raw.get("hard_failures", [])
        ):
            issues.append(f"{_identity_label(identity)}: hard_failures must be a string array")
        for field in ("failure_reason", "final_edited_draft", "reviewer_note"):
            if not isinstance(raw.get(field), str) or not raw[field].strip():
                issues.append(f"{_identity_label(identity)}: {field} must be non-empty")

    expected = {_identity(record) for record in _run_records(run)}
    missing = expected - set(indexed)
    extra = set(indexed) - expected
    if missing:
        issues.append(f"scores.records missing identities: {sorted(map(_identity_label, missing))}")
    if extra:
        issues.append(f"scores.records has unexpected identities: {sorted(map(_identity_label, extra))}")
    return issues, indexed


def calculate_metrics(
    run: dict[str, Any], scores: dict[tuple[str, int], dict[str, Any]]
) -> dict[str, Any]:
    # 运行指标和人工指标在同一个函数汇总，报告与退出码复用同一份结果，
    # 避免命令行显示通过但报告内容不一致。
    records = _run_records(run)
    count = len(records)
    succeeded = sum(record.get("status") == "succeeded" for record in records)
    agent_failures = count - succeeded
    automatic_failures = sum(bool(record.get("automatic_hard_failures")) for record in records)
    major_rewrites = sum(
        "major_rewrite" in scores.get(_identity(record), {}).get("hard_failures", [])
        for record in records
    )
    manual_hard_failures = sum(
        bool(scores.get(_identity(record), {}).get("hard_failures")) for record in records
    )
    coverage_values = [float(fact_coverage(record_case, record)["ratio"]) for record_case, record in _case_record_pairs(run)]
    totals = [scores.get(_identity(record), {}).get("total") for record in records]
    valid_totals = [value for value in totals if isinstance(value, int)]
    dimensions = {
        dimension: _average(
            [scores.get(_identity(record), {}).get("scores", {}).get(dimension) for record in records]
        )
        for dimension in SCORE_DIMENSIONS
    }
    prompt_tokens = sum(_diagnostic_int(record, "prompt_tokens") for record in records)
    completion_tokens = sum(_diagnostic_int(record, "completion_tokens") for record in records)
    total_tokens = sum(_diagnostic_int(record, "total_tokens") for record in records)
    costs = [record.get("estimated_cost_usd") for record in records]
    return {
        "run_count": count,
        "success_rate": succeeded / count if count else 0.0,
        "agent_failure_rate": agent_failures / count if count else 0.0,
        "automatic_hard_failure_rate": automatic_failures / count if count else 0.0,
        "manual_hard_failure_rate": manual_hard_failures / count if count else 0.0,
        "fact_coverage": _average(coverage_values),
        "fact_coverage_min": min(coverage_values) if coverage_values else 0.0,
        "major_rewrite_rate": major_rewrites / count if count else 0.0,
        "manual_average_score": _average(valid_totals),
        "score_dimension_averages": dimensions,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": sum(costs) if costs and all(_numeric(value) for value in costs) else None,
        "failure_codes": _failure_codes(records),
        "by_case": _case_metrics(run, scores),
    }


def _case_record_pairs(run: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    cases = load_json(CASES_PATH)
    by_id = {case["case_id"]: case for case in cases if isinstance(case, dict)}
    return [
        (by_id[record["case_id"]], record)
        for record in _run_records(run)
        if record.get("case_id") in by_id
    ]


def _case_metrics(run: dict[str, Any], scores: dict[tuple[str, int], dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in _run_records(run):
        grouped.setdefault(str(record.get("case_id")), []).append(record)
    output: dict[str, Any] = {}
    for case_id, records in sorted(grouped.items()):
        coverages = [float(record.get("fact_coverage", {}).get("ratio", 0.0)) for record in records]
        totals = [scores.get(_identity(record), {}).get("total") for record in records]
        output[case_id] = {
            "run_count": len(records),
            "success_rate": sum(record.get("status") == "succeeded" for record in records)
            / len(records),
            "fact_coverage": _average(coverages),
            "automatic_hard_failure_count": sum(
                bool(record.get("automatic_hard_failures")) for record in records
            ),
            "manual_average_score": _average([value for value in totals if isinstance(value, int)]),
        }
    return output


def _diagnostic_int(record: dict[str, Any], field: str) -> int:
    diagnostics = record.get("agent_diagnostics")
    value = diagnostics.get(field, 0) if isinstance(diagnostics, dict) else 0
    return int(value) if isinstance(value, int) else 0


def _failure_codes(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        diagnostics = record.get("agent_diagnostics")
        code = diagnostics.get("failure_code") if isinstance(diagnostics, dict) else None
        if isinstance(code, str) and code:
            counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _average(values: list[Any]) -> float:
    numeric = [float(value) for value in values if _numeric(value)]
    return sum(numeric) / len(numeric) if numeric else 0.0


def _threshold_checks(metrics: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    thresholds = manifest.get("thresholds")
    if not isinstance(thresholds, dict):
        return [{"name": "thresholds", "passed": False, "reason": "manifest.thresholds is missing"}]
    definitions = (
        ("success_rate", "min_success_rate", ">=", metrics.get("success_rate")),
        ("fact_coverage", "min_fact_coverage", ">=", metrics.get("fact_coverage")),
        ("automatic_hard_failure_rate", "max_hard_failure_rate", "<=", metrics.get("automatic_hard_failure_rate")),
        ("manual_hard_failure_rate", "max_manual_hard_failure_rate", "<=", metrics.get("manual_hard_failure_rate")),
        ("agent_failure_rate", "max_agent_failure_rate", "<=", metrics.get("agent_failure_rate")),
        ("manual_average_score", "min_manual_average_score", ">=", metrics.get("manual_average_score")),
        ("major_rewrite_rate", "max_major_rewrite_rate", "<=", metrics.get("major_rewrite_rate")),
        ("estimated_cost_usd", "max_estimated_cost_usd", "<=", metrics.get("estimated_cost_usd")),
    )
    checks: list[dict[str, Any]] = []
    for name, threshold_name, operator, actual in definitions:
        expected = thresholds.get(threshold_name)
        passed = False
        if _numeric(actual) and _numeric(expected):
            passed = actual >= expected if operator == ">=" else actual <= expected
        checks.append(
            {
                "name": name,
                "operator": operator,
                "actual": actual,
                "threshold": expected,
                "passed": passed,
            }
        )
    return checks


def _compare(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any] | None:
    if baseline is None:
        return None
    metric_names = (
        "success_rate",
        "fact_coverage",
        "automatic_hard_failure_rate",
        "manual_hard_failure_rate",
        "agent_failure_rate",
        "major_rewrite_rate",
        "manual_average_score",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "estimated_cost_usd",
    )
    deltas: dict[str, float | None] = {}
    for name in metric_names:
        current_value = current.get(name)
        baseline_value = baseline.get(name)
        deltas[name] = (
            float(current_value) - float(baseline_value)
            if _numeric(current_value) and _numeric(baseline_value)
            else None
        )
    dimensions: dict[str, float | None] = {}
    current_dimensions = current.get("score_dimension_averages", {})
    baseline_dimensions = baseline.get("score_dimension_averages", {})
    for name in SCORE_DIMENSIONS:
        dimensions[name] = (
            float(current_dimensions[name]) - float(baseline_dimensions[name])
            if _numeric(current_dimensions.get(name)) and _numeric(baseline_dimensions.get(name))
            else None
        )
    case_deltas: dict[str, dict[str, float | None]] = {}
    current_cases = current.get("by_case", {})
    baseline_cases = baseline.get("by_case", {})
    for case_id in sorted(set(current_cases) | set(baseline_cases)):
        current_case = current_cases.get(case_id, {})
        baseline_case = baseline_cases.get(case_id, {})
        case_deltas[case_id] = {
            name: (
                float(current_case[name]) - float(baseline_case[name])
                if _numeric(current_case.get(name)) and _numeric(baseline_case.get(name))
                else None
            )
            for name in (
                "success_rate",
                "fact_coverage",
                "automatic_hard_failure_count",
                "manual_average_score",
            )
        }
    return {
        "metric_deltas": deltas,
        "score_dimension_deltas": dimensions,
        "case_deltas": case_deltas,
    }


def evaluate_gate(
    run: dict[str, Any],
    scores: dict[str, Any],
    manifest: dict[str, Any],
    cases: list[dict[str, Any]],
    baseline: tuple[dict[str, Any], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    # binding/score validation 不会短路 metrics 计算：失败报告仍要尽量给出
    # 实际值和对应案例，方便定位下一轮需要修复的主链路。
    binding_issues = validate_manifest_binding(run, manifest, cases)
    score_issues, indexed_scores = validate_scores(run, scores)
    metrics = calculate_metrics(run, indexed_scores)
    checks = _threshold_checks(metrics, manifest)
    issues = [*binding_issues, *score_issues]
    passed = not issues and all(check.get("passed") is True for check in checks)
    baseline_report = None
    if baseline is not None:
        baseline_run, baseline_scores = baseline
        _, baseline_indexed = validate_scores(baseline_run, baseline_scores)
        baseline_metrics = calculate_metrics(baseline_run, baseline_indexed)
        baseline_report = {
            "run_id": baseline_run.get("run_id"),
            "score_run_id": baseline_scores.get("run_id"),
            "metrics": baseline_metrics,
            "comparison": _compare(metrics, baseline_metrics),
        }
    return {
        "report_schema_version": 1,
        "gate": "passed" if passed else "failed",
        "run_id": run.get("run_id"),
        "score_run_id": scores.get("run_id"),
        "issues": issues,
        "checks": checks,
        "metrics": metrics,
        "comparison": baseline_report,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Agent Quality Gate Report",
        "",
        f"- Gate: **{report['gate']}**",
        f"- Run: `{report.get('run_id')}`",
        f"- Score: `{report.get('score_run_id')}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in report["metrics"].items():
        if key in {"by_case", "score_dimension_averages"}:
            continue
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(["", "## Checks", "", "| Check | Actual | Threshold | Result |", "|---|---:|---:|---|"])
    for check in report["checks"]:
        lines.append(
            f"| `{check['name']}` | `{check.get('actual')}` | "
            f"`{check.get('operator', '')} {check.get('threshold', '')}` | "
            f"`{'pass' if check.get('passed') else 'fail'}` |"
        )
    lines.extend(["", "## Issues", ""])
    lines.extend(f"- {issue}" for issue in report["issues"] or ["无"])
    lines.extend(["", "## By case", "", "| Case | Success | Fact coverage | Hard failures | Manual score |", "|---|---:|---:|---:|---:|"])
    for case_id, metrics in report["metrics"]["by_case"].items():
        lines.append(
            f"| `{case_id}` | `{metrics['success_rate']}` | `{metrics['fact_coverage']}` | "
            f"`{metrics['automatic_hard_failure_count']}` | `{metrics['manual_average_score']}` |"
        )
    if report.get("comparison"):
        lines.extend(["", "## Comparison", "", "```json", json.dumps(report["comparison"]["comparison"], ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines) + "\n"


def write_reports(report: dict[str, Any], json_path: Path, markdown_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(_markdown(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the blocking P1-06 Agent quality gate")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--baseline-run", type=Path)
    parser.add_argument("--baseline-scores", type=Path)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--markdown-report", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        cases = load_json(CASES_PATH)
        case_ids = validate_cases(cases)
        if len(case_ids) != len(cases):
            raise ValueError("case ids must be unique")
        run = load_json(args.run)
        scores = load_json(args.scores)
        manifest = load_manifest(args.manifest)
        baseline = None
        if bool(args.baseline_run) != bool(args.baseline_scores):
            raise ValueError("--baseline-run and --baseline-scores must be provided together")
        if args.baseline_run and args.baseline_scores:
            baseline = (load_json(args.baseline_run), load_json(args.baseline_scores))
        report = evaluate_gate(run, scores, manifest, cases, baseline)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        report = {
            "report_schema_version": 1,
            "gate": "failed",
            "run_id": None,
            "score_run_id": None,
            "issues": [f"quality gate input error: {error}"],
            "checks": [],
            "metrics": {},
            "comparison": None,
        }
    json_path = args.json_report or REPORTS_DIR / f"{report.get('run_id', 'unknown')}.quality-gate.json"
    markdown_path = args.markdown_report or REPORTS_DIR / f"{report.get('run_id', 'unknown')}.quality-gate.md"
    write_reports(report, json_path, markdown_path)
    print(f"Quality gate: {report['gate']}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {markdown_path}")
    for issue in report["issues"]:
        print(f"FAIL: {issue}", file=sys.stderr)
    return 0 if report["gate"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
