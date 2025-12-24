"""
Centralized test constants to avoid duplication across test files.
"""

# Authentication & Authorization
TEST_BYPASS_TOKEN = "test_bypass_token_12345"
TEST_TOKEN_LENGTH = 32

# Database Configuration
TEST_DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/devbin_test"
TEST_DB_PORT = 5433

# File Storage
TEST_FILE_STORAGE_PATH = "/tmp/devbin_test_files"

# CORS Configuration
TEST_CORS_DOMAINS = ["http://test"]
TEST_ALLOW_CORS_WILDCARD = False

# Time & Validation
TIME_TOLERANCE_SECONDS = 2  # Tolerance for datetime comparisons in tests

# Storage Mocking
STORAGE_MOCK_TOTAL = 1000000  # 1MB total storage
STORAGE_MOCK_USED = 999999    # Almost full
STORAGE_MOCK_FREE = 1          # 1 byte free
