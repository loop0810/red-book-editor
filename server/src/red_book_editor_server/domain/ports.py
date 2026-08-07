from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from red_book_editor_server.domain.contracts import NoteDraftDto, SourceExperienceDto


class ContentGenerator(Protocol):
    async def generate(
        self,
        source: SourceExperienceDto,
        *,
        account_id: UUID | None = None,
        column_id: UUID | None = None,
    ) -> NoteDraftDto: ...


class NoteRepository(Protocol):
    async def get(self, note_id: UUID) -> NoteDraftDto | None: ...

    async def list_for_account(self, account_id: UUID) -> Sequence[NoteDraftDto]: ...
