"""Abstract storage client interface."""

from abc import ABC, abstractmethod


class StorageClient(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def put_object(self, key: str, data: bytes) -> None:
        """
        Store object with given key.

        Args:
            key: Storage key/path for the object
            data: Binary data to store

        Raises:
            Exception: If storage operation fails
        """
        pass

    @abstractmethod
    async def get_object(self, key: str) -> bytes | None:
        """
        Retrieve object by key.

        Args:
            key: Storage key/path for the object

        Returns:
            Binary data if found, None otherwise

        Raises:
            Exception: If storage operation fails
        """
        pass

    @abstractmethod
    async def delete_object(self, key: str) -> None:
        """
        Delete object by key.

        Args:
            key: Storage key/path for the object

        Raises:
            Exception: If storage operation fails
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if object exists.

        Args:
            key: Storage key/path for the object

        Returns:
            True if object exists, False otherwise
        """
        pass

    @abstractmethod
    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        List all keys with given prefix.

        Args:
            prefix: Key prefix to filter by (optional)

        Returns:
            List of keys matching the prefix
        """
        pass
