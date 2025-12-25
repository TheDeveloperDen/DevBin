"""Storage abstraction layer for paste content."""

from app.storage.storage_client import StorageClient
from app.storage.local_storage import LocalStorageClient

__all__ = ["StorageClient", "LocalStorageClient"]
