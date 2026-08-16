from __future__ import annotations

import re

from red_book_editor_server.domain.contracts import (
    ClaimAuditItemDto,
    ClaimSupport,
    NoteDraftDto,
    NoteStatus,
    ReviewFindingDto,
    ReviewResultDto,
    RiskLevel,
)
from red_book_editor_server.modules.content_workflow.fact_ledger import (
    AUDIT_VERSION,
    POLICY_VERSION,
    audit_claims,
    build_fact_ledger,
    content_digest,
    source_digest,
)

_DIAGNOSIS_PATTERNS = (r"是不是.+病", r"判断.+疾病", r"诊断", r"什么病")
_MEDICATION_PATTERNS = (r"吃什么药", r"用什么药", r"药量", r"剂量", r"用药", r"疗程")
_GUARANTEE_PATTERNS = (r"一定有效", r"保证治好", r"百分之百", r"最有效", r"根治")
_SLEEP_RECOUNT_PATTERNS = (
    r"趴在(?:我|成人|大人|妈妈|爸爸)?身上(?:睡|睡觉|睡着)",
    r"让宝宝趴在身上",
)
_SLEEP_RECOMMENDATION_PATTERNS = (
    r"安全前提",
    r"可以(?:让|在).{0,12}趴(?:在|着).{0,12}(睡|睡觉)",
    r"推荐.{0,12}趴睡",
    r"照做",
    r"放心",
)
_PRODUCT_SAFETY_PATTERNS = (
    r"绝对安全",
    r"安全无忧",
    r"适合所有",
    r"所有宝宝",
    r"促进.{0,8}(发育|爬行|站立|走路)",
    r"一定能.{0,8}(发育|爬行|站立|走路)",
)
_EXTERNAL_BACKING_PATTERNS = (
    r"研究表明",
    r"专家(?:建议|说|表示)",
    r"医生(?:建议|说|表示)",
    r"调查显示",
    r"数据表明",
    r"很多家长都说",
)
_FABRICATED_DETAIL_PATTERNS = (
    r"抓周",
    r"宴会.{0,8}(场地|布置|菜品|流程)",
    r"(场地|布置|菜品|流程).{0,8}(宴会|周岁)",
    r"亲友.{0,8}(祝福|评价)",
)
_ACCOUNT_SCOPE_PATTERNS = (r"小学|初中|高中|考研|工作|职场|婚姻|恋爱|减肥|护肤|化妆|穿搭",)
_ANXIETY_PATTERNS = (r"太吓人|千万不要|千万别|必须马上|非常危险|会出事|后悔|焦虑|恐慌|吓死",)
_MEDICAL_CONTEXT_PATTERNS = (r"发烧|高烧|退烧|湿疹|尿布疹|医院|退烧药|用药",)


class DeterministicContentReviewer:
    """执行不依赖模型的第一层内容和领域风险检查。"""

    def review(self, draft: NoteDraftDto) -> ReviewResultDto:
        findings: list[ReviewFindingDto] = []
        findings.extend(self._find(draft, _DIAGNOSIS_PATTERNS, "diagnosis", "内容不能进行疾病判断"))
        findings.extend(
            self._find(draft, _MEDICATION_PATTERNS, "medication", "内容不能提供用药建议")
        )
        findings.extend(
            self._find(
                draft,
                _GUARANTEE_PATTERNS,
                "guarantee",
                "请删除保证性或绝对化效果表达",
                RiskLevel.WARNING,
            )
        )
        findings.extend(
            self._find(
                draft,
                _MEDICAL_CONTEXT_PATTERNS,
                "medical_context",
                "医疗相关经历需要人工复核，不能扩展为普遍建议",
                RiskLevel.WARNING,
            )
        )
        findings.extend(self._sleep_findings(draft))
        findings.extend(
            self._find(
                draft,
                _PRODUCT_SAFETY_PATTERNS,
                "product_safety_claim",
                "不能保证产品绝对安全、适合所有宝宝或促进发育",
            )
        )
        findings.extend(
            self._find(
                draft,
                _EXTERNAL_BACKING_PATTERNS,
                "external_backing",
                "不能伪造研究、医生或专家背书",
            )
        )
        findings.extend(
            self._find(
                draft,
                _FABRICATED_DETAIL_PATTERNS,
                "fabricated_detail",
                "请删除来源经历中没有提供的活动细节",
            )
        )
        passed = not any(finding.level is RiskLevel.BLOCKING for finding in findings)
        return ReviewResultDto(passed=passed, findings=findings)

    def _sleep_findings(self, draft: NoteDraftDto) -> list[ReviewFindingDto]:
        for field, text in _draft_text_fields(draft):
            match = _first_match(text, _SLEEP_RECOUNT_PATTERNS)
            if match is None:
                continue
            level = (
                RiskLevel.BLOCKING
                if _first_match(text, _SLEEP_RECOMMENDATION_PATTERNS)
                else RiskLevel.WARNING
            )
            message = (
                "不能把让宝宝趴在成人身上睡觉包装成可复制的安全方法"
                if level is RiskLevel.BLOCKING
                else "涉及成人接触睡眠方式，请人工确认睡眠安全边界"
            )
            return [
                ReviewFindingDto(
                    level=level,
                    code="sleep_safety",
                    message=message,
                    field=field,
                    matched_text=match,
                )
            ]
        return []

    def _find(
        self,
        draft: NoteDraftDto,
        patterns: tuple[str, ...],
        code: str,
        message: str,
        level: RiskLevel = RiskLevel.BLOCKING,
    ) -> list[ReviewFindingDto]:
        for field, text in _draft_text_fields(draft):
            match = _first_match(text, patterns)
            if match is not None:
                return [
                    ReviewFindingDto(
                        level=level,
                        code=code,
                        message=message,
                        field=field,
                        matched_text=match,
                    )
                ]
        return []


class ModelAssistedContentReviewer:
    """保留模型辅助审核接口；当前使用确定性规则作为可重复回退实现。"""

    async def review(self, draft: NoteDraftDto) -> ReviewResultDto:
        findings: list[ReviewFindingDto] = []
        findings.extend(
            self._find(
                draft,
                _ACCOUNT_SCOPE_PATTERNS,
                "account_scope",
                "内容偏离0-2岁育儿账号定位, 请确认或调整主题",
                RiskLevel.WARNING,
            )
        )
        findings.extend(
            self._find(
                draft,
                (*_EXTERNAL_BACKING_PATTERNS, *_FABRICATED_DETAIL_PATTERNS),
                "unsupported_claim",
                "请删除来源经历中不存在的结论、结果、细节或外部背书",
            )
        )
        findings.extend(
            self._find(
                draft,
                _ANXIETY_PATTERNS,
                "anxiety_language",
                "请避免制造焦虑的表达, 改用平静的描述",
                RiskLevel.WARNING,
            )
        )
        passed = not any(finding.level is RiskLevel.BLOCKING for finding in findings)
        return ReviewResultDto(passed=passed, findings=findings)

    def _find(
        self,
        draft: NoteDraftDto,
        patterns: tuple[str, ...],
        code: str,
        message: str,
        level: RiskLevel = RiskLevel.BLOCKING,
    ) -> list[ReviewFindingDto]:
        for field, text in _draft_text_fields(draft):
            match = _first_match(text, patterns)
            if match is not None:
                return [
                    ReviewFindingDto(
                        level=level,
                        code=code,
                        message=message,
                        field=field,
                        matched_text=match,
                    )
                ]
        return []


async def review_draft(draft: NoteDraftDto) -> ReviewResultDto:
    """统一生成事实账本、声明审计和内容安全结果。"""

    ledger = build_fact_ledger(draft.source)
    claim_audit = audit_claims(draft, ledger)
    deterministic = DeterministicContentReviewer().review(draft)
    model_assisted = await ModelAssistedContentReviewer().review(draft)
    claim_findings = _claim_findings(claim_audit)
    findings_by_key = {
        (finding.code, finding.field, finding.matched_text): finding
        for finding in [*deterministic.findings, *model_assisted.findings, *claim_findings]
    }
    findings = list(findings_by_key.values())
    passed = not any(finding.level is RiskLevel.BLOCKING for finding in findings)
    return ReviewResultDto(
        passed=passed,
        findings=findings,
        claim_audit=claim_audit,
        source_digest=source_digest(draft.source),
        content_digest=content_digest(draft),
        audit_version=AUDIT_VERSION,
        policy_version=POLICY_VERSION,
    )


def status_for_review(
    review: ReviewResultDto | None, draft: NoteDraftDto | None = None
) -> NoteStatus:
    """把审核结果、声明审计和版本指纹集中映射为草稿状态。"""

    if review is None:
        return NoteStatus.NEEDS_REVIEW
    if not review.passed or any(
        finding.level in (RiskLevel.BLOCKING, RiskLevel.WARNING) for finding in review.findings
    ):
        return NoteStatus.NEEDS_REVIEW
    if any(
        item.support is not ClaimSupport.SUPPORTED
        or item.level in (RiskLevel.BLOCKING, RiskLevel.WARNING)
        for item in review.claim_audit
    ):
        return NoteStatus.NEEDS_REVIEW
    if not _has_audit_metadata(review):
        return NoteStatus.NEEDS_REVIEW
    if draft is not None and not review_matches_draft(review, draft):
        return NoteStatus.NEEDS_REVIEW
    return NoteStatus.READY


def review_matches_draft(review: ReviewResultDto | None, draft: NoteDraftDto) -> bool:
    return bool(
        review
        and _has_audit_metadata(review)
        and review.source_digest == source_digest(draft.source)
        and review.content_digest == content_digest(draft)
    )


def _claim_findings(claim_audit: list[ClaimAuditItemDto]) -> list[ReviewFindingDto]:
    findings: list[ReviewFindingDto] = []
    for item in claim_audit:
        risk = _claim_risk(item.claim)
        if item.support is ClaimSupport.SUPPORTED and risk is RiskLevel.NONE:
            continue
        if risk is RiskLevel.NONE:
            risk = RiskLevel.WARNING
        item.level = risk
        if item.support is ClaimSupport.UNCERTAIN:
            code = "uncertain_claim"
            message = "这段内容无法确认是否超出来源事实，请人工复核"
        elif item.support is ClaimSupport.UNSUPPORTED:
            code = "unsupported_claim"
            message = "这段内容没有找到对应的来源事实"
        else:
            code = "claim_safety"
            message = "这段内容触发了育儿领域安全规则"
        findings.append(
            ReviewFindingDto(
                level=risk,
                code=code,
                message=message,
                field=_normalize_field(item.field),
                matched_text=item.claim,
                evidence_fact_ids=item.evidence_fact_ids,
            )
        )
    return findings


def _claim_risk(claim: str) -> RiskLevel:
    if _first_match(claim, _DIAGNOSIS_PATTERNS + _MEDICATION_PATTERNS):
        return RiskLevel.BLOCKING
    if _first_match(claim, _PRODUCT_SAFETY_PATTERNS + _EXTERNAL_BACKING_PATTERNS):
        return RiskLevel.BLOCKING
    if _first_match(claim, _FABRICATED_DETAIL_PATTERNS):
        return RiskLevel.BLOCKING
    if _first_match(claim, _SLEEP_RECOUNT_PATTERNS):
        return (
            RiskLevel.BLOCKING
            if _first_match(claim, _SLEEP_RECOMMENDATION_PATTERNS)
            else RiskLevel.WARNING
        )
    if _first_match(claim, _GUARANTEE_PATTERNS):
        return RiskLevel.WARNING
    return RiskLevel.NONE


def _has_audit_metadata(review: ReviewResultDto) -> bool:
    return bool(
        review.source_digest
        and review.content_digest
        and review.audit_version == AUDIT_VERSION
        and review.policy_version == POLICY_VERSION
    )


def _draft_text(draft: NoteDraftDto) -> str:
    return "\n".join(text for _, text in _draft_text_fields(draft))


def _draft_text_fields(draft: NoteDraftDto) -> list[tuple[str, str]]:
    return [
        ("topic_angle", draft.topic_angle),
        ("title", "\n".join(draft.title_candidates)),
        ("body", draft.body),
        ("hashtags", " ".join(draft.hashtags)),
        ("cover_copy", draft.cover_copy),
    ]


def _normalize_field(field: str) -> str:
    if field.startswith("title_candidates"):
        return "title"
    if field.startswith("hashtags"):
        return "hashtags"
    return field


def _first_match(text: str, patterns: tuple[str, ...]) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None
