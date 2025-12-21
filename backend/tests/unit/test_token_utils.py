"""Unit tests for token utility functions."""
import pytest

from app.utils.token_utils import hash_token, is_token_hashed, verify_token


@pytest.mark.unit
class TestTokenHashing:
    """Tests for Argon2 token hashing."""

    def test_hash_token_produces_valid_argon2_hash(self):
        """Hashed token should start with $argon2id$."""
        token = "my_secret_token_123"
        hashed = hash_token(token)

        assert hashed.startswith("$argon2id$")
        assert len(hashed) > 50  # Argon2 hashes are long

    def test_hash_token_produces_different_hashes_for_same_input(self):
        """Same token should produce different hashes (salted)."""
        token = "my_secret_token_123"
        hash1 = hash_token(token)
        hash2 = hash_token(token)

        assert hash1 != hash2  # Different due to random salt

    def test_hash_token_with_empty_string_raises_error(self):
        """Empty token should raise ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            hash_token("")

    def test_verify_token_succeeds_with_correct_token(self):
        """Verification should succeed with correct plaintext token."""
        plaintext = "my_secret_token_123"
        hashed = hash_token(plaintext)

        assert verify_token(plaintext, hashed) is True

    def test_verify_token_fails_with_wrong_token(self):
        """Verification should fail with wrong plaintext token."""
        plaintext = "my_secret_token_123"
        wrong = "wrong_token"
        hashed = hash_token(plaintext)

        assert verify_token(wrong, hashed) is False

    def test_verify_token_returns_false_for_empty_strings(self):
        """Empty token or hash should return False."""
        assert verify_token("", "some_hash") is False
        assert verify_token("some_token", "") is False

    def test_is_token_hashed_detects_argon2_format(self):
        """Should detect Argon2 hashed tokens."""
        hashed = hash_token("test_token")
        assert is_token_hashed(hashed) is True

    def test_is_token_hashed_returns_false_for_plaintext(self):
        """Should return False for plaintext tokens."""
        plaintext = "plaintext_token_123"
        assert is_token_hashed(plaintext) is False
