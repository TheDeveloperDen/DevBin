"""Tests for custom exception classes."""
import pytest

from app.exceptions import (
    ContentTooLargeError,
    DevBinException,
    InvalidTokenError,
    PasteExpiredError,
    PasteNotFoundError,
    StorageError,
    StorageQuotaExceededError,
    CompressionError,
    DatabaseError,
    CacheError,
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_paste_not_found_error(self):
        """PasteNotFoundError should have correct attributes."""
        paste_id = "test-id-123"
        exc = PasteNotFoundError(paste_id)

        assert exc.paste_id == paste_id
        assert exc.status_code == 404
        assert paste_id in exc.message

    def test_paste_expired_error(self):
        """PasteExpiredError should have correct attributes."""
        paste_id = "expired-id-456"
        exc = PasteExpiredError(paste_id)

        assert exc.paste_id == paste_id
        assert exc.status_code == 404
        assert paste_id in exc.message

    def test_invalid_token_error(self):
        """InvalidTokenError should have correct attributes."""
        exc = InvalidTokenError(operation="edit")

        assert exc.operation == "edit"
        assert exc.status_code == 404
        assert "edit" in exc.message

    def test_storage_quota_exceeded_error(self):
        """StorageQuotaExceededError should have correct attributes."""
        exc = StorageQuotaExceededError(required_mb=100.5, available_mb=50.25)

        assert exc.required_mb == 100.5
        assert exc.available_mb == 50.25
        assert exc.status_code == 507
        assert "100.50" in exc.message
        assert "50.25" in exc.message

    def test_content_too_large_error(self):
        """ContentTooLargeError should have correct attributes."""
        exc = ContentTooLargeError(content_size=20000, max_size=10000)

        assert exc.content_size == 20000
        assert exc.max_size == 10000
        assert exc.status_code == 413
        assert "20000" in exc.message
        assert "10000" in exc.message

    def test_storage_error(self):
        """StorageError should have correct attributes."""
        exc = StorageError(message="Connection failed", operation="write")

        assert exc.operation == "write"
        assert exc.status_code == 500
        assert "write" in exc.message
        assert "Connection failed" in exc.message

    def test_compression_error(self):
        """CompressionError should have correct attributes."""
        exc = CompressionError(message="Invalid data", operation="decompression")

        assert exc.operation == "decompression"
        assert exc.status_code == 500
        assert "decompression" in exc.message.lower()

    def test_database_error(self):
        """DatabaseError should have correct attributes."""
        exc = DatabaseError(message="Query failed", operation="insert")

        assert exc.operation == "insert"
        assert exc.status_code == 500
        assert "insert" in exc.message

    def test_cache_error(self):
        """CacheError should have correct attributes."""
        exc = CacheError(message="Redis timeout", operation="get")

        assert exc.operation == "get"
        assert exc.status_code == 500
        assert "get" in exc.message

    def test_base_devbin_exception(self):
        """Base DevBinException should work with custom values."""
        exc = DevBinException(message="Custom error", status_code=418)

        assert exc.message == "Custom error"
        assert exc.status_code == 418
        assert str(exc) == "Custom error"
