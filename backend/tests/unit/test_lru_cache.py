"""Unit tests for LRUMemoryCache."""

import pytest


class TestLRUMemoryCache:
    """Tests for LRU memory cache implementation."""

    @pytest.fixture
    def lru_cache(self):
        """Create LRUMemoryCache instance for testing."""
        from app.utils.LRUMemoryCache import LRUMemoryCache

        return LRUMemoryCache(max_size=3, ttl=60)

    def test_cache_has_correct_name(self, lru_cache):
        """Cache should have NAME attribute set to 'memory'."""
        assert lru_cache.NAME == "memory"

    def test_cache_stores_max_size_and_ttl(self, lru_cache):
        """Cache should store max_size and ttl configuration."""
        assert lru_cache.max_size == 3
        assert lru_cache.ttl == 60

    def test_cache_defaults(self):
        """Cache should have sensible defaults."""
        from app.utils.LRUMemoryCache import LRUMemoryCache

        cache = LRUMemoryCache()
        assert cache.max_size == 128
        assert cache.ttl == 300

    @pytest.mark.asyncio
    async def test_set_stores_value(self, lru_cache):
        """Set should store value in cache."""
        await lru_cache._set("key1", "value1")
        result = await lru_cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set_respects_custom_ttl(self, lru_cache):
        """Set with custom TTL should work."""
        await lru_cache._set("key1", "value1", ttl=120)
        result = await lru_cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_set_uses_default_ttl_when_none(self, lru_cache):
        """Set should use default TTL when TTL is None."""
        await lru_cache._set("key1", "value1", ttl=None)
        result = await lru_cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_evicts_oldest_when_at_max_size(self, lru_cache):
        """Cache should evict oldest entry when at max size."""
        # Fill cache to max size (3)
        await lru_cache._set("key1", "value1")
        await lru_cache._set("key2", "value2")
        await lru_cache._set("key3", "value3")

        # Add one more - should evict key1 (oldest)
        await lru_cache._set("key4", "value4")

        # key1 should be evicted
        result1 = await lru_cache.get("key1")
        assert result1 is None

        # Others should still exist
        result2 = await lru_cache.get("key2")
        result3 = await lru_cache.get("key3")
        result4 = await lru_cache.get("key4")
        assert result2 == "value2"
        assert result3 == "value3"
        assert result4 == "value4"

    @pytest.mark.asyncio
    async def test_eviction_order_is_fifo(self, lru_cache):
        """Eviction should follow FIFO order (first in, first out)."""
        # Add 4 items to a size-3 cache
        await lru_cache._set("a", 1)
        await lru_cache._set("b", 2)
        await lru_cache._set("c", 3)
        await lru_cache._set("d", 4)  # Evicts 'a'

        assert await lru_cache.get("a") is None
        assert await lru_cache.get("b") == 2

        await lru_cache._set("e", 5)  # Evicts 'b'
        assert await lru_cache.get("b") is None
        assert await lru_cache.get("c") == 3

    @pytest.mark.asyncio
    async def test_cache_handles_different_value_types(self, lru_cache):
        """Cache should handle various value types."""
        await lru_cache._set("string", "hello")
        await lru_cache._set("int", 42)

        assert await lru_cache.get("string") == "hello"
        assert await lru_cache.get("int") == 42

    @pytest.mark.asyncio
    async def test_overwriting_existing_key_does_not_evict(self, lru_cache):
        """Overwriting an existing key should not trigger eviction."""
        await lru_cache._set("key1", "value1")
        await lru_cache._set("key2", "value2")

        # Overwrite key1 (should not add new entry)
        await lru_cache._set("key1", "updated_value1")

        # Both keys should exist
        assert await lru_cache.get("key1") == "updated_value1"
        assert await lru_cache.get("key2") == "value2"

    @pytest.mark.asyncio
    async def test_delete_removes_key(self, lru_cache):
        """Delete should remove key from cache."""
        await lru_cache._set("key1", "value1")
        await lru_cache.delete("key1")

        result = await lru_cache.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_cache_get_returns_none(self, lru_cache):
        """Get on empty cache should return None."""
        result = await lru_cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_with_size_one(self):
        """Cache with size 1 should work correctly."""
        from app.utils.LRUMemoryCache import LRUMemoryCache

        tiny_cache = LRUMemoryCache(max_size=1, ttl=60)

        await tiny_cache._set("key1", "value1")
        await tiny_cache._set("key2", "value2")  # Should evict key1

        assert await tiny_cache.get("key1") is None
        assert await tiny_cache.get("key2") == "value2"
