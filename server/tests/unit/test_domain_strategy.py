from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from red_book_editor_server.domain.contracts import (
    AccountProfileDto,
    ContentBriefDto,
    ContentColumnDto,
    DomainStrategyDescriptorDto,
    StyleForm,
    UserIssueCategory,
    UserFacingIssueDto,
)
from red_book_editor_server.domain.strategy import (
    DomainStrategyRegistry,
    DomainUnavailableError,
)
from red_book_editor_server.modules.content_workflow.service import ContentWorkflowService


class _FutureDomainPack:
    descriptor = DomainStrategyDescriptorDto(
        domain_id="travel",
        version="travel-pack-v1",
        display_name="旅行",
        supplemental_input_schema={"destination": {"type": "string"}},
        generation_context="以旅行见闻为背景。",
        quality_rules=["focus_first"],
        safety_policy=["source_fidelity"],
        allowed_tools=[],
    )

    def validate_brief(self, brief: ContentBriefDto) -> None:
        if not isinstance(brief.domain_context.get("destination"), str):
            raise ValueError("destination_required")

    def generation_context(
        self,
        brief: ContentBriefDto,
        account: AccountProfileDto | None,
        column_description: str,
    ) -> str:
        return f"目的地：{brief.domain_context['destination']}"

    def project_issue(
        self,
        *,
        code: str,
        field: str | None,
        fallback_message: str,
    ) -> UserFacingIssueDto | None:
        return UserFacingIssueDto(
            category=UserIssueCategory.FACTS,
            message=fallback_message,
            field=field,
            action="请回到原始素材核对",
        )


class _FutureDomainContext:
    async def get_account(self, account_id: UUID) -> AccountProfileDto:
        return AccountProfileDto(
            account_id=account_id,
            domain_id="travel",
            positioning="城市周末旅行记录",
            tone="克制真实",
        )

    async def get_column(self, account_id: UUID, column_id: UUID) -> ContentColumnDto:
        return ContentColumnDto(
            column_id=column_id,
            account_id=account_id,
            name="周末路线",
            description="记录真实路线和体验",
        )


def test_unavailable_domain_does_not_fall_back_to_parenting() -> None:
    with pytest.raises(DomainUnavailableError):
        DomainStrategyRegistry().resolve("travel")


@pytest.mark.asyncio
async def test_generic_workflow_accepts_future_domain_context_without_branching() -> None:
    account_id = UUID("00000000-0000-0000-0000-000000000001")
    column_id = UUID("00000000-0000-0000-0000-000000000002")
    result = await ContentWorkflowService(
        context=_FutureDomainContext(),
        strategy_registry=DomainStrategyRegistry({"travel": _FutureDomainPack()}),
    ).generate(
        account_id=account_id,
        column_id=column_id,
        brief=ContentBriefDto(
            focus="周末海边路线",
            raw_material="从市区坐地铁到海边，傍晚返回。",
            domain_context={"destination": "海边"},
        ),
        form=StyleForm.EXPERIENCE,
    )

    assert result.draft.domain_id == "travel"
    assert result.draft.content_brief is not None
    assert result.draft.content_brief.domain_context["destination"] == "海边"
    assert result.draft.updated_at > datetime(2026, 1, 1, tzinfo=UTC)
