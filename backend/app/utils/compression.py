"""Content compression utilities for paste storage."""
import gzip
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class CompressionError(Exception):
    """Raised when compression/decompression fails."""
    pass


def compress_content(content: str, compression_level: int = 6) -> Tuple[bytes, int]:
    """
    Compress content using gzip.

    Args:
        content: String content to compress
        compression_level: Compression level (1-9)

    Returns:
        Tuple of (compressed_bytes, original_size)

    Raises:
        CompressionError: If compression fails
    """
    try:
        content_bytes = content.encode('utf-8')
        original_size = len(content_bytes)

        compressed = gzip.compress(
            content_bytes,
            compresslevel=compression_level,
            mtime=0  # Deterministic output
        )

        logger.debug(
            "Compressed %d bytes to %d bytes (%.1f%% reduction)",
            original_size,
            len(compressed),
            100 * (1 - len(compressed) / original_size) if original_size > 0 else 0
        )

        return compressed, original_size

    except Exception as exc:
        logger.error("Compression failed: %s", exc)
        raise CompressionError(f"Failed to compress content: {exc}") from exc


def decompress_content(compressed_data: bytes) -> str:
    """
    Decompress gzip-compressed content.

    Args:
        compressed_data: Gzip-compressed bytes

    Returns:
        Decompressed string content

    Raises:
        CompressionError: If decompression fails
    """
    try:
        decompressed_bytes = gzip.decompress(compressed_data)
        return decompressed_bytes.decode('utf-8')

    except gzip.BadGzipFile as exc:
        logger.error("Invalid gzip data: %s", exc)
        raise CompressionError("Corrupted compressed data") from exc
    except UnicodeDecodeError as exc:
        logger.error("Failed to decode decompressed content: %s", exc)
        raise CompressionError("Invalid UTF-8 in decompressed content") from exc
    except Exception as exc:
        logger.error("Decompression failed: %s", exc)
        raise CompressionError(f"Failed to decompress content: {exc}") from exc


def should_compress(content: str, threshold: int) -> bool:
    """
    Determine if content should be compressed based on size threshold.

    Args:
        content: Content to evaluate
        threshold: Minimum size in bytes to trigger compression

    Returns:
        True if content should be compressed
    """
    content_size = len(content.encode('utf-8'))
    return content_size >= threshold
