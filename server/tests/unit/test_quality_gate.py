from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from evals.agent_baseline.evaluation_metadata import load_manifest, sha256_json
from scripts.quality_gate import evaluate_gate
from scripts.validate_agent_eval import load_json


def _payload() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    cases = load_json(Path("evals/agent_baseline/cases.json"))
    manifest = load_manifest()
    context = {
        "manifest_version": manifest["manifest_version"],
        "manifest_sha256": sha256_json(manifest),
        "model_provider": manifest["model_provider"],
        "model": manifest["model"],
        "model_max_tokens": manifest["model_max_tokens"],
        "scorecard_version": manifest["scorecard_version"],
        "prompt_version": "styling-system-v2",
        "profile_version": "style-profiles-v2",
        "agent_runtime_version": "agent-runtime-v1",
        "agent_config_version": "styling-agent-config-v1",
        "cases_sha256": manifest["expected_digests"]["cases_sha256"],
        "scorecard_sha256": manifest["expected_digests"]["scorecard_sha256"],
        "prompt_sha256": manifest["expected_digests"]["prompt_sha256"],
        "profile_sha256": manifest["expected_digests"]["profile_sha256"],
        "agent_config_sha256": manifest["expected_digests"]["agent_config_sha256"],
        "input_rate_usd_per_million_tokens": 1.0,
        "output_rate_usd_per_million_tokens": 1.0,
    }
    records: list[dict[str, object]] = []
    score_records: list[dict[str, object]] = []
    for case in cases:
        body = "；".join(
            [
                case["content_brief"]["focus"],
                case["content_brief"]["raw_material"],
            ]
        )
        for attempt in (1, 2):
            identity = {"case_id": case["case_id"], "attempt": attempt}
            records.append(
                {
                    **identity,
                    "status": "succeeded",
                    "draft": {"body": body},
                    "automatic_hard_failures": [],
                    "agent_diagnostics": {
                        "usage_available": True,
                        "prompt_tokens": 10,
                        "completion_tokens": 10,
                        "total_tokens": 20,
                    },
                    "estimated_cost_usd": 0.00002,
                }
            )
            score_records.append(
                {
                    **identity,
                    "scores": {
                        dimension: 2
                        for dimension in (
                            "focus_alignment",
                            "account_style_fit",
                            "factual_fidelity",
                            "source_transformation",
                            "enrichment_usefulness",
                            "source_overlap_rate",
                            "safety",
                            "structure",
                            "naturalness",
                            "usefulness",
                            "edit_cost",
                        )
                    },
                    "total": 22,
                    "hard_failures": [],
                    "failure_reason": "none",
                    "final_edited_draft": "reviewed final draft",
                    "reviewer_note": "reviewed",
                }
            )
    run = {
        "schema_version": 4,
        "run_id": "quality-test",
        "model_provider": "deepseek",
        "model": "deepseek-chat",
        "repetitions": 2,
        "case_count": len(cases),
        "evaluation_context": context,
        "records": records,
    }
    scores = {
        "schema_version": 2,
        "scorecard_version": "scorecard-v3",
        "run_id": "quality-test",
        "records": score_records,
    }
    return run, scores, manifest, cases


def test_quality_gate_passes_complete_evidence() -> None:
    run, scores, manifest, cases = _payload()

    report = evaluate_gate(run, scores, manifest, cases)

    assert report["gate"] == "passed"
    assert report["issues"] == []
    assert report["metrics"]["fact_coverage"] == 1.0
    assert report["metrics"]["total_tokens"] == 320


def test_quality_gate_fails_version_drift_and_missing_usage() -> None:
    run, scores, manifest, cases = _payload()
    run = deepcopy(run)
    run["evaluation_context"]["prompt_sha256"] = "stale"
    run["records"][0]["agent_diagnostics"]["usage_available"] = False

    report = evaluate_gate(run, scores, manifest, cases)

    assert report["gate"] == "failed"
    assert any("prompt_sha256" in issue for issue in report["issues"])
    assert any("model usage is missing" in issue for issue in report["issues"])


def test_quality_gate_fails_incomplete_manual_review_and_fact_coverage() -> None:
    run, scores, manifest, cases = _payload()
    scores = deepcopy(scores)
    run = deepcopy(run)
    run["records"][0]["draft"]["body"] = "只有一条事实"
    scores["records"] = scores["records"][:-1]
    scores["records"][0]["total"] = 1

    report = evaluate_gate(run, scores, manifest, cases)

    assert report["gate"] == "failed"
    assert any("missing identities" in issue for issue in report["issues"])
    assert any(
        check["name"] == "fact_coverage" and not check["passed"] for check in report["checks"]
    )
