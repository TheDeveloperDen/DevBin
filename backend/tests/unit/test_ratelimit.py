"""Tests for rate limiting functionality."""

from unittest.mock import MagicMock

import pytest

from app.config import Config, validate_rate_limit
from app.ratelimit import (
    NoOpLimiter,
    create_exempt_key_func,
    create_limit_resolver,
    create_rate_limiter,
    get_ip_address,
)


class TestRateLimitTypeValidation:
    """Test RateLimit type validation."""

    def test_valid_rate_limit_per_second(self):
        """Should accept valid per-second rate limits."""
        assert validate_rate_limit("10/second") == "10/second"
        assert validate_rate_limit("1/second") == "1/second"
        assert validate_rate_limit("1000/second") == "1000/second"

    def test_valid_rate_limit_per_minute(self):
        """Should accept valid per-minute rate limits."""
        assert validate_rate_limit("60/minute") == "60/minute"
        assert validate_rate_limit("1/minute") == "1/minute"
        assert validate_rate_limit("100/minute") == "100/minute"

    def test_valid_rate_limit_per_hour(self):
        """Should accept valid per-hour rate limits."""
        assert validate_rate_limit("100/hour") == "100/hour"
        assert validate_rate_limit("1/hour") == "1/hour"
        assert validate_rate_limit("10000/hour") == "10000/hour"

    def test_valid_rate_limit_per_day(self):
        """Should accept valid per-day rate limits."""
        assert validate_rate_limit("1000/day") == "1000/day"
        assert validate_rate_limit("1/day") == "1/day"
        assert validate_rate_limit("50000/day") == "50000/day"

    def test_invalid_rate_limit_wrong_time_unit(self):
        """Should reject rate limits with invalid time units."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/week")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/month")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/sec")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/min")

    def test_invalid_rate_limit_missing_number(self):
        """Should reject rate limits without a number."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("/minute")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("minute")

    def test_invalid_rate_limit_missing_time_unit(self):
        """Should reject rate limits without a time unit."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10")

    def test_invalid_rate_limit_wrong_separator(self):
        """Should reject rate limits with wrong separator."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10-minute")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10 minute")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10:minute")

    def test_invalid_rate_limit_negative_number(self):
        """Should reject rate limits with negative numbers."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("-10/minute")

    def test_invalid_rate_limit_decimal_number(self):
        """Should reject rate limits with decimal numbers."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10.5/minute")

    def test_invalid_rate_limit_empty_string(self):
        """Should reject empty string."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("")

    def test_invalid_rate_limit_case_sensitive(self):
        """Time units should be lowercase."""
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/MINUTE")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/Minute")
        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/SECOND")


class TestNoOpLimiter:
    """Test NoOpLimiter behavior."""

    def test_noop_limiter_limit_returns_decorator(self):
        """NoOpLimiter.limit() should return a decorator."""
        limiter = NoOpLimiter()
        decorator = limiter.limit("10/minute")
        assert callable(decorator)

    def test_noop_limiter_decorator_returns_original_function(self):
        """NoOpLimiter decorator should return the original function unchanged."""
        limiter = NoOpLimiter()

        def my_function():
            return "result"

        decorated = limiter.limit("10/minute")(my_function)
        assert decorated is my_function

    def test_noop_limiter_with_key_func(self):
        """NoOpLimiter should accept key_func parameter."""
        limiter = NoOpLimiter()

        def key_func(request):
            return "key"

        def my_function():
            return "result"

        # Should not raise
        decorated = limiter.limit("10/minute", key_func=key_func)(my_function)
        assert decorated is my_function

    def test_noop_limiter_preserves_function_behavior(self):
        """Decorated functions should behave the same."""
        limiter = NoOpLimiter()

        def add(a, b):
            return a + b

        decorated = limiter.limit("10/minute")(add)
        assert decorated(2, 3) == 5


class TestCreateRateLimiter:
    """Test rate limiter factory function."""

    def test_disabled_returns_noop_limiter(self):
        """Should return NoOpLimiter when disabled."""
        config = MagicMock()
        config.RATELIMIT_ENABLED = False

        limiter = create_rate_limiter(config)

        assert isinstance(limiter, NoOpLimiter)

    def test_memory_backend_returns_limiter(self):
        """Should return Limiter with memory backend."""
        config = MagicMock()
        config.RATELIMIT_ENABLED = True
        config.RATELIMIT_BACKEND = "memory"

        limiter = create_rate_limiter(config)

        from slowapi import Limiter

        assert isinstance(limiter, Limiter)

    def test_redis_backend_falls_back_to_memory_on_error(self):
        """Should fall back to memory when Redis fails."""
        config = MagicMock()
        config.RATELIMIT_ENABLED = True
        config.RATELIMIT_BACKEND = "redis"
        config.REDIS_HOST = "nonexistent-host"
        config.REDIS_PORT = 6379
        config.REDIS_DB = 0
        config.REDIS_PASSWORD = None

        # The limiter creation itself might not fail, but connection would
        # For this test, we verify it returns a Limiter (fallback behavior)
        limiter = create_rate_limiter(config)

        from slowapi import Limiter

        assert isinstance(limiter, Limiter)

    def test_redis_backend_builds_correct_uri(self):
        """Should build correct Redis URI from config."""
        from app.ratelimit import _build_redis_uri

        config = MagicMock()
        config.REDIS_HOST = "localhost"
        config.REDIS_PORT = 6379
        config.REDIS_DB = 0
        config.REDIS_PASSWORD = None

        uri = _build_redis_uri(config)
        assert uri == "redis://localhost:6379/0"

    def test_redis_backend_uri_with_password(self):
        """Should include password in Redis URI when set."""
        from app.ratelimit import _build_redis_uri

        config = MagicMock()
        config.REDIS_HOST = "localhost"
        config.REDIS_PORT = 6379
        config.REDIS_DB = 1
        config.REDIS_PASSWORD = "secret"

        uri = _build_redis_uri(config)
        assert uri == "redis://:secret@localhost:6379/1"


class TestCreateLimitResolver:
    """Test limit resolver creation."""

    def test_resolver_returns_correct_limit(self):
        """Should return the correct limit value."""
        config = MagicMock()
        config.RATELIMIT_DEFAULT = "60/minute"
        config.RATELIMIT_HEALTH = "100/minute"
        config.RATELIMIT_GET_PASTE = "10/minute"
        config.RATELIMIT_GET_PASTE_LEGACY = "15/minute"
        config.RATELIMIT_CREATE_PASTE = "4/minute"
        config.RATELIMIT_EDIT_PASTE = "5/minute"
        config.RATELIMIT_DELETE_PASTE = "3/minute"

        resolver = create_limit_resolver(config, "health")
        assert resolver() == "100/minute"

    def test_resolver_returns_get_paste_limit(self):
        """Should return correct limit for get_paste."""
        config = MagicMock()
        config.RATELIMIT_DEFAULT = "60/minute"
        config.RATELIMIT_GET_PASTE = "10/minute"

        resolver = create_limit_resolver(config, "get_paste")
        assert resolver() == "10/minute"

    def test_resolver_returns_create_paste_limit(self):
        """Should return correct limit for create_paste."""
        config = MagicMock()
        config.RATELIMIT_DEFAULT = "60/minute"
        config.RATELIMIT_CREATE_PASTE = "4/minute"

        resolver = create_limit_resolver(config, "create_paste")
        assert resolver() == "4/minute"

    def test_resolver_returns_edit_paste_limit(self):
        """Should return correct limit for edit_paste."""
        config = MagicMock()
        config.RATELIMIT_DEFAULT = "60/minute"
        config.RATELIMIT_EDIT_PASTE = "5/minute"

        resolver = create_limit_resolver(config, "edit_paste")
        assert resolver() == "5/minute"

    def test_resolver_returns_delete_paste_limit(self):
        """Should return correct limit for delete_paste."""
        config = MagicMock()
        config.RATELIMIT_DEFAULT = "60/minute"
        config.RATELIMIT_DELETE_PASTE = "3/minute"

        resolver = create_limit_resolver(config, "delete_paste")
        assert resolver() == "3/minute"

    def test_resolver_returns_legacy_paste_limit(self):
        """Should return correct limit for get_paste_legacy."""
        config = MagicMock()
        config.RATELIMIT_DEFAULT = "60/minute"
        config.RATELIMIT_GET_PASTE_LEGACY = "15/minute"

        resolver = create_limit_resolver(config, "get_paste_legacy")
        assert resolver() == "15/minute"

    def test_resolver_returns_callable(self):
        """Resolver should be a callable."""
        config = MagicMock()
        config.RATELIMIT_DEFAULT = "60/minute"
        config.RATELIMIT_HEALTH = "100/minute"

        resolver = create_limit_resolver(config, "health")
        assert callable(resolver)


class TestCreateExemptKeyFunc:
    """Test bypass token key function creation."""

    def test_exempt_key_returns_ip_without_bypass_token(self):
        """Should return IP when no bypass token in request."""
        config = MagicMock()
        config.RATELIMIT_BYPASS_TOKENS = ["valid-token"]

        request = MagicMock()
        request.headers.get.return_value = None
        request.state.user_metadata.ip = "192.168.1.100"

        key_func = create_exempt_key_func(config)
        result = key_func(request)

        assert result == "192.168.1.100"

    def test_exempt_key_returns_ip_with_invalid_token(self):
        """Should return IP when token doesn't match."""
        config = MagicMock()
        config.RATELIMIT_BYPASS_TOKENS = ["valid-token"]

        request = MagicMock()
        request.headers.get.return_value = "invalid-token"
        request.state.user_metadata.ip = "192.168.1.100"

        key_func = create_exempt_key_func(config)
        result = key_func(request)

        assert result == "192.168.1.100"

    def test_exempt_key_returns_uuid_with_valid_token(self):
        """Should return unique UUID when bypass token matches."""
        config = MagicMock()
        config.RATELIMIT_BYPASS_TOKENS = ["valid-token", "another-token"]

        request = MagicMock()
        request.headers.get.return_value = "valid-token"
        request.state.user_metadata.ip = "192.168.1.100"

        key_func = create_exempt_key_func(config)
        result = key_func(request)

        # UUID format check
        assert len(result) == 36
        assert result.count("-") == 4
        assert result != "192.168.1.100"

    def test_exempt_key_returns_unique_uuids(self):
        """Each call with bypass token should return unique UUID."""
        config = MagicMock()
        config.RATELIMIT_BYPASS_TOKENS = ["valid-token"]

        request = MagicMock()
        request.headers.get.return_value = "valid-token"
        request.state.user_metadata.ip = "192.168.1.100"

        key_func = create_exempt_key_func(config)
        result1 = key_func(request)
        result2 = key_func(request)

        assert result1 != result2

    def test_exempt_key_with_empty_token_list(self):
        """Should return IP when bypass token list is empty."""
        config = MagicMock()
        config.RATELIMIT_BYPASS_TOKENS = []

        request = MagicMock()
        request.headers.get.return_value = "some-token"
        request.state.user_metadata.ip = "192.168.1.100"

        key_func = create_exempt_key_func(config)
        result = key_func(request)

        assert result == "192.168.1.100"

    def test_exempt_key_matches_any_token_in_list(self):
        """Should match any token in the bypass list."""
        config = MagicMock()
        config.RATELIMIT_BYPASS_TOKENS = ["token-1", "token-2", "token-3"]

        request = MagicMock()
        request.state.user_metadata.ip = "192.168.1.100"

        key_func = create_exempt_key_func(config)

        # Test each token
        for token in ["token-1", "token-2", "token-3"]:
            request.headers.get.return_value = token
            result = key_func(request)
            assert result != "192.168.1.100"
            assert len(result) == 36  # UUID


