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
    NoteDraftDto,
    NoteStatus,
    SourceExperienceDto,
    StyleForm,
    StyleProfile,
)
from red_book_editor_server.domain.ports import ModelGateway
from red_book_editor_server.modules.content_workflow.styling.decorator import (
    apply_decorator,
    check_facts,
)
from red_book_editor_server.modules.content_workflow.styling.models import FinalizeArgs
from red_book_editor_server.modules.content_workflow.styling.profiles import load_style_profile
from red_book_editor_server.modules.content_workflow.styling.tools import build_styling_tools

SYSTEM_PROMPT = (
    # 这是业务 Agent 的“行为合同”：模型可以自由组织语言，
    # 但必须遵守事实边界、工具顺序和最终 JSON 结构。
    "你是一位资深的小红书育儿内容运营专家，负责把用户的中性草稿改写成"
    "符合所选表达形式的小红书风格文案。\n\n"
    "规则：\n"
    "1. 事实底线：只能使用用户提供的 SourceExperience 中的事实，不得编造"
    "专家观点、医院诊断、结果、时间线或任何用户未提供的经历；"
    '"就医红线""及时就医"等通用提醒可以写，但不得伪造"医生说"'
    '"崔玉涛说"等具体背书。\n'
    "2. 必须先调用 load_style_profile 读取所选表达形式的风格档案，"
    "严格按档案的钩子、结构、语气、富文本与封面规则写作。\n"
    "3. 起草内容时调用 critique_draft（draft 必须包含 topic_angle、"
    "title_candidates、body、hashtags、cover_copy，source 原样传入）；"
    "critique 返回 passed=false 时，按 issues 修订后再次调用 critique_draft，"
    "最多修订 2 轮。\n"
    "4. 可以调用 suggest_tags 获取话题建议，最终话题数量必须落在档案"
    " tag_count_range 内。\n"
    "5. 只有 critique passed=true 后才能调用 finalize_note 确认内容，"
    "然后以与 finalize_note 入参相同结构的 JSON 对象作为最终回答。\n"
    '6. 最终回答必须是合法 JSON：{"form": "...", "draft": {...},'
    ' "image_suggestions": [...]}。'
)


async def style_draft(
    gateway: ModelGateway,
    *,
    source: SourceExperienceDto,
    neutral_draft: NoteDraftDto | None,
    form: StyleForm,
    account_context: str = "",
    column_context: str = "",
    cancel_check: Callable[[], Awaitable[bool]] | None = None,
    event_sink: Callable[[AgentRuntimeEvent], Awaitable[None]] | None = None,
) -> AgentRunResult:
    # 这里是业务 Agent 的入口：准备业务上下文和工具；真正的通用循环
    # 放在 domain/agent.py，因此“写育儿文案”和“如何循环”彼此解耦。
    profile = load_style_profile(form)
    runtime = AgentRuntime(
        gateway,
        max_steps=12,
        max_revisions=2,
        max_tool_calls=12,
        max_same_error=2,
        stage_timeout_seconds=120,
    )
    return await runtime.run(
        system=SYSTEM_PROMPT,
        user=_build_user_prompt(
            source=source,
            neutral_draft=neutral_draft,
            form=form,
            profile_display=profile.display_name,
            account_context=account_context,
            column_context=column_context,
        ),
        tools=build_styling_tools(),
        final_validator=_make_final_validator(source, profile),
        cancel_check=cancel_check,
        event_sink=event_sink,
    )


def finalize_to_note_draft(
    finalized: FinalizeArgs,
    *,
    account_id: UUID,
    column_id: UUID,
    source: SourceExperienceDto,
    note_id: UUID | None = None,
) -> NoteDraftDto:
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
        source=source,
        style_form=finalized.form,
        review=None,
        updated_at=datetime.now(UTC),
    )


def _build_user_prompt(
    *,
    source: SourceExperienceDto,
    neutral_draft: NoteDraftDto | None,
    form: StyleForm,
    profile_display: str,
    account_context: str,
    column_context: str,
) -> str:
    # system prompt 规定 Agent 的行为；这里的 user prompt 提供本次请求的数据。
    # 二者分开后，换账号/栏目/经历不会修改全局规则。
    parts = [
        f"表达形式：{profile_display}（{form.value}）",
        f"账号定位：{account_context or '备孕-孕检-育儿全程记录的新手爸妈账号'}",
        f"栏目说明：{column_context or '无'}",
        f"用户真实经历（SourceExperience）：\n{source.model_dump_json(indent=2)}",
    ]
    if neutral_draft is not None:
        parts.append(
            f"已有中性草稿（可参考，可完全重写）：\n{neutral_draft.model_dump_json(indent=2)}"
        )
    parts.append("请先调用 load_style_profile 开始。")
    return "\n\n".join(parts)


def _make_final_validator(
    source: SourceExperienceDto, profile: StyleProfile
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
        ok, issues = check_facts(source, decorated.draft)
        if not ok:
            return FinalValidation(ok=False, error="；".join(issues))
        return FinalValidation(ok=True, result=decorated)

    return validate


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
