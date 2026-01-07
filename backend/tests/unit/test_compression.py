"""Unit tests for compression utilities."""

import pytest

from app.utils.compression import CompressionError, compress_content, decompress_content, should_compress


class TestCompressionUtils:
    """Test compression utility functions."""

    def test_compress_decompress_roundtrip(self):
        """Compress and decompress should return original content."""
        original = "This is test content that should compress well. " * 20
        compressed, original_size = compress_content(original)

        assert len(compressed) < len(original.encode("utf-8"))
        assert original_size == len(original.encode("utf-8"))

        decompressed = decompress_content(compressed)
        assert decompressed == original

    def test_compress_unicode_content(self):
        """Compression should handle unicode content."""
        original = "Hello 世界 🌍 Здравствуй мир" * 10
        compressed, original_size = compress_content(original)
        decompressed = decompress_content(compressed)

        assert decompressed == original

    def test_decompress_corrupted_data_raises_error(self):
        """Decompressing corrupted data should raise CompressionError."""
        corrupted_data = b"This is not gzip data"

        with pytest.raises(CompressionError):
            decompress_content(corrupted_data)

    def test_should_compress_below_threshold(self):
        """Content below threshold should not be compressed."""
        content = "Small"
        assert not should_compress(content, threshold=512)

    def test_should_compress_above_threshold(self):
        """Content above threshold should be compressed."""
        content = "X" * 1000
        assert should_compress(content, threshold=512)
