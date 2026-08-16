"""Persist note-scoped field suggestion history."""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260816_0003"
down_revision: Union[str, None] = "20260816_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    json_type = sa.JSON()
    op.create_table(
        "field_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("field", sa.String(length=32), nullable=False),
        sa.Column("value", json_type, nullable=False),
        sa.Column("base_field_digest", sa.String(length=64), nullable=False),
        sa.Column("base_content_digest", sa.String(length=64), nullable=False),
        sa.Column("review", json_type, nullable=True),
        sa.Column("evidence", json_type, nullable=False),
        sa.Column("evidence_fact_ids", json_type, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_field_suggestions_note_status_created",
        "field_suggestions",
        ["note_id", "status", "created_at"],
    )
    op.create_index("ix_field_suggestions_account_id", "field_suggestions", ["account_id"])


def downgrade() -> None:
    op.drop_index("ix_field_suggestions_account_id", table_name="field_suggestions")
    op.drop_index("ix_field_suggestions_note_status_created", table_name="field_suggestions")
    op.drop_table("field_suggestions")
