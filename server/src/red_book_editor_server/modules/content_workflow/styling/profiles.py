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

    # YAML 是给人维护的配置，StyleProfile 是运行时使用的类型安全对象。
    # lru_cache 让一次进程内的多次 Agent 调用不必重复读盘和解析 YAML。
    profiles: dict[StyleForm, StyleProfile] = {}
    for path in sorted(_PROFILES_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        profile = StyleProfile.model_validate(raw)
        profiles[profile.form] = profile
    return profiles


def load_style_profile(form: StyleForm) -> StyleProfile:
    # Agent 只拿到用户选择的表达形式，具体钩子、结构、语气和标签规则
    # 都从这里统一解析，避免 prompt 和业务代码各自维护一份风格规则。
    profile = load_all_profiles().get(form)
    if profile is None:
        raise StyleProfileNotFoundError(form)
    return profile
