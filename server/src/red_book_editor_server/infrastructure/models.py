from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AccountModel(Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    positioning: Mapped[str] = mapped_column(Text)
    min_age_months: Mapped[int] = mapped_column(Integer)
    max_age_months: Mapped[int] = mapped_column(Integer)
    current_baby_month: Mapped[int] = mapped_column(Integer)
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
