"""Redis-based distributed lock implementation."""

import logging

from app.locks.distributed_lock import DistributedLock


class RedisLock(DistributedLock):
    """Redis-based distributed lock implementation."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
    ):
        """
        Initialize Redis-based lock.

        Args:
            host: Redis server host
            port: Redis server port
            db: Redis database number
            password: Redis password (optional)
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None
        self._lock_prefix = "lock:"

    def _get_client(self):
        """Get or create Redis client."""
        if self._client is None:
            try:
                import redis
            except ImportError:
                raise ImportError("redis is required for Redis locks. Install it with: uv sync --extra") from None

            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )
        return self._client

    def acquire(self, key: str, timeout: int = 900) -> bool:
        """
        Try to acquire Redis-based lock using SET NX with expiry.

        Args:
            key: Lock identifier
            timeout: Lock timeout in seconds

        Returns:
            True if lock acquired, False if already held
        """
        try:
            client = self._get_client()
            lock_key = f"{self._lock_prefix}{key}"

            # SET NX (set if not exists) with expiry
            result = client.set(lock_key, "1", nx=True, ex=timeout)

            if result:
                self.logger.info("Lock %s acquired (timeout: %ds)", key, timeout)
                return True
            else:
                self.logger.debug("Lock %s is held by another instance", key)
                return False
        except Exception as exc:
            self.logger.error("Failed to acquire Redis lock %s: %s", key, exc)
            return False

    def release(self, key: str) -> None:
        """
        Release Redis-based lock.

        Args:
            key: Lock identifier
        """
        try:
            client = self._get_client()
            lock_key = f"{self._lock_prefix}{key}"

            client.delete(lock_key)
            self.logger.info("Lock %s released", key)
        except Exception as exc:
            self.logger.error("Failed to release Redis lock %s: %s", key, exc)

    def touch(self, key: str) -> None:
        """
        Extend lock expiry to keep it alive.

        Args:
            key: Lock identifier
        """
        try:
            client = self._get_client()
            lock_key = f"{self._lock_prefix}{key}"

            # Extend expiry by 900 seconds (15 minutes)
            client.expire(lock_key, 900)
            self.logger.debug("Lock %s expiry extended", key)
        except Exception as exc:
            self.logger.error("Failed to touch Redis lock %s: %s", key, exc)
