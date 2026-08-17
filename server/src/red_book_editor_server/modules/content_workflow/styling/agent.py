from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from red_book_editor_server.domain.agent import (
    AgentRunResult,
    AgentRuntime,
    AgentRuntimeEvent,
    FinalValidation,
)
from red_book_editor_server.domain.contracts import (
    ContentBriefDto,
    FactKind,
    NoteDraftDto,
    NoteStatus,
    SourceExperienceDto,
    StyleForm,
    StyleProfile,
)
from red_book_editor_server.domain.ports import ModelGateway
from red_book_editor_server.modules.content_workflow.fact_ledger import build_fact_ledger
from red_book_editor_server.modules.content_workflow.styling.decorator import (
    apply_decorator,
    check_facts,
)
from red_book_editor_server.modules.content_workflow.styling.models import FinalizeArgs
from red_book_editor_server.modules.content_workflow.styling.profiles import load_style_profile
from red_book_editor_server.modules.content_workflow.styling.quality import (
    enrichment_issues,
    source_overlap_issues,
)
from red_book_editor_server.modules.content_workflow.styling.tools import build_styling_tools

SYSTEM_PROMPT = (
    # 这是业务 Agent 的“行为合同”：模型可以自由组织语言，
    # 但必须遵守事实边界、工具顺序和最终 JSON 结构。
    "你是一位资深的小红书内容运营专家，负责把 ContentBrief 改写成"
    "符合账号领域和所选表达形式的小红书风格文案。\n\n"
    "规则：\n"
    "1. 事实底线：只能使用用户提供的 ContentBrief 中的事实，不得编造"
    "专家观点、医院诊断、结果、时间线或任何用户未提供的经历；"
    '"就医红线""及时就医"等通用提醒可以写，但不得伪造"医生说"'
    '"崔玉涛说"等具体背书；风格档案中的示例只是结构提示，不是本次经历的事实。\n'
    "领域安全相关经历只能如实记录用户提供的事情，"
    "不得用安全、放心、适合照做或保证结果的表达包装风险做法。\n"
    "1.1 素材语义：raw_material 是用户的事实便签、关键词或流水账，不是需要原样复用的成稿。"
    "先在内部整理 confirmed/observed/constraint/opinion 等来源单元，再确定 focus 对应的叙事角度和正文结构，"
    "最后从事实单元重新起草；不能把原始第一句话直接当作正文开头。focus 是标题第一优先级，"
    "raw_material 中的限制条件只能作为正文细节，除非 focus 明确要求，不能反客为主成为标题主题。\n"
    "1.2 编辑性丰富边界：可以增加连接句、段落结构、叙事钩子、重新排序和由已知事实直接支持的中性总结；"
    "不得增加用户未提供的具体人物、地点、动作、对话、礼物、结果、时间线、专业背书或真实情绪。"
    "不要通过复制原文来满足正文长度。\n"
    "2. 必须先调用 load_style_profile 读取所选表达形式的风格档案，"
    "严格按档案的钩子、结构、语气、富文本与封面规则写作。\n"
    "3. 起草内容时调用 critique_draft（draft 必须包含 topic_angle、"
    "title_candidates、body、hashtags、cover_copy、image_suggestions，source 原样传入）；"
    "critique 返回 passed=false 时，按 issues 修订后再次调用 critique_draft，"
    "最多修订 2 轮。\n"
    "4. 可以调用 suggest_tags 获取话题建议，最终话题数量必须落在档案"
    " tag_count_range 内。\n"
    "5. 只有 critique passed=true 后才能调用 finalize_note 确认内容，"
    "然后以与 finalize_note 入参相同结构的 JSON 对象作为最终回答。\n"
    "6. 至少给出 3 个围绕 focus 的标题候选；正文要有经过重新组织的开头、过程细节、"
    "真实感受/观察和收束，不得把用户输入拆段后原样粘贴；短素材也要形成完整结构。"
    "封面文案不能只重复 focus；配图建议至少 3 条，必须对应本次素材中的场景、"
    "动作、物件或细节，不能使用‘场景照片/过程记录’这种空泛模板。\n"
    '7. 最终回答必须是合法 JSON：{"form": "...", "draft": {...},'
    ' "image_suggestions": [...]}。'
)
STYLING_PROMPT_VERSION = "styling-system-v2"
STYLING_AGENT_CONFIG_VERSION = "styling-agent-config-v1"
STYLING_AGENT_CONFIG = {
    "max_steps": 12,
    "max_revisions": 2,
    "max_tool_calls": 12,
    "max_same_error": 2,
    "stage_timeout_seconds": 120,
}


