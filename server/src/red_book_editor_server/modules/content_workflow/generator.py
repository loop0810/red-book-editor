from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from red_book_editor_server.domain.contracts import (
    ContentBriefDto,
    NoteDraftDto,
    NoteStatus,
    SourceExperienceDto,
)
from red_book_editor_server.domain.ports import ContentGenerator


class ContentGenerationError(RuntimeError):
    """模型超时或返回无法解析的结构化结果。"""

    def __init__(self, message: str, *, agent_error: Exception | None = None) -> None:
        super().__init__(message)
        self.agent_error = agent_error


def normalize_source(source: SourceExperienceDto) -> SourceExperienceDto:
    """清理空白但不补写用户没有提供的事实。"""

    return source.model_copy(
        update={
            "scenario": source.scenario.strip(),
            "actions": [action.strip() for action in source.actions if action.strip()],
            "observations": source.observations.strip(),
            "notes": source.notes.strip(),
        }
    )


def normalize_content_brief(
    brief: ContentBriefDto | SourceExperienceDto,
) -> tuple[ContentBriefDto, SourceExperienceDto | None]:
    """把旧来源转换到通用边界，并保留旧对象用于兼容存量草稿。"""

    if isinstance(brief, SourceExperienceDto):
        normalized_source = normalize_source(brief)
        return ContentBriefDto.from_legacy_source(normalized_source), normalized_source
    return brief.model_copy(
        update={
            "focus": brief.focus.strip(),
            "raw_material": brief.raw_material.strip(),
            "domain_context": dict(brief.domain_context),
        }
    ), None


class StubContentGenerator:
    """离线开发和测试用生成器；它不代表 DeepSeek 的真实写作能力。

    即使在没有模型的环境里，也必须完整保留用户素材，避免把离线样例误认为
    成功生成了一篇完整的小红书内容。
    """

    async def generate(
        self,
        brief: ContentBriefDto | SourceExperienceDto,
        *,
        account_id: UUID | None = None,
        column_id: UUID | None = None,
    ) -> NoteDraftDto:
        normalized, legacy_source = normalize_content_brief(brief)
        focus = normalized.focus
        material = normalized.raw_material
        clauses = _material_clauses(material)
        focus_tag = _focus_tag(focus)
        body_sections = [
            f"这次想记录的是：{focus}。",
            "\n".join(f"· {clause}" for clause in clauses),
            "这篇先把原始素材完整整理下来，方便之后继续补充细节。",
        ]
        return NoteDraftDto(
            note_id=uuid4(),
            account_id=account_id or uuid4(),
            column_id=column_id or uuid4(),
            status=NoteStatus.DRAFT,
            topic_angle=focus,
            title_candidates=[
                f"{focus}｜这次经历，我想完整记录下来",
                f"{focus}：把过程、选择和变化写清楚",
                f"关于{focus}，一篇不删细节的真实记录",
            ],
            body="\n\n".join(section for section in body_sections if section).strip(),
            hashtags=[f"#{focus_tag}", "#真实记录", "#生活分享", "#经验分享"],
            cover_copy=f"{focus}\n这次经历完整记录",
            image_suggestions=[
                f"封面：拍下与“{focus}”直接相关的主画面",
                f"过程：记录素材中提到的关键环节或物件（{clauses[0]}）",
                f"细节：补一张能对应正文细节的近景（{clauses[-1]}）",
                "收尾：保留一张自然状态照，和正文最后一段呼应",
            ],
            content_brief=normalized,
            source=legacy_source,
            updated_at=datetime.now(UTC),
        )


def _material_clauses(material: str) -> list[str]:
    clauses = [
        clause.strip() for clause in re.split(r"[\n。！？!?；;]+", material) if clause.strip()
    ]
    return clauses or [material.strip()]


def _focus_tag(focus: str) -> str:
    tag = re.sub(r"[\s，。！？、,.!?；;：:（）()\[\]【】]+", "", focus)
    return tag[:24] or "真实记录"


async def generate_with_retry(
    generator: ContentGenerator,
    brief: ContentBriefDto | SourceExperienceDto,
    *,
    account_id: UUID,
    column_id: UUID,
    max_attempts: int = 2,
) -> NoteDraftDto:
    """重试短暂的模型失败，并在失败时保留原始 source。"""

    attempts = max(1, max_attempts)
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            raw = await generator.generate(
                brief,
                account_id=account_id,
                column_id=column_id,
            )
            return NoteDraftDto.model_validate(raw)
        except (TimeoutError, ValidationError, ValueError) as error:
            last_error = error
    raise ContentGenerationError("content_generation_failed") from last_error
