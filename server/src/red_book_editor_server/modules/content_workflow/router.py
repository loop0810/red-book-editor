from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from red_book_editor_server.app.config import get_settings
from red_book_editor_server.app.dependencies import build_model_gateway, database_session
from red_book_editor_server.domain.contracts import (
    FieldSuggestionDto,
    NoteDraftDto,
    SourceExperienceDto,
    SuggestionStatusUpdateDto,
    StyledNoteResponseDto,
    StyleForm,
)
from red_book_editor_server.domain.ports import ModelGatewayError
from red_book_editor_server.infrastructure.repositories import (
    SqlAlchemyAccountColumnContextRepository,
    SqlAlchemyFieldSuggestionRepository,
    SqlAlchemyNoteRepository,
)
from red_book_editor_server.modules.content_workflow.generator import ContentGenerationError
from red_book_editor_server.modules.content_workflow.service import (
    ContentWorkflowService,
    StyleFormRequiredError,
    WorkflowContextError,
)

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
    # form 是历史请求字段；style_form 允许恢复后的客户端显式补齐旧草稿元数据。
    form: StyleForm | None = None
    style_form: StyleForm | None = None

    @property
    def effective_form(self) -> StyleForm | None:
        return self.form or self.style_form


@router.post("/generate", response_model=StyledNoteResponseDto)
async def generate_note(
    request: GenerateNoteRequest,
    session: AsyncSession = Depends(database_session),
) -> StyledNoteResponseDto:
    settings = get_settings()
    service = _build_service(settings, session=session)
    try:
        result = await service.generate(
            account_id=request.account_id,
            column_id=request.column_id,
            source=request.source,
            form=request.form,
        )
        # 主生成入口现在和账号工作台一样持久化 NoteModel + 初始版本，
        # 因此返回的 note_id 可以直接用于保存、列表和恢复。
        persisted = await SqlAlchemyNoteRepository(session).create(result.draft)
    except WorkflowContextError as error:
        raise _context_http_error(error) from error
    except (ContentGenerationError, ModelGatewayError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        ) from error
    return StyledNoteResponseDto(draft=persisted, agent_trace=result.agent_trace)


@router.post("/style", response_model=StyledNoteResponseDto)
async def restyle_note(request: RestyleNoteRequest) -> StyledNoteResponseDto:
    settings = get_settings()
    service = _build_service(settings)
    try:
        result = await service.restyle(request.draft, request.form)
    except (ContentGenerationError, ModelGatewayError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        ) from error
    return result.as_response()


@router.post("/regenerate-field", response_model=FieldSuggestionDto)
async def regenerate_field(
    request: RegenerateFieldRequest,
    session: AsyncSession = Depends(database_session),
) -> FieldSuggestionDto:
    settings = get_settings()
    service = _build_service(settings)
    try:
        suggestion = await service.regenerate_field(
            request.draft,
            request.field,
            request.effective_form,
        )
        try:
            return await SqlAlchemyFieldSuggestionRepository().create(suggestion, session)
        except LookupError:
            # Draft-only callers remain compatible with the original session-only behavior.
            return suggestion
    except StyleFormRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="style_form_required",
        ) from error
    except (ContentGenerationError, ModelGatewayError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        ) from error


@router.get("/{note_id}/suggestions", response_model=list[FieldSuggestionDto])
async def list_suggestions(
    note_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> list[FieldSuggestionDto]:
    suggestions = await SqlAlchemyFieldSuggestionRepository().list_for_note(note_id, session)
    if suggestions is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note_not_found")
    return suggestions


@router.patch(
    "/{note_id}/suggestions/{suggestion_id}",
    response_model=FieldSuggestionDto,
)
async def update_suggestion_status(
    note_id: UUID,
    suggestion_id: UUID,
    payload: SuggestionStatusUpdateDto,
    session: AsyncSession = Depends(database_session),
) -> FieldSuggestionDto:
    try:
        return await SqlAlchemyFieldSuggestionRepository().update_status(
            note_id=note_id,
            suggestion_id=suggestion_id,
            status=payload.status,
            current_field_digest=payload.current_field_digest,
            current_content_digest=payload.current_content_digest,
            session=session,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))


def _build_service(settings: object, session: AsyncSession | None = None) -> ContentWorkflowService:
    # 通过参数传入上下文端口和模型网关，服务本身不感知 HTTP/ORM。
    from red_book_editor_server.app.config import Settings

    if not isinstance(settings, Settings):
        raise TypeError("settings must be Settings")
    context = SqlAlchemyAccountColumnContextRepository(session) if session else None
    gateway = build_model_gateway(settings) if settings.model_provider == "deepseek" else None
    return ContentWorkflowService(
        context=context,
        model_provider=settings.model_provider,
        gateway=gateway,
    )


def _context_http_error(error: WorkflowContextError) -> HTTPException:
    code = error.code
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=code,
    )
