"""Fixtures for API endpoint tests."""
import uuid

import pytest


@pytest.fixture
def nonexistent_paste_id():
    """Returns a UUID that doesn't exist in the database."""
    return str(uuid.uuid4())
