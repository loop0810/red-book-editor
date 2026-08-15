from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from red_book_editor_server.domain.contracts import (
    AccountProfileDto,
    ContentColumnDto,
    NoteDraftDto,
    NoteStatus,
    ReviewResultDto,
    SourceExperienceDto,
    StyleForm,
)
from red_book_editor_server.infrastructure.models import (
    AccountModel,
    ContentColumnModel,
    DraftVersionModel,
    NoteModel,
)
from red_book_editor_server.modules.content_workflow.review import status_for_review


class SqlAlchemyAccountColumnContextRepository:
    """把 ORM 账号/栏目记录映射为内容工作流所需的领域 DTO。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_account(self, account_id: UUID) -> AccountProfileDto | None:
        account = await self._session.get(AccountModel, account_id)
        if account is None:
            return None
        return AccountProfileDto(
            account_id=account.id,
            positioning=account.positioning,
            age_range_months=(account.min_age_months, account.max_age_months),
            current_baby_month=account.current_baby_month,
            tone=account.tone,
            boundaries=account.boundaries,
            common_expressions=account.common_expressions,
        )

    async def get_column(self, account_id: UUID, column_id: UUID) -> ContentColumnDto | None:
        column = await self._session.get(ContentColumnModel, column_id)
        if column is None or column.account_id != account_id:
            return None
        return ContentColumnDto(
            column_id=column.id,
            account_id=column.account_id,
            name=column.name,
            description=column.description,
            content_types=column.content_types,
            enabled=column.enabled,
        )


class SqlAlchemyNoteRepository:
    """使用请求范围内 session 读取账号隔离的笔记草稿。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, note_id: UUID) -> NoteDraftDto | None:
        note = await self._session.get(NoteModel, note_id)
        return self._to_dto(note) if note is not None else None

    async def list_for_account(self, account_id: UUID) -> Sequence[NoteDraftDto]:
        result = await self._session.execute(
            select(NoteModel)
            .where(NoteModel.account_id == account_id)
            .order_by(NoteModel.updated_at.desc())
        )
        return [self._to_dto(note) for note in result.scalars()]

    async def create(self, draft: NoteDraftDto) -> NoteDraftDto:
        note = NoteModel(
            id=draft.note_id,
            account_id=draft.account_id,
            column_id=draft.column_id,
            status=draft.status.value,
            source=draft.source.model_dump(mode="json"),
            content=_content_from_draft(draft),
            review=draft.review.model_dump(mode="json") if draft.review else None,
        )
        self._session.add(note)
        await self._session.flush()
        self._session.add(DraftVersionModel(note_id=note.id, version=1, content=dict(note.content)))
        await self._session.commit()
        await self._session.refresh(note)
        return self._to_dto(note)

    async def save(self, draft: NoteDraftDto) -> NoteDraftDto:
        note = await self._session.get(NoteModel, draft.note_id)
        if note is None:
            raise LookupError("note_not_found")
        note.status = draft.status.value
        note.updated_at = datetime.now(UTC)
        note.content = _content_from_draft(draft)
        note.review = draft.review.model_dump(mode="json") if draft.review else None
        latest = (
            (
                await self._session.execute(
                    select(DraftVersionModel)
                    .where(DraftVersionModel.note_id == draft.note_id)
                    .order_by(DraftVersionModel.version.desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        self._session.add(
            DraftVersionModel(
                note_id=draft.note_id,
                version=(latest.version + 1 if latest else 1),
                content=dict(note.content),
            )
        )
        await self._session.commit()
        await self._session.refresh(note)
        return self._to_dto(note)

    @staticmethod
    def _to_dto(note: NoteModel) -> NoteDraftDto:
        content = note.content
        review = ReviewResultDto.model_validate(note.review) if note.review else None
        draft = NoteDraftDto(
            note_id=note.id,
            account_id=note.account_id,
            column_id=note.column_id,
            status=NoteStatus(note.status),
            topic_angle=content.get("topic_angle", ""),
            title_candidates=content.get("title_candidates", []),
            body=content.get("body", ""),
            hashtags=content.get("hashtags", []),
            cover_copy=content.get("cover_copy", ""),
            image_suggestions=content.get("image_suggestions", []),
            source=SourceExperienceDto.model_validate(note.source),
            style_form=StyleForm(content["style_form"])
            if content.get("style_form") is not None
            else None,
            review=review,
            updated_at=note.updated_at or datetime.now(UTC),
        )
        stored_status = NoteStatus(note.status)
        if stored_status in (
            NoteStatus.DRAFT,
            NoteStatus.NEEDS_REVIEW,
            NoteStatus.READY,
        ):
            draft = draft.model_copy(update={"status": status_for_review(review, draft)})
        return draft


def _content_from_draft(draft: NoteDraftDto) -> dict[str, object]:
    return draft.model_dump(
        mode="json",
        include={
            "topic_angle",
            "title_candidates",
            "body",
            "hashtags",
            "cover_copy",
            "image_suggestions",
            "style_form",
            "review",
        },
    )
