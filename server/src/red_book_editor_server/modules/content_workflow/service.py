from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID, uuid4

from pydantic import BaseModel, ValidationError

from red_book_editor_server.domain.agent import (
    AgentFailureCode,
    AgentPhase,
    AgentRunDiagnostics,
    AgentRunError,
    AgentRunStatus,
    AgentRuntime,
    AgentRuntimeEvent,
    AgentTraceStep,
    FinalValidation,
)
from red_book_editor_server.domain.contracts import (
    AccountProfileDto,
    AgentTraceStepDto,
    ContentBriefDto,
    ContentColumnDto,
    EditableField,
    FieldSuggestionDto,
    NoteDraftDto,
    SourceExperienceDto,
    StyledNoteResponseDto,
    StyleForm,
    UserResultProjectionDto,
)
from red_book_editor_server.domain.ports import (
    AccountColumnContextPort,
    ContentGenerator,
    ModelGateway,
    ModelGatewayError,
)
from red_book_editor_server.domain.strategy import DomainStrategyPack, DomainStrategyRegistry
from red_book_editor_server.modules.content_workflow.fact_ledger import (
    content_digest,
    field_digest,
)
from red_book_editor_server.modules.content_workflow.generator import (
    ContentGenerationError,
    StubContentGenerator,
    _material_clauses,
    generate_with_retry,
    normalize_content_brief,
    rewrite_material_clause,
)
from red_book_editor_server.modules.content_workflow.review import (
    project_user_issue,
    review_draft,
    status_for_review,
)
from red_book_editor_server.modules.content_workflow.styling.agent import (
    _material_context,
    finalize_to_note_draft,
    style_draft,
)
from red_book_editor_server.modules.content_workflow.styling.models import (
    BodyFieldResult,
    CoverCopyFieldResult,
    FinalizeArgs,
    HashtagsFieldResult,
    TitleFieldResult,
)
from red_book_editor_server.modules.content_workflow.styling.quality import (
    enrichment_issues,
    source_overlap_issues,
)

FieldName = Literal["title", "body", "hashtags", "cover_copy"]


