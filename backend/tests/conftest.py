"""Shared test fixtures for DevBin backend tests."""
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

from tests.constants import (
    TEST_BYPASS_TOKEN,
    TEST_CORS_DOMAINS,
    TEST_ALLOW_CORS_WILDCARD,
    TEST_DB_URL,
    TEST_FILE_STORAGE_PATH,
)

# Set test environment variables BEFORE importing app modules
os.environ.setdefault("APP_DATABASE_URL", TEST_DB_URL)
os.environ.setdefault("APP_BASE_FOLDER_PATH", TEST_FILE_STORAGE_PATH)
os.environ.setdefault("APP_DEBUG", "true")
# Use consistent CORS configuration with test_config fixture
# Must set wildcard to true BEFORE setting domains to allow wildcard
os.environ.setdefault("APP_ALLOW_CORS_WILDCARD", "true")
os.environ.setdefault("APP_CORS_DOMAINS", json.dumps(TEST_CORS_DOMAINS))
# Set a very high rate limit for tests (essentially disabled)
os.environ.setdefault("RATELIMIT_STORAGE_URL", "memory://")
os.environ.setdefault("RATELIMIT_ENABLED", "false")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config
from app.containers import Container
from app.db.base import Base
from main import create_app


@pytest.fixture(scope="session")
def test_config() -> Config:
    """Override config for testing."""
    # Use environment variable or default to test database
    db_url = os.getenv("APP_DATABASE_URL", TEST_DB_URL)

    return Config(
        DATABASE_URL=db_url,
        BASE_FOLDER_PATH=TEST_FILE_STORAGE_PATH,
        DEBUG=True,
        CACHE_SIZE_LIMIT=100,
        CACHE_TTL=10,
        ALLOW_CORS_WILDCARD=TEST_ALLOW_CORS_WILDCARD,
        CORS_DOMAINS=TEST_CORS_DOMAINS,
        ENFORCE_HTTPS=False,
        MIN_STORAGE_MB=1,  # Low threshold for testing
        BYPASS_TOKEN=TEST_BYPASS_TOKEN,  # For rate limit testing
    )


@pytest_asyncio.fixture(scope="function")
async def test_db_engine(test_config: Config) -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine and tables."""
    engine = create_async_engine(test_config.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with automatic rollback."""
    async_session = sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def temp_file_storage() -> Generator[Path, None, None]:
    """Create temporary directory for file storage tests."""
    temp_dir = Path(tempfile.mkdtemp(prefix="devbin_test_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="function")
def test_container(test_db_engine: AsyncEngine):
    """Create dependency injection container with test dependencies."""
    container = Container()

    # Override engine with test engine
    container.engine.override(test_db_engine)

    # Wire the container
    container.wire(modules=["app.api.routes", "app.api.subroutes.pastes"])
    return container


@pytest_asyncio.fixture(scope="function")
async def test_client(test_container: Container) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with dependency overrides."""
    app = create_app()
    app.container = test_container

    # Disable rate limiting for tests by removing state
    app.state.limiter = None

    async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def sample_paste_data():
    """Sample paste creation data."""
    return {
        "title": "Test Paste",
        "content": "This is test content",
        "content_language": "plain_text",
    }


@pytest.fixture
def bypass_headers():
    """Headers with bypass token to skip rate limiting."""
    return {"Authorization": TEST_BYPASS_TOKEN}


@pytest_asyncio.fixture
async def authenticated_paste(test_client: AsyncClient, sample_paste_data, bypass_headers):
    """Create a paste and return it with auth tokens."""
    response = await test_client.post("/pastes", json=sample_paste_data, headers=bypass_headers)
    assert response.status_code == 200
    return response.json()


@pytest_asyncio.fixture
async def legacy_plaintext_token_paste_factory(db_session: AsyncSession):
    """
    Factory fixture for creating pastes with legacy plaintext tokens.

    This is useful for testing token migration from plaintext to hashed tokens.
    Returns a function that creates a paste with a plaintext token.
    """
    from app.db.models import PasteEntity
    from datetime import datetime, timezone
    import uuid

    async def _create_legacy_paste(
        plaintext_token: str,
        paste_id: str = None,
        title: str = "Legacy Paste",
        content_language: str = "plain_text"
    ):
        """Create a paste with a legacy plaintext token."""
        paste_id = paste_id or str(uuid.uuid4())

        paste = PasteEntity(
            id=paste_id,
            title=title,
            content_language=content_language,
            edit_token=plaintext_token,  # Store as plaintext (legacy behavior)
            delete_token=plaintext_token,
            created_at=datetime.now(tz=timezone.utc),
        )

        db_session.add(paste)
        await db_session.commit()
        await db_session.refresh(paste)

        return {
            "id": paste.id,
            "edit_token": plaintext_token,
            "delete_token": plaintext_token,
            "title": paste.title,
        }

    return _create_legacy_paste
