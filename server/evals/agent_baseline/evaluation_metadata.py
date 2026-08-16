from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from red_book_editor_server.domain.agent import AGENT_RUNTIME_VERSION
from red_book_editor_server.modules.content_workflow.styling.agent import (
    STYLING_AGENT_CONFIG,
    STYLING_AGENT_CONFIG_VERSION,
    STYLING_PROMPT_VERSION,
    SYSTEM_PROMPT,
)
from red_book_editor_server.modules.content_workflow.styling.profiles import STYLE_PROFILE_VERSION

ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "evals" / "agent_baseline" / "cases.json"
SCORECARD_PATH = ROOT / "evals" / "agent_baseline" / "scorecard.md"
PROFILES_DIR = ROOT / "src" / "red_book_editor_server" / "style_profiles"
MANIFEST_PATH = ROOT / "evals" / "agent_baseline" / "quality-gate-manifest.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(encoded.encode("utf-8"))


def profile_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(PROFILES_DIR.glob("*.yaml")):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def current_digests() -> dict[str, str]:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return {
        "cases_sha256": sha256_json(cases),
        "scorecard_sha256": sha256_bytes(SCORECARD_PATH.read_bytes()),
        "prompt_sha256": sha256_bytes(SYSTEM_PROMPT.encode("utf-8")),
        "profile_sha256": profile_digest(),
        "agent_config_sha256": sha256_json(STYLING_AGENT_CONFIG),
    }


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("quality gate manifest must be a JSON object")
    return value


def build_evaluation_context(
    manifest: dict[str, Any],
    *,
    model_provider: str,
    model: str,
    model_max_tokens: int | None,
    input_rate_usd_per_million: float | None,
    output_rate_usd_per_million: float | None,
) -> dict[str, Any]:
    digests = current_digests()
    context = {
        "manifest_version": manifest.get("manifest_version"),
        "manifest_sha256": sha256_json(manifest),
        "model_provider": model_provider,
        "model": model,
        "model_max_tokens": model_max_tokens,
        "scorecard_version": manifest.get("scorecard_version"),
        "prompt_version": STYLING_PROMPT_VERSION,
        "profile_version": STYLE_PROFILE_VERSION,
        "agent_runtime_version": AGENT_RUNTIME_VERSION,
        "agent_config_version": STYLING_AGENT_CONFIG_VERSION,
        "input_rate_usd_per_million_tokens": input_rate_usd_per_million,
        "output_rate_usd_per_million_tokens": output_rate_usd_per_million,
        **digests,
    }
    return context
