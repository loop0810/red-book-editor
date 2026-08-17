from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from red_book_editor_server.app.config import get_settings
from red_book_editor_server.app.dependencies import build_model_gateway, database_session
from red_book_editor_server.domain.contracts import (
    AssetDto,
    ContentBriefDto,
    DraftVersionDto,
    NoteDraftDto,
    NoteStatus,
    PublishRecordDto,
    ReviewResultDto,
    SourceExperienceDto,
    StyleForm,
    UserFacingIssueDto,
)
from red_book_editor_server.domain.ports import ModelGatewayError
from red_book_editor_server.domain.strategy import DomainStrategyRegistry
from red_book_editor_server.infrastructure.models import (
    AccountModel,
    AssetModel,
    DraftVersionModel,
    NoteModel,
    PublishRecordModel,
)
from red_book_editor_server.infrastructure.repositories import (
    SqlAlchemyAccountColumnContextRepository,
    SqlAlchemyNoteRepository,
)
from red_book_editor_server.modules.content_workflow.generator import ContentGenerationError
from red_book_editor_server.modules.content_workflow.review import (
    project_user_issue,
    review_draft,
    review_matches_draft,
    status_for_review,
)
from red_book_editor_server.modules.content_workflow.service import (
    ContentWorkflowService,
    WorkflowContextError,
)

router = APIRouter(tags=["notes"])


class CreateNoteRequest(BaseModel):
    column_id: UUID
    form: StyleForm | None = None
    style_form: StyleForm | None = None
    content_brief: ContentBriefDto | None = None
    source: SourceExperienceDto | None = None

    @model_validator(mode="after")
    def require_content_input(self) -> "CreateNoteRequest":
        if self.content_brief is None and self.source is None:
            raise ValueError("content_brief_required")
        return self


class PublishRecordInput(BaseModel):
    status: NoteStatus
    published_at: datetime | None = None
    link: str | None = None
    notes: str = ""
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)


class ReorderAssetsRequest(BaseModel):
    asset_ids: list[UUID] = Field(min_length=1)


class UpdateNoteRequest(BaseModel):
    topic_angle: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cover_copy: str = ""
    image_suggestions: list[str] = Field(default_factory=list)
    style_form: StyleForm | None = None


@router.post("/api/v1/accounts/{account_id}/assets", response_model=dict[str, str], status_code=201)
async def upload_asset(
    account_id: UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(database_session),
) -> dict[str, str]:
    account = await session.get(AccountModel, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="account_not_found")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="image_required"
        )
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="asset_too_large"
        )
    asset_id = uuid4()
    safe_filename = Path(file.filename or "asset").name
    storage_key = f"{account_id}/{asset_id}/{safe_filename}"
    storage_path = get_settings().storage_root / storage_key
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_bytes(contents)
    record = AssetModel(
        id=asset_id,
        account_id=account_id,
        filename=safe_filename,
        content_type=file.content_type,
        storage_key=storage_key,
    )
    session.add(record)
    await session.commit()
    return {"asset_id": str(asset_id), "storage_key": storage_key}


