from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from red_book_editor_server.domain.agent import (
    AgentFailureCode,
    AgentPhase,
    AgentRunDiagnostics,
    AgentRunStatus,
)
from red_book_editor_server.domain.contracts import StyleForm


class AgentRunLifecycleStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


class AgentRunOperation(StrEnum):
    GENERATE = "generate"


class AgentRunEventType(StrEnum):
    CREATED = "run.created"
    STARTED = "run.started"
    PHASE = "phase"
    MODEL = "model"
    TOOL = "tool"
    COMPLETED = "run.completed"
    FAILED = "run.failed"
    CANCELLED = "run.cancelled"
    INTERRUPTED = "run.interrupted"
    RESUMED = "run.resumed"


class AgentRunRecord(BaseModel):
    run_id: UUID
    note_id: UUID
    account_id: UUID
    column_id: UUID
    operation: AgentRunOperation
    form: StyleForm
    status: AgentRunLifecycleStatus
    current_phase: AgentPhase | None = None
    attempt: int = Field(ge=1)
    cancel_requested: bool = False
    diagnostics: AgentRunDiagnostics | None = None
    failure_code: AgentFailureCode | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AgentRunEventRecord(BaseModel):
    run_id: UUID
    sequence: int = Field(ge=1)
    event_type: AgentRunEventType
    phase: AgentPhase | None = None
    label: str
    summary: str = Field(max_length=400)
    status: AgentRunLifecycleStatus | AgentRunStatus | None = None
    failure_code: AgentFailureCode | None = None
    attempt: int = Field(ge=1)
    created_at: datetime
