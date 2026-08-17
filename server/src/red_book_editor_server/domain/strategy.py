from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from red_book_editor_server.domain.contracts import (
    AccountProfileDto,
    ContentBriefDto,
    DomainStrategyDescriptorDto,
    UserFacingIssueDto,
    UserIssueCategory,
)


class DomainUnavailableError(ValueError):
    """账号引用的领域不存在、未启用或无法使用。"""

    def __init__(self, domain_id: str) -> None:
        super().__init__(f"domain_strategy_unavailable:{domain_id}")
        self.domain_id = domain_id


class DomainStrategyPack(Protocol):
    """领域差异的端口；通用内容流程不需要知道具体领域。"""

    @property
    def descriptor(self) -> DomainStrategyDescriptorDto: ...

    def validate_brief(self, brief: ContentBriefDto) -> None: ...

    def generation_context(
        self,
        brief: ContentBriefDto,
        account: AccountProfileDto | None,
        column_description: str,
    ) -> str: ...

    def project_issue(
        self,
        *,
        code: str,
        field: str | None,
        fallback_message: str,
    ) -> UserFacingIssueDto | None: ...


@dataclass(frozen=True)
class ParentingStrategyPack:
    """第一版育儿策略包，集中承载育儿补充字段和用户问题文案。"""

    descriptor: DomainStrategyDescriptorDto = field(
        default_factory=lambda: DomainStrategyDescriptorDto(
            domain_id="parenting",
            version="parenting-pack-v1",
            display_name="育儿",
            supplemental_input_schema={
                "baby_month": {"type": "integer", "minimum": 0, "maximum": 240},
                "care_scene": {"type": "string"},
            },
            generation_context="以照护经验为背景，避免把个人经历扩写成诊断、用药或普遍安全结论。",
            quality_rules=["focus_first", "source_fidelity", "natural_paraphrase"],
            safety_policy=["diagnosis_block", "medication_block", "unsafe_sleep_block"],
            allowed_tools=["load_style_profile", "suggest_tags", "critique_draft", "finalize_note"],
        )
    )

    def validate_brief(self, brief: ContentBriefDto) -> None:
        baby_month = brief.domain_context.get("baby_month")
        if baby_month is not None and (
            not isinstance(baby_month, int) or not 0 <= baby_month <= 240
        ):
            raise ValueError("invalid_parenting_baby_month")

    def generation_context(
        self,
        brief: ContentBriefDto,
        account: AccountProfileDto | None,
        column_description: str,
    ) -> str:
        values: list[str] = [self.descriptor.generation_context]
        baby_month = brief.domain_context.get("baby_month")
        if baby_month is not None:
            values.append(f"宝宝月龄：{baby_month}个月")
        care_scene = brief.domain_context.get("care_scene")
        if isinstance(care_scene, str) and care_scene.strip():
            values.append(f"照护场景：{care_scene.strip()}")
        if account is not None and account.domain_context:
            values.append(f"账号补充上下文：{_compact_mapping(account.domain_context)}")
        if column_description.strip():
            values.append(f"栏目上下文：{column_description.strip()}")
        return "；".join(values)

    def project_issue(
        self,
        *,
        code: str,
        field: str | None,
        fallback_message: str,
    ) -> UserFacingIssueDto | None:
        mapping: dict[str, tuple[UserIssueCategory, str, str | None]] = {
            "diagnosis": (
                UserIssueCategory.SAFETY,
                "这段内容涉及疾病判断，请改为记录个人经历。",
                "请删除诊断结论",
            ),
            "medication": (
                UserIssueCategory.SAFETY,
                "这段内容涉及用药建议，暂不能复制或导出。",
                "请删除药物、剂量或疗程建议",
            ),
            "sleep_safety": (
                UserIssueCategory.SAFETY,
                "这段内容涉及可能不安全的睡眠做法，请修改后再继续。",
                "请改为客观记录，不要给出可照做的安全结论",
            ),
            "product_safety_claim": (
                UserIssueCategory.SAFETY,
                "请删除产品绝对安全或适合所有人的结论。",
                "请改为基于实际体验的描述",
            ),
            "unsupported_claim": (
                UserIssueCategory.FACTS,
                "这段内容包含原始素材没有提供的经历或结论。",
                "请删除或补充对应事实",
            ),
            "fabricated_detail": (
                UserIssueCategory.FACTS,
                "请删除原始素材中没有出现的具体经历细节。",
                "请回到原始素材核对",
            ),
            "account_scope": (
                UserIssueCategory.DOMAIN,
                "这篇内容与当前账号定位不匹配，请调整主题或切换账号。",
                "请修改主题",
            ),
            "focus_alignment": (
                UserIssueCategory.FACTS,
                "标题需要更明确地围绕本次主题。",
                "请把主题放在标题开头",
            ),
        }
        category, message, action = mapping.get(
            code, (UserIssueCategory.REVIEW, fallback_message, "请修改后重试")
        )
        # warning/uncertain 等内部状态不生成用户问题；只有真正 blocking 的调用方才投影。
        return UserFacingIssueDto(category=category, message=message, field=field, action=action)


class DomainStrategyRegistry:
    def __init__(self, packs: Mapping[str, DomainStrategyPack] | None = None) -> None:
        self._packs = dict(packs or {"parenting": ParentingStrategyPack()})

    def resolve(self, domain_id: str) -> DomainStrategyPack:
        pack = self._packs.get(domain_id)
        if pack is None:
            raise DomainUnavailableError(domain_id)
        return pack

    def descriptors(self) -> list[DomainStrategyDescriptorDto]:
        return [pack.descriptor for pack in self._packs.values()]


def _compact_mapping(values: Mapping[str, Any]) -> str:
    return ", ".join(f"{key}={value}" for key, value in values.items())
