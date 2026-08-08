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
        # stub 分支用于本地开发: 不请求模型, 只生成可编辑的中性草稿。
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
        # 真实模型分支直接进入风格 Agent; Agent 完成后才回到 API 层组装 DTO。
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
    finalized = result.result
    if not isinstance(finalized, FinalizeArgs):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        )
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
