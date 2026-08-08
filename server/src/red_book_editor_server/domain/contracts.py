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


class StyleForm(StrEnum):
    POPULAR_SCIENCE = "popular_science"
    EXPERIENCE = "experience"
    ADVERTORIAL = "advertorial"


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


class ToneProfile(BaseModel):
    person: str = ""
    words: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)


class RichTextProfile(BaseModel):
    emoji_rules: str = ""
    separators: list[str] = Field(default_factory=list)
    tag_count_range: tuple[int, int] = (4, 15)


class TagPool(BaseModel):
    generic: list[str] = Field(default_factory=list)
    precise: list[str] = Field(default_factory=list)
    trending: list[str] = Field(default_factory=list)


class CoverProfile(BaseModel):
    pattern: str = ""
    examples: list[str] = Field(default_factory=list)


class StructureTemplate(BaseModel):
    name: str
    sequence: list[str] = Field(default_factory=list)


class StyleProfile(BaseModel):
    """一种表达形式的风格档案，来自服务端代码库内版本化 YAML。"""

    form: StyleForm
    display_name: str
    hooks: list[str] = Field(default_factory=list)
    structures: list[StructureTemplate] = Field(default_factory=list)
    tone: ToneProfile = Field(default_factory=ToneProfile)
    rich_text: RichTextProfile = Field(default_factory=RichTextProfile)
    tags: TagPool = Field(default_factory=TagPool)
    cover: CoverProfile = Field(default_factory=CoverProfile)
    cta: list[str] = Field(default_factory=list)


class AgentTraceStepDto(BaseModel):
    """API 层返回的 agent 步骤。"""

    order: int
    kind: str
    label: str
    summary: str


class StyledNoteResponseDto(BaseModel):
    """风格转换响应：风格化草稿 + agent 逐步 trace。"""

    draft: NoteDraftDto
    agent_trace: list[AgentTraceStepDto] = Field(default_factory=list)


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
