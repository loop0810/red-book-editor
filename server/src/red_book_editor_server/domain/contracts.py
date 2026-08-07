from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class NoteStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    READY = "ready"
    PUBLISHED = "published"
    DISCARDED = "discarded"


class RiskLevel(StrEnum):
    NONE = "none"
    WARNING = "warning"
    BLOCKING = "blocking"


class AccountProfileDto(BaseModel):
    account_id: UUID
    positioning: str = Field(min_length=1)
    age_range_months: tuple[int, int]
    current_baby_month: int = Field(ge=0, le=240)
    tone: str = Field(min_length=1)
    boundaries: list[str] = Field(default_factory=list)
    common_expressions: list[str] = Field(default_factory=list)


class ContentColumnDto(BaseModel):
    column_id: UUID
    account_id: UUID
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    content_types: list[str] = Field(default_factory=list)
    enabled: bool = True


class SourceExperienceDto(BaseModel):
    baby_month: int = Field(ge=0, le=240)
    scenario: str = Field(min_length=1)
    actions: list[str] = Field(min_length=1)
    observations: str = ""
    notes: str = ""
    asset_ids: list[UUID] = Field(default_factory=list)


class ReviewFindingDto(BaseModel):
    level: RiskLevel
    code: str
    message: str
    matched_text: str | None = None


class ReviewResultDto(BaseModel):
    passed: bool
    findings: list[ReviewFindingDto] = Field(default_factory=list)


class NoteDraftDto(BaseModel):
    note_id: UUID
    account_id: UUID
    column_id: UUID
    status: NoteStatus
    topic_angle: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cover_copy: str = ""
    image_suggestions: list[str] = Field(default_factory=list)
    source: SourceExperienceDto
    review: ReviewResultDto | None = None
    updated_at: datetime


class DraftVersionDto(BaseModel):
    version: int = Field(ge=1)
    topic_angle: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cover_copy: str = ""
    image_suggestions: list[str] = Field(default_factory=list)
    created_at: datetime


class AssetDto(BaseModel):
    asset_id: UUID
    account_id: UUID
    filename: str
    content_type: str
    position: int = Field(ge=0)


class PublishRecordDto(BaseModel):
    note_id: UUID
    status: NoteStatus
    published_at: datetime | None = None
    link: str | None = None
    notes: str = ""
    views: int | None = Field(default=None, ge=0)
    likes: int | None = Field(default=None, ge=0)
    saves: int | None = Field(default=None, ge=0)
    comments: int | None = Field(default=None, ge=0)
