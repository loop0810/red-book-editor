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
