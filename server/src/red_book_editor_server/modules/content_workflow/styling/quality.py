from __future__ import annotations

import re

from red_book_editor_server.domain.contracts import ContentBriefDto, SourceExperienceDto

_CLAUSE_SEPARATOR = re.compile(r"[。！？!?；;\n]+")
_PUNCTUATION = re.compile(r"[\s，。！？、,.!?；;：:（）()\[\]【】《》“”‘’\"'…·]+")


def source_overlap_issues(
    source: ContentBriefDto | SourceExperienceDto,
    body: str,
) -> list[str]:
    """Detect copied source spans without treating short facts as plagiarism."""

    material = _material(source)
    source_clauses = [
        _compact(clause)
        for clause in _CLAUSE_SEPARATOR.split(material)
        if len(_compact(clause)) >= 16
    ]
    if not source_clauses:
        return []
    normalized_body = _compact(body)
    copied = [clause for clause in source_clauses if clause in normalized_body]
    if not copied:
        return []

    first_paragraph = body.split("\n\n", 1)[0]
    normalized_opening = _compact(first_paragraph)
    opening_copy = [clause for clause in copied if clause in normalized_opening]
    material_length = len(_compact(material))
    copied_length = sum(len(clause) for clause in copied)
    overlap_ratio = copied_length / max(1, material_length)
    if opening_copy:
        return ["正文开头直接复用了原始素材，需要重新组织开场和内容角度"]
    if len(copied) >= 2 and overlap_ratio >= 0.55:
        return ["正文连续复用了较多原始素材，不能只拆段或增加连接词"]
    if any(len(clause) >= 32 for clause in copied):
        return ["正文包含较长的原始句子复用，需要改写表达"]
    return []


def enrichment_issues(
    source: ContentBriefDto | SourceExperienceDto,
    body: str,
) -> list[str]:
    """Require a usable editorial structure while keeping short input viable."""

    paragraphs = [paragraph.strip() for paragraph in body.split("\n\n") if paragraph.strip()]
    has_structural_marker = bool(re.search(r"(?m)^\s*(?:\d+[.、．)）]|[•·●◆])", body))
    issues: list[str] = []
    if len(body.strip()) < 60:
        issues.append("正文过短，无法把粗略素材整理成可直接使用的内容")
    if len(paragraphs) < 3 and not has_structural_marker:
        issues.append("正文需要形成开头、过程细节和收束，不能只保留一段素材复述")
    if not body.strip():
        issues.append("正文不能为空")
    return issues


def _material(source: ContentBriefDto | SourceExperienceDto) -> str:
    if isinstance(source, ContentBriefDto):
        return source.raw_material.strip()
    return "；".join(
        part.strip()
        for part in [*source.actions, source.observations, source.notes]
        if part.strip()
    )


def _compact(value: str) -> str:
    return _PUNCTUATION.sub("", value).lower()
