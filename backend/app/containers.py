from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import Config, get_config
from app.locks import DistributedLock
from app.locks.file_lock import FileLock
from app.locks.redis_lock import RedisLock
from app.storage import StorageClient
from app.storage.local_storage import LocalStorageClient
from app.storage.minio_storage import MinIOStorageClient
from app.storage.s3_storage import S3StorageClient
from app.utils.LRUMemoryCache import LRUMemoryCache


@asynccontextmanager
async def _engine_resource(db_url: str, echo: bool = False) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(db_url, echo=echo, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@asynccontextmanager
async def _session_resource(factory: sessionmaker) -> AsyncIterator[AsyncSession]:
    session: AsyncSession = factory()
    try:
        yield session
    finally:
        await session.close()


def _create_storage_client(config: Config) -> StorageClient:
    """Create storage client based on configuration."""
    storage_type = config.STORAGE_TYPE

    if storage_type == "s3":
        return S3StorageClient(
            bucket_name=config.S3_BUCKET_NAME,
            region=config.S3_REGION,
            access_key=config.S3_ACCESS_KEY,
            secret_key=config.S3_SECRET_KEY,
            endpoint_url=config.S3_ENDPOINT_URL,
        )
    elif storage_type == "minio":
        return MinIOStorageClient(
            bucket_name=config.S3_BUCKET_NAME,  # MinIO uses same bucket concept
            endpoint_url=config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=config.MINIO_SECURE,
        )
    else:  # default to local
        return LocalStorageClient(base_path=config.BASE_FOLDER_PATH)


def _create_distributed_lock(config: Config) -> DistributedLock:
    """Create distributed lock based on configuration with fallback to file lock."""
    import logging

    logger = logging.getLogger(__name__)
    lock_type = config.LOCK_TYPE

    if lock_type == "redis":
        try:
            import redis  # noqa: F401

            logger.info(
                "Initializing Redis lock at %s:%d (db=%d)",
                config.REDIS_HOST,
                config.REDIS_PORT,
                config.REDIS_DB,
            )
            return RedisLock(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD,
            )
        except ImportError:
            logger.warning(
                "Redis lock requested but redis package not installed. "
                "Falling back to file-based lock. "
                "Install with: pip install redis"
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize Redis lock: %s. Falling back to file-based lock.",
                exc,
            )

    # Default to file-based lock
    logger.info("Using file-based lock")
    return FileLock(lock_dir=".")


def _create_cache(config: Config):
    """Create cache based on configuration with fallback to memory cache."""
    import logging

    from aiocache.serializers import PickleSerializer

    logger = logging.getLogger(__name__)
    cache_type = config.CACHE_TYPE

    if cache_type == "redis":
        try:
            from aiocache import RedisCache

            logger.info(
                "Initializing Redis cache at %s:%d (db=%d)",
                config.REDIS_HOST,
                config.REDIS_PORT,
                config.REDIS_DB,
            )
            return RedisCache(
                endpoint=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD,
                serializer=PickleSerializer(),
                ttl=config.CACHE_TTL,
                namespace="paste:",
            )
        except ImportError:
            logger.warning(
                "Redis cache requested but aiocache[redis] not installed. "
                "Falling back to in-memory cache. "
                "Install with: pip install aiocache[redis]"
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize Redis cache: %s. Falling back to in-memory cache.",
                exc,
            )

    # Default to in-memory cache
    logger.info("Using in-memory LRU cache (max_size=%d)", config.CACHE_SIZE_LIMIT)
    return LRUMemoryCache(
        serializer=PickleSerializer(),
        max_size=config.CACHE_SIZE_LIMIT,
        ttl=config.CACHE_TTL,
    )


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.api.routes",
            "app.api.subroutes.pastes",
            "app.services",
            "app.dependencies.db",
        ]
    )

    config = providers.Callable(get_config)
    # Database engine (async) as a managed resource
    engine = providers.Resource(
        _engine_resource,
        db_url=config().DATABASE_URL,
        echo=config().SQLALCHEMY_ECHO,
    )

    # SQLAlchemy session factory
    session_factory = providers.Factory(
        sessionmaker,
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Storage client
    storage_client = providers.Singleton(
        _create_storage_client,
        config=config,
    )

    # Distributed lock
    distributed_lock = providers.Singleton(
        _create_distributed_lock,
        config=config,
    )

    # Cache client
    cache_client = providers.Singleton(
        _create_cache,
        config=config,
    )

    # Services
    from app.services.cleanup_service import CleanupService
    from app.services.health_service import HealthService
    from app.services.paste_service import PasteService

    health_service = providers.Factory(
        HealthService,
        session_factory,
        storage_client,
        cache_client,
    )

    cleanup_service = providers.Factory(
        CleanupService,
        session_factory,
        config().BASE_FOLDER_PATH,
        distributed_lock,
    )

    paste_service = providers.Factory(PasteService, session_factory, cleanup_service, storage_client)
