"""Add user_id to pastes

Revision ID: add_user_id_to_pastes
Revises: add_auth_tables
Create Date: 2026-04-04

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_user_id_to_pastes"
down_revision: str | None = "add_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pastes", sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_pastes_user_id",
        "pastes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_pastes_user_id", "pastes", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_pastes_user_id", table_name="pastes")
    op.drop_constraint("fk_pastes_user_id", "pastes", type_="foreignkey")
    op.drop_column("pastes", "user_id")
