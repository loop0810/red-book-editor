from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from red_book_editor_server.app.dependencies import database_session
from red_book_editor_server.domain.contracts import AccountProfileDto, ContentColumnDto
from red_book_editor_server.infrastructure.models import AccountModel, ContentColumnModel

router = APIRouter(prefix="/api/v1/accounts", tags=["accounts"])


class AccountProfileInput(BaseModel):
    positioning: str = Field(min_length=1)
    age_range_months: tuple[int, int]
    current_baby_month: int = Field(ge=0, le=240)
    tone: str = Field(min_length=1)
    boundaries: list[str] = Field(default_factory=list)
    common_expressions: list[str] = Field(default_factory=list)


class ContentColumnInput(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    content_types: list[str] = Field(default_factory=list)


def account_dto(account: AccountModel) -> AccountProfileDto:
    return AccountProfileDto(
        account_id=account.id,
        positioning=account.positioning,
        age_range_months=(account.min_age_months, account.max_age_months),
        current_baby_month=account.current_baby_month,
        tone=account.tone,
        boundaries=account.boundaries,
        common_expressions=account.common_expressions,
    )


@router.put("/{account_id}", response_model=AccountProfileDto)
async def upsert_account(
    account_id: UUID,
    payload: AccountProfileInput,
    session: AsyncSession = Depends(database_session),
) -> AccountProfileDto:
    account = await session.get(AccountModel, account_id)
    if account is None:
        account = AccountModel(id=account_id)
        session.add(account)
    account.positioning = payload.positioning
    account.min_age_months, account.max_age_months = payload.age_range_months
    account.current_baby_month = payload.current_baby_month
    account.tone = payload.tone
    account.boundaries = payload.boundaries
    account.common_expressions = payload.common_expressions
    await session.commit()
    await session.refresh(account)
    return account_dto(account)


@router.get("/{account_id}", response_model=AccountProfileDto)
async def get_account(
    account_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> AccountProfileDto:
    account = await session.get(AccountModel, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="account_not_found")
    return account_dto(account)


@router.post("/{account_id}/columns", response_model=ContentColumnDto, status_code=201)
async def create_column(
    account_id: UUID,
    payload: ContentColumnInput,
    session: AsyncSession = Depends(database_session),
) -> ContentColumnDto:
    if await session.get(AccountModel, account_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="account_not_found")
    column = ContentColumnModel(
        account_id=account_id,
        name=payload.name,
        description=payload.description,
        content_types=payload.content_types,
    )
    session.add(column)
    await session.commit()
    await session.refresh(column)
    return ContentColumnDto(
        column_id=column.id,
        account_id=column.account_id,
        name=column.name,
        description=column.description,
        content_types=column.content_types,
        enabled=column.enabled,
    )


@router.get("/{account_id}/columns", response_model=list[ContentColumnDto])
async def list_columns(
    account_id: UUID,
    session: AsyncSession = Depends(database_session),
) -> list[ContentColumnDto]:
    result = await session.execute(
        select(ContentColumnModel)
        .where(ContentColumnModel.account_id == account_id)
        .order_by(ContentColumnModel.name)
    )
    return [
        ContentColumnDto(
            column_id=column.id,
            account_id=column.account_id,
            name=column.name,
            description=column.description,
            content_types=column.content_types,
            enabled=column.enabled,
        )
        for column in result.scalars()
    ]
