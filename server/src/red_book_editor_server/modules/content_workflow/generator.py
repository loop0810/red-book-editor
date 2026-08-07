from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import ValidationError

from red_book_editor_server.domain.contracts import NoteDraftDto, NoteStatus, SourceExperienceDto
from red_book_editor_server.domain.ports import ContentGenerator


class ContentGenerationError(RuntimeError):
    """模型超时或返回无法解析的结构化结果。"""


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


class StubContentGenerator:
    """本地开发和测试用生成器，生产环境替换为模型适配器。"""

    async def generate(
        self,
        source: SourceExperienceDto,
        *,
        account_id: UUID | None = None,
        column_id: UUID | None = None,
    ) -> NoteDraftDto:
        normalized = normalize_source(source)
        actions = "、".join(normalized.actions)
        return NoteDraftDto(
            note_id=uuid4(),
            account_id=account_id or uuid4(),
            column_id=column_id or uuid4(),
            status=NoteStatus.DRAFT,
            topic_angle=f"{normalized.baby_month}个月宝宝的{normalized.scenario}记录",
            title_candidates=[
                f"{normalized.baby_month}个月宝宝的{normalized.scenario}，我是这样做的",
                f"记录一次宝宝{normalized.scenario}：{actions}",
            ],
            body=(
                f"宝宝{normalized.baby_month}个月时，遇到了{normalized.scenario}。\n"
                f"我当时做了：{actions}。\n"
                f"{normalized.observations}"
            ).strip(),
            hashtags=["#育儿日常", f"#{normalized.baby_month}个月宝宝"],
            cover_copy=normalized.scenario,
            image_suggestions=["场景照片", "过程记录"],
            source=normalized,
            updated_at=datetime.now(UTC),
        )


async def generate_with_retry(
    generator: ContentGenerator,
    source: SourceExperienceDto,
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
                source,
                account_id=account_id,
                column_id=column_id,
            )
            return NoteDraftDto.model_validate(raw)
        except (TimeoutError, ValidationError, ValueError) as error:
            last_error = error
    raise ContentGenerationError("content_generation_failed") from last_error
