"""Unit tests for ActivePastesCounter."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
class TestActivePastesCounterInit:
    """Tests for ActivePastesCounter initialization."""

    def test_initialization_stores_session_factory(self):
        """ActivePastesCounter should store session factory."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        assert counter._session_factory == mock_factory

    def test_initialization_refresh_task_is_none(self):
        """ActivePastesCounter should start with no refresh task."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        assert counter._refresh_task is None


@pytest.mark.unit
class TestActivePastesCounterInitialize:
    """Tests for ActivePastesCounter.initialize method."""

    @pytest.mark.asyncio
    async def test_initialize_calls_get_count_from_db(self):
        """initialize should call _get_count_from_db."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)
        counter._get_count_from_db = AsyncMock(return_value=42)

        with patch("app.utils.active_pastes_counter.active_pastes"):
            await counter.initialize()

            counter._get_count_from_db.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_initialize_sets_gauge_value(self):
        """initialize should set the gauge value from DB count."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)
        counter._get_count_from_db = AsyncMock(return_value=42)

        with patch("app.utils.active_pastes_counter.active_pastes") as mock_gauge:
            await counter.initialize()

            mock_gauge.set.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_initialize_with_zero_count(self):
        """initialize should handle zero count."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)
        counter._get_count_from_db = AsyncMock(return_value=0)

        with patch("app.utils.active_pastes_counter.active_pastes") as mock_gauge:
            await counter.initialize()

            mock_gauge.set.assert_called_once_with(0)


@pytest.mark.unit
class TestActivePastesCounterRefreshTask:
    """Tests for refresh task management."""

    def test_start_refresh_task_creates_task(self):
        """start_refresh_task should create an asyncio task."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        with patch("asyncio.create_task") as mock_create_task:
            mock_task = MagicMock()
            mock_create_task.return_value = mock_task

            counter.start_refresh_task()

            mock_create_task.assert_called_once()
            assert counter._refresh_task == mock_task

    def test_start_refresh_task_does_not_duplicate(self):
        """start_refresh_task should not create duplicate tasks."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)
        counter._refresh_task = MagicMock()  # Simulate existing task

        with patch("asyncio.create_task") as mock_create_task:
            counter.start_refresh_task()

            mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_refresh_task_cancels_task(self):
        """stop_refresh_task should cancel the running task."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        # Create a real asyncio task that we can cancel
        async def dummy_coroutine():
            await asyncio.sleep(100)

        counter._refresh_task = asyncio.create_task(dummy_coroutine())

        await counter.stop_refresh_task()

        assert counter._refresh_task is None

    @pytest.mark.asyncio
    async def test_stop_refresh_task_when_no_task(self):
        """stop_refresh_task should handle no existing task."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)
        counter._refresh_task = None

        # Should not raise
        await counter.stop_refresh_task()

        assert counter._refresh_task is None


@pytest.mark.unit
class TestActivePastesCounterIncDec:
    """Tests for increment and decrement operations."""

    def test_inc_increments_gauge(self):
        """inc should increment the active_pastes gauge."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        with patch("app.utils.active_pastes_counter.active_pastes") as mock_gauge:
            counter.inc()

            mock_gauge.inc.assert_called_once_with(1)

    def test_inc_with_custom_amount(self):
        """inc should accept custom increment amount."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        with patch("app.utils.active_pastes_counter.active_pastes") as mock_gauge:
            counter.inc(5)

            mock_gauge.inc.assert_called_once_with(5)

    def test_dec_decrements_gauge(self):
        """dec should decrement the active_pastes gauge."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        with patch("app.utils.active_pastes_counter.active_pastes") as mock_gauge:
            counter.dec()

            mock_gauge.dec.assert_called_once_with(1)

    def test_dec_with_custom_amount(self):
        """dec should accept custom decrement amount."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        counter = ActivePastesCounter(mock_factory)

        with patch("app.utils.active_pastes_counter.active_pastes") as mock_gauge:
            counter.dec(3)

            mock_gauge.dec.assert_called_once_with(3)


@pytest.mark.unit
class TestActivePastesCounterGetCountFromDb:
    """Tests for _get_count_from_db method."""

    @pytest.mark.asyncio
    async def test_get_count_returns_zero_on_error(self):
        """_get_count_from_db should return 0 on error."""
        from app.utils.active_pastes_counter import ActivePastesCounter

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB Error"))
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        counter = ActivePastesCounter(mock_factory)

        result = await counter._get_count_from_db()

        assert result == 0


@pytest.mark.unit
class TestGlobalCounterFunctions:
    """Tests for global getter/setter functions."""

    def test_get_active_pastes_counter_returns_none_initially(self):
        """get_active_pastes_counter should return None if not set."""
        import app.utils.active_pastes_counter as module
        from app.utils.active_pastes_counter import get_active_pastes_counter

        # Store original value
        original = module._counter

        try:
            module._counter = None
            result = get_active_pastes_counter()
            assert result is None
        finally:
            # Restore original value
            module._counter = original

    def test_set_active_pastes_counter_sets_global(self):
        """set_active_pastes_counter should set the global instance."""
        import app.utils.active_pastes_counter as module
        from app.utils.active_pastes_counter import (
            ActivePastesCounter,
            get_active_pastes_counter,
            set_active_pastes_counter,
        )

        # Store original value
        original = module._counter

        try:
            mock_factory = MagicMock()
            counter = ActivePastesCounter(mock_factory)

            set_active_pastes_counter(counter)

            result = get_active_pastes_counter()
            assert result is counter
        finally:
            # Restore original value
            module._counter = original


@pytest.mark.unit
class TestRefreshIntervalConstant:
    """Tests for REFRESH_INTERVAL_SECONDS constant."""

    def test_refresh_interval_is_defined(self):
        """REFRESH_INTERVAL_SECONDS should be defined."""
        from app.utils.active_pastes_counter import REFRESH_INTERVAL_SECONDS

        assert REFRESH_INTERVAL_SECONDS is not None
        assert isinstance(REFRESH_INTERVAL_SECONDS, int)

    def test_refresh_interval_is_reasonable(self):
        """REFRESH_INTERVAL_SECONDS should be a reasonable value."""
        from app.utils.active_pastes_counter import REFRESH_INTERVAL_SECONDS

        # Should be at least 10 seconds, at most 24 hours
        assert REFRESH_INTERVAL_SECONDS >= 10
        assert REFRESH_INTERVAL_SECONDS <= 86400
