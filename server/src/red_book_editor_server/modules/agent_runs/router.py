from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from red_book_editor_server.app.dependencies import database_session
from red_book_editor_server.domain.agent_runs import (
    AgentRunEventRecord,
    AgentRunEventType,
    AgentRunLifecycleStatus,
    AgentRunRecord,
)
from red_book_editor_server.domain.contracts import SourceExperienceDto, StyleForm
from red_book_editor_server.infrastructure.repositories import (
    SqlAlchemyAccountColumnContextRepository,
    SqlAlchemyAgentRunRepository,
    SqlAlchemyNoteRepository,
)
from red_book_editor_server.modules.agent_runs.service import (
    AgentRunCoordinator,
    placeholder_note,
)

router = APIRouter(prefix="/api/v1/agent-runs", tags=["agent-runs"])


class CreateAgentRunRequest(BaseModel):
    account_id: UUID
    column_id: UUID
    form: StyleForm
    source: SourceExperienceDto


_TERMINAL_STATUSES = {
    AgentRunLifecycleStatus.COMPLETED,
    AgentRunLifecycleStatus.FAILED,
    AgentRunLifecycleStatus.CANCELLED,
    AgentRunLifecycleStatus.INTERRUPTED,
}


@router.post("", response_model=AgentRunRecord, status_code=status.HTTP_202_ACCEPTED)
async def create_agent_run(
    request: CreateAgentRunRequest,
    http_request: Request,
    session: AsyncSession = Depends(database_session),
) -> AgentRunRecord:
    context = SqlAlchemyAccountColumnContextRepository(session)
    account = await context.get_account(request.account_id)
    column = await context.get_column(request.account_id, request.column_id)
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")
    if column is None or not column.enabled:
        raise HTTPException(status_code=404, detail="column_not_found")

    note = placeholder_note(
        account_id=request.account_id,
        column_id=request.column_id,
        source=request.source,
        form=request.form,
    )
    persisted_note = await SqlAlchemyNoteRepository(session).create(note)
    repository = SqlAlchemyAgentRunRepository(session)
    record = await repository.create(
        note_id=persisted_note.note_id,
        account_id=request.account_id,
        column_id=request.column_id,
        form=request.form,
    )
    await repository.append_event(
        record.run_id,
        AgentRunEventRecord(
            run_id=record.run_id,
            sequence=1,
            event_type=AgentRunEventType.CREATED,
            label="created",
            summary="已创建 Agent 运行，等待执行",
            attempt=record.attempt,
            created_at=record.created_at,
        ),
    )
    coordinator: AgentRunCoordinator = http_request.app.state.agent_run_coordinator
    await coordinator.start(record.run_id)
    return record


@router.get("/{run_id}", response_model=AgentRunRecord)
async def get_agent_run(
    run_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> AgentRunRecord:
    record = await SqlAlchemyAgentRunRepository(session).get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="agent_run_not_found")
    return record


@router.post("/{run_id}/cancel", response_model=AgentRunRecord)
async def cancel_agent_run(run_id: UUID, http_request: Request) -> AgentRunRecord:
    coordinator: AgentRunCoordinator = http_request.app.state.agent_run_coordinator
    record = await coordinator.cancel(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="agent_run_not_found")
    return record


@router.post("/{run_id}/resume", response_model=AgentRunRecord, status_code=202)
async def resume_agent_run(run_id: UUID, http_request: Request) -> AgentRunRecord:
    coordinator: AgentRunCoordinator = http_request.app.state.agent_run_coordinator
    try:
        return await coordinator.resume(run_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail="agent_run_not_found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{run_id}/events")
async def stream_agent_run_events(
    run_id: UUID,
    request: Request,
    after: int = 0,
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    async with request.app.state.session_factory() as session:
        record = await SqlAlchemyAgentRunRepository(session).get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="agent_run_not_found")
    try:
        cursor = max(after, int(last_event_id or 0))
    except ValueError:
        cursor = max(0, after)

    async def event_stream() -> AsyncIterator[str]:
        nonlocal cursor
        while True:
            if await request.is_disconnected():
                return
            async with request.app.state.session_factory() as session:
                repository = SqlAlchemyAgentRunRepository(session)
                events = await repository.list_events(run_id, after=cursor)
                current = await repository.get(run_id)
            for event in events:
                cursor = event.sequence
                yield _sse_event(event)
            if current is None or (current.status in _TERMINAL_STATUSES and not events):
                return
            await asyncio.sleep(0.15)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"cache-control": "no-cache", "x-accel-buffering": "no"},
    )


def _sse_event(event: AgentRunEventRecord) -> str:
    payload = event.model_dump(mode="json")
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type.value}\n"
        f"data: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"
    )
