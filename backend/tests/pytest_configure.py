"""Pytest configuration plugin that sets environment variables early."""
import os


def pytest_configure(config):
    """Set test environment variables before any test collection."""
    os.environ.setdefault("APP_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/devbin_test")
    os.environ.setdefault("APP_BASE_FOLDER_PATH", "/tmp/devbin_test_files")
    os.environ.setdefault("APP_DEBUG", "true")
    # Use a test domain instead of wildcard to avoid validator issues
    os.environ.setdefault("APP_CORS_DOMAINS", '["http://test"]')
    os.environ.setdefault("APP_ALLOW_CORS_WILDCARD", "false")
