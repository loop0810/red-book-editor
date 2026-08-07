from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from red_book_editor_server.domain.contracts import (
    NoteDraftDto,
    NoteStatus,
    ReviewResultDto,
    SourceExperienceDto,
)
from red_book_editor_server.infrastructure.models import NoteModel


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

    @staticmethod
    def _to_dto(note: NoteModel) -> NoteDraftDto:
        content = note.content
        return NoteDraftDto(
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
            review=ReviewResultDto.model_validate(note.review) if note.review else None,
            updated_at=note.updated_at or datetime.now(UTC),
        )
