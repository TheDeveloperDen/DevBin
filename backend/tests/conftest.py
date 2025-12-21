"""Shared test fixtures for DevBin backend tests."""
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

# Set test environment variables BEFORE importing app modules
os.environ.setdefault("APP_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/devbin_test")
os.environ.setdefault("APP_BASE_FOLDER_PATH", "/tmp/devbin_test_files")
os.environ.setdefault("APP_DEBUG", "true")
# Use a test domain instead of wildcard to avoid validator issues
os.environ.setdefault("APP_CORS_DOMAINS", '["http://test"]')
os.environ.setdefault("APP_ALLOW_CORS_WILDCARD", "false")

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
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config() -> Config:
    """Override config for testing."""
    import os
    # Use environment variable or default to test database on port 5433
    db_url = os.getenv(
        "APP_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5433/devbin_test"
    )

    return Config(
        DATABASE_URL=db_url,
        BASE_FOLDER_PATH="/tmp/devbin_test_files",
        DEBUG=True,
        CACHE_SIZE_LIMIT=100,
        CACHE_TTL=10,
        ALLOW_CORS_WILDCARD=True,
        CORS_DOMAINS=["*"],
        ENFORCE_HTTPS=False,
        MIN_STORAGE_MB=1,  # Low threshold for testing
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
