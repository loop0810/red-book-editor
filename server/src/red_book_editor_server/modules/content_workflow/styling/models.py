from __future__ import annotations

from pydantic import BaseModel, Field

from red_book_editor_server.domain.contracts import SourceExperienceDto, StyleForm


class DraftContent(BaseModel):
    """agent 起草的完整笔记内容。"""

    topic_angle: str = ""
    title_candidates: list[str] = Field(default_factory=list)
    body: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cover_copy: str = ""


class CritiqueArgs(BaseModel):
    form: StyleForm
    draft: DraftContent
    source: SourceExperienceDto


class CritiqueResult(BaseModel):
    scores: dict[str, int]
    issues: list[str] = Field(default_factory=list)
    passed: bool


class FinalizeArgs(BaseModel):
    """最终结构化输出的入参，也是最终回答的 JSON 结构。"""

    form: StyleForm
    draft: DraftContent
    image_suggestions: list[str] = Field(default_factory=list)


class SuggestTagsArgs(BaseModel):
    topic: str
    form: StyleForm


class StyleFormArg(BaseModel):
    form: StyleForm


class TitleFieldResult(BaseModel):
    """标题字段重生成的唯一结构化结果。"""

    title_candidates: list[str] = Field(min_length=1)


class BodyFieldResult(BaseModel):
    """正文单字段重生成结果。"""

    body: str = Field(min_length=1)


class HashtagsFieldResult(BaseModel):
    """话题单字段重生成结果。"""

    hashtags: list[str] = Field(min_length=1)


class CoverCopyFieldResult(BaseModel):
    """封面文案单字段重生成结果。"""

    cover_copy: str = Field(min_length=1)
