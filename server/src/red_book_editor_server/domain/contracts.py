from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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


class FactKind(StrEnum):
    CONFIRMED = "confirmed"
    OBSERVED = "observed"
    OPINION = "opinion"
    CONSTRAINT = "constraint"
    UNKNOWN = "unknown"
    FORBIDDEN_INFERENCE = "forbidden_inference"


class ClaimSupport(StrEnum):
    SUPPORTED = "supported"
    UNCERTAIN = "uncertain"
    UNSUPPORTED = "unsupported"


class EditableField(StrEnum):
    TITLE = "title"
    BODY = "body"
    HASHTAGS = "hashtags"
    COVER_COPY = "cover_copy"


class SuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    STALE = "stale"


class UserIssueCategory(StrEnum):
    DOMAIN = "domain"
    SAFETY = "safety"
    FACTS = "facts"
    GENERATION = "generation"
    REVIEW = "review"


class ContentBriefDto(BaseModel):
    """通用内容输入；领域专属字段只能进入 domain_context。"""

    focus: str = Field(min_length=1, max_length=240)
    raw_material: str = Field(min_length=1, max_length=20000)
    domain_context: dict[str, Any] = Field(default_factory=dict)
    asset_ids: list[UUID] = Field(default_factory=list)

    @classmethod
    def from_legacy_source(cls, source: "SourceExperienceDto") -> "ContentBriefDto":
        material = "\n".join(
            value
            for value in (
                "；".join(source.actions),
                source.observations.strip(),
                source.notes.strip(),
            )
            if value
        )
        return cls(
            focus=source.scenario.strip(),
            raw_material=material or source.scenario.strip(),
            domain_context={"baby_month": source.baby_month},
            asset_ids=source.asset_ids,
        )


class UserFacingIssueDto(BaseModel):
    """面向普通用户的最小问题投影，不携带内部命中或证据。"""

    category: UserIssueCategory
    message: str = Field(min_length=1, max_length=240)
    field: str | None = Field(default=None, max_length=64)
    action: str | None = Field(default=None, max_length=240)


class DomainStrategyDescriptorDto(BaseModel):
    domain_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    supplemental_input_schema: dict[str, Any] = Field(default_factory=dict)
    generation_context: str = ""
    quality_rules: list[str] = Field(default_factory=list)
    safety_policy: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)


class SourceFactDto(BaseModel):
    fact_id: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    kind: FactKind
    text: str = Field(min_length=1)


class FactLedgerDto(BaseModel):
    facts: list[SourceFactDto] = Field(default_factory=list)


class AccountProfileDto(BaseModel):
    account_id: UUID
    positioning: str = Field(min_length=1)
    tone: str = Field(min_length=1)
    domain_id: str = Field(default="parenting", min_length=1)
    domain_context: dict[str, Any] = Field(default_factory=dict)
    age_range_months: tuple[int, int] | None = None
    current_baby_month: int | None = Field(default=None, ge=0, le=240)
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
    # SourceExperience 是内容生成的事实源头；生成内容应能回溯到这里，
    # 而不是把模型的推测当成用户真实经历。
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
    field: str | None = Field(default=None, max_length=64)
    matched_text: str | None = None
    evidence_fact_ids: list[str] = Field(default_factory=list)


class ClaimAuditItemDto(BaseModel):
    field: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    support: ClaimSupport
    evidence_fact_ids: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    reason: str = ""
    level: RiskLevel = RiskLevel.NONE


class ReviewResultDto(BaseModel):
    passed: bool
    findings: list[ReviewFindingDto] = Field(default_factory=list)
    claim_audit: list[ClaimAuditItemDto] = Field(default_factory=list)
    source_digest: str | None = None
    content_digest: str | None = None
    audit_version: str | None = None
    policy_version: str | None = None


class FieldSuggestionDto(BaseModel):
    """只携带一个目标字段的 AI 候选及其审核元数据。"""

    suggestion_id: UUID
    note_id: UUID
    field: EditableField
    value: str | list[str]
    base_field_digest: str = Field(min_length=1)
    base_content_digest: str = Field(min_length=1)
    review: ReviewResultDto | None = None
    evidence: list[str] = Field(default_factory=list)
    evidence_fact_ids: list[str] = Field(default_factory=list)
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime


class SuggestionStatusUpdateDto(BaseModel):
    status: SuggestionStatus
    current_field_digest: str | None = None
    current_content_digest: str | None = None


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
    rewrite_rules: list[str] = Field(default_factory=list)
    tone: ToneProfile = Field(default_factory=ToneProfile)
    rich_text: RichTextProfile = Field(default_factory=RichTextProfile)
    tags: TagPool = Field(default_factory=TagPool)
    cover: CoverProfile = Field(default_factory=CoverProfile)
    cta: list[str] = Field(default_factory=list)


class UserResultProjectionDto(BaseModel):
    """普通客户端需要的内容结果；不包含 trace、review 或审计证据。"""

    note_id: UUID
    account_id: UUID
    column_id: UUID
    status: NoteStatus
    domain_id: str = "parenting"
    content_brief: ContentBriefDto
    focus: str
    topic_angle: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cover_copy: str = ""
    image_suggestions: list[str] = Field(default_factory=list)
    style_form: StyleForm | None = None
    issue: UserFacingIssueDto | None = None
    updated_at: datetime

    @classmethod
    def from_draft(cls, draft: "NoteDraftDto") -> "UserResultProjectionDto":
        assert draft.content_brief is not None
        return cls(
            note_id=draft.note_id,
            account_id=draft.account_id,
            column_id=draft.column_id,
            status=draft.status,
            domain_id=draft.domain_id,
            content_brief=draft.content_brief,
            focus=draft.content_brief.focus,
            topic_angle=draft.topic_angle,
            title_candidates=draft.title_candidates,
            body=draft.body,
            hashtags=draft.hashtags,
            cover_copy=draft.cover_copy,
            image_suggestions=draft.image_suggestions,
            style_form=draft.style_form,
            issue=draft.user_issue,
            updated_at=draft.updated_at,
        )


class AgentTraceStepDto(BaseModel):
    """API 层返回的 agent 步骤。"""

    # trace 只用于展示/调试，不能当作业务结果，也不应承载完整模型消息。

    order: int
    kind: str
    label: str
    summary: str
    phase: str | None = None


class StyledNoteResponseDto(BaseModel):
    """兼容内部调用的结果容器；普通 HTTP 响应只应消费 user_result。"""

    draft: NoteDraftDto
    user_result: UserResultProjectionDto | None = None
    # trace 保留给服务端内部调用，FastAPI 默认序列化时不会暴露它。
    # 授权调试接口可以直接读取 WorkflowResult.agent_trace。
    agent_trace: list[AgentTraceStepDto] = Field(default_factory=list, exclude=True)


class NoteDraftDto(BaseModel):
    # NoteDraft 是跨端主数据对象：它把账号、栏目、来源事实和生成字段绑定在一起。
    note_id: UUID
    account_id: UUID
    column_id: UUID
    status: NoteStatus
    domain_id: str = "parenting"
    topic_angle: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cover_copy: str = ""
    image_suggestions: list[str] = Field(default_factory=list)
    content_brief: ContentBriefDto | None = None
    # 旧 JSONB 和旧客户端仍可读取；新领域流程不依赖该字段。
    source: SourceExperienceDto | None = None
    # 旧 JSONB 草稿可能没有该键，因此必须保持可空并兼容读取。
    style_form: StyleForm | None = None
    review: ReviewResultDto | None = None
    user_issue: UserFacingIssueDto | None = None
    updated_at: datetime

    @model_validator(mode="after")
    def ensure_compatible_brief(self) -> "NoteDraftDto":
        if self.content_brief is None and self.source is not None:
            self.content_brief = ContentBriefDto.from_legacy_source(self.source)
        if self.content_brief is None:
            raise ValueError("content_brief_or_source_required")
        return self


class UserResultResponseDto(BaseModel):
    """普通客户端响应；只暴露结果和需要用户处理的最小问题集合。"""

    draft: UserResultProjectionDto
    issues: list[UserFacingIssueDto] = Field(default_factory=list)

    @classmethod
    def from_draft(cls, draft: NoteDraftDto) -> "UserResultResponseDto":
        projection = UserResultProjectionDto.from_draft(draft)
        return cls(
            draft=projection,
            issues=[projection.issue] if projection.issue is not None else [],
        )


class DraftVersionDto(BaseModel):
    version: int = Field(ge=1)
    topic_angle: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cover_copy: str = ""
    image_suggestions: list[str] = Field(default_factory=list)
    content_brief: ContentBriefDto | None = None
    style_form: StyleForm | None = None
    review: ReviewResultDto | None = None
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