@router.get("/api/v1/accounts/{account_id}/assets", response_model=list[AssetDto])
async def list_assets(
    account_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> list[AssetDto]:
    result = await session.execute(
        select(AssetModel).where(AssetModel.account_id == account_id).order_by(AssetModel.position)
    )
    return [
        AssetDto(
            asset_id=asset.id,
            account_id=asset.account_id,
            filename=asset.filename,
            content_type=asset.content_type,
            position=asset.position,
        )
        for asset in result.scalars()
    ]


@router.put("/api/v1/accounts/{account_id}/assets/order", response_model=list[AssetDto])
async def reorder_assets(
    account_id: UUID,
    request: ReorderAssetsRequest,
    session: AsyncSession = Depends(database_session),
) -> list[AssetDto]:
    records = list(
        (
            await session.execute(
                select(AssetModel).where(
                    AssetModel.account_id == account_id,
                    AssetModel.id.in_(request.asset_ids),
                )
            )
        ).scalars()
    )
    by_id = {asset.id: asset for asset in records}
    if len(by_id) != len(request.asset_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset_not_found")
    for position, asset_id in enumerate(request.asset_ids):
        by_id[asset_id].position = position
    await session.commit()
    return [
        AssetDto(
            asset_id=asset.id,
            account_id=asset.account_id,
            filename=asset.filename,
            content_type=asset.content_type,
            position=asset.position,
        )
        for asset in sorted(records, key=lambda asset: asset.position)
    ]


@router.get("/api/v1/assets/{asset_id}")
async def download_asset(
    asset_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> FileResponse:
    asset = await session.get(AssetModel, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset_not_found")
    path = get_settings().storage_root / asset.storage_key
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset_file_not_found")
    return FileResponse(path, media_type=asset.content_type, filename=asset.filename)


@router.delete("/api/v1/assets/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> None:
    asset = await session.get(AssetModel, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset_not_found")
    path = get_settings().storage_root / asset.storage_key
    path.unlink(missing_ok=True)
    await session.delete(asset)
    await session.commit()


def note_dto(note: NoteModel) -> NoteDraftDto:
    content = note.content
    review = ReviewResultDto.model_validate(note.review) if note.review else None
    draft = NoteDraftDto(
        note_id=note.id,
        account_id=note.account_id,
        column_id=note.column_id,
        status=NoteStatus(note.status),
        domain_id=content.get("domain_id", "parenting"),
        topic_angle=content.get("topic_angle", ""),
        title_candidates=content.get("title_candidates", []),
        body=content.get("body", ""),
        hashtags=content.get("hashtags", []),
        cover_copy=content.get("cover_copy", ""),
        image_suggestions=content.get("image_suggestions", []),
        content_brief=ContentBriefDto.model_validate(content["content_brief"])
        if content.get("content_brief")
        else None,
        source=SourceExperienceDto.model_validate(note.source)
        if "baby_month" in note.source
        else None,
        style_form=StyleForm(content["style_form"])
        if content.get("style_form") is not None
        else None,
        review=review,
        user_issue=(
            UserFacingIssueDto.model_validate(content["user_issue"])
            if content.get("user_issue")
            else None
        ),
        updated_at=note.updated_at or datetime.now(UTC),
    )
    stored_status = NoteStatus(note.status)
    if stored_status in (NoteStatus.DRAFT, NoteStatus.NEEDS_REVIEW, NoteStatus.READY):
        draft = draft.model_copy(update={"status": status_for_review(review, draft)})
    return draft


@router.post(
    "/api/v1/accounts/{account_id}/notes",
    response_model=NoteDraftDto,
    response_model_exclude={"review"},
    status_code=201,
)
async def create_note(
    account_id: UUID,
    request: CreateNoteRequest,
    session: AsyncSession = Depends(database_session),
) -> NoteDraftDto:
    settings = get_settings()
    try:
        service = ContentWorkflowService(
            context=SqlAlchemyAccountColumnContextRepository(session),
            model_provider=settings.model_provider,
            gateway=(
                build_model_gateway(settings) if settings.model_provider == "deepseek" else None
            ),
        )
        result = await service.generate(
            account_id=account_id,
            column_id=request.column_id,
            brief=request.content_brief,
            source=request.source,
            form=request.form or request.style_form or StyleForm.EXPERIENCE,
        )
        return await SqlAlchemyNoteRepository(session).create(result.draft)
    except WorkflowContextError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error.code) from error
    except (ContentGenerationError, ModelGatewayError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="content_generation_failed",
        ) from error


@router.get(
    "/api/v1/notes/{note_id}",
    response_model=NoteDraftDto,
    response_model_exclude={"review"},
)
async def get_note(
    note_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> NoteDraftDto:
    note = await session.get(NoteModel, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note_not_found")
    return note_dto(note)


@router.get(
    "/api/v1/accounts/{account_id}/notes",
    response_model=list[NoteDraftDto],
    response_model_exclude={"review"},
)
async def list_account_notes(
    account_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> list[NoteDraftDto]:
    result = await session.execute(
        select(NoteModel)
        .where(NoteModel.account_id == account_id)
        .order_by(NoteModel.updated_at.desc())
    )
    return [note_dto(note) for note in result.scalars()]


@router.put(
    "/api/v1/notes/{note_id}",
    response_model=NoteDraftDto,
    response_model_exclude={"review"},
)
async def update_note(
    note_id: UUID,
    payload: UpdateNoteRequest,
    session: AsyncSession = Depends(database_session),
) -> NoteDraftDto:
    note = await session.get(NoteModel, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note_not_found")
    current = note_dto(note)
    style_form = (
        payload.style_form if "style_form" in payload.model_fields_set else current.style_form
    )
    candidate = current.model_copy(
        update={
            "topic_angle": payload.topic_angle,
            "title_candidates": payload.title_candidates,
            "body": payload.body,
            "hashtags": payload.hashtags,
            "cover_copy": payload.cover_copy,
            "image_suggestions": payload.image_suggestions,
            "style_form": style_form,
            # 客户端提交的 status/review 不存在信任边界，保存前一律重算。
            "status": NoteStatus.DRAFT,
            "review": None,
        }
    )
    account = await session.get(AccountModel, current.account_id)
    strategy = DomainStrategyRegistry().resolve(account.domain_id if account else "parenting")
    review = await review_draft(candidate, strategy=strategy)
    reviewed = candidate.model_copy(
        update={
            "review": review,
            "status": status_for_review(review, candidate),
            "user_issue": project_user_issue(review, strategy=strategy),
        }
    )
    try:
        return await SqlAlchemyNoteRepository(session).save(reviewed)
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="note_not_found",
        ) from error


@router.get("/api/v1/notes/{note_id}/versions", response_model=list[DraftVersionDto])
async def list_note_versions(
    note_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> list[DraftVersionDto]:
    if await session.get(NoteModel, note_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note_not_found")
    result = await session.execute(
        select(DraftVersionModel)
        .where(DraftVersionModel.note_id == note_id)
        .order_by(DraftVersionModel.version.asc())
    )
    return [
        DraftVersionDto(
            version=version.version,
            content_brief=ContentBriefDto.model_validate(version.content["content_brief"])
            if version.content.get("content_brief")
            else None,
            topic_angle=version.content.get("topic_angle", ""),
            title_candidates=version.content.get("title_candidates", []),
            body=version.content.get("body", ""),
            hashtags=version.content.get("hashtags", []),
            cover_copy=version.content.get("cover_copy", ""),
            image_suggestions=version.content.get("image_suggestions", []),
            style_form=StyleForm(version.content["style_form"])
            if version.content.get("style_form") is not None
            else None,
            review=ReviewResultDto.model_validate(version.content["review"])
            if version.content.get("review")
            else None,
            created_at=version.created_at,
        )
        for version in result.scalars()
    ]


@router.get(
    "/api/v1/notes/{note_id}/export",
    response_model=NoteDraftDto,
    response_model_exclude={"review"},
)
async def export_note(
    note_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> NoteDraftDto:
    note = await session.get(NoteModel, note_id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note_not_found")
    draft = note_dto(note)
    review = draft.review
    if review is None or not review_matches_draft(review, draft):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "review_required",
                "message": "草稿尚未完成当前版本审核，暂不能导出",
                "reasons": [],
            },
        )
    blocking = [finding for finding in review.findings if finding.level.value == "blocking"]
    if blocking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "blocking_review",
                "message": "草稿包含阻断级风险，暂不能导出",
                "reasons": [finding.message for finding in blocking],
            },
        )
    return draft


@router.post(
    "/api/v1/notes/{note_id}/publish-record", response_model=PublishRecordDto, status_code=201
)
async def create_publish_record(
    note_id: UUID,
    payload: PublishRecordInput,
    session: AsyncSession = Depends(database_session),
) -> PublishRecordDto:
    if await session.get(NoteModel, note_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="note_not_found")
    record = PublishRecordModel(
        note_id=note_id,
        status=payload.status.value,
        published_at=payload.published_at,
        link=payload.link,
        notes=payload.notes,
        views=payload.views,
        likes=payload.likes,
        saves=payload.saves,
        comments=payload.comments,
    )
    session.add(record)
    await session.commit()
    note = await session.get(NoteModel, note_id)
    if note is not None:
        note.status = payload.status.value
        await session.commit()
    return PublishRecordDto(
        note_id=record.note_id,
        status=NoteStatus(record.status),
        published_at=record.published_at,
        link=record.link,
        notes=record.notes,
        views=record.views,
        likes=record.likes,
        saves=record.saves,
        comments=record.comments,
    )
