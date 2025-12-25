"""add_paste_indexes

Revision ID: 4e57d32ab2ac
Revises: 6c5a2c764fb8
Create Date: 2025-12-25 20:15:09.567249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e57d32ab2ac'
down_revision: Union[str, Sequence[str], None] = '6c5a2c764fb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add indexes to optimize paste queries
    op.create_index('idx_pastes_expires_at', 'pastes', ['expires_at'])
    op.create_index('idx_pastes_deleted_at', 'pastes', ['deleted_at'])
    op.create_index('idx_pastes_created_at', 'pastes', ['created_at'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove indexes
    op.drop_index('idx_pastes_created_at', 'pastes')
    op.drop_index('idx_pastes_deleted_at', 'pastes')
    op.drop_index('idx_pastes_expires_at', 'pastes')
