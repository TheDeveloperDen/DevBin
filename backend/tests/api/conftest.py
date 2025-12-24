"""Fixtures for API endpoint tests."""
import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest.fixture
def bypass_headers():
    """Headers with bypass token to skip rate limiting."""
    return {"Authorization": "test_bypass_token_12345"}


@pytest_asyncio.fixture
async def authenticated_paste(test_client: AsyncClient, sample_paste_data, bypass_headers):
    """Create a paste and return it with auth tokens."""
    response = await test_client.post("/pastes", json=sample_paste_data, headers=bypass_headers)
    assert response.status_code == 200
    return response.json()
