from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from red_book_editor_server.app.config import get_settings
from red_book_editor_server.app.dependencies import build_model_gateway
from red_book_editor_server.domain.agent import AgentRunError, AgentTraceStep
from red_book_editor_server.domain.contracts import (
    AgentTraceStepDto,
    NoteDraftDto,
    NoteStatus,
    SourceExperienceDto,
    StyledNoteResponseDto,
    StyleForm,
)
from red_book_editor_server.domain.ports import ModelGatewayError
from red_book_editor_server.modules.content_workflow.generator import (
    ContentGenerationError,
    StubContentGenerator,
    generate_with_retry,
)
from red_book_editor_server.modules.content_workflow.styling.agent import (
    finalize_to_note_draft,
    style_draft,
)
from red_book_editor_server.modules.content_workflow.styling.models import FinalizeArgs

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])


class GenerateNoteRequest(BaseModel):
    # 这是 HTTP 层的输入契约：账号/栏目决定上下文，source 是事实，form 是文风。
    account_id: UUID
    column_id: UUID
    form: StyleForm
    source: SourceExperienceDto


class RestyleNoteRequest(BaseModel):
    draft: NoteDraftDto
    form: StyleForm


class RegenerateFieldRequest(BaseModel):
    draft: NoteDraftDto
    field: Literal["title", "body", "hashtags", "cover_copy"]
    form: StyleForm | None = None


@router.post("/generate", response_model=StyledNoteResponseDto)
async def generate_note(request: GenerateNoteRequest) -> StyledNoteResponseDto:
    settings = get_settings()
    if settings.model_provider != "deepseek":
        # stub 分支用于本地开发：不请求模型，只生成可编辑的中性草稿。
        # 这样 Flutter 可以在没有 API key 或网络时先联调页面和数据结构。
        draft = await _neutral_draft(
            account_id=request.account_id,
            column_id=request.column_id,
            source=request.source,
        )
        return StyledNoteResponseDto(
            draft=draft,
            agent_trace=_stub_trace(
                "MODEL_PROVIDER=stub：未调用模型，返回中性草稿（未做风格转换）"
            ),
        )
    try:
        # 真实模型分支进入风格 Agent。
        # Agent 内部负责 prompt、工具循环和最终校验；本路由只负责组装输入和输出。
        result = await style_draft(
            build_model_gateway(settings),
            source=request.source,
            neutral_draft=None,
            form=request.form,
        )
    except (AgentRunError, ModelGatewayError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        ) from error
    # AgentRunResult.result 已经通过 FinalizeArgs 校验；这里再做一次类型检查，
    # 防止未来替换 Agent 实现后把错误对象直接返回给 API 客户端。
    finalized = result.result
    if not isinstance(finalized, FinalizeArgs):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        )
    # FinalizeArgs 是 Agent 内部结构，NoteDraftDto 是对外 API 结构。
    # 这个转换点把账号、栏目、来源和生成内容合并成客户端可编辑的草稿。
    draft = finalize_to_note_draft(
        finalized,
        account_id=request.account_id,
        column_id=request.column_id,
        source=request.source,
    )
    return StyledNoteResponseDto(draft=draft, agent_trace=_trace_dto(result.trace))


@router.post("/style", response_model=StyledNoteResponseDto)
async def restyle_note(request: RestyleNoteRequest) -> StyledNoteResponseDto:
    settings = get_settings()
    if settings.model_provider != "deepseek":
        return StyledNoteResponseDto(
            draft=request.draft,
            agent_trace=_stub_trace("MODEL_PROVIDER=stub：未调用模型，草稿保持不变"),
        )
    try:
        result = await style_draft(
            build_model_gateway(settings),
            source=request.draft.source,
            neutral_draft=request.draft,
            form=request.form,
        )
    except (AgentRunError, ModelGatewayError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        ) from error
    finalized = result.result
    if not isinstance(finalized, FinalizeArgs):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        )
    draft = finalize_to_note_draft(
        finalized,
        account_id=request.draft.account_id,
        column_id=request.draft.column_id,
        source=request.draft.source,
    )
    return StyledNoteResponseDto(draft=draft, agent_trace=_trace_dto(result.trace))


@router.post("/regenerate-field", response_model=NoteDraftDto)
async def regenerate_field(request: RegenerateFieldRequest) -> NoteDraftDto:
    settings = get_settings()
    if settings.model_provider == "deepseek" and request.form is not None:
        # 当前实现会重新生成一份完整风格稿，再从中取出目标字段；
        # field_map + model_copy 确保最终只覆盖用户请求的字段。
        try:
            result = await style_draft(
                build_model_gateway(settings),
                source=request.draft.source,
                neutral_draft=request.draft,
                form=request.form,
            )
        except (AgentRunError, ModelGatewayError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="content_generation_failed",
            ) from error
        finalized = result.result
        if not isinstance(finalized, FinalizeArgs):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="content_generation_failed",
            )
        styled = finalize_to_note_draft(
            finalized,
            account_id=request.draft.account_id,
            column_id=request.draft.column_id,
            source=request.draft.source,
        )
    else:
        try:
            styled = await generate_with_retry(
                StubContentGenerator(),
                request.draft.source,
                account_id=request.draft.account_id,
                column_id=request.draft.column_id,
            )
        except ContentGenerationError as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="content_generation_failed",
            ) from error
    # API 字段名和 NoteDraftDto 属性名不完全相同，因此集中维护映射，
    # 避免把用户传入的 "title" 直接当成 Python 属性读取。
    field_map = {
        "title": "title_candidates",
        "body": "body",
        "hashtags": "hashtags",
        "cover_copy": "cover_copy",
    }
    updates: dict[str, object] = {
        field_map[request.field]: getattr(styled, field_map[request.field])
    }
    updated = request.draft.model_copy(update=updates)
    return updated.model_copy(
        update={
            "status": NoteStatus.READY,
            "review": None,
        }
    )


async def _neutral_draft(
    *,
    account_id: UUID,
    column_id: UUID,
    source: SourceExperienceDto,
) -> NoteDraftDto:
    draft = await generate_with_retry(
        StubContentGenerator(),
        source,
        account_id=account_id,
        column_id=column_id,
    )
    return draft.model_copy(update={"status": NoteStatus.READY, "review": None})


def _stub_trace(message: str) -> list[AgentTraceStepDto]:
    return [
        AgentTraceStepDto(
            order=1,
            kind="phase",
            label="stub_fallback",
            summary=message,
        )
    ]


def _trace_dto(trace: list[AgentTraceStep]) -> list[AgentTraceStepDto]:
    return [
        AgentTraceStepDto(
            order=step.order,
            kind=step.kind,
            label=step.label,
            summary=step.summary,
        )
        for step in trace
    ]
