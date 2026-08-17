from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AccountModel(Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    domain_id: Mapped[str] = mapped_column(String(64), default="parenting")
    domain_context: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    positioning: Mapped[str] = mapped_column(Text)
    min_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_age_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_baby_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tone: Mapped[str] = mapped_column(Text)
    boundaries: Mapped[list[str]] = mapped_column(JSONB, default=list)
    common_expressions: Mapped[list[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ContentColumnModel(Base):
    __tablename__ = "content_columns"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    content_types: Mapped[list[str]] = mapped_column(JSONB, default=list)
    enabled: Mapped[bool] = mapped_column(default=True)


class NoteModel(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="CASCADE"))
    column_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("content_columns.id"))
    status: Mapped[str] = mapped_column(String(32), default="draft")
    source: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    review: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DraftVersionModel(Base):
    __tablename__ = "draft_versions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    note_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("notes.id", ondelete="CASCADE"))
    version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FieldSuggestionModel(Base):
    __tablename__ = "field_suggestions"
    __table_args__ = (
        Index("ix_field_suggestions_note_status_created", "note_id", "status", "created_at"),
        Index("ix_field_suggestions_account_id", "account_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    note_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("notes.id", ondelete="CASCADE"))
    account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="CASCADE"))
    field: Mapped[str] = mapped_column(String(32))
    value: Mapped[str | list[str]] = mapped_column(JSONB)
    base_field_digest: Mapped[str] = mapped_column(String(64))
    base_content_digest: Mapped[str] = mapped_column(String(64))
    review: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    evidence: Mapped[list[str]] = mapped_column(JSONB, default=list)
    evidence_fact_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AssetModel(Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="CASCADE"))
    note_id: Mapped[UUID | None] = mapped_column(Uuid, ForeignKey("notes.id", ondelete="SET NULL"))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    storage_key: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)


class PublishRecordModel(Base):
    __tablename__ = "publish_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    note_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("notes.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    likes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    saves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comments: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AgentRunModel(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    note_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("notes.id", ondelete="CASCADE"))
    account_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("accounts.id", ondelete="CASCADE"))
    column_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("content_columns.id", ondelete="CASCADE")
    )
    operation: Mapped[str] = mapped_column(String(32))
    form: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    current_phase: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    diagnostics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentRunEventModel(Base):
    __tablename__ = "agent_run_events"
    __table_args__ = (
        UniqueConstraint("run_id", "sequence", name="uq_agent_run_events_run_sequence"),
        Index("ix_agent_run_events_run_sequence", "run_id", "sequence"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("agent_runs.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    phase: Mapped[str | None] = mapped_column(String(64), nullable=True)
    label: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(String(400))
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    attempt: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
