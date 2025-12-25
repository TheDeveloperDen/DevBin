import time
import pytest
from app.utils.compression import compress_content, decompress_content


class TestCompressionPerformance:
    """Performance tests for compression functionality."""

    @pytest.mark.parametrize("size", [512, 1024, 5000, 10000])
    def test_compression_performance_overhead(self, size):
        """Test that compression overhead is under 20ms threshold."""
        # Create content of specified size
        content = "x" * size

        # Measure compression time
        start_compress = time.perf_counter()
        compressed, original_size = compress_content(content)
        end_compress = time.perf_counter()
        compress_time_ms = (end_compress - start_compress) * 1000

        # Measure decompression time
        start_decompress = time.perf_counter()
        decompressed = decompress_content(compressed)
        end_decompress = time.perf_counter()
        decompress_time_ms = (end_decompress - start_decompress) * 1000

        # Calculate total overhead
        total_overhead_ms = compress_time_ms + decompress_time_ms

        # Print results for visibility
        print(f"\nSize {size}: compress={compress_time_ms:.3f}ms, decompress={decompress_time_ms:.3f}ms, total={total_overhead_ms:.3f}ms")

        # Verify decompression works
        assert decompressed == content

        # Assert total overhead is under 20ms
        assert total_overhead_ms < 20, f"Compression overhead {total_overhead_ms:.3f}ms exceeds 20ms threshold"

    def test_compression_ratio_realistic_code(self):
        """Test compression ratio for realistic code content."""
        # Create realistic code content - Python function repeated 20 times
        code_snippet = """
def calculate_fibonacci(n):
    '''Calculate the nth Fibonacci number.'''
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

class DataProcessor:
    def __init__(self, data):
        self.data = data
        self.processed = False

    def process(self):
        '''Process the data.'''
        result = []
        for item in self.data:
            if isinstance(item, int):
                result.append(item * 2)
            else:
                result.append(str(item).upper())
        self.processed = True
        return result
"""
        realistic_content = code_snippet * 20
        original_size = len(realistic_content)

        # Compress the content
        compressed, _ = compress_content(realistic_content)
        compressed_size = len(compressed)

        # Calculate compression ratio
        compression_ratio = compressed_size / original_size

        # Print results
        print(f"\nOriginal size: {original_size} bytes")
        print(f"Compressed size: {compressed_size} bytes")
        print(f"Compression ratio: {compression_ratio:.3f}")

        # Verify decompression works
        decompressed = decompress_content(compressed)
        assert decompressed == realistic_content

        # Assert compression ratio is under 0.4 (40%)
        assert compression_ratio < 0.4, f"Compression ratio {compression_ratio:.3f} exceeds 0.4 threshold"
