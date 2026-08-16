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
    ContentColumnDto,
    EditableField,
    FieldSuggestionDto,
    NoteDraftDto,
    SourceExperienceDto,
    StyledNoteResponseDto,
    StyleForm,
)
from red_book_editor_server.domain.ports import (
    AccountColumnContextPort,
    ContentGenerator,
    ModelGateway,
    ModelGatewayError,
)
from red_book_editor_server.modules.content_workflow.generator import (
    ContentGenerationError,
    StubContentGenerator,
    generate_with_retry,
)
from red_book_editor_server.modules.content_workflow.fact_ledger import (
    content_digest,
    field_digest,
)
from red_book_editor_server.modules.content_workflow.review import (
    review_draft,
    status_for_review,
)
from red_book_editor_server.modules.content_workflow.styling.agent import (
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
        return StyledNoteResponseDto(draft=self.draft, agent_trace=self.agent_trace)


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
    ) -> None:
        self._context = context
        self._model_provider = model_provider
        self._gateway = gateway
        self._generator = generator or StubContentGenerator()

    async def generate(
        self,
        *,
        account_id: UUID,
        column_id: UUID,
        source: SourceExperienceDto,
        form: StyleForm,
        cancel_check: Callable[[], Awaitable[bool]] | None = None,
        event_sink: Callable[[AgentRuntimeEvent], Awaitable[None]] | None = None,
    ) -> WorkflowResult:
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
        account, column = await self._load_context(account_id, column_id)
        if self._model_provider == "deepseek":
            finalized, trace, diagnostics = await self._style(
                source=source,
                neutral_draft=None,
                form=form,
                account_context=_account_context(account),
                column_context=column.description if column else "",
                cancel_check=cancel_check,
                event_sink=event_sink,
            )
            draft = finalize_to_note_draft(
                finalized,
                account_id=account_id,
                column_id=column_id,
                source=source,
            )
        else:
            draft = await generate_with_retry(
                self._generator,
                source,
                account_id=account_id,
                column_id=column_id,
            )
            draft = draft.model_copy(update={"style_form": form})
            trace = _stub_trace("MODEL_PROVIDER=stub：未调用模型，返回中性草稿")
            diagnostics = AgentRunDiagnostics(
                status=AgentRunStatus.COMPLETED,
                phase=AgentPhase.DRAFT,
                steps=0,
            )
        if cancel_check is not None and await cancel_check():
            raise AgentRunError(
                "agent_cancelled",
                [],
                diagnostics=AgentRunDiagnostics(
                    status=AgentRunStatus.CANCELLED,
                    phase=AgentPhase.SAFETY_REVIEW,
                    failure_code=AgentFailureCode.CANCELLED,
                ),
            )
        return await self._reviewed_result(draft, trace, diagnostics=diagnostics)

    async def restyle(self, draft: NoteDraftDto, form: StyleForm) -> WorkflowResult:
        if self._model_provider == "deepseek":
            finalized, trace, diagnostics = await self._style(
                source=draft.source,
                neutral_draft=draft,
                form=form,
            )
            candidate = finalize_to_note_draft(
                finalized,
                account_id=draft.account_id,
                column_id=draft.column_id,
                source=draft.source,
                note_id=draft.note_id,
            )
        else:
            candidate = draft.model_copy(update={"style_form": form})
            trace = _stub_trace("MODEL_PROVIDER=stub：未调用模型，保留当前草稿内容")
            diagnostics = AgentRunDiagnostics(
                status=AgentRunStatus.COMPLETED,
                phase=AgentPhase.DRAFT,
                steps=0,
            )
        return await self._reviewed_result(candidate, trace, diagnostics=diagnostics)

    async def regenerate_field(
        self,
        draft: NoteDraftDto,
        field: FieldName,
        form: StyleForm | None = None,
    ) -> FieldSuggestionDto:
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
        review = await review_draft(candidate)
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
        diagnostics: AgentRunDiagnostics | None = None,
    ) -> WorkflowResult:
        review = await review_draft(draft)
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
            update={"review": review, "status": status_for_review(review, draft)}
        )
        return WorkflowResult(draft=reviewed, agent_trace=trace, diagnostics=diagnostics)

    async def _style(
        self,
        *,
        source: SourceExperienceDto,
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
                source=source,
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
                    "你只负责重生成指定的一个笔记字段。只能使用 SourceExperience 中的事实，"
                    f"表达形式为 {form.value}。只输出合法 JSON，格式为 {schema}，不要输出其他字段。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "field": field,
                        "source": draft.source.model_dump(mode="json"),
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
    source = draft.source
    actions = "、".join(source.actions)
    if field == "title":
        return {
            "title_candidates": [
                f"{source.baby_month}个月宝宝的{source.scenario}，{form.value}记录",
                f"记录宝宝{source.scenario}：{actions}",
            ]
        }
    if field == "body":
        return {
            "body": (
                f"宝宝{source.baby_month}个月时，遇到了{source.scenario}。\n"
                f"我当时做了：{actions}。\n{source.observations}"
            ).strip()
        }
    if field == "hashtags":
        return {"hashtags": ["#育儿日常", f"#{source.baby_month}个月宝宝", f"#{source.scenario}"]}
    return {"cover_copy": source.scenario}


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
    return (
        f"定位：{account.positioning}；月龄范围：{account.age_range_months[0]}-"
        f"{account.age_range_months[1]}个月；当前月龄：{account.current_baby_month}；"
        f"语气：{account.tone}；边界：{boundaries}；常用表达：{expressions}"
    )


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
