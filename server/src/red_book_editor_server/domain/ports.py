from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel

from red_book_editor_server.domain.contracts import (
    AccountProfileDto,
    ContentColumnDto,
    NoteDraftDto,
    SourceExperienceDto,
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


class AccountColumnContextPort(Protocol):
    """内容工作流读取账号和栏目上下文的端口。"""

    async def get_account(self, account_id: UUID) -> AccountProfileDto | None: ...

    async def get_column(self, account_id: UUID, column_id: UUID) -> ContentColumnDto | None: ...


class ToolCall(BaseModel):
    """模型发起的工具调用。"""

    id: str
    name: str
    arguments: str = "{}"


class ModelResponse(BaseModel):
    """模型网关的统一响应：纯文本、工具调用，或两者都有。"""

    content: str | None = None
    tool_calls: list[ToolCall] | None = None


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
