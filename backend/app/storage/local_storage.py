"""Local filesystem storage implementation."""

import logging
from pathlib import Path

import aiofiles

from app.storage.storage_client import StorageClient


class LocalStorageClient(StorageClient):
    """Local filesystem storage implementation."""

    def __init__(self, base_path: str):
        """
        Initialize local storage client.

        Args:
            base_path: Base directory path for storage
        """
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(self.__class__.__name__)

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def put_object(self, key: str, data: bytes) -> None:
        """
        Store object in local filesystem.

        Args:
            key: Relative path from base_path
            data: Binary data to store
        """
        file_path = self.base_path / key

        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(data)

        self.logger.debug("Stored object at %s (%d bytes)", file_path, len(data))

    async def get_object(self, key: str) -> bytes | None:
        """
        Retrieve object from local filesystem.

        Args:
            key: Relative path from base_path

        Returns:
            Binary data if found, None otherwise
        """
        file_path = self.base_path / key

        if not file_path.exists():
            self.logger.debug("Object not found at %s", file_path)
            return None

        try:
            async with aiofiles.open(file_path, "rb") as f:
                data = await f.read()
            self.logger.debug("Retrieved object from %s (%d bytes)", file_path, len(data))
            return data
        except Exception as exc:
            self.logger.error("Failed to read object from %s: %s", file_path, exc)
            raise

    async def delete_object(self, key: str) -> None:
        """
        Delete object from local filesystem.

        Args:
            key: Relative path from base_path
        """
        file_path = self.base_path / key

        if file_path.exists():
            file_path.unlink()
            self.logger.debug("Deleted object at %s", file_path)
        else:
            self.logger.debug("Object not found for deletion at %s", file_path)

    async def exists(self, key: str) -> bool:
        """
        Check if object exists in local filesystem.

        Args:
            key: Relative path from base_path

        Returns:
            True if object exists, False otherwise
        """
        file_path = self.base_path / key
        return file_path.exists()

    async def list_keys(self, prefix: str = "") -> list[str]:
        """
        List all keys with given prefix in local filesystem.

        Args:
            prefix: Path prefix to filter by (optional)

        Returns:
            List of relative paths matching the prefix
        """
        search_path = self.base_path / prefix if prefix else self.base_path

        if not search_path.exists():
            return []

        # Find all files recursively
        keys = []
        if search_path.is_dir():
            for file_path in search_path.rglob("*"):
                if file_path.is_file():
                    # Get relative path from base_path
                    relative_path = file_path.relative_to(self.base_path)
                    keys.append(str(relative_path))
        elif search_path.is_file():
            relative_path = search_path.relative_to(self.base_path)
            keys.append(str(relative_path))

        return keys
