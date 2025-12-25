"""Prometheus metrics for monitoring application performance."""

from prometheus_client import Counter, Gauge, Histogram

# Paste operations metrics
paste_operations = Counter(
    'paste_operations_total',
    'Total paste operations',
    ['operation', 'status']
)

# Paste size distribution
paste_size = Histogram(
    'paste_size_bytes',
    'Paste size distribution in bytes',
    buckets=[100, 500, 1024, 2048, 5120, 10240, 51200, 102400]
)

# Cache operations metrics
cache_operations = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result']
)

# Cleanup operation duration
cleanup_duration = Histogram(
    'cleanup_duration_seconds',
    'Cleanup operation duration in seconds',
    buckets=[1, 5, 10, 30, 60, 120, 300]
)

# Active pastes gauge
active_pastes = Gauge(
    'active_pastes_total',
    'Total number of active pastes'
)

# Compressed pastes counter
compressed_pastes = Counter(
    'compressed_pastes_total',
    'Total number of compressed pastes'
)

# Storage operations
storage_operations = Counter(
    'storage_operations_total',
    'Total storage operations',
    ['operation', 'backend', 'status']
)
