"""Unit tests for Config validation."""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

# Suppress RuntimeWarnings from pydantic_settings triggering async code during Config import
pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")


@pytest.mark.unit
class TestConfigEnvironments:
    """Tests for environment configuration."""

    def test_environment_field_exists(self):
        """Config should have ENVIRONMENT field."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert hasattr(config, "ENVIRONMENT")
        assert config.ENVIRONMENT in ["dev", "staging", "prod"]

    def test_environment_accepts_staging(self):
        """Environment should accept 'staging'."""
        from app.config import Config

        with patch.dict(os.environ, {"APP_ENVIRONMENT": "staging"}, clear=False):
            config = Config(
                ENVIRONMENT="staging",
                ALLOW_CORS_WILDCARD=True,
                _env_file=None,
            )
            assert config.ENVIRONMENT == "staging"


@pytest.mark.unit
class TestConfigDatabaseURL:
    """Tests for database URL validation."""

    def test_database_url_contains_asyncpg(self):
        """Database URL should contain asyncpg driver."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert "asyncpg" in config.DATABASE_URL

    def test_database_url_converts_to_asyncpg(self):
        """Database URL validator should convert to asyncpg."""
        from app.config import Config

        # Use the validator directly
        result = Config.verify_db_url("postgresql://user:pass@localhost:5432/db")
        assert "asyncpg" in result


@pytest.mark.unit
class TestConfigCORS:
    """Tests for CORS configuration validation."""

    def test_cors_domains_is_list(self):
        """CORS_DOMAINS should be a list."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert isinstance(config.CORS_DOMAINS, list)

    def test_cors_wildcard_requires_allow_flag(self):
        """CORS wildcard should require ALLOW_CORS_WILDCARD flag."""
        from app.config import Config

        # This should raise because we're trying to use wildcard without allowing it
        # But we need to clear the env var first
        with patch.dict(os.environ, {}, clear=True), pytest.raises((ValidationError, ValueError)):
            Config(
                ALLOW_CORS_WILDCARD=False,
                CORS_DOMAINS=["*"],
                DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/db",
                _env_file=None,
            )


@pytest.mark.unit
class TestConfigCompression:
    """Tests for compression configuration validation."""

    def test_compression_enabled_field_exists(self):
        """Config should have COMPRESSION_ENABLED field."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert hasattr(config, "COMPRESSION_ENABLED")
        assert isinstance(config.COMPRESSION_ENABLED, bool)

    def test_compression_level_in_valid_range(self):
        """Compression level should be in valid range (1-9)."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert 1 <= config.COMPRESSION_LEVEL <= 9

    def test_compression_level_validator_corrects_invalid(self):
        """Compression level validator should correct invalid values."""
        from app.config import Config

        # Test the validator directly
        assert Config.validate_compression_level(5) == 5
        assert Config.validate_compression_level(0) == 6  # Falls back to 6
        assert Config.validate_compression_level(10) == 6  # Falls back to 6

    def test_compression_threshold_is_non_negative(self):
        """Compression threshold should be non-negative."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.COMPRESSION_THRESHOLD_BYTES >= 0

    def test_compression_threshold_validator_corrects_negative(self):
        """Compression threshold validator should correct negative values."""
        from app.config import Config

        # Test the validator directly
        assert Config.validate_compression_threshold(1024) == 1024
        assert Config.validate_compression_threshold(0) == 0
        assert Config.validate_compression_threshold(-100) == 512  # Falls back


@pytest.mark.unit
class TestConfigStorageLimits:
    """Tests for storage limit configuration."""

    def test_min_storage_mb_is_positive(self):
        """MIN_STORAGE_MB should be positive."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.MIN_STORAGE_MB > 0

    def test_max_content_length_is_positive(self):
        """MAX_CONTENT_LENGTH should be positive."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.MAX_CONTENT_LENGTH > 0


