from aiocache import BaseCache
from aiocache.backends.memory import SimpleMemoryBackend
from aiocache.serializers import NullSerializer


class LRUMemoryCache(SimpleMemoryBackend, BaseCache):
    NAME = "memory"

    def __init__(self, serializer=None, max_size=128, ttl=300, **kwargs):
        super().__init__(serializer=serializer or NullSerializer(), **kwargs)
        self.max_size = max_size
        self.ttl = ttl

    async def _set(self, key, value, ttl=None, **kwargs):
        if ttl is None:
            ttl = self.ttl
        # Remove the oldest item if cache is at max size
        if len(self._cache) >= self.max_size:
            # Get the first (oldest) key from the cache dict
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        return await super()._set(key, value, ttl)
