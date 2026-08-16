from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from pydantic import BaseModel

from red_book_editor_server.domain.contracts import (
    AccountProfileDto,
    ContentColumnDto,
    NoteDraftDto,
    SourceExperienceDto,
    StyleForm,
)

if TYPE_CHECKING:
    from red_book_editor_server.domain.agent_runs import (
        AgentRunEventRecord,
        AgentRunLifecycleStatus,
        AgentRunRecord,
    )


class ContentGenerator(Protocol):
    async def generate(
        self,
        source: SourceExperienceDto,
        *,
        account_id: UUID | None = None,
        column_id: UUID | None = None,
    ) -> NoteDraftDto: ...


class NoteRepository(Protocol):
    async def get(self, note_id: UUID) -> NoteDraftDto | None: ...

    async def list_for_account(self, account_id: UUID) -> Sequence[NoteDraftDto]: ...

    async def create(self, draft: NoteDraftDto) -> NoteDraftDto: ...

    async def save(self, draft: NoteDraftDto) -> NoteDraftDto: ...


class AgentRunRepository(Protocol):
    async def create(
        self,
        *,
        note_id: UUID,
        account_id: UUID,
        column_id: UUID,
        form: StyleForm,
    ) -> AgentRunRecord: ...

    async def get(self, run_id: UUID) -> AgentRunRecord | None: ...

    async def mark_running(self, run_id: UUID) -> AgentRunRecord: ...

    async def mark_interrupted(self) -> list[AgentRunRecord]: ...

    async def request_cancel(self, run_id: UUID) -> AgentRunRecord | None: ...

    async def prepare_resume(self, run_id: UUID) -> AgentRunRecord: ...

    async def update_state(
        self,
        run_id: UUID,
        *,
        status: AgentRunLifecycleStatus,
        current_phase: str | None = None,
        diagnostics: object | None = None,
        failure_code: str | None = None,
    ) -> AgentRunRecord: ...

    async def is_cancel_requested(self, run_id: UUID) -> bool: ...

    async def append_event(
        self,
        run_id: UUID,
        event: AgentRunEventRecord,
    ) -> AgentRunEventRecord: ...

    async def list_events(
        self,
        run_id: UUID,
        *,
        after: int = 0,
        limit: int = 100,
    ) -> list[AgentRunEventRecord]: ...


class AccountColumnContextPort(Protocol):
    """内容工作流读取账号和栏目上下文的端口。"""

    async def get_account(self, account_id: UUID) -> AccountProfileDto | None: ...

    async def get_column(self, account_id: UUID, column_id: UUID) -> ContentColumnDto | None: ...


class ToolCall(BaseModel):
    """模型发起的工具调用。"""

    id: str
    name: str
    arguments: str = "{}"


class ModelUsage(BaseModel):
    """模型调用的计量信息，不包含 prompt 或模型原始消息。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ModelResponse(BaseModel):
    """模型网关的统一响应：纯文本、工具调用，或两者都有。"""

    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: ModelUsage | None = None


class ModelGatewayError(RuntimeError):
    """模型网关错误：超时、服务不可达或 API 返回错误。"""


class ModelGateway(Protocol):
    """模型网关端口，屏蔽具体模型供应商的消息与工具调用协议。"""

    async def chat(
        self,
        messages: list[dict[str, object]],
        *,
        tools: list[dict[str, object]] | None = None,
    ) -> ModelResponse: ...
