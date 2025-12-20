"""Fixtures for API endpoint tests."""
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def authenticated_paste(test_client: AsyncClient, sample_paste_data):
    """Create a paste and return it with auth tokens."""
    response = await test_client.post("/pastes", json=sample_paste_data)
    assert response.status_code == 200
    return response.json()
