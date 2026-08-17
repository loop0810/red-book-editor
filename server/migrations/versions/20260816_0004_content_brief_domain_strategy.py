"""Add account domains and persisted content brief context."""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260816_0004"
down_revision: Union[str, None] = "20260816_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = sa.JSON()
    for column in ("min_age_months", "max_age_months", "current_baby_month"):
        op.alter_column("accounts", column, existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "accounts",
        sa.Column("domain_id", sa.String(length=64), server_default="parenting", nullable=False),
    )
    op.add_column(
        "accounts",
        sa.Column("domain_context", json_type, server_default=sa.text("'{}'"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("accounts", "domain_context")
    op.drop_column("accounts", "domain_id")
    # 首次配置允许不填写旧版年龄范围；回滚到 0003 时补齐旧 schema 的
    # 非空约束，避免测试清理或本地回滚因为新账号的空值失败。
    op.execute(
        sa.text(
            "UPDATE accounts "
            "SET min_age_months = COALESCE(min_age_months, 0), "
            "max_age_months = COALESCE(max_age_months, 240), "
            "current_baby_month = COALESCE(current_baby_month, 0)"
        )
    )
    for column in ("min_age_months", "max_age_months", "current_baby_month"):
        op.alter_column("accounts", column, existing_type=sa.Integer(), nullable=False)