@pytest.mark.unit
class TestConfigCache:
    """Tests for cache configuration."""

    def test_cache_size_limit_is_positive(self):
        """CACHE_SIZE_LIMIT should be positive."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.CACHE_SIZE_LIMIT > 0

    def test_cache_ttl_is_positive(self):
        """CACHE_TTL should be positive."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.CACHE_TTL > 0

    def test_cache_type_is_valid(self):
        """CACHE_TYPE should be a valid value."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.CACHE_TYPE in ["memory", "redis"]


@pytest.mark.unit
class TestConfigTrustedHosts:
    """Tests for trusted hosts configuration."""

    def test_trusted_hosts_is_list(self):
        """TRUSTED_HOSTS should be a list."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert isinstance(config.TRUSTED_HOSTS, list)


@pytest.mark.unit
class TestConfigSecurity:
    """Tests for security-related configuration."""

    def test_enforce_https_is_bool(self):
        """ENFORCE_HTTPS should be a boolean."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert isinstance(config.ENFORCE_HTTPS, bool)

    def test_debug_is_bool(self):
        """DEBUG should be a boolean."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert isinstance(config.DEBUG, bool)

    def test_metrics_token_field_exists(self):
        """METRICS_TOKEN field should exist."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert hasattr(config, "METRICS_TOKEN")

    def test_ratelimit_enabled_is_bool(self):
        """RATELIMIT_ENABLED should be a boolean."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert isinstance(config.RATELIMIT_ENABLED, bool)

    def test_ratelimit_backend_is_valid(self):
        """RATELIMIT_BACKEND should be valid."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.RATELIMIT_BACKEND in ["memory", "redis"]


@pytest.mark.unit
class TestConfigGetConfig:
    """Tests for get_config function."""

    def test_get_config_returns_config_instance(self):
        """get_config should return Config instance."""
        from app.config import Config, get_config

        result = get_config()

        assert isinstance(result, Config)

    def test_get_config_returns_module_level_config(self):
        """get_config should return the module-level config."""
        from app.config import config, get_config

        result = get_config()

        assert result is config


@pytest.mark.unit
class TestValidateRateLimit:
    """Tests for rate limit validation function."""

    def test_validate_rate_limit_accepts_second(self):
        """Should accept per-second rate limits."""
        from app.config import validate_rate_limit

        assert validate_rate_limit("10/second") == "10/second"

    def test_validate_rate_limit_accepts_minute(self):
        """Should accept per-minute rate limits."""
        from app.config import validate_rate_limit

        assert validate_rate_limit("60/minute") == "60/minute"

    def test_validate_rate_limit_accepts_hour(self):
        """Should accept per-hour rate limits."""
        from app.config import validate_rate_limit

        assert validate_rate_limit("100/hour") == "100/hour"

    def test_validate_rate_limit_accepts_day(self):
        """Should accept per-day rate limits."""
        from app.config import validate_rate_limit

        assert validate_rate_limit("1000/day") == "1000/day"

    def test_validate_rate_limit_rejects_invalid_unit(self):
        """Should reject invalid time units."""
        from app.config import validate_rate_limit

        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("10/week")

    def test_validate_rate_limit_rejects_missing_number(self):
        """Should reject rate limits without a number."""
        from app.config import validate_rate_limit

        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("/minute")

    def test_validate_rate_limit_rejects_empty_string(self):
        """Should reject empty string."""
        from app.config import validate_rate_limit

        with pytest.raises(ValueError, match="Invalid rate limit format"):
            validate_rate_limit("")


@pytest.mark.unit
class TestConfigLogging:
    """Tests for logging configuration."""

    def test_log_level_is_valid(self):
        """LOG_LEVEL should be a valid logging level."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def test_log_format_is_valid(self):
        """LOG_FORMAT should be a valid format."""
        from app.config import Config

        config = Config(
            ALLOW_CORS_WILDCARD=True,
            _env_file=None,
        )

        assert config.LOG_FORMAT in ["text", "json"]