class WorkflowContextError(RuntimeError):
    """账号或栏目上下文不存在、归属不正确或已停用。"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class StyleFormRequiredError(RuntimeError):
    """旧草稿没有表达形式，字段重生成无法安全推断。"""


@dataclass(frozen=True)
class WorkflowResult:
    draft: NoteDraftDto
    agent_trace: list[AgentTraceStepDto]
    diagnostics: AgentRunDiagnostics | None = None

    def as_response(self) -> StyledNoteResponseDto:
        return StyledNoteResponseDto(
            draft=self.draft,
            user_result=UserResultProjectionDto.from_draft(self.draft),
            agent_trace=self.agent_trace,
        )


class ContentWorkflowService:
    """生成、审核和状态计算的共享应用服务。

    该类只依赖领域端口和模型网关，不依赖 FastAPI、SQLAlchemy 或具体 ORM。
    """

    def __init__(
        self,
        *,
        context: AccountColumnContextPort | None = None,
        model_provider: str = "stub",
        gateway: ModelGateway | None = None,
        generator: ContentGenerator | None = None,
        strategy_registry: DomainStrategyRegistry | None = None,
    ) -> None:
        self._context = context
        self._model_provider = model_provider
        self._gateway = gateway
        self._generator = generator or StubContentGenerator()
        self._strategies = strategy_registry or DomainStrategyRegistry()

    async def generate(
        self,
        *,
        account_id: UUID,
        column_id: UUID,
        brief: ContentBriefDto | None = None,
        source: SourceExperienceDto | None = None,
        form: StyleForm,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
        event_sink: Callable[[AgentRuntimeEvent], Awaitable[None]] | None = None,
    ) -> WorkflowResult:
        # 生成流程先检查取消，再加载账号/栏目上下文；只有通过上下文校验，
        # Agent 才能拿到正确的表达边界。模型生成和 stub 生成最终都会汇合到同一审核出口。
        if cancel_check is not None and await cancel_check():
            raise AgentRunError(
                "agent_cancelled",
                [],
                diagnostics=AgentRunDiagnostics(
                    status=AgentRunStatus.CANCELLED,
                    phase=AgentPhase.COLLECT_CONTEXT,
                    failure_code=AgentFailureCode.CANCELLED,
                ),
            )
        content_brief, legacy_source = _normalize_request_brief(brief=brief, source=source)
        account, column = await self._load_context(account_id, column_id)
        strategy = self._strategies.resolve(account.domain_id if account else "parenting")
        strategy.validate_brief(content_brief)
        if self._model_provider == "deepseek":
            # 真实模型路径由 styling Agent 负责工具循环和结构化输出，
            # 本服务只负责把领域上下文传入，并把最终参数转换成 NoteDraft。
            finalized, trace, diagnostics = await self._style(
                brief=content_brief,
                neutral_draft=None,
                form=form,
                account_context=_account_context(account),
                column_context=strategy.generation_context(
                    content_brief,
                    account,
                    column.description if column else "",
                ),
                cancel_check=cancel_check,
                event_sink=event_sink,
            )
            draft = finalize_to_note_draft(
                finalized,
                account_id=account_id,
                column_id=column_id,
                brief=content_brief,
                source=legacy_source,
            )
            draft = draft.model_copy(update={"domain_id": strategy.descriptor.domain_id})
        else:
            # stub 只用于本地开发和测试，不模拟模型行为；但仍补齐 style_form，
            # 这样后续审核、保存和字段重生成与真实模型路径保持同一契约。
            draft = await generate_with_retry(
                self._generator,
                legacy_source or content_brief,
                account_id=account_id,
                column_id=column_id,
            )
            draft = draft.model_copy(
                update={
                    "style_form": form,
                    "domain_id": strategy.descriptor.domain_id,
                    "content_brief": draft.content_brief or content_brief,
                    "source": draft.source or legacy_source,
                }
            )
            trace = _stub_trace("MODEL_PROVIDER=stub：未调用模型，返回中性草稿")
            diagnostics = AgentRunDiagnostics(
                status=AgentRunStatus.COMPLETED,
                phase=AgentPhase.DRAFT,
                steps=0,
            )
        if cancel_check is not None and await cancel_check():
            # 生成完成后再次检查取消，避免用户在审核前取消却仍把结果当成成功返回。
            raise AgentRunError(
                "agent_cancelled",
                [],
                diagnostics=AgentRunDiagnostics(
                    status=AgentRunStatus.CANCELLED,
                    phase=AgentPhase.SAFETY_REVIEW,
                    failure_code=AgentFailureCode.CANCELLED,
                ),
            )
        return await self._reviewed_result(draft, trace, strategy=strategy, diagnostics=diagnostics)

    async def restyle(self, draft: NoteDraftDto, form: StyleForm) -> WorkflowResult:
        if self._model_provider == "deepseek":
            finalized, trace, diagnostics = await self._style(
                brief=_brief_for_draft(draft),
                neutral_draft=draft,
                form=form,
            )
            candidate = finalize_to_note_draft(
                finalized,
                account_id=draft.account_id,
                column_id=draft.column_id,
                brief=_brief_for_draft(draft),
                source=draft.source,
                note_id=draft.note_id,
            )
            candidate = candidate.model_copy(update={"domain_id": draft.domain_id})
        else:
            values: dict[str, object] = {}
            for field_name in ("title", "body", "hashtags", "cover_copy"):
                values.update(_generate_stub_field(draft, field_name, form))
            candidate = draft.model_copy(update={**values, "style_form": form})
            trace = _stub_trace("MODEL_PROVIDER=stub：未调用模型，按当前素材重新组织草稿")
            diagnostics = AgentRunDiagnostics(
                status=AgentRunStatus.COMPLETED,
                phase=AgentPhase.DRAFT,
                steps=0,
            )
        strategy = self._strategies.resolve(draft.domain_id)
        return await self._reviewed_result(
            candidate, trace, strategy=strategy, diagnostics=diagnostics
        )

    async def regenerate_field(
        self,
        draft: NoteDraftDto,
        field: FieldName,
        form: StyleForm | None = None,
    ) -> FieldSuggestionDto:
        # 字段重生成只产生候选，不直接修改当前草稿；客户端必须显式采纳或拒绝。
        # form 缺失时不能安全推断风格，因此宁可返回冲突，也不使用默认值悄悄生成。
        effective_form = form or draft.style_form
        if effective_form is None:
            raise StyleFormRequiredError("style_form_required")
        if self._model_provider == "deepseek":
            values = await self._generate_field_with_model(draft, field, effective_form)
        else:
            values = _generate_stub_field(draft, field, effective_form)
        # 只在内存中的候选草稿覆盖请求字段；来源事实、用户编辑过的其余字段
        # 和表达形式都沿用原草稿。HTTP 响应不会把这个完整草稿返回给客户端。
        candidate = draft.model_copy(
            update={**values, "style_form": effective_form, "updated_at": datetime.now(UTC)}
        )
        strategy = self._strategies.resolve(draft.domain_id)
        review = await review_draft(candidate, strategy=strategy)
        normalized_field = EditableField(field)
        field_claims = [
            item
            for item in review.claim_audit
            if _normalize_audit_field(item.field) == normalized_field.value
        ]
        evidence = [text for item in field_claims for text in item.evidence]
        evidence_fact_ids = [fact_id for item in field_claims for fact_id in item.evidence_fact_ids]
        return FieldSuggestionDto(
            suggestion_id=uuid4(),
            note_id=draft.note_id,
            field=normalized_field,
            value=_field_value(candidate, normalized_field),
            base_field_digest=field_digest(draft, normalized_field),
            base_content_digest=content_digest(draft),
            review=review,
            evidence=list(dict.fromkeys(evidence)),
            evidence_fact_ids=list(dict.fromkeys(evidence_fact_ids)),
            created_at=datetime.now(UTC),
        )

    async def _load_context(
        self, account_id: UUID, column_id: UUID
    ) -> tuple[AccountProfileDto | None, ContentColumnDto | None]:
        if self._context is None:
            return None, None
        account = await self._context.get_account(account_id)
        if account is None:
            raise WorkflowContextError("account_not_found")
        column = await self._context.get_column(account_id, column_id)
        if column is None or not column.enabled:
            raise WorkflowContextError("column_not_found")
        return account, column

    async def _reviewed_result(
        self,
        draft: NoteDraftDto,
        trace: list[AgentTraceStepDto],
        *,
        strategy: DomainStrategyPack,
        diagnostics: AgentRunDiagnostics | None = None,
    ) -> WorkflowResult:
        # 所有生成入口在返回前都经过同一个 Fact Ledger / Claim Audit 审核出口，
        # 防止主生成、重写和 stub 路径各自维护一套不同的状态判断。
        review = await review_draft(draft, strategy=strategy)
        trace = [
            *trace,
            AgentTraceStepDto(
                order=(trace[-1].order + 1) if trace else 1,
                kind="phase",
                label=AgentPhase.SAFETY_REVIEW.value,
                summary="统一事实与安全审核完成",
                phase=AgentPhase.SAFETY_REVIEW.value,
            ),
        ]
        reviewed = draft.model_copy(
            update={
                "review": review,
                "status": status_for_review(review, draft),
                "user_issue": project_user_issue(review, strategy=strategy),
            }
        )
        return WorkflowResult(draft=reviewed, agent_trace=trace, diagnostics=diagnostics)

    async def _style(
        self,
        *,
        brief: ContentBriefDto | SourceExperienceDto,
        neutral_draft: NoteDraftDto | None,
        form: StyleForm,
        account_context: str = "",
        column_context: str = "",
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
        event_sink: Callable[[AgentRuntimeEvent], Awaitable[None]] | None = None,
    ) -> tuple[FinalizeArgs, list[AgentTraceStepDto], AgentRunDiagnostics]:
        if self._gateway is None:
            raise ContentGenerationError("model_gateway_missing")
        try:
            result = await style_draft(
                self._gateway,
                brief=brief,
                neutral_draft=neutral_draft,
                form=form,
                account_context=account_context,
                column_context=column_context,
                cancel_check=cancel_check,
                event_sink=event_sink,
            )
        except AgentRunError as error:
            raise ContentGenerationError("content_generation_failed", agent_error=error) from error
        except ModelGatewayError as error:
            raise ContentGenerationError("content_generation_failed") from error
        if not isinstance(result.result, FinalizeArgs):
            raise ContentGenerationError("content_generation_failed")
        return result.result, [_trace_dto(step) for step in result.trace], result.diagnostics

    async def _generate_field_with_model(
        self, draft: NoteDraftDto, field: FieldName, form: StyleForm
    ) -> dict[str, object]:
        if self._gateway is None:
            raise ContentGenerationError("model_gateway_missing")
        # 请求中携带完整草稿是为了让模型理解上下文，但输出 schema 只允许目标字段；
        # 服务端随后还会把候选合并回内存副本并重新审核，不能把 prompt 约束当成安全边界。
        schema = {
            "title": '{"title_candidates":["..."]}',
            "body": '{"body":"..."}',
            "hashtags": '{"hashtags":["#..."]}',
            "cover_copy": '{"cover_copy":"..."}',
        }[field]
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "你只负责重生成指定的一个笔记字段。ContentBrief 中的 raw_material 是粗略素材，"
                    "只能使用其中的事实，但必须重新组织语言；如果目标字段是正文，第一段不得直接复制素材，"
                    f"表达形式为 {form.value}。只输出合法 JSON，格式为 {schema}，不要输出其他字段。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "field": field,
                        "content_brief": _brief_for_draft(draft).model_dump(mode="json"),
                        "material_context": _material_context(_brief_for_draft(draft)),
                        "draft": draft.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        def validate(content: str) -> FinalValidation:
            if not content:
                return FinalValidation(ok=False, error="empty_model_response")
            try:
                payload = json.loads(_extract_json(content))
            except (json.JSONDecodeError, ValueError) as error:
                return FinalValidation(ok=False, error=f"invalid_field_json:{type(error).__name__}")
            try:
                result: BaseModel
                if field == "title":
                    result = TitleFieldResult.model_validate(payload)
                elif field == "body":
                    result = BodyFieldResult.model_validate(payload)
                elif field == "hashtags":
                    result = HashtagsFieldResult.model_validate(payload)
                else:
                    result = CoverCopyFieldResult.model_validate(payload)
            except (ValidationError, ValueError) as error:
                return FinalValidation(
                    ok=False, error=f"invalid_field_schema:{type(error).__name__}"
                )
            if field == "body" and isinstance(result, BodyFieldResult):
                brief = _brief_for_draft(draft)
                quality_issues = [
                    *enrichment_issues(brief, result.body),
                    *source_overlap_issues(brief, result.body),
                ]
                if quality_issues:
                    return FinalValidation(ok=False, error="；".join(quality_issues))
            return FinalValidation(ok=True, result=result)

        try:
            runtime = AgentRuntime(
                self._gateway,
                max_steps=4,
                max_revisions=2,
                max_tool_calls=0,
                max_same_error=2,
                stage_timeout_seconds=120,
            )
            run = await runtime.run(
                system=messages[0]["content"] if isinstance(messages[0]["content"], str) else "",
                user=messages[1]["content"] if isinstance(messages[1]["content"], str) else "",
                tools=[],
                final_validator=validate,
            )
            if not isinstance(run.result, BaseModel):
                raise ValueError("field_result_missing")
            return cast(dict[str, object], run.result.model_dump())
        except (AgentRunError, ModelGatewayError, ValidationError, ValueError) as error:
            raise ContentGenerationError("field_generation_failed") from error


def _generate_stub_field(
    draft: NoteDraftDto, field: FieldName, form: StyleForm
) -> dict[str, object]:
    brief = _brief_for_draft(draft)
    focus = brief.focus
    if field == "title":
        return {
            "title_candidates": [
                f"{focus}｜这次经历，我想完整记录下来",
                f"{focus}：把过程、选择和变化写清楚",
                f"关于{focus}，一篇不删细节的真实记录",
            ]
        }
    if field == "body":
        clauses = _material_clauses(brief.raw_material)
        detail_lines = "\n".join(
            f"{index}. {rewrite_material_clause(clause)}"
            for index, clause in enumerate(clauses, start=1)
        )
        return {
            "body": (
                f"围绕{focus}，这次先从已经发生的事实和明确观察开始整理。\n\n"
                f"记录中的信息点：\n{detail_lines}\n\n"
                f"这些内容共同组成了{focus}的记录主线；没有提供的经历和结果不额外补写。"
            ).strip()
        }
    if field == "hashtags":
        clean_focus = "".join(
            character
            for character in focus
            if character not in " \t\n，。！？、,.!?；;：:（）()[]【】"
        )
        return {
            "hashtags": [
                f"#{clean_focus[:24] or '真实记录'}",
                "#真实记录",
                "#生活分享",
                "#经验分享",
            ]
        }
    return {"cover_copy": f"{focus}\n这次经历完整记录"}


def _field_value(draft: NoteDraftDto, field: EditableField) -> str | list[str]:
    if field is EditableField.TITLE:
        return draft.title_candidates
    if field is EditableField.BODY:
        return draft.body
    if field is EditableField.HASHTAGS:
        return draft.hashtags
    return draft.cover_copy


def _normalize_audit_field(field: str) -> str:
    if field.startswith("title_candidates"):
        return EditableField.TITLE.value
    if field.startswith("hashtags"):
        return EditableField.HASHTAGS.value
    return field


def _account_context(account: AccountProfileDto | None) -> str:
    if account is None:
        return ""
    boundaries = "、".join(account.boundaries) or "无"
    expressions = "、".join(account.common_expressions) or "无"
    age = (
        f"月龄范围：{account.age_range_months[0]}-{account.age_range_months[1]}个月；"
        if account.age_range_months
        else ""
    )
    month = (
        f"当前月龄：{account.current_baby_month}；"
        if account.current_baby_month is not None
        else ""
    )
    return f"领域：{account.domain_id}；定位：{account.positioning}；{age}{month}语气：{account.tone}；边界：{boundaries}；常用表达：{expressions}"


def _brief_for_draft(draft: NoteDraftDto) -> ContentBriefDto:
    if draft.content_brief is not None:
        return draft.content_brief
    if draft.source is not None:
        return ContentBriefDto.from_legacy_source(draft.source)
    raise ValueError("content_brief_or_source_required")


def _normalize_request_brief(
    *,
    brief: ContentBriefDto | None,
    source: SourceExperienceDto | None,
) -> tuple[ContentBriefDto, SourceExperienceDto | None]:
    if brief is None and source is None:
        raise ValueError("content_brief_required")
    if brief is not None and source is not None:
        # 新请求优先使用通用 brief，但仍保留 legacy source 供旧草稿回溯。
        normalized, _ = normalize_content_brief(brief)
        return normalized, source
    normalized, legacy = normalize_content_brief(brief or source)  # type: ignore[arg-type]
    return normalized, legacy


def _stub_trace(message: str) -> list[AgentTraceStepDto]:
    return [AgentTraceStepDto(order=1, kind="phase", label="stub_fallback", summary=message)]


def _trace_dto(step: AgentTraceStep) -> AgentTraceStepDto:
    return AgentTraceStepDto(
        order=step.order,
        kind=step.kind,
        label=step.label,
        summary=step.summary,
        phase=step.phase.value if step.phase else None,
    )


def _extract_json(content: str) -> str:
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
    return stripped[start : end + 1] if start >= 0 and end > start else stripped