async def style_draft(
    gateway: ModelGateway,
    *,
    brief: ContentBriefDto | SourceExperienceDto | None = None,
    source: SourceExperienceDto | None = None,
    neutral_draft: NoteDraftDto | None,
    form: StyleForm,
    account_context: str = "",
    column_context: str = "",
    cancel_check: Callable[[], Awaitable[bool]] | None = None,
    event_sink: Callable[[AgentRuntimeEvent], Awaitable[None]] | None = None,
) -> AgentRunResult:
    # 这里是业务 Agent 的入口：准备业务上下文和工具；真正的通用循环
    # 放在 domain/agent.py，因此“写育儿文案”和“如何循环”彼此解耦。
    active_brief = brief or source
    if active_brief is None:
        raise ValueError("content_brief_required")
    profile = load_style_profile(form)
    runtime = AgentRuntime(
        gateway,
        max_steps=STYLING_AGENT_CONFIG["max_steps"],
        max_revisions=STYLING_AGENT_CONFIG["max_revisions"],
        max_tool_calls=STYLING_AGENT_CONFIG["max_tool_calls"],
        max_same_error=STYLING_AGENT_CONFIG["max_same_error"],
        stage_timeout_seconds=STYLING_AGENT_CONFIG["stage_timeout_seconds"],
    )
    return await runtime.run(
        system=SYSTEM_PROMPT,
        user=_build_user_prompt(
            brief=active_brief,
            neutral_draft=neutral_draft,
            form=form,
            profile_display=profile.display_name,
            rewrite_rules=profile.rewrite_rules,
            account_context=account_context,
            column_context=column_context,
        ),
        tools=build_styling_tools(),
        final_validator=_make_final_validator(active_brief, profile),
        cancel_check=cancel_check,
        event_sink=event_sink,
    )


def finalize_to_note_draft(
    finalized: FinalizeArgs,
    *,
    account_id: UUID,
    column_id: UUID,
    brief: ContentBriefDto | SourceExperienceDto | None = None,
    source: SourceExperienceDto | None = None,
    note_id: UUID | None = None,
) -> NoteDraftDto:
    active_brief = brief or source
    if active_brief is None:
        raise ValueError("content_brief_required")
    return NoteDraftDto(
        note_id=note_id or uuid4(),
        account_id=account_id,
        column_id=column_id,
        status=NoteStatus.READY,
        topic_angle=finalized.draft.topic_angle,
        title_candidates=finalized.draft.title_candidates,
        body=finalized.draft.body,
        hashtags=finalized.draft.hashtags,
        cover_copy=finalized.draft.cover_copy,
        image_suggestions=finalized.image_suggestions,
        content_brief=(
            active_brief
            if isinstance(active_brief, ContentBriefDto)
            else ContentBriefDto.from_legacy_source(active_brief)
        ),
        source=source or (active_brief if isinstance(active_brief, SourceExperienceDto) else None),
        style_form=finalized.form,
        review=None,
        updated_at=datetime.now(UTC),
    )


def _build_user_prompt(
    *,
    brief: ContentBriefDto | SourceExperienceDto,
    neutral_draft: NoteDraftDto | None,
    form: StyleForm,
    profile_display: str,
    rewrite_rules: list[str],
    account_context: str,
    column_context: str,
) -> str:
    # system prompt 规定 Agent 的行为；这里的 user prompt 提供本次请求的数据。
    # 二者分开后，换账号/栏目/经历不会修改全局规则。
    parts = [
        f"表达形式：{profile_display}（{form.value}）",
        f"账号定位：{account_context or '以用户主题和原始素材为中心的内容账号'}",
        f"栏目说明：{column_context or '无'}",
        f"风格专属改写规则：{json.dumps(rewrite_rules, ensure_ascii=False)}",
        "写作任务：先阅读服务端整理的素材理解卡，确认事实、观察、限制和观点，再选择 focus 对应的内容角度和结构。"
        "raw_material 只是粗略素材，不是成稿；请重新组织语言，正文第一段不得直接复制用户输入。"
        "保留关键事实、动作、观察和限制，但不要把用户提供的内容压缩成一句泛泛总结。请输出 3 个以上标题候选、完整正文、"
        "符合主题的话题、带有具体信息的封面文案，以及至少 3 条与本次素材直接对应的配图建议。",
        f"本次内容简报（ContentBrief）：\n{brief.model_dump_json(indent=2)}",
        f"素材理解卡（仅作事实索引，不是正文模板）：\n{_material_context(brief)}",
    ]
    if neutral_draft is not None:
        parts.append(
            f"已有中性草稿（可参考，可完全重写）：\n{neutral_draft.model_dump_json(indent=2)}"
        )
    parts.append("请先调用 load_style_profile 开始。")
    return "\n\n".join(parts)


