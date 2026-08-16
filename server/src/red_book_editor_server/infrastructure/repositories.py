from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
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
from red_book_editor_server.domain.agent import AgentFailureCode, AgentPhase, AgentRunDiagnostics
from red_book_editor_server.domain.agent_runs import (
    AgentRunEventRecord,
    AgentRunEventType,
    AgentRunLifecycleStatus,
    AgentRunOperation,
    AgentRunRecord,
)
from red_book_editor_server.infrastructure.models import (
    AccountModel,
    AgentRunEventModel,
    AgentRunModel,
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


class SqlAlchemyAgentRunRepository:
    """保存 AgentRun 生命周期和可断点读取的安全事件摘要。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        note_id: UUID,
        account_id: UUID,
        column_id: UUID,
        form: StyleForm,
    ) -> AgentRunRecord:
        run = AgentRunModel(
            note_id=note_id,
            account_id=account_id,
            column_id=column_id,
            operation=AgentRunOperation.GENERATE.value,
            form=form.value,
            status=AgentRunLifecycleStatus.QUEUED.value,
            attempt=1,
            cancel_requested=False,
        )
        self._session.add(run)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(run)
        return self._to_record(run)

    async def get(self, run_id: UUID) -> AgentRunRecord | None:
        run = await self._session.get(AgentRunModel, run_id)
        return self._to_record(run) if run is not None else None

    async def mark_running(self, run_id: UUID) -> AgentRunRecord:
        run = await self._require(run_id)
        if run.status == AgentRunLifecycleStatus.QUEUED.value:
            run.status = AgentRunLifecycleStatus.RUNNING.value
            run.started_at = datetime.now(UTC)
            run.updated_at = datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(run)
        return self._to_record(run)

    async def mark_interrupted(self) -> list[AgentRunRecord]:
        result = await self._session.execute(
            select(AgentRunModel).where(
                AgentRunModel.status == AgentRunLifecycleStatus.RUNNING.value
            )
        )
        runs = list(result.scalars())
        now = datetime.now(UTC)
        for run in runs:
            run.status = AgentRunLifecycleStatus.INTERRUPTED.value
            run.updated_at = now
            run.finished_at = now
        if runs:
            await self._session.commit()
        return [self._to_record(run) for run in runs]

    async def request_cancel(self, run_id: UUID) -> AgentRunRecord | None:
        run = await self._session.get(AgentRunModel, run_id)
        if run is None:
            return None
        if run.status in (
            AgentRunLifecycleStatus.QUEUED.value,
            AgentRunLifecycleStatus.RUNNING.value,
        ):
            run.cancel_requested = True
            run.updated_at = datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(run)
        return self._to_record(run)

    async def prepare_resume(self, run_id: UUID) -> AgentRunRecord:
        run = await self._require(run_id)
        if run.status not in (
            AgentRunLifecycleStatus.FAILED.value,
            AgentRunLifecycleStatus.CANCELLED.value,
            AgentRunLifecycleStatus.INTERRUPTED.value,
        ):
            raise ValueError("agent_run_not_resumable")
        run.status = AgentRunLifecycleStatus.QUEUED.value
        run.attempt += 1
        run.cancel_requested = False
        run.current_phase = None
        run.diagnostics = None
        run.failure_code = None
        run.started_at = None
        run.finished_at = None
        run.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(run)
        return self._to_record(run)

    async def update_state(
        self,
        run_id: UUID,
        *,
        status: AgentRunLifecycleStatus,
        current_phase: str | None = None,
        diagnostics: object | None = None,
        failure_code: str | None = None,
    ) -> AgentRunRecord:
        run = await self._require(run_id)
        run.status = status.value
        if current_phase is not None:
            run.current_phase = current_phase
        if diagnostics is not None:
            if isinstance(diagnostics, AgentRunDiagnostics):
                run.diagnostics = diagnostics.model_dump(mode="json")
        run.failure_code = failure_code
        run.updated_at = datetime.now(UTC)
        if status is AgentRunLifecycleStatus.RUNNING and run.started_at is None:
            run.started_at = run.updated_at
        if status in (
            AgentRunLifecycleStatus.COMPLETED,
            AgentRunLifecycleStatus.FAILED,
            AgentRunLifecycleStatus.CANCELLED,
            AgentRunLifecycleStatus.INTERRUPTED,
        ):
            run.finished_at = run.updated_at
        await self._session.commit()
        await self._session.refresh(run)
        return self._to_record(run)

    async def is_cancel_requested(self, run_id: UUID) -> bool:
        run = await self._session.get(AgentRunModel, run_id)
        return bool(run and run.cancel_requested)

    async def append_event(
        self,
        run_id: UUID,
        event: AgentRunEventRecord,
    ) -> AgentRunEventRecord:
        run = await self._require(run_id)
        latest = await self._session.scalar(
            select(func.max(AgentRunEventModel.sequence)).where(AgentRunEventModel.run_id == run_id)
        )
        sequence = int(latest or 0) + 1
        row = AgentRunEventModel(
            run_id=run_id,
            sequence=sequence,
            event_type=event.event_type.value,
            phase=event.phase.value if event.phase else None,
            label=event.label,
            summary=event.summary[:400],
            status=event.status.value if event.status else None,
            failure_code=event.failure_code.value if event.failure_code else None,
            attempt=run.attempt,
        )
        self._session.add(row)
        if event.phase is not None:
            run.current_phase = event.phase.value
        run.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_event(row)

    async def list_events(
        self,
        run_id: UUID,
        *,
        after: int = 0,
        limit: int = 100,
    ) -> list[AgentRunEventRecord]:
        result = await self._session.execute(
            select(AgentRunEventModel)
            .where(
                AgentRunEventModel.run_id == run_id,
                AgentRunEventModel.sequence > max(0, after),
            )
            .order_by(AgentRunEventModel.sequence.asc())
            .limit(max(1, min(limit, 1000)))
        )
        return [self._to_event(row) for row in result.scalars()]

    async def _require(self, run_id: UUID) -> AgentRunModel:
        run = await self._session.get(AgentRunModel, run_id)
        if run is None:
            raise LookupError("agent_run_not_found")
        return run

    @staticmethod
    def _to_record(run: AgentRunModel) -> AgentRunRecord:
        return AgentRunRecord(
            run_id=run.id,
            note_id=run.note_id,
            account_id=run.account_id,
            column_id=run.column_id,
            operation=AgentRunOperation(run.operation),
            form=StyleForm(run.form),
            status=AgentRunLifecycleStatus(run.status),
            current_phase=AgentPhase(run.current_phase) if run.current_phase else None,
            attempt=run.attempt,
            cancel_requested=run.cancel_requested,
            diagnostics=(
                AgentRunDiagnostics.model_validate(run.diagnostics) if run.diagnostics else None
            ),
            failure_code=AgentFailureCode(run.failure_code) if run.failure_code else None,
            created_at=run.created_at,
            updated_at=run.updated_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
        )

    @staticmethod
    def _to_event(row: AgentRunEventModel) -> AgentRunEventRecord:
        return AgentRunEventRecord(
            run_id=row.run_id,
            sequence=row.sequence,
            event_type=AgentRunEventType(row.event_type),
            phase=AgentPhase(row.phase) if row.phase else None,
            label=row.label,
            summary=row.summary,
            status=(
                AgentRunLifecycleStatus(row.status)
                if row.status in {item.value for item in AgentRunLifecycleStatus}
                else None
            ),
            failure_code=AgentFailureCode(row.failure_code) if row.failure_code else None,
            attempt=row.attempt,
            created_at=row.created_at,
        )
