from __future__ import annotations

import re

from red_book_editor_server.domain.contracts import SourceExperienceDto, StyleProfile
from red_book_editor_server.modules.content_workflow.styling.models import (
    DraftContent,
    FinalizeArgs,
)


def apply_decorator(finalized: FinalizeArgs, profile: StyleProfile) -> FinalizeArgs:
    """确定性富文本装饰：标签去重/裁剪、科普形式补充 CTA。"""

    hashtags = _normalize_tags(finalized.draft.hashtags, profile)
    body = finalized.draft.body.strip()
    if (
        profile.form.value == "popular_science"
        and profile.cta
        and not any(phrase in body for phrase in profile.cta)
    ):
        body = f"{body}\n\n{profile.cta[0]}"
    draft = finalized.draft.model_copy(update={"hashtags": hashtags, "body": body})
    return finalized.model_copy(update={"draft": draft})


def check_facts(source: SourceExperienceDto, draft: DraftContent) -> tuple[bool, list[str]]:
    """核对关键来源事实是否出现在草稿中。"""

    text = "\n".join([draft.topic_angle, *draft.title_candidates, draft.body])
    missing = [fact for fact in _required_facts(source) if not _contains_fact(fact, text)]
    return (not missing, [f"来源事实缺失：{fact}" for fact in missing])


def _contains_fact(fact: str, text: str) -> bool:
    compact_fact = _compact(fact)
    compact_text = _compact(text)
    if compact_fact in compact_text:
        return True
    # 中文叙述常在动作后加“了”，不应把语法变化误判为编造或遗漏。
    return compact_fact.replace("了", "") in compact_text.replace("了", "")


def _compact(value: str) -> str:
    return re.sub(r"[\s，。！？、,.!?；;：:（）()\[\]【】]", "", value)


def _required_facts(source: SourceExperienceDto) -> list[str]:
    facts = _split_fact_clauses(source.scenario)
    facts.append(str(source.baby_month))
    for action in source.actions:
        facts.extend(_split_fact_clauses(action, split=False))
    facts.extend(_split_fact_clauses(source.observations))
    return [fact for fact in facts if fact]


def _split_fact_clauses(value: str, *, split: bool = True) -> list[str]:
    """Return independently checkable source clauses without semantic inference."""

    stripped = value.strip()
    if not stripped:
        return []
    parts = re.split(r"[，,；;。！？!?]+", stripped) if split else [stripped]
    return [part.strip() for part in parts if part.strip()]


def _normalize_tags(hashtags: list[str], profile: StyleProfile) -> list[str]:
    max_tags = profile.rich_text.tag_count_range[1]
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in hashtags:
        clean = tag.strip().lstrip("#").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        normalized.append(f"#{clean}")
    return normalized[:max_tags]
