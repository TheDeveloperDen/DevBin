"""Add authentication tables

Revision ID: add_auth_tables
Revises: 20251219_203917_hash_existing_tokens
Create Date: 2025-01-25

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "add_auth_tables"
down_revision: str | None = "4e57d32ab2ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )

    # Create indexes for users table
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_username", "users", ["username"])
    op.create_index("idx_users_created_at", "users", ["created_at"])

    # Create email_verification_tokens table
    op.create_table(
        "email_verification_tokens",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes for email_verification_tokens table
    op.create_index(
        "idx_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
    )
    op.create_index(
        "idx_email_verification_tokens_expires_at",
        "email_verification_tokens",
        ["expires_at"],
    )

    # Create password_reset_tokens table
    op.create_table(
        "password_reset_tokens",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Create indexes for password_reset_tokens table
    op.create_index(
        "idx_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"]
    )
    op.create_index(
        "idx_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"]
    )

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),  # IPv6 max length
    )

    # Create indexes for refresh_tokens table
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("idx_refresh_tokens_revoked_at", "refresh_tokens", ["revoked_at"])


def downgrade() -> None:
    # Drop refresh_tokens table and indexes
    op.drop_index("idx_refresh_tokens_revoked_at", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    # Drop password_reset_tokens table and indexes
    op.drop_index(
        "idx_password_reset_tokens_expires_at", table_name="password_reset_tokens"
    )
    op.drop_index(
        "idx_password_reset_tokens_user_id", table_name="password_reset_tokens"
    )
    op.drop_table("password_reset_tokens")

    # Drop email_verification_tokens table and indexes
    op.drop_index(
        "idx_email_verification_tokens_expires_at",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "idx_email_verification_tokens_user_id", table_name="email_verification_tokens"
    )
    op.drop_table("email_verification_tokens")

    # Drop users table and indexes
    op.drop_index("idx_users_created_at", table_name="users")
    op.drop_index("idx_users_username", table_name="users")
    op.drop_index("idx_users_email", table_name="users")
    op.drop_table("users")
