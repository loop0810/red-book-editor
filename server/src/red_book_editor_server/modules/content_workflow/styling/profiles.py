from __future__ import annotations

import functools
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from red_book_editor_server.domain.contracts import StyleForm, StyleProfile

_PROFILES_DIR = Path(__file__).resolve().parents[3] / "style_profiles"


class StyleProfileNotFoundError(KeyError):
    def __init__(self, form: StyleForm) -> None:
        super().__init__(f"style_profile_not_found: {form.value}")
        self.form = form


@functools.lru_cache
def load_all_profiles() -> dict[StyleForm, StyleProfile]:
    """加载并校验全部风格档案；任一档案 schema 违规都会抛错。"""

    profiles: dict[StyleForm, StyleProfile] = {}
    for path in sorted(_PROFILES_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        profile = StyleProfile.model_validate(raw)
        profiles[profile.form] = profile
    return profiles


def load_style_profile(form: StyleForm) -> StyleProfile:
    profile = load_all_profiles().get(form)
    if profile is None:
        raise StyleProfileNotFoundError(form)
    return profile
