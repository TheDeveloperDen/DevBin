"""File-based distributed lock implementation."""

import logging
from datetime import datetime
from pathlib import Path

from app.locks.distributed_lock import DistributedLock


class FileLock(DistributedLock):
    """File-based lock implementation (single-instance only)."""

    def __init__(self, lock_dir: str = "."):
        """
        Initialize file-based lock.

        Args:
            lock_dir: Directory to store lock files
        """
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.__class__.__name__)
        self._locks: dict[str, Path] = {}

    def acquire(self, key: str, timeout: int = 900) -> bool:
        """
        Try to acquire file-based lock.

        Args:
            key: Lock identifier
            timeout: Lock timeout in seconds

        Returns:
            True if lock acquired, False if lock already held
        """
        lock_file = self.lock_dir / f".{key}.lock"

        try:
            if lock_file.exists():
                # Check if lock is stale (older than timeout)
                lock_time = lock_file.stat().st_mtime
                age = datetime.now().timestamp() - lock_time
                if age < timeout:
                    self.logger.debug("Lock %s is held (age: %.1fs)", key, age)
                    return False  # Lock still valid
                else:
                    self.logger.info(
                        "Lock %s is stale (age: %.1fs > timeout: %ds), acquiring",
                        key,
                        age,
                        timeout,
                    )

            # Create or update lock file
            lock_file.touch()
            self._locks[key] = lock_file
            self.logger.info("Lock %s acquired", key)
            return True
        except Exception as exc:
            self.logger.error("Failed to acquire lock %s: %s", key, exc)
            return False

    def release(self, key: str) -> None:
        """
        Release file-based lock.

        Args:
            key: Lock identifier
        """
        try:
            lock_file = self._locks.get(key)
            if lock_file and lock_file.exists():
                lock_file.unlink()
                self.logger.info("Lock %s released", key)
            del self._locks[key]
        except KeyError:
            pass
        except Exception as exc:
            self.logger.error("Failed to release lock %s: %s", key, exc)

    def touch(self, key: str) -> None:
        """
        Update lock file timestamp to keep it alive.

        Args:
            key: Lock identifier
        """
        try:
            lock_file = self._locks.get(key)
            if lock_file:
                lock_file.touch()
                self.logger.debug("Lock %s touched", key)
        except Exception as exc:
            self.logger.error("Failed to touch lock %s: %s", key, exc)
