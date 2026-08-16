from __future__ import annotations

import hashlib
import json
import re

from red_book_editor_server.domain.contracts import (
    ClaimAuditItemDto,
    ClaimSupport,
    EditableField,
    FactKind,
    FactLedgerDto,
    NoteDraftDto,
    SourceExperienceDto,
    SourceFactDto,
)

AUDIT_VERSION = "fact-ledger-v1"
POLICY_VERSION = "parenting-safety-v1"

_BOUNDARY_FACTS = (
    ("unknown.medication", "source.unknown", FactKind.UNKNOWN, "药物名称、剂量和疗程"),
    ("unknown.medical", "source.unknown", FactKind.UNKNOWN, "医生诊断、具体医嘱和医疗结论"),
    ("unknown.environment", "source.unknown", FactKind.UNKNOWN, "未提供的环境、监护和安全结果"),
    ("unknown.product", "source.unknown", FactKind.UNKNOWN, "产品品牌、价格、材质和安全检测"),
    ("unknown.event", "source.unknown", FactKind.UNKNOWN, "未提供的地点、流程、细节和他人评价"),
    (
        "forbidden.inference",
        "policy.forbidden_inference",
        FactKind.FORBIDDEN_INFERENCE,
        "来源外的确定疗效、因果关系、普遍适用性和安全保证",
    ),
)


def build_fact_ledger(source: SourceExperienceDto) -> FactLedgerDto:
    """从用户来源派生只读事实账本；模型输出永远不会写回这里。"""

    facts: list[SourceFactDto] = [
        SourceFactDto(
            fact_id="source.baby_month",
            source_path="source.baby_month",
            kind=FactKind.CONFIRMED,
            text=f"{source.baby_month}个月",
        ),
        SourceFactDto(
            fact_id="source.scenario",
            source_path="source.scenario",
            kind=FactKind.CONFIRMED,
            text=source.scenario.strip(),
        ),
    ]
    facts.extend(
        SourceFactDto(
            fact_id=f"source.actions[{index}]",
            source_path=f"source.actions[{index}]",
            kind=FactKind.CONFIRMED,
            text=action.strip(),
        )
        for index, action in enumerate(source.actions)
        if action.strip()
    )
    if source.observations.strip():
        facts.append(
            SourceFactDto(
                fact_id="source.observations",
                source_path="source.observations",
                kind=FactKind.OBSERVED,
                text=source.observations.strip(),
            )
        )
    if source.notes.strip():
        facts.append(
            SourceFactDto(
                fact_id="source.notes",
                source_path="source.notes",
                kind=FactKind.OPINION,
                text=source.notes.strip(),
            )
        )
    facts.extend(
        SourceFactDto(fact_id=fact_id, source_path=path, kind=kind, text=text)
        for fact_id, path, kind, text in _BOUNDARY_FACTS
    )
    return FactLedgerDto(facts=facts)


def source_digest(source: SourceExperienceDto) -> str:
    return _digest(source.model_dump(mode="json"))


def content_digest(draft: NoteDraftDto) -> str:
    payload = {
        "topic_angle": draft.topic_angle,
        "title_candidates": draft.title_candidates,
        "body": draft.body,
        "hashtags": draft.hashtags,
        "cover_copy": draft.cover_copy,
        "image_suggestions": draft.image_suggestions,
        "style_form": draft.style_form.value if draft.style_form else None,
    }
    return _digest(payload)


def field_value(draft: NoteDraftDto, field: EditableField) -> str | list[str]:
    if field is EditableField.TITLE:
        return draft.title_candidates
    if field is EditableField.BODY:
        return draft.body
    if field is EditableField.HASHTAGS:
        return draft.hashtags
    return draft.cover_copy


def field_digest(draft: NoteDraftDto, field: EditableField) -> str:
    return _digest(field_value(draft, field))


def audit_claims(draft: NoteDraftDto, ledger: FactLedgerDto) -> list[ClaimAuditItemDto]:
    """对生成文本做保守的来源匹配；安全级别由 review 层的政策规则决定。"""

    source_facts = [
        fact
        for fact in ledger.facts
        if fact.kind in (FactKind.CONFIRMED, FactKind.OBSERVED, FactKind.OPINION)
    ]
    audited: list[ClaimAuditItemDto] = []
    for field, text in _draft_text_fields(draft):
        for claim in _claim_segments(text):
            evidence = [fact for fact in source_facts if _contains_fact(fact.text, claim)]
            if evidence:
                audited.append(
                    ClaimAuditItemDto(
                        field=field,
                        claim=claim,
                        support=ClaimSupport.SUPPORTED,
                        evidence_fact_ids=[fact.fact_id for fact in evidence],
                        evidence=[fact.text for fact in evidence],
                    )
                )
                continue
            support = (
                ClaimSupport.UNCERTAIN
                if _contains_uncertainty_marker(claim)
                else ClaimSupport.UNSUPPORTED
            )
            audited.append(
                ClaimAuditItemDto(
                    field=field,
                    claim=claim,
                    support=support,
                    reason="未找到对应的来源事实"
                    if support is ClaimSupport.UNSUPPORTED
                    else "无法确认是否超出来源事实",
                )
            )
    return audited


def _draft_text_fields(draft: NoteDraftDto) -> list[tuple[str, str]]:
    fields: list[tuple[str, str]] = [("topic_angle", draft.topic_angle), ("body", draft.body)]
    fields.extend(
        (f"title_candidates[{index}]", title) for index, title in enumerate(draft.title_candidates)
    )
    fields.extend((f"hashtags[{index}]", tag) for index, tag in enumerate(draft.hashtags))
    fields.append(("cover_copy", draft.cover_copy))
    return fields


def _claim_segments(text: str) -> list[str]:
    segments: list[str] = []
    for raw in re.split(r"[\n。！？!?；;]+", text):
        claim = raw.strip(" \t，,：:、")
        if len(_compact(claim)) >= 4 and not claim.startswith("#"):
            segments.append(claim[:240])
    return segments


def _contains_fact(fact: str, claim: str) -> bool:
    compact_fact = _compact(fact)
    compact_claim = _compact(claim)
    if not compact_fact or not compact_claim:
        return False
    if compact_fact in compact_claim:
        return True
    # 允许常见的“了/的/地”语法变化，但不把空字符串当成证据。
    reduced_fact = re.sub(r"[了的地]", "", compact_fact)
    reduced_claim = re.sub(r"[了的地]", "", compact_claim)
    return len(reduced_fact) >= 2 and reduced_fact in reduced_claim


def _contains_uncertainty_marker(claim: str) -> bool:
    return bool(re.search(r"可能|也许|似乎|感觉|好像|不确定|看起来|或许", claim))


def _compact(value: str) -> str:
    return re.sub(r"[\s，。！？、,.!?；;：:（）()\[\]【】《》“”‘’\"'…·]", "", value).lower()


def _digest(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
