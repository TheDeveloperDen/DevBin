"""Storage abstraction layer for paste content."""

from app.storage.local_storage import LocalStorageClient
from app.storage.storage_client import StorageClient

__all__ = ["StorageClient", "LocalStorageClient"]
