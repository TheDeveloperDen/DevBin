"""Tests for storage abstraction layer."""
from pathlib import Path

import pytest

from app.storage.local_storage import LocalStorageClient


@pytest.mark.asyncio
class TestLocalStorageClient:
    """Test local filesystem storage client."""

    async def test_put_and_get_object(self, temp_file_storage):
        """Should store and retrieve objects."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))
        key = "test/file.txt"
        data = b"Hello, World!"

        # Put object
        await storage.put_object(key, data)

        # Get object
        retrieved = await storage.get_object(key)
        assert retrieved == data

    async def test_get_nonexistent_object(self, temp_file_storage):
        """Getting nonexistent object should return None."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))

        result = await storage.get_object("nonexistent/key.txt")
        assert result is None

    async def test_delete_object(self, temp_file_storage):
        """Should delete objects."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))
        key = "test/deleteme.txt"
        data = b"Delete this"

        # Put and verify exists
        await storage.put_object(key, data)
        assert await storage.exists(key)

        # Delete and verify gone
        await storage.delete_object(key)
        assert not await storage.exists(key)

    async def test_exists_check(self, temp_file_storage):
        """Should correctly check object existence."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))
        key = "test/exists.txt"

        # Should not exist initially
        assert not await storage.exists(key)

        # Should exist after put
        await storage.put_object(key, b"data")
        assert await storage.exists(key)

    async def test_list_keys(self, temp_file_storage):
        """Should list all keys with prefix."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))

        # Create some objects
        await storage.put_object("prefix/file1.txt", b"data1")
        await storage.put_object("prefix/file2.txt", b"data2")
        await storage.put_object("other/file3.txt", b"data3")

        # List with prefix
        keys = await storage.list_keys(prefix="prefix/")
        assert len(keys) == 2
        assert "prefix/file1.txt" in keys
        assert "prefix/file2.txt" in keys
        assert "other/file3.txt" not in keys

    async def test_list_all_keys(self, temp_file_storage):
        """Should list all keys when no prefix given."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))

        # Create some objects
        await storage.put_object("file1.txt", b"data1")
        await storage.put_object("dir/file2.txt", b"data2")

        # List all
        keys = await storage.list_keys(prefix="")
        assert len(keys) >= 2

    async def test_put_creates_directories(self, temp_file_storage):
        """Should create parent directories automatically."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))
        key = "deep/nested/path/file.txt"

        await storage.put_object(key, b"data")

        # Verify directory structure was created
        file_path = Path(temp_file_storage) / key
        assert file_path.exists()
        assert file_path.is_file()

    async def test_binary_data_handling(self, temp_file_storage):
        """Should handle binary data correctly."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))
        key = "binary/data.bin"
        binary_data = bytes([0, 1, 2, 255, 254, 253])

        await storage.put_object(key, binary_data)
        retrieved = await storage.get_object(key)

        assert retrieved == binary_data

    async def test_large_file_handling(self, temp_file_storage):
        """Should handle larger files efficiently."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))
        key = "large/file.dat"
        # Create 1MB of data
        large_data = b"x" * (1024 * 1024)

        await storage.put_object(key, large_data)
        retrieved = await storage.get_object(key)

        assert len(retrieved) == len(large_data)
        assert retrieved == large_data

    async def test_delete_nonexistent_object_no_error(self, temp_file_storage):
        """Deleting nonexistent object should not raise error."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))

        # Should not raise
        await storage.delete_object("nonexistent/file.txt")

    async def test_empty_key_handling(self, temp_file_storage):
        """Should handle empty keys gracefully."""
        storage = LocalStorageClient(base_path=str(temp_file_storage))

        # List with empty prefix should work
        keys = await storage.list_keys(prefix="")
        assert isinstance(keys, list)
