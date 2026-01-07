"""Abstract distributed lock interface."""

from abc import ABC, abstractmethod


class DistributedLock(ABC):
    """Abstract base class for distributed locks."""

    @abstractmethod
    def acquire(self, key: str, timeout: int = 900) -> bool:
        """
        Try to acquire lock with given key.

        Args:
            key: Lock identifier
            timeout: Lock timeout in seconds (default: 900 = 15 minutes)

        Returns:
            True if lock acquired, False otherwise
        """
        pass

    @abstractmethod
    def release(self, key: str) -> None:
        """
        Release lock with given key.

        Args:
            key: Lock identifier
        """
        pass

    @abstractmethod
    def touch(self, key: str) -> None:
        """
        Update lock timestamp to prevent expiration (keep-alive).

        Args:
            key: Lock identifier
        """
        pass
