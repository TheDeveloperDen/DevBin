"""Token hashing and verification utilities using Argon2."""

from __future__ import annotations

import logging

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

logger = logging.getLogger(__name__)

# Configure Argon2 with OWASP recommended parameters
# time_cost=2, memory_cost=19456 (19 MiB), parallelism=1
ph = PasswordHasher(
    time_cost=2,  # Number of iterations
    memory_cost=19456,  # Memory usage in KiB (19 MiB)
    parallelism=1,  # Number of parallel threads
    hash_len=32,  # Length of hash in bytes
    salt_len=16,  # Length of salt in bytes
)


def hash_token(token: str) -> str:
    """
    Hash a token using Argon2id.

    Args:
        token: The plaintext token to hash

    Returns:
        The hashed token string (Argon2 format: $argon2id$v=19$m=19456,t=2,p=1$...)

    Raises:
        ValueError: If token is empty or invalid
    """
    if not token or not isinstance(token, str):
        raise ValueError("Token must be a non-empty string")

    try:
        return ph.hash(token)
    except Exception as exc:
        logger.error("Failed to hash token: %s", exc)
        raise


def verify_token(plaintext_token: str, hashed_token: str) -> bool:
    """
    Verify a plaintext token against a hashed token.

    Args:
        plaintext_token: The plaintext token to verify
        hashed_token: The hashed token to verify against

    Returns:
        True if the token matches, False otherwise
    """
    if not plaintext_token or not hashed_token:
        return False

    try:
        ph.verify(hashed_token, plaintext_token)

        # Check if rehashing is needed (parameters changed)
        if ph.check_needs_rehash(hashed_token):
            logger.warning("Token hash needs rehashing with updated parameters")

        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # Token doesn't match or hash is invalid
        return False
    except Exception as exc:
        logger.error("Unexpected error during token verification: %s", exc)
        return False


def is_token_hashed(token: str) -> bool:
    """
    Check if a token is already hashed (starts with $argon2).

    This is useful during migration to detect plaintext vs hashed tokens.

    Args:
        token: The token to check

    Returns:
        True if token appears to be hashed, False otherwise
    """
    if not token:
        return False

    return token.startswith("$argon2")
