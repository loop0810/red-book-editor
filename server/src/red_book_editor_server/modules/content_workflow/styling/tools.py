from __future__ import annotations

import json
import re

from red_book_editor_server.domain.agent import AgentPhase, Tool
from red_book_editor_server.domain.contracts import (
    ContentBriefDto,
    SourceExperienceDto,
    StyleProfile,
)
from red_book_editor_server.modules.content_workflow.styling.decorator import (
    _contains_fact,
    _required_facts,
)
from red_book_editor_server.modules.content_workflow.styling.models import (
    CritiqueArgs,
    CritiqueResult,
    FinalizeArgs,
    StyleFormArg,
    SuggestTagsArgs,
)
from red_book_editor_server.modules.content_workflow.styling.profiles import load_style_profile

_NUMBERED_ITEM = re.compile(r"(?m)^\s*\d+[.、．)）]")
_BULLET = re.compile(r"[•·●◆]")
_SECTION = re.compile(r"[|｜]")
_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]")


def build_styling_tools() -> list[Tool]:
    # Tool 是模型“可以请求什么”的声明；真正的 handler 仍由服务端执行。
    # 这四个工具形成当前风格 Agent 的最小工作台：读档案、找话题、自评、定稿。
    return [
        Tool(
            name="load_style_profile",
            description="加载指定表达形式（popular_science/experience/advertorial）的小红书风格档案，返回钩子、结构、语气、富文本与标签规则",
            parameters={
                "type": "object",
                "properties": {
                    "form": {
                        "type": "string",
                        "enum": ["popular_science", "experience", "advertorial"],
                    }
                },
                "required": ["form"],
            },
            handler=load_style_profile_tool,
            phase=AgentPhase.COLLECT_CONTEXT,
            transition=lambda _: AgentPhase.DRAFT,
        ),
        Tool(
            name="suggest_tags",
            description="按主题和表达形式生成三层话题标签建议（泛标签+精准标签+蹭热点标签）",
            parameters={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "form": {
                        "type": "string",
                        "enum": ["popular_science", "experience", "advertorial"],
                    },
                },
                "required": ["topic", "form"],
            },
            handler=suggest_tags_tool,
            phase=AgentPhase.DRAFT,
        ),
        Tool(
            name="critique_draft",
            description="对照风格档案自评草稿：钩子、结构、语气、事实保持、富文本，返回评分与待修订问题",
            parameters={
                "type": "object",
                "properties": {
                    "form": {"type": "string"},
                    "draft": {
                        "type": "object",
                        "properties": {
                            "topic_angle": {"type": "string"},
                            "title_candidates": {"type": "array", "items": {"type": "string"}},
                            "body": {"type": "string"},
                            "hashtags": {"type": "array", "items": {"type": "string"}},
                            "cover_copy": {"type": "string"},
                            "image_suggestions": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                    },
                    "source": {"type": "object"},
                },
                "required": ["form", "draft", "source"],
            },
            handler=critique_draft_tool,
            phase=AgentPhase.CRITIQUE,
            transition=_critique_transition,
        ),
        Tool(
            name="finalize_note",
            description="校验并确认最终笔记内容，返回结构化结果",
            parameters={
                "type": "object",
                "properties": {
                    "form": {"type": "string"},
                    "draft": {"type": "object"},
                    "image_suggestions": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["form", "draft"],
            },
            handler=finalize_note_tool,
            phase=AgentPhase.FINALIZE,
        ),
    ]


def _critique_transition(result: str) -> AgentPhase:
    try:
        return AgentPhase.FINALIZE if bool(json.loads(result).get("passed")) else AgentPhase.REVISE
    except (AttributeError, json.JSONDecodeError):
        return AgentPhase.REVISE


async def load_style_profile_tool(args: dict[str, object]) -> str:
    # 模型传入的是普通 JSON，先用 Pydantic 转成 StyleForm，避免无效形式进入业务层。
    form = StyleFormArg.model_validate(args).form
    profile = load_style_profile(form)
    return profile.model_dump_json()


async def suggest_tags_tool(args: dict[str, object]) -> str:
    # 话题建议目前来自版本化档案，不访问外部热点服务；因此结果可重复且容易测试。
    parsed = SuggestTagsArgs.model_validate(args)
    profile = load_style_profile(parsed.form)
    topic = parsed.topic
    precise = [tag for tag in profile.tags.precise if _tag_matches(tag, topic)]
    trending = [tag for tag in profile.tags.trending if _tag_matches(tag, topic)]
    topic_tag = _topic_tag(topic)
    combined = [topic_tag, *precise, *trending, *profile.tags.generic]
    deduped = list(dict.fromkeys(tag.lstrip("#") for tag in combined))
    max_tags = profile.rich_text.tag_count_range[1]
    return json.dumps([f"#{tag}" for tag in deduped[:max_tags]], ensure_ascii=False)


async def critique_draft_tool(args: dict[str, object]) -> str:
    # critique 是确定性检查工具：它不让模型“自称通过”，而是由代码计算分数和问题。
    parsed = CritiqueArgs.model_validate(args)
    profile = load_style_profile(parsed.form)
    draft = parsed.draft
    text = "\n".join(
        [
            draft.topic_angle,
            *draft.title_candidates,
            draft.body,
            *draft.hashtags,
            draft.cover_copy,
            *draft.image_suggestions,
        ]
    )
    issues: list[str] = []

    hook = _score_hook(draft.title_candidates)
    structure = _score_structure(draft.body)
    tone_score, tone_issues = _score_tone(profile, text)
    facts_score, fact_issues = _score_facts(parsed.source, text)
    rich_score, rich_issues = _score_rich_text(profile, draft.hashtags, draft.body)
    issues.extend(tone_issues)
    issues.extend(fact_issues)
    issues.extend(rich_issues)
    focus = (
        parsed.source.focus
        if isinstance(parsed.source, ContentBriefDto)
        else parsed.source.scenario
    )
    material = (
        parsed.source.raw_material
        if isinstance(parsed.source, ContentBriefDto)
        else "；".join([*parsed.source.actions, parsed.source.observations, parsed.source.notes])
    ).strip()
    if len(draft.title_candidates) < 3:
        issues.append("标题候选至少需要 3 个")
    if not any(_compact(focus) in _compact(title) for title in draft.title_candidates):
        issues.append("标题候选必须明确围绕内容主题")
    if _compact(focus) not in _compact(draft.topic_angle):
        issues.append("选题角度必须明确围绕内容主题")
    if len(draft.body) < max(100, len(material) * 2):
        issues.append("正文过短，必须保留原始素材的完整信息并展开过程细节")
    if not draft.cover_copy.strip() or _compact(draft.cover_copy) == _compact(focus):
        issues.append("封面文案不能只重复内容主题")
    if _compact(focus) not in _compact(draft.cover_copy):
        issues.append("封面文案必须包含内容主题并补充具体角度")
    if not any(_compact(focus) in _compact(tag) for tag in draft.hashtags):
        issues.append("至少要有一个话题直接对应内容主题")
    if len(draft.image_suggestions) < 3:
        issues.append("配图建议至少需要 3 条具体建议")
    if not any(_compact(focus) in _compact(item) for item in draft.image_suggestions):
        issues.append("至少要有一条配图建议直接对应内容主题")

    # 事实分数和各风格分项都达到门槛后，模型才被允许继续 finalize。
    passed = not issues and facts_score >= 4 and min(hook, structure, tone_score, rich_score) >= 3
    result = CritiqueResult(
        scores={
            "hook": hook,
            "structure": structure,
            "tone": tone_score,
            "facts": facts_score,
            "rich_text": rich_score,
        },
        issues=issues,
        passed=passed,
    )
    return result.model_dump_json()


async def finalize_note_tool(args: dict[str, object]) -> str:
    # finalize 本身主要做结构化解析；真正的事实闸门还会在 styling/agent.py
    # 的 final_validator 中再次执行，形成“工具约束 + 服务端校验”的两层保护。
    parsed = FinalizeArgs.model_validate(args)
    return parsed.model_dump_json()


def _score_hook(titles: list[str]) -> int:
    if any(re.search(r"\d", title) for title in titles):
        return 5
    if any("？" in title or "！" in title for title in titles):
        return 4
    if any(len(title) >= 12 for title in titles):
        return 3
    return 2


def _score_structure(body: str) -> int:
    markers = sum(1 for pattern in (_NUMBERED_ITEM, _BULLET, _SECTION) if pattern.search(body))
    if markers >= 2:
        return 5
    if markers == 1:
        return 4
    # 经验类文案常用自然段完成“事件→过程→感受→结果”的叙述，
    # 不应因为没有编号列表而被反复要求重写。
    if len([paragraph for paragraph in body.split("\n\n") if paragraph.strip()]) >= 3:
        return 3
    return 2


def _score_tone(profile: StyleProfile, text: str) -> tuple[int, list[str]]:
    hits = sum(1 for word in profile.tone.words if word in text)
    issues = [f"包含禁用表达：{word}" for word in profile.tone.forbidden if word in text]
    score = 5 if hits >= 2 else (4 if hits == 1 else 3)
    if issues:
        score = max(0, score - 2)
    return score, issues


def _score_facts(source: ContentBriefDto | SourceExperienceDto, text: str) -> tuple[int, list[str]]:
    # 当前版本使用关键事实的文本匹配，优点是简单可解释，缺点是对同义改写不够宽容。
    # 这正是后续引入 Source Fact Ledger 时需要替换/增强的地方。
    missing = [fact for fact in _required_facts(source) if not _contains_fact(fact, text)]
    issues = [f"来源事实缺失：{fact}" for fact in missing]
    return (5 if not missing else max(1, 5 - len(missing))), issues


def _score_rich_text(
    profile: StyleProfile, hashtags: list[str], body: str
) -> tuple[int, list[str]]:
    low, high = profile.rich_text.tag_count_range
    issues: list[str] = []
    count = len(hashtags)
    score = 5 if low <= count <= high else 3
    if not low <= count <= high:
        issues.append(f"话题数量 {count} 超出档案范围 {low}-{high}")
    if len(_EMOJI.findall(body)) > 6:
        issues.append("emoji 数量过多")
    return score, issues


def _tag_matches(tag: str, topic: str) -> bool:
    clean_topic = topic.strip()
    if not clean_topic:
        return False
    return clean_topic in tag or tag in clean_topic


def _compact(value: str) -> str:
    return re.sub(r"[\s，。！？、,.!?；;：:（）()\[\]【】]", "", value)


def _topic_tag(topic: str) -> str:
    clean = re.sub(r"[\s，。！？、,.!?；;：:（）()\[\]【】#]", "", topic)
    return clean[:24] or "真实记录"