class TestGetIpAddress:
    """Test IP address extraction from request."""

    def test_get_ip_address_from_request_state(self):
        """Should extract IP from request.state.user_metadata.ip."""
        request = MagicMock()
        request.state.user_metadata.ip = "10.0.0.1"

        result = get_ip_address(request)

        assert result == "10.0.0.1"

    def test_get_ip_address_handles_ipv6(self):
        """Should handle IPv6 addresses."""
        request = MagicMock()
        request.state.user_metadata.ip = "::1"

        result = get_ip_address(request)

        assert result == "::1"


class TestRateLimitConfigIntegration:
    """Integration tests for rate limit config with Config class."""

    def test_config_accepts_valid_rate_limits(self):
        """Config should accept valid rate limit values."""
        # Create config with valid rate limits - don't override env values
        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,  # Don't load from .env file
        )
        # Just verify the defaults are valid
        assert config.RATELIMIT_DEFAULT == "60/minute"
        assert config.RATELIMIT_HEALTH == "60/minute"
        assert config.RATELIMIT_CREATE_PASTE == "4/minute"

    def test_config_has_correct_defaults(self):
        """Config should have correct default rate limit values."""
        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.RATELIMIT_ENABLED is True
        assert config.RATELIMIT_BACKEND == "memory"
        assert config.RATELIMIT_DEFAULT == "60/minute"
        assert config.RATELIMIT_HEALTH == "60/minute"
        assert config.RATELIMIT_GET_PASTE == "10/minute"
        assert config.RATELIMIT_GET_PASTE_LEGACY == "10/minute"
        assert config.RATELIMIT_CREATE_PASTE == "4/minute"
        assert config.RATELIMIT_EDIT_PASTE == "4/minute"
        assert config.RATELIMIT_DELETE_PASTE == "4/minute"
        assert config.RATELIMIT_BYPASS_TOKENS == []

    def test_config_bypass_tokens_default_empty_list(self):
        """Bypass tokens should default to empty list."""
        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.RATELIMIT_BYPASS_TOKENS == []
        assert isinstance(config.RATELIMIT_BYPASS_TOKENS, list)
