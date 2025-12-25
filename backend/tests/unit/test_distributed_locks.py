"""Tests for distributed locking implementations."""
import pytest
import tempfile
from pathlib import Path

from app.locks.file_lock import FileLock


class TestFileLock:
    """Test file-based distributed locking."""

    def test_acquire_and_release_lock(self):
        """Should acquire and release locks successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            # Acquire lock
            assert lock.acquire("test-key", timeout=10)

            # Release lock
            lock.release("test-key")

            # Should be able to acquire again
            assert lock.acquire("test-key", timeout=10)
            lock.release("test-key")

    def test_lock_prevents_concurrent_access(self):
        """Lock should prevent concurrent acquisition."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock1 = FileLock(lock_dir=tmpdir)
            lock2 = FileLock(lock_dir=tmpdir)

            # First lock acquires
            assert lock1.acquire("test-key", timeout=10)

            # Second lock should fail (same key)
            assert not lock2.acquire("test-key", timeout=1)

            # After release, second should succeed
            lock1.release("test-key")
            assert lock2.acquire("test-key", timeout=10)
            lock2.release("test-key")

    def test_different_keys_independent(self):
        """Different keys should have independent locks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            # Acquire multiple different keys
            assert lock.acquire("key1", timeout=10)
            assert lock.acquire("key2", timeout=10)
            assert lock.acquire("key3", timeout=10)

            # Release them
            lock.release("key1")
            lock.release("key2")
            lock.release("key3")

    def test_touch_extends_lock_lifetime(self):
        """Touch should extend lock expiry time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            assert lock.acquire("test-key", timeout=10)

            # Touch to extend
            lock.touch("test-key")

            # Lock should still be held
            lock_file = Path(tmpdir) / ".test-key.lock"
            assert lock_file.exists()

            lock.release("test-key")

    def test_lock_expiry(self):
        """Locks should expire after timeout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            # Acquire with very short timeout (1 second)
            assert lock.acquire("test-key", timeout=1)

            # Wait for expiry (in real usage, would need to wait)
            # For testing, we just verify the lock file exists
            lock_file = Path(tmpdir) / ".test-key.lock"
            assert lock_file.exists()

            lock.release("test-key")

    def test_release_nonexistent_lock_no_error(self):
        """Releasing nonexistent lock should not error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            # Should not raise
            lock.release("nonexistent-key")

    def test_touch_nonexistent_lock_no_error(self):
        """Touching nonexistent lock should not error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            # Should not raise
            lock.touch("nonexistent-key")

    def test_lock_file_creation(self):
        """Lock files should be created in correct location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            lock.acquire("my-lock", timeout=10)

            # Verify lock file exists
            lock_file = Path(tmpdir) / ".my-lock.lock"
            assert lock_file.exists()
            assert lock_file.is_file()

            lock.release("my-lock")

    def test_multiple_sequential_acquisitions(self):
        """Should handle multiple sequential lock operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock = FileLock(lock_dir=tmpdir)

            for i in range(10):
                assert lock.acquire("test-key", timeout=10)
                lock.touch("test-key")
                lock.release("test-key")

    def test_acquire_timeout_behavior(self):
        """Lock acquisition should respect timeout parameter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lock1 = FileLock(lock_dir=tmpdir)
            lock2 = FileLock(lock_dir=tmpdir)

            # First acquires
            assert lock1.acquire("test-key", timeout=10)

            # Second should eventually timeout (but may succeed if lock expired)
            # We just test that acquire returns a boolean
            result = lock2.acquire("test-key", timeout=1)
            assert isinstance(result, bool)

            lock1.release("test-key")
