from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from red_book_editor_server.domain.contracts import NoteDraftDto, NoteStatus, SourceExperienceDto
from red_book_editor_server.modules.content_workflow.generator import (
    ContentGenerationError,
    StubContentGenerator,
    generate_with_retry,
)
from red_book_editor_server.modules.content_workflow.review import review_draft

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])


class GenerateNoteRequest(BaseModel):
    account_id: UUID
    column_id: UUID
    source: SourceExperienceDto


class RegenerateFieldRequest(BaseModel):
    draft: NoteDraftDto
    field: Literal["title", "body", "hashtags", "cover_copy"]


@router.post("/generate", response_model=NoteDraftDto)
async def generate_note(request: GenerateNoteRequest) -> NoteDraftDto:
    try:
        draft = await generate_with_retry(
            StubContentGenerator(),
            request.source,
            account_id=request.account_id,
            column_id=request.column_id,
        )
    except ContentGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        ) from error
    review = await review_draft(draft)
    return draft.model_copy(
        update={
            "status": NoteStatus.NEEDS_REVIEW if not review.passed else NoteStatus.READY,
            "review": review,
        }
    )


@router.post("/regenerate-field", response_model=NoteDraftDto)
async def regenerate_field(request: RegenerateFieldRequest) -> NoteDraftDto:
    try:
        generated = await generate_with_retry(
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
    generated_field = {
        "title": "title_candidates",
        "body": "body",
        "hashtags": "hashtags",
        "cover_copy": "cover_copy",
    }[request.field]
    updates: dict[str, object] = {generated_field: getattr(generated, generated_field)}
    updated = request.draft.model_copy(update=updates)
    review = await review_draft(updated)
    return updated.model_copy(
        update={
            "status": NoteStatus.NEEDS_REVIEW if not review.passed else NoteStatus.READY,
            "review": review,
        }
    )
