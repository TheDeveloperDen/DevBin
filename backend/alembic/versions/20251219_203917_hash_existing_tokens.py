"""Hash existing tokens

Revision ID: 0ed6c1042110
Revises: 08393764144d
Create Date: 2025-12-19 20:39:17.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from argon2 import PasswordHasher

# revision identifiers, used by Alembic.
revision: str = "0ed6c1042110"
down_revision: Union[str, Sequence[str], None] = "08393764144d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Configure Argon2 with same parameters as token_utils.py
ph = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


def upgrade() -> None:
    """Hash all existing plaintext tokens."""
    # Get database connection
    connection = op.get_bind()

    # Fetch all pastes with tokens
    result = connection.execute(
        sa.text(
            "SELECT id, edit_token, delete_token FROM pastes WHERE edit_token IS NOT NULL OR delete_token IS NOT NULL"
        )
    )

    pastes = result.fetchall()

    print(f"Hashing tokens for {len(pastes)} pastes...")

    for paste in pastes:
        paste_id, edit_token, delete_token = paste

        # Hash tokens if they exist and are not already hashed
        new_edit_token = None
        new_delete_token = None

        if edit_token and not edit_token.startswith("$argon2"):
            new_edit_token = ph.hash(edit_token)

        if delete_token and not delete_token.startswith("$argon2"):
            new_delete_token = ph.hash(delete_token)

        # Update if any token was hashed
        if new_edit_token or new_delete_token:
            update_stmt = "UPDATE pastes SET"
            params = {"paste_id": paste_id}
            updates = []

            if new_edit_token:
                updates.append("edit_token = :edit_token")
                params["edit_token"] = new_edit_token

            if new_delete_token:
                updates.append("delete_token = :delete_token")
                params["delete_token"] = new_delete_token

            update_stmt += " " + ", ".join(updates) + " WHERE id = :paste_id"

            connection.execute(sa.text(update_stmt), params)

    print(f"Successfully hashed tokens for {len(pastes)} pastes")


def downgrade() -> None:
    """Cannot downgrade - hashed tokens cannot be reversed to plaintext."""
    print("WARNING: Cannot downgrade token hashing migration.")
    print("Hashed tokens cannot be converted back to plaintext.")
    print("If you need to downgrade, you must:")
    print("  1. Restore from a backup taken before this migration")
    print("  2. Or, accept that existing tokens will be invalidated")
    raise Exception("Irreversible migration - cannot downgrade token hashing")