def _material_context(brief: ContentBriefDto | SourceExperienceDto) -> str:
    """Build a deterministic fact index so the model can rewrite instead of quote."""

    ledger = build_fact_ledger(brief)
    source_facts = [
        {
            "kind": fact.kind.value,
            "text": fact.text,
            "source_path": fact.source_path,
        }
        for fact in ledger.facts
        if fact.kind
        in {
            FactKind.CONFIRMED,
            FactKind.OBSERVED,
            FactKind.OPINION,
            FactKind.CONSTRAINT,
        }
        and fact.fact_id != "brief.raw_material"
    ]
    return json.dumps(
        {
            "focus": brief.focus if isinstance(brief, ContentBriefDto) else brief.scenario,
            "source_units": source_facts,
            "do_not_infer": [
                "未提供的具体活动、人物、地点、对话、结果和时间线",
                "来源外的专业背书、确定因果和普遍适用结论",
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def _make_final_validator(
    brief: ContentBriefDto | SourceExperienceDto, profile: StyleProfile
) -> Callable[[str], FinalValidation]:
    def validate(content: str) -> FinalValidation:
        # 模型的最终回答只是字符串，先解析成 FinalizeArgs，再做服务端确定性检查。
        # 这一步是模型输出进入业务对象前的最后一道闸门：prompt 不是安全边界，
        # validator 才是服务端可以强制执行的边界。
        try:
            finalized = FinalizeArgs.model_validate(json.loads(_extract_json(content)))
        except (json.JSONDecodeError, ValidationError) as error:
            return FinalValidation(ok=False, error=f"结构化输出无法解析：{error}")
        decorated = apply_decorator(finalized, profile)
        ok, issues = check_facts(brief, decorated.draft)
        issues.extend(_quality_issues(brief, decorated, profile))
        if not ok or issues:
            return FinalValidation(ok=False, error="；".join(issues))
        return FinalValidation(ok=True, result=decorated)

    return validate


def _quality_issues(
    brief: ContentBriefDto | SourceExperienceDto,
    finalized: FinalizeArgs,
    profile: StyleProfile,
) -> list[str]:
    """对模型容易偷工减料的用户结果做确定性检查。"""

    draft = finalized.draft
    focus = brief.focus if isinstance(brief, ContentBriefDto) else brief.scenario
    issues: list[str] = []
    if len(draft.title_candidates) < 3:
        issues.append("标题候选至少需要 3 个")
    if not any(_compact(focus) in _compact(title) for title in draft.title_candidates):
        issues.append("标题候选必须明确围绕内容主题")
    if _compact(focus) not in _compact(draft.topic_angle):
        issues.append("选题角度必须明确围绕内容主题")
    issues.extend(enrichment_issues(brief, draft.body))
    issues.extend(source_overlap_issues(brief, draft.body))
    if not draft.cover_copy.strip() or _compact(draft.cover_copy) == _compact(focus):
        issues.append("封面文案不能只重复内容主题")
    if _compact(focus) not in _compact(draft.cover_copy):
        issues.append("封面文案必须包含内容主题并补充具体角度")
    if not any(_compact(focus) in _compact(tag) for tag in draft.hashtags):
        issues.append("至少要有一个话题直接对应内容主题")
    if len(finalized.image_suggestions) < 3:
        issues.append("配图建议至少需要 3 条具体建议")
    if not any(_compact(focus) in _compact(item) for item in finalized.image_suggestions):
        issues.append("至少要有一条配图建议直接对应内容主题")
    low, high = profile.rich_text.tag_count_range
    if not low <= len(draft.hashtags) <= high:
        issues.append(f"话题数量必须在 {low}-{high} 个之间")
    return issues


def _compact(value: str) -> str:
    return "".join(
        character for character in value if character not in " \t\n，。！？、,.!?；;：:（）()[]【】"
    )


def _extract_json(content: str) -> str:
    """接受模型常见的 ```json 包裹或前后说明文字。"""

    # 模型有时会在 JSON 前后附加解释或 Markdown fence；先剥离包装，
    # 再交给 Pydantic 做严格结构校验，而不是直接信任整段文本。
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped
