from __future__ import annotations

import re

from red_book_editor_server.domain.contracts import (
    NoteDraftDto,
    NoteStatus,
    ReviewFindingDto,
    ReviewResultDto,
    RiskLevel,
)

_DIAGNOSIS_PATTERNS = (r"是不是.+病", r"判断.+疾病", r"诊断", r"什么病")
_MEDICATION_PATTERNS = (r"吃什么药", r"用什么药", r"药量", r"剂量", r"用药", r"疗程")
_GUARANTEE_PATTERNS = (r"一定有效", r"保证治好", r"百分之百", r"最有效", r"根治")

# 模型辅助检查在未接入模型适配器时使用确定性启发式回退。
# 覆盖账号定位偏离 / 未经来源支持的结论 / 制造焦虑的表达。
_ACCOUNT_SCOPE_PATTERNS = (r"小学|初中|高中|考研|工作|职场|婚姻|恋爱|减肥|护肤|化妆|穿搭",)
_UNSUPPORTED_CLAIM_PATTERNS = (
    r"研究表明|专家建议|专家说|医生建议|医生说|调查显示|数据表明|很多家长都说",
    r"保证有效|一定可以|坚持.{1,8}(天|周).{0,6}(就|会)(好|有效|退|睡)",
)
_ANXIETY_PATTERNS = (r"太吓人|千万不要|千万别|必须马上|非常危险|会出事|后悔|焦虑|恐慌|吓死",)


class DeterministicContentReviewer:
    """执行不依赖模型的第一层内容风险检查。"""

    def review(self, draft: NoteDraftDto) -> ReviewResultDto:
        text = "\n".join([draft.topic_angle, *draft.title_candidates, draft.body, *draft.hashtags])
        findings: list[ReviewFindingDto] = []
        findings.extend(self._find(text, _DIAGNOSIS_PATTERNS, "diagnosis", "内容不能进行疾病判断"))
        findings.extend(
            self._find(text, _MEDICATION_PATTERNS, "medication", "内容不能提供用药建议")
        )
        findings.extend(
            self._find(
                text,
                _GUARANTEE_PATTERNS,
                "guarantee",
                "请删除保证性或绝对化效果表达",
                RiskLevel.WARNING,
            )
        )
        passed = not any(finding.level is RiskLevel.BLOCKING for finding in findings)
        return ReviewResultDto(passed=passed, findings=findings)

    def _find(
        self,
        text: str,
        patterns: tuple[str, ...],
        code: str,
        message: str,
        level: RiskLevel = RiskLevel.BLOCKING,
    ) -> list[ReviewFindingDto]:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return [
                    ReviewFindingDto(
                        level=level,
                        code=code,
                        message=message,
                        matched_text=match.group(0),
                    )
                ]
        return []


class ModelAssistedContentReviewer:
    """模型辅助检查: 账号定位偏离, 未经来源支持的结论, 制造焦虑的表达。

    当前环境未配置模型适配器, 先使用确定性启发式规则作为回退实现。
    后续接入模型适配器时保持同一个 review 接口并返回相同结构化 findings。
    """

    async def review(self, draft: NoteDraftDto) -> ReviewResultDto:
        text = "\n".join([draft.topic_angle, *draft.title_candidates, draft.body, *draft.hashtags])
        findings: list[ReviewFindingDto] = []
        findings.extend(
            self._find(
                text,
                _ACCOUNT_SCOPE_PATTERNS,
                "account_scope",
                "内容偏离0-2岁育儿账号定位, 请确认或调整主题",
                RiskLevel.WARNING,
            )
        )
        findings.extend(
            self._find(
                text,
                _UNSUPPORTED_CLAIM_PATTERNS,
                "unsupported_claim",
                "请删除来源经历中不存在的结论、结果或外部背书",
            )
        )
        findings.extend(
            self._find(
                text,
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
        text: str,
        patterns: tuple[str, ...],
        code: str,
        message: str,
        level: RiskLevel = RiskLevel.BLOCKING,
    ) -> list[ReviewFindingDto]:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return [
                    ReviewFindingDto(
                        level=level,
                        code=code,
                        message=message,
                        matched_text=match.group(0),
                    )
                ]
        return []


async def review_draft(draft: NoteDraftDto) -> ReviewResultDto:
    """合并确定性检查和模型辅助检查的结果, 按 code 去重。"""

    deterministic = DeterministicContentReviewer().review(draft)
    model_assisted = await ModelAssistedContentReviewer().review(draft)
    findings_by_code = {
        finding.code: finding for finding in [*deterministic.findings, *model_assisted.findings]
    }
    findings = list(findings_by_code.values())
    passed = not any(finding.level is RiskLevel.BLOCKING for finding in findings)
    return ReviewResultDto(passed=passed, findings=findings)


def status_for_review(review: ReviewResultDto | None) -> NoteStatus:
    """把审核结果集中映射为草稿状态。

    ``passed`` 只表示没有 blocking；warning 仍然要求人工复核，
    而没有审核结果绝不能被当成 ready。
    """

    if review is None:
        return NoteStatus.NEEDS_REVIEW
    if not review.passed or any(
        finding.level in (RiskLevel.BLOCKING, RiskLevel.WARNING) for finding in review.findings
    ):
        return NoteStatus.NEEDS_REVIEW
    return NoteStatus.READY
