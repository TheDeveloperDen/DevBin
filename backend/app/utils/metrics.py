"""
Prometheus metrics for monitoring application performance.

Supports Redis backend for multi-instance deployments. When Redis is available,
counters and gauges are stored in Redis for accurate aggregation across instances.
Histograms remain local as Prometheus can aggregate them properly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from prometheus_client import Counter, Gauge, Histogram

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)

# Redis key prefix for metrics
REDIS_METRICS_PREFIX = "devbin:metrics:"


class RedisCounter:
    """
    A Counter that uses Redis as backend for multi-instance support.
    Falls back to local Prometheus counter when Redis is unavailable.
    """

    def __init__(self, name: str, description: str, labels: list[str] | None = None):
        self._name = name
        self._labels = labels or []
        self._redis: Redis | None = None
        self._local_counter = Counter(name, description, labels) if labels else Counter(name, description)

    def set_redis(self, redis_client: Redis | None) -> None:
        """Set the Redis client for this counter."""
        self._redis = redis_client

    def labels(self, **kwargs) -> RedisCounterChild:
        """Return a child counter with the given labels."""
        return RedisCounterChild(self, kwargs)

    def _get_redis_key(self, label_values: dict | None = None) -> str:
        """Get the Redis key for this counter."""
        if label_values:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(label_values.items()))
            return f"{REDIS_METRICS_PREFIX}counter:{self._name}{{{label_str}}}"
        return f"{REDIS_METRICS_PREFIX}counter:{self._name}"

    def inc(self, amount: float = 1, label_values: dict | None = None) -> None:
        """Increment the counter."""
        if self._redis:
            try:
                key = self._get_redis_key(label_values)
                new_value = self._redis.incrbyfloat(key, amount)
                # Sync to local Prometheus counter for /metrics endpoint
                if label_values:
                    # Get current local value and set difference
                    local = self._local_counter.labels(**label_values)
                    current = local._value.get()
                    if new_value > current:
                        local.inc(new_value - current)
                else:
                    current = self._local_counter._value.get()
                    if new_value > current:
                        self._local_counter.inc(new_value - current)
                return
            except Exception as exc:
                logger.warning("Redis counter increment failed for %s: %s", self._name, exc)

        # Fallback to local counter
        if label_values:
            self._local_counter.labels(**label_values).inc(amount)
        else:
            self._local_counter.inc(amount)


class RedisCounterChild:
    """A labeled child of a RedisCounter."""

    def __init__(self, parent: RedisCounter, label_values: dict):
        self._parent = parent
        self._label_values = label_values

    def inc(self, amount: float = 1) -> None:
        """Increment the counter."""
        self._parent.inc(amount, self._label_values)


class RedisGauge:
    """
    A Gauge that uses Redis as backend for multi-instance support.
    Falls back to local Prometheus gauge when Redis is unavailable.
    """

    def __init__(self, name: str, description: str):
        self._name = name
        self._redis: Redis | None = None
        self._local_gauge = Gauge(name, description)

    def set_redis(self, redis_client: Redis | None) -> None:
        """Set the Redis client for this gauge."""
        self._redis = redis_client

    def _get_redis_key(self) -> str:
        """Get the Redis key for this gauge."""
        return f"{REDIS_METRICS_PREFIX}gauge:{self._name}"

    def set(self, value: float) -> None:
        """Set the gauge value."""
        if self._redis:
            try:
                self._redis.set(self._get_redis_key(), value)
            except Exception as exc:
                logger.warning("Redis gauge set failed for %s: %s", self._name, exc)

        self._local_gauge.set(value)

    def inc(self, amount: float = 1) -> None:
        """Increment the gauge."""
        if self._redis:
            try:
                key = self._get_redis_key()
                new_value = self._redis.incrbyfloat(key, amount)
                self._local_gauge.set(new_value)
                return
            except Exception as exc:
                logger.warning("Redis gauge increment failed for %s: %s", self._name, exc)

        self._local_gauge.inc(amount)

    def dec(self, amount: float = 1) -> None:
        """Decrement the gauge."""
        if self._redis:
            try:
                key = self._get_redis_key()
                new_value = self._redis.incrbyfloat(key, -amount)
                if new_value < 0:
                    self._redis.set(key, 0)
                    new_value = 0
                self._local_gauge.set(new_value)
                return
            except Exception as exc:
                logger.warning("Redis gauge decrement failed for %s: %s", self._name, exc)

        self._local_gauge.dec(amount)


# Paste operations metrics
paste_operations = RedisCounter("paste_operations_total", "Total paste operations", ["operation", "status"])

# Paste size distribution (histogram - kept local, Prometheus aggregates these)
paste_size = Histogram(
    "paste_size_bytes", "Paste size distribution in bytes", buckets=[100, 500, 1024, 2048, 5120, 10240, 51200, 102400]
)

# Cache operations metrics
cache_operations = RedisCounter("cache_operations_total", "Total cache operations", ["operation", "result"])

# Cleanup operation duration (histogram - kept local)
cleanup_duration = Histogram(
    "cleanup_duration_seconds", "Cleanup operation duration in seconds", buckets=[1, 5, 10, 30, 60, 120, 300]
)

# Active pastes gauge
active_pastes = RedisGauge("active_pastes_total", "Total number of active pastes")

# Compressed pastes counter
compressed_pastes = RedisCounter("compressed_pastes_total", "Total number of compressed pastes")

# Storage operations
storage_operations = RedisCounter(
    "storage_operations_total", "Total storage operations", ["operation", "backend", "status"]
)


def init_metrics_redis(redis_client: Redis | None) -> None:
    """Initialize all metrics with Redis backend."""
    if redis_client:
        logger.info("Initializing metrics with Redis backend")
    else:
        logger.info("Metrics using local backend (no Redis)")
        return

    paste_operations.set_redis(redis_client)
    cache_operations.set_redis(redis_client)
    active_pastes.set_redis(redis_client)
    compressed_pastes.set_redis(redis_client)
    storage_operations.set_redis(redis_client)
