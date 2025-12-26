"""Unit tests for CleanupService."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestCleanupServiceInit:
    """Tests for CleanupService initialization."""

    def test_initialization_stores_session_maker(self):
        """CleanupService should store session maker."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        assert service.session_maker == mock_session_maker

    def test_initialization_stores_base_folder_path(self):
        """CleanupService should store base folder path."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        assert service.paste_base_folder_path == "/tmp/test"  # noqa: S108

    def test_initialization_with_lock(self):
        """CleanupService should accept distributed lock."""
        from app.locks import DistributedLock
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        mock_lock = MagicMock(spec=DistributedLock)

        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test", lock=mock_lock)  # noqa: S108

        # Lock is stored as _lock (private attribute)
        assert service._lock == mock_lock

    def test_initialization_without_lock(self):
        """CleanupService should work without distributed lock."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        assert service._lock is None

    def test_initialization_cleanup_task_is_none(self):
        """CleanupService should start with no cleanup task."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        assert service._cleanup_task is None

    def test_initialization_creates_logger(self):
        """CleanupService should create a logger."""
        import logging

        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        assert service.logger is not None
        assert isinstance(service.logger, logging.Logger)


@pytest.mark.unit
class TestCleanupServiceWorker:
    """Tests for cleanup worker management."""

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_start_cleanup_worker_creates_task(self):
        """start_cleanup_worker should create asyncio task."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            service.start_cleanup_worker()

            mock_create_task.assert_called_once()
            assert service._cleanup_task == mock_task

    @pytest.mark.filterwarnings("ignore::RuntimeWarning")
    def test_start_cleanup_worker_does_not_duplicate(self):
        """start_cleanup_worker should not create duplicate tasks."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108
        service._cleanup_task = MagicMock()  # Simulate existing task

        # We don't need to call the real method since we already have a task
        # Just verify create_task is not called
        with patch("asyncio.create_task") as mock_create_task:
            service.start_cleanup_worker()

            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_cleanup_worker_cancels_task(self):
        """stop_cleanup_worker should cancel running task."""
        import asyncio

        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        # Create a real asyncio task that we can cancel
        async def dummy_coroutine():
            await asyncio.sleep(100)

        service._cleanup_task = asyncio.create_task(dummy_coroutine())

        await service.stop_cleanup_worker()

        assert service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_stop_cleanup_worker_clears_task_reference(self):
        """stop_cleanup_worker should clear task reference."""
        import asyncio

        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108

        async def dummy_coroutine():
            await asyncio.sleep(100)

        service._cleanup_task = asyncio.create_task(dummy_coroutine())

        await service.stop_cleanup_worker()

        assert service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_stop_cleanup_worker_when_no_task(self):
        """stop_cleanup_worker should handle no existing task."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test")  # noqa: S108
        service._cleanup_task = None

        # Should not raise
        await service.stop_cleanup_worker()

        assert service._cleanup_task is None

    @pytest.mark.asyncio
    async def test_stop_cleanup_worker_releases_lock(self):
        """stop_cleanup_worker should release distributed lock."""
        import asyncio

        from app.locks import DistributedLock
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        mock_lock = MagicMock(spec=DistributedLock)

        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test", lock=mock_lock)  # noqa: S108

        async def dummy_coroutine():
            await asyncio.sleep(100)

        service._cleanup_task = asyncio.create_task(dummy_coroutine())

        await service.stop_cleanup_worker()

        mock_lock.release.assert_called_once_with("cleanup")


@pytest.mark.unit
class TestCleanupServiceWithDistributedLock:
    """Tests for cleanup service with distributed locking."""

    def test_cleanup_uses_lock_when_provided(self):
        """Cleanup should store lock when distributed lock is provided."""
        from app.locks import DistributedLock
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        mock_lock = MagicMock(spec=DistributedLock)

        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test", lock=mock_lock)  # noqa: S108

        assert service._lock is not None
        assert service._lock == mock_lock

    def test_cleanup_works_without_lock(self):
        """Cleanup should work without distributed lock."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()

        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/tmp/test", lock=None)  # noqa: S108

        assert service._lock is None


@pytest.mark.unit
class TestCleanupServicePaths:
    """Tests for cleanup service file path handling."""

    def test_base_folder_path_can_be_empty(self):
        """Empty base folder path should be accepted."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="")

        assert service.paste_base_folder_path == ""

    def test_base_folder_path_absolute(self):
        """Absolute path should be stored correctly."""
        from app.services.cleanup_service import CleanupService

        mock_session_maker = MagicMock()
        service = CleanupService(session_maker=mock_session_maker, paste_base_folder_path="/var/data/pastes")

        assert service.paste_base_folder_path == "/var/data/pastes"
