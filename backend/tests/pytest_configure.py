"""Pytest configuration plugin that sets environment variables early."""

import json
import os

from tests.constants import (
    TEST_ALLOW_CORS_WILDCARD,
    TEST_CORS_DOMAINS,
    TEST_DB_URL,
    TEST_FILE_STORAGE_PATH,
)


def pytest_configure(config):
    """Set test environment variables before any test collection."""
    os.environ.setdefault("APP_DATABASE_URL", TEST_DB_URL)
    os.environ.setdefault("APP_BASE_FOLDER_PATH", TEST_FILE_STORAGE_PATH)
    os.environ.setdefault("APP_DEBUG", "true")
    # Set CORS configuration - must set wildcard flag before domains
    os.environ.setdefault("APP_ALLOW_CORS_WILDCARD", str(TEST_ALLOW_CORS_WILDCARD).lower())
    os.environ.setdefault("APP_CORS_DOMAINS", json.dumps(TEST_CORS_DOMAINS))
