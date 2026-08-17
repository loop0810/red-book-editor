from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from red_book_editor_server.app.config import Settings
from red_book_editor_server.app.dependencies import build_model_gateway
from red_book_editor_server.domain.agent import (
    AgentFailureCode,
    AgentPhase,
    AgentRunDiagnostics,
    AgentRunError,
    AgentRunStatus,
    AgentRuntimeEvent,
)
from red_book_editor_server.domain.agent_runs import (
    AgentRunEventRecord,
    AgentRunEventType,
    AgentRunLifecycleStatus,
    AgentRunRecord,
)
from red_book_editor_server.domain.contracts import (
    ContentBriefDto,
    NoteDraftDto,
    NoteStatus,
    SourceExperienceDto,
    StyleForm,
)
from red_book_editor_server.domain.ports import ModelGatewayError
from red_book_editor_server.infrastructure.repositories import (
    SqlAlchemyAccountColumnContextRepository,
    SqlAlchemyAgentRunRepository,
    SqlAlchemyNoteRepository,
)
from red_book_editor_server.modules.content_workflow.generator import ContentGenerationError
from red_book_editor_server.modules.content_workflow.service import ContentWorkflowService


class AgentRunCoordinator:
    """单实例后台执行器；数据库状态是运行生命周期的权威来源。"""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self._session_factory = session_factory
        self._settings = settings
        self._tasks: dict[UUID, asyncio.Task[None]] = {}

    async def recover_orphans(self) -> None:
        async with self._session_factory() as session:
            records = await SqlAlchemyAgentRunRepository(session).mark_interrupted()
        for record in records:
            await self._append_event(
                record.run_id,
                AgentRunEventRecord(
                    run_id=record.run_id,
                    sequence=1,
                    event_type=AgentRunEventType.INTERRUPTED,
                    label=AgentRunLifecycleStatus.INTERRUPTED.value,
                    summary="服务重启后发现未完成运行，可重新执行",
                    status=AgentRunLifecycleStatus.INTERRUPTED,
                    attempt=record.attempt,
                    created_at=record.updated_at,
                ),
            )

    async def start(self, run_id: UUID) -> None:
        current = self._tasks.get(run_id)
        if current is not None and not current.done():
            return
        task = asyncio.create_task(self._run(run_id))
        self._tasks[run_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(run_id, None))

    async def cancel(self, run_id: UUID) -> AgentRunRecord | None:
        async with self._session_factory() as session:
            record = await SqlAlchemyAgentRunRepository(session).request_cancel(run_id)
        if record is None:
            return None
        task = self._tasks.get(run_id)
        if task is not None and not task.done():
            task.cancel()
        return record

    async def resume(self, run_id: UUID) -> AgentRunRecord:
        current = self._tasks.get(run_id)
        async with self._session_factory() as session:
            repository = SqlAlchemyAgentRunRepository(session)
            existing = await repository.get(run_id)
            if existing is None:
                raise LookupError("agent_run_not_found")
            if (
                current is not None
                and not current.done()
                and existing.status
                not in (
                    AgentRunLifecycleStatus.FAILED,
                    AgentRunLifecycleStatus.CANCELLED,
                    AgentRunLifecycleStatus.INTERRUPTED,
                )
            ):
                raise ValueError("agent_run_already_running")
            if current is not None and not current.done():
                await asyncio.shield(current)
            record = await repository.prepare_resume(run_id)
            await repository.append_event(
                run_id,
                AgentRunEventRecord(
                    run_id=run_id,
                    sequence=1,
                    event_type=AgentRunEventType.RESUMED,
                    label="resumed",
                    summary="重新执行已持久化的笔记输入",
                    attempt=record.attempt,
                    created_at=record.updated_at,
                ),
            )
        await self.start(run_id)
        return record

    async def _run(self, run_id: UUID) -> None:
        record: AgentRunRecord | None = None
        try:
            # 数据库状态是生命周期真相，内存 task 只负责调度；因此服务重启后仍能
            # 根据 queued/running/failed/interrupted 状态查询、取消或恢复运行。
            record = await self._mark_started(run_id)
            if record is None:
                return
            async with self._session_factory() as session:
                note = await SqlAlchemyNoteRepository(session).get(record.note_id)
                if note is None:
                    await self._finish_failure(
                        record,
                        AgentFailureCode.INPUT_ERROR,
                        "关联笔记不存在",
                    )
                    return

                async def cancel_check() -> bool:
                    async with self._session_factory() as check_session:
                        return await SqlAlchemyAgentRunRepository(
                            check_session
                        ).is_cancel_requested(run_id)

                async def event_sink(event: AgentRuntimeEvent) -> None:
                    # AgentRuntime 的内部事件在这里转成有界、可续读的数据库事件，
                    # 不把完整 prompt、模型消息或工具原始参数写入持久化层。
                    await self._append_runtime_event(run_id, event)

                if self._settings.model_provider != "deepseek":
                    await self._append_phase(run_id, AgentPhase.COLLECT_CONTEXT)
                    await self._append_phase(run_id, AgentPhase.DRAFT)

                service = ContentWorkflowService(
                    context=SqlAlchemyAccountColumnContextRepository(session),
                    model_provider=self._settings.model_provider,
                    gateway=(
                        build_model_gateway(self._settings)
                        if self._settings.model_provider == "deepseek"
                        else None
                    ),
                )
                result = await service.generate(
                    account_id=record.account_id,
                    column_id=record.column_id,
                    brief=note.content_brief,
                    source=note.source,
                    form=record.form,
                    cancel_check=cancel_check,
                    event_sink=event_sink,
                )
                if await cancel_check():
                    raise AgentRunError(
                        AgentFailureCode.CANCELLED.value,
                        [],
                        diagnostics=AgentRunDiagnostics(
                            status=AgentRunStatus.CANCELLED,
                            phase=AgentPhase.SAFETY_REVIEW,
                            failure_code=AgentFailureCode.CANCELLED,
                        ),
                    )

                final_draft = result.draft.model_copy(update={"note_id": record.note_id})
                # 只有统一生成和审核都完成后才保存最终草稿；失败/取消不会把半成品标成可用。
                await SqlAlchemyNoteRepository(session).save(final_draft)
                await self._append_phase(run_id, AgentPhase.SAFETY_REVIEW)
                diagnostics = result.diagnostics or AgentRunDiagnostics(
                    status=AgentRunStatus.COMPLETED,
                    phase=AgentPhase.SAFETY_REVIEW,
                )
                diagnostics = diagnostics.model_copy(
                    update={"status": AgentRunStatus.COMPLETED, "phase": AgentPhase.SAFETY_REVIEW}
                )
                await self._finish_success(record, diagnostics)
        except asyncio.CancelledError:
            await self._finish_cancelled(run_id)
        except ContentGenerationError as error:
            agent_error = error.agent_error
            if record is not None and isinstance(agent_error, AgentRunError):
                await self._finish_agent_error(record, agent_error)
            elif record is not None:
                await self._finish_failure(record, AgentFailureCode.MODEL_ERROR, str(error))
        except AgentRunError as error:
            if record is not None:
                await self._finish_agent_error(record, error)
        except ModelGatewayError as error:
            if record is not None:
                summary = (
                    "模型配置缺失：请在 server/.env 中配置 DEEPSEEK_API_KEY"
                    if str(error) == "model_api_key_missing"
                    else "模型请求失败，请检查 DeepSeek 配置和网络连接"
                )
                await self._finish_failure(record, AgentFailureCode.MODEL_ERROR, summary)
        except Exception as error:  # pragma: no cover - defensive worker boundary
            if record is not None:
                await self._finish_failure(record, AgentFailureCode.UNEXPECTED_ERROR, str(error))

    async def _mark_started(self, run_id: UUID) -> AgentRunRecord | None:
        try:
            async with self._session_factory() as session:
                repository = SqlAlchemyAgentRunRepository(session)
                record = await repository.mark_running(run_id)
                await repository.append_event(
                    run_id,
                    AgentRunEventRecord(
                        run_id=run_id,
                        sequence=1,
                        event_type=AgentRunEventType.STARTED,
                        label="started",
                        summary="Agent 开始执行",
                        attempt=record.attempt,
                        created_at=record.updated_at,
                    ),
                )
                return record
        except (LookupError, ValueError):
            return None

    async def _append_runtime_event(self, run_id: UUID, event: AgentRuntimeEvent) -> None:
        event_type = {
            "model": AgentRunEventType.MODEL,
            "tool": AgentRunEventType.TOOL,
            "phase": AgentRunEventType.PHASE,
        }.get(event.kind)
        if event_type is None:
            return
        await self._append_event(
            run_id,
            AgentRunEventRecord(
                run_id=run_id,
                sequence=event.order,
                event_type=event_type,
                phase=event.phase,
                label=event.label,
                summary=event.summary,
                attempt=1,
                created_at=datetime.now(UTC),
            ),
        )

    async def _append_phase(self, run_id: UUID, phase: AgentPhase) -> None:
        await self._append_event(
            run_id,
            AgentRunEventRecord(
                run_id=run_id,
                sequence=1,
                event_type=AgentRunEventType.PHASE,
                phase=phase,
                label=phase.value,
                summary=f"进入阶段：{phase.value}",
                attempt=1,
                created_at=datetime.now(UTC),
            ),
        )

    async def _append_event(self, run_id: UUID, event: AgentRunEventRecord) -> None:
        async with self._session_factory() as session:
            await SqlAlchemyAgentRunRepository(session).append_event(run_id, event)

    async def _finish_success(
        self, record: AgentRunRecord, diagnostics: AgentRunDiagnostics
    ) -> None:
        async with self._session_factory() as session:
            repository = SqlAlchemyAgentRunRepository(session)
            updated = await repository.update_state(
                record.run_id,
                status=AgentRunLifecycleStatus.COMPLETED,
                current_phase=AgentPhase.SAFETY_REVIEW.value,
                diagnostics=diagnostics,
            )
            await repository.append_event(
                record.run_id,
                AgentRunEventRecord(
                    run_id=record.run_id,
                    sequence=1,
                    event_type=AgentRunEventType.COMPLETED,
                    phase=AgentPhase.SAFETY_REVIEW,
                    label="completed",
                    summary="Agent 运行完成，草稿已通过统一审核流程",
                    status=AgentRunLifecycleStatus.COMPLETED,
                    attempt=updated.attempt,
                    created_at=updated.updated_at,
                ),
            )

    async def _finish_agent_error(self, record: AgentRunRecord, error: AgentRunError) -> None:
        status = (
            AgentRunLifecycleStatus.CANCELLED
            if error.diagnostics.status is AgentRunStatus.CANCELLED
            else AgentRunLifecycleStatus.FAILED
        )
        await self._finish_failure(
            record,
            error.diagnostics.failure_code or AgentFailureCode.UNEXPECTED_ERROR,
            error.args[0] if error.args else "agent_run_failed",
            diagnostics=error.diagnostics,
            status=status,
        )

    async def _finish_failure(
        self,
        record: AgentRunRecord,
        code: AgentFailureCode,
        summary: str,
        *,
        diagnostics: AgentRunDiagnostics | None = None,
        status: AgentRunLifecycleStatus = AgentRunLifecycleStatus.FAILED,
    ) -> None:
        diagnostics = diagnostics or AgentRunDiagnostics(
            status=AgentRunStatus.FAILED,
            phase=AgentPhase.FINALIZE,
            failure_code=code,
        )
        async with self._session_factory() as session:
            repository = SqlAlchemyAgentRunRepository(session)
            updated = await repository.update_state(
                record.run_id,
                status=status,
                current_phase=diagnostics.phase.value,
                diagnostics=diagnostics,
                failure_code=code.value,
            )
            event_type = (
                AgentRunEventType.CANCELLED
                if status is AgentRunLifecycleStatus.CANCELLED
                else AgentRunEventType.FAILED
            )
            await repository.append_event(
                record.run_id,
                AgentRunEventRecord(
                    run_id=record.run_id,
                    sequence=1,
                    event_type=event_type,
                    phase=diagnostics.phase,
                    label=code.value,
                    summary=summary,
                    status=status,
                    failure_code=code,
                    attempt=updated.attempt,
                    created_at=datetime.now(UTC),
                ),
            )

    async def _finish_cancelled(self, run_id: UUID) -> None:
        async with self._session_factory() as session:
            repository = SqlAlchemyAgentRunRepository(session)
            record = await repository.get(run_id)
            if record is None or record.status in (
                AgentRunLifecycleStatus.COMPLETED,
                AgentRunLifecycleStatus.FAILED,
                AgentRunLifecycleStatus.CANCELLED,
            ):
                return
            diagnostics = AgentRunDiagnostics(
                status=AgentRunStatus.CANCELLED,
                phase=record.current_phase or AgentPhase.COLLECT_CONTEXT,
                failure_code=AgentFailureCode.CANCELLED,
            )
            updated = await repository.update_state(
                run_id,
                status=AgentRunLifecycleStatus.CANCELLED,
                diagnostics=diagnostics,
                failure_code=AgentFailureCode.CANCELLED.value,
            )
            await repository.append_event(
                run_id,
                AgentRunEventRecord(
                    run_id=run_id,
                    sequence=1,
                    event_type=AgentRunEventType.CANCELLED,
                    phase=diagnostics.phase,
                    label=AgentFailureCode.CANCELLED.value,
                    summary="运行已取消",
                    status=AgentRunLifecycleStatus.CANCELLED,
                    failure_code=AgentFailureCode.CANCELLED,
                    attempt=updated.attempt,
                    created_at=updated.updated_at,
                ),
            )


def placeholder_note(
    *,
    account_id: UUID,
    column_id: UUID,
    brief: ContentBriefDto | None = None,
    source: SourceExperienceDto | None = None,
    form: StyleForm,
) -> NoteDraftDto:
    if brief is None and source is None:
        raise ValueError("content_brief_required")
    return NoteDraftDto(
        note_id=uuid4(),
        account_id=account_id,
        column_id=column_id,
        status=NoteStatus.DRAFT,
        content_brief=brief,
        source=source,
        style_form=form,
        updated_at=datetime.now(UTC),
    )
