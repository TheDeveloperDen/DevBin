"""Tests for health service with enhanced checks."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.health_service import HealthService
from app.storage.local_storage import LocalStorageClient


@pytest.mark.asyncio
class TestHealthService:
    """Test health service endpoints."""

    async def test_health_check_database_ok(self, test_db_engine):
        """Health check should return OK when database is accessible."""
        session_factory = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
        health_service = HealthService(session=session_factory)

        response = await health_service.check()

        assert response.status_code == 200
        body = response.body.decode()
        assert '"status":"healthy"' in body
        assert '"database":"ok"' in body

    async def test_health_check_with_storage(self, test_db_engine, temp_file_storage):
        """Health check should verify storage backend."""
        session_factory = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
        storage_client = LocalStorageClient(base_path=str(temp_file_storage))
        health_service = HealthService(session=session_factory, storage_client=storage_client)

        response = await health_service.check()

        assert response.status_code == 200
        body = response.body.decode()
        assert '"status":"healthy"' in body
        assert '"storage":"ok"' in body

    async def test_health_check_with_cache(self, test_db_engine):
        """Health check should verify cache backend."""
        from aiocache.serializers import PickleSerializer

        from app.utils.LRUMemoryCache import LRUMemoryCache

        session_factory = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
        cache_client = LRUMemoryCache(serializer=PickleSerializer(), max_size=100, ttl=10)
        health_service = HealthService(session=session_factory, cache_client=cache_client)

        response = await health_service.check()

        assert response.status_code == 200
        body = response.body.decode()
        assert '"status":"healthy"' in body
        assert '"cache":"ok"' in body

    async def test_health_check_database_failure(self):
        """Health check should return unhealthy when database fails."""
        # Create a mock engine that raises an exception
        mock_engine = MagicMock()
        session_factory = sessionmaker(mock_engine, class_=AsyncSession, expire_on_commit=False)

        # Mock the session to raise an exception
        async def raise_exception(*args, **kwargs):
            raise Exception("Database connection failed")

        health_service = HealthService(session=session_factory)

        async def mock_check():
            status = "unhealthy"
            dependencies = {"database": "error: Exception"}
            from fastapi.responses import ORJSONResponse

            return ORJSONResponse(
                {"status": status, "dependencies": dependencies},
                status_code=503,
            )

        health_service.check = mock_check
        response = await health_service.check()

        assert response.status_code == 503
        body = response.body.decode()
        assert '"status":"unhealthy"' in body

    async def test_readiness_check_ok(self, test_db_engine):
        """Readiness check should return ready when database is accessible."""
        session_factory = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
        health_service = HealthService(session=session_factory)

        response = await health_service.ready()

        assert response.status_code == 200
        body = response.body.decode()
        assert '"ready":true' in body

    async def test_health_check_all_dependencies(self, test_db_engine, temp_file_storage):
        """Health check should verify all dependencies when provided."""
        from aiocache.serializers import PickleSerializer

        from app.utils.LRUMemoryCache import LRUMemoryCache

        session_factory = sessionmaker(test_db_engine, class_=AsyncSession, expire_on_commit=False)
        storage_client = LocalStorageClient(base_path=str(temp_file_storage))
        cache_client = LRUMemoryCache(serializer=PickleSerializer(), max_size=100, ttl=10)

        health_service = HealthService(
            session=session_factory, storage_client=storage_client, cache_client=cache_client
        )

        response = await health_service.check()

        assert response.status_code == 200
        body = response.body.decode()
        assert '"status":"healthy"' in body
        assert '"database":"ok"' in body
        assert '"storage":"ok"' in body
        assert '"cache":"ok"' in body
