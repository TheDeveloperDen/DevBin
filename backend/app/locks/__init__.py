"""Distributed locking abstraction layer."""

from app.locks.distributed_lock import DistributedLock
from app.locks.file_lock import FileLock

__all__ = ["DistributedLock", "FileLock"]
