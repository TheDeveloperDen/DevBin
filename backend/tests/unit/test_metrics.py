"""Unit tests for Prometheus metrics utilities."""

import pytest
from unittest.mock import MagicMock, patch

from app.utils.metrics import (
    RedisCounter,
    RedisCounterChild,
    RedisGauge,
    REDIS_METRICS_PREFIX,
    init_metrics_redis,
    paste_operations,
    cache_operations,
    active_pastes,
    compressed_pastes,
    storage_operations,
)


@pytest.mark.unit
class TestRedisCounter:
    """Tests for RedisCounter class."""

    def test_counter_initialization(self):
        """Counter should initialize with name and description."""
        # Use unique names to avoid Prometheus registry conflicts
        counter = RedisCounter("test_counter_init_unique1", "Test description")
        assert counter._name == "test_counter_init_unique1"
        assert counter._labels == []
        assert counter._redis is None

    def test_counter_with_labels(self):
        """Counter should accept labels list."""
        counter = RedisCounter("test_counter_labels_unique1", "Test", labels=["method", "status"])
        assert counter._labels == ["method", "status"]

    def test_set_redis_client(self):
        """set_redis should store Redis client."""
        counter = RedisCounter("test_counter_setredis_unique1", "Test")
        mock_redis = MagicMock()
        
        counter.set_redis(mock_redis)
        
        assert counter._redis == mock_redis

    def test_set_redis_client_to_none(self):
        """set_redis should accept None."""
        counter = RedisCounter("test_counter_setredis_none_unique1", "Test")
        mock_redis = MagicMock()
        counter.set_redis(mock_redis)
        
        counter.set_redis(None)
        
        assert counter._redis is None

    def test_labels_returns_child_counter(self):
        """labels() should return RedisCounterChild."""
        counter = RedisCounter("test_counter_child_unique1", "Test", labels=["operation"])
        
        child = counter.labels(operation="create")
        
        assert isinstance(child, RedisCounterChild)
        assert child._parent == counter
        assert child._label_values == {"operation": "create"}

    def test_get_redis_key_without_labels(self):
        """_get_redis_key should generate correct key without labels."""
        counter = RedisCounter("test_counter_key_nolabels_unique1", "Test")
        
        key = counter._get_redis_key()
        
        assert key == f"{REDIS_METRICS_PREFIX}counter:test_counter_key_nolabels_unique1"

    def test_get_redis_key_with_labels(self):
        """_get_redis_key should generate correct key with labels."""
        counter = RedisCounter("test_counter_key_labels_unique1", "Test", labels=["a", "b"])
        
        key = counter._get_redis_key(label_values={"a": "1", "b": "2"})
        
        assert key == f"{REDIS_METRICS_PREFIX}counter:test_counter_key_labels_unique1{{a=1,b=2}}"

    def test_get_redis_key_labels_are_sorted(self):
        """_get_redis_key should sort labels alphabetically."""
        counter = RedisCounter("test_counter_sorted_unique1", "Test", labels=["z", "a", "m"])
        
        key = counter._get_redis_key(label_values={"z": "3", "a": "1", "m": "2"})
        
        # Labels should be sorted: a, m, z
        assert "a=1,m=2,z=3" in key

    def test_inc_without_redis_uses_local_counter(self):
        """inc() should use local Prometheus counter when Redis is not set."""
        counter = RedisCounter("test_counter_inc_local_unique1", "Test")
        
        # Should not raise even without Redis
        counter.inc()

    def test_inc_with_redis_increments_redis(self):
        """inc() should increment Redis counter when Redis is set."""
        counter = RedisCounter("test_counter_inc_redis_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.return_value = 1.0
        counter.set_redis(mock_redis)
        
        counter.inc()
        
        mock_redis.incrbyfloat.assert_called_once()

    def test_inc_with_redis_error_falls_back_to_local(self):
        """inc() should fall back to local counter on Redis error."""
        counter = RedisCounter("test_counter_inc_fallback_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.side_effect = Exception("Redis error")
        counter.set_redis(mock_redis)
        
        # Should not raise, falls back to local
        counter.inc()

    def test_inc_with_custom_amount(self):
        """inc() should accept custom increment amount."""
        counter = RedisCounter("test_counter_inc_amount_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.return_value = 5.0
        counter.set_redis(mock_redis)
        
        counter.inc(amount=5)
        
        mock_redis.incrbyfloat.assert_called_once()
        call_args = mock_redis.incrbyfloat.call_args
        assert call_args[0][1] == 5  # Second argument is amount

    def test_inc_with_labels(self):
        """inc() should work with label_values."""
        counter = RedisCounter("test_counter_inc_with_labels_unique1", "Test", labels=["op"])
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.return_value = 1.0
        counter.set_redis(mock_redis)
        
        counter.inc(label_values={"op": "create"})
        
        call_args = mock_redis.incrbyfloat.call_args
        assert "op=create" in call_args[0][0]


@pytest.mark.unit
class TestRedisCounterChild:
    """Tests for RedisCounterChild class."""

    def test_child_initialization(self):
        """Child should store parent and label values."""
        parent = RedisCounter("parent_counter_unique1", "Test", labels=["status"])
        child = RedisCounterChild(parent, {"status": "ok"})
        
        assert child._parent == parent
        assert child._label_values == {"status": "ok"}

    def test_child_inc_calls_parent_inc(self):
        """Child inc() should call parent inc() with label values."""
        parent = RedisCounter("parent_counter_inc_unique1", "Test", labels=["status"])
        parent.inc = MagicMock()
        child = RedisCounterChild(parent, {"status": "ok"})
        
        child.inc()
        
        parent.inc.assert_called_once_with(1, {"status": "ok"})

    def test_child_inc_with_amount(self):
        """Child inc() should pass amount to parent."""
        parent = RedisCounter("parent_counter_inc_amount_unique1", "Test", labels=["status"])
        parent.inc = MagicMock()
        child = RedisCounterChild(parent, {"status": "ok"})
        
        child.inc(amount=10)
        
        parent.inc.assert_called_once_with(10, {"status": "ok"})


@pytest.mark.unit
class TestRedisGauge:
    """Tests for RedisGauge class."""

    def test_gauge_initialization(self):
        """Gauge should initialize with name and description."""
        gauge = RedisGauge("test_gauge_init_unique1", "Test description")
        assert gauge._name == "test_gauge_init_unique1"
        assert gauge._redis is None

    def test_set_redis_client(self):
        """set_redis should store Redis client."""
        gauge = RedisGauge("test_gauge_setredis_unique1", "Test")
        mock_redis = MagicMock()
        
        gauge.set_redis(mock_redis)
        
        assert gauge._redis == mock_redis

    def test_get_redis_key(self):
        """_get_redis_key should generate correct key."""
        gauge = RedisGauge("test_gauge_key_unique1", "Test")
        
        key = gauge._get_redis_key()
        
        assert key == f"{REDIS_METRICS_PREFIX}gauge:test_gauge_key_unique1"

    def test_set_value_without_redis(self):
        """set() should use local gauge when Redis is not set."""
        gauge = RedisGauge("test_gauge_set_local_unique1", "Test")
        
        # Should not raise
        gauge.set(42.0)

    def test_set_value_with_redis(self):
        """set() should set Redis value when Redis is set."""
        gauge = RedisGauge("test_gauge_set_redis_unique1", "Test")
        mock_redis = MagicMock()
        gauge.set_redis(mock_redis)
        
        gauge.set(42.0)
        
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][1] == 42.0

    def test_set_with_redis_error_still_sets_local(self):
        """set() should still set local gauge on Redis error."""
        gauge = RedisGauge("test_gauge_set_fallback_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.set.side_effect = Exception("Redis error")
        gauge.set_redis(mock_redis)
        
        # Should not raise
        gauge.set(42.0)

    def test_inc_without_redis(self):
        """inc() should use local gauge when Redis is not set."""
        gauge = RedisGauge("test_gauge_inc_local_unique1", "Test")
        
        # Should not raise
        gauge.inc()

    def test_inc_with_redis(self):
        """inc() should use Redis incrbyfloat when Redis is set."""
        gauge = RedisGauge("test_gauge_inc_redis_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.return_value = 1.0
        gauge.set_redis(mock_redis)
        
        gauge.inc()
        
        mock_redis.incrbyfloat.assert_called_once()

    def test_inc_with_custom_amount(self):
        """inc() should accept custom amount."""
        gauge = RedisGauge("test_gauge_inc_amount_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.return_value = 5.0
        gauge.set_redis(mock_redis)
        
        gauge.inc(amount=5)
        
        call_args = mock_redis.incrbyfloat.call_args
        assert call_args[0][1] == 5

    def test_dec_without_redis(self):
        """dec() should use local gauge when Redis is not set."""
        gauge = RedisGauge("test_gauge_dec_local_unique1", "Test")
        
        # Should not raise
        gauge.dec()

    def test_dec_with_redis(self):
        """dec() should use Redis incrbyfloat with negative amount."""
        gauge = RedisGauge("test_gauge_dec_redis_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.return_value = 4.0
        gauge.set_redis(mock_redis)
        
        gauge.dec()
        
        call_args = mock_redis.incrbyfloat.call_args
        assert call_args[0][1] == -1

    def test_dec_clamps_to_zero(self):
        """dec() should clamp value to zero if it goes negative."""
        gauge = RedisGauge("test_gauge_dec_clamp_unique1", "Test")
        mock_redis = MagicMock()
        mock_redis.incrbyfloat.return_value = -5.0  # Would be negative
        gauge.set_redis(mock_redis)
        
        gauge.dec()
        
        # Should reset to 0
        mock_redis.set.assert_called_with(gauge._get_redis_key(), 0)


@pytest.mark.unit
class TestInitMetricsRedis:
    """Tests for init_metrics_redis function."""

    def test_init_with_redis_sets_all_metrics(self):
        """init_metrics_redis should set Redis on all metrics."""
        mock_redis = MagicMock()
        
        with patch.object(paste_operations, 'set_redis') as mock_po, \
             patch.object(cache_operations, 'set_redis') as mock_co, \
             patch.object(active_pastes, 'set_redis') as mock_ap, \
             patch.object(compressed_pastes, 'set_redis') as mock_cp, \
             patch.object(storage_operations, 'set_redis') as mock_so:
            
            init_metrics_redis(mock_redis)
            
            mock_po.assert_called_once_with(mock_redis)
            mock_co.assert_called_once_with(mock_redis)
            mock_ap.assert_called_once_with(mock_redis)
            mock_cp.assert_called_once_with(mock_redis)
            mock_so.assert_called_once_with(mock_redis)

    def test_init_with_none_does_nothing(self):
        """init_metrics_redis with None should not set Redis."""
        with patch.object(paste_operations, 'set_redis') as mock_po:
            init_metrics_redis(None)
            
            mock_po.assert_not_called()


@pytest.mark.unit
class TestGlobalMetrics:
    """Tests for global metric instances."""

    def test_paste_operations_has_correct_labels(self):
        """paste_operations should have operation and status labels."""
        assert paste_operations._labels == ["operation", "status"]

    def test_cache_operations_has_correct_labels(self):
        """cache_operations should have operation and result labels."""
        assert cache_operations._labels == ["operation", "result"]

    def test_storage_operations_has_correct_labels(self):
        """storage_operations should have operation, backend, and status labels."""
        assert storage_operations._labels == ["operation", "backend", "status"]

    def test_active_pastes_is_gauge(self):
        """active_pastes should be a RedisGauge."""
        assert isinstance(active_pastes, RedisGauge)

    def test_compressed_pastes_is_counter(self):
        """compressed_pastes should be a RedisCounter."""
        assert isinstance(compressed_pastes, RedisCounter)
