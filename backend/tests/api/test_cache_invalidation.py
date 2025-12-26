"""Tests for cache invalidation on edit and delete operations."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestCacheInvalidation:
    """Test cache invalidation on mutations."""

    async def test_edit_paste_invalidates_cache(self, test_client: AsyncClient):
        """Editing a paste should invalidate its cache entry."""
        # Create a paste
        create_response = await test_client.post(
            "/pastes",
            json={
                "content": "Original content",
                "language": "python",
                "title": "Test Paste",
            },
        )
        assert create_response.status_code == 200
        paste_data = create_response.json()
        paste_id = paste_data["id"]
        edit_token = paste_data["edit_token"]

        # Get paste to populate cache
        get_response1 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response1.status_code == 200
        assert get_response1.json()["content"] == "Original content"

        # Edit the paste
        edit_response = await test_client.put(
            f"/pastes/{paste_id}",
            json={"content": "Updated content"},
            headers={"Authorization": edit_token},
        )
        assert edit_response.status_code == 200

        # Get paste again - should return updated content (not cached)
        get_response2 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response2.status_code == 200
        assert get_response2.json()["content"] == "Updated content"

    async def test_delete_paste_invalidates_cache(self, test_client: AsyncClient):
        """Deleting a paste should invalidate its cache entry."""
        # Create a paste
        create_response = await test_client.post(
            "/pastes",
            json={
                "content": "Content to delete",
                "language": "text",
                "title": "Delete Test",
            },
        )
        assert create_response.status_code == 200
        paste_data = create_response.json()
        paste_id = paste_data["id"]
        delete_token = paste_data["delete_token"]

        # Get paste to populate cache
        get_response1 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response1.status_code == 200
        assert get_response1.json()["content"] == "Content to delete"

        # Delete the paste
        delete_response = await test_client.delete(
            f"/pastes/{paste_id}",
            headers={"Authorization": delete_token},
        )
        assert delete_response.status_code == 200

        # Get paste again - should return 404 (not cached)
        get_response2 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response2.status_code == 404

    async def test_edit_title_invalidates_cache(self, test_client: AsyncClient):
        """Editing paste title should invalidate cache."""
        # Create a paste
        create_response = await test_client.post(
            "/pastes",
            json={
                "content": "Test content",
                "language": "javascript",
                "title": "Original Title",
            },
        )
        assert create_response.status_code == 200
        paste_data = create_response.json()
        paste_id = paste_data["id"]
        edit_token = paste_data["edit_token"]

        # Get paste to populate cache
        get_response1 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response1.status_code == 200
        assert get_response1.json()["title"] == "Original Title"

        # Edit only the title
        edit_response = await test_client.put(
            f"/pastes/{paste_id}",
            json={"title": "New Title"},
            headers={"Authorization": edit_token},
        )
        assert edit_response.status_code == 200

        # Get paste again - should return updated title
        get_response2 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response2.status_code == 200
        assert get_response2.json()["title"] == "New Title"
        assert get_response2.json()["content"] == "Test content"

    async def test_multiple_edits_invalidate_cache(self, test_client: AsyncClient):
        """Multiple sequential edits should each invalidate cache."""
        # Create a paste
        create_response = await test_client.post(
            "/pastes",
            json={
                "content": "Version 1",
                "language": "text",
                "title": "Multi Edit Test",
            },
        )
        assert create_response.status_code == 200
        paste_data = create_response.json()
        paste_id = paste_data["id"]
        edit_token = paste_data["edit_token"]

        # First edit
        await test_client.put(
            f"/pastes/{paste_id}",
            json={"content": "Version 2"},
            headers={"Authorization": edit_token},
        )

        get_response1 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response1.json()["content"] == "Version 2"

        # Second edit
        await test_client.put(
            f"/pastes/{paste_id}",
            json={"content": "Version 3"},
            headers={"Authorization": edit_token},
        )

        get_response2 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response2.json()["content"] == "Version 3"

        # Third edit
        await test_client.put(
            f"/pastes/{paste_id}",
            json={"content": "Version 4"},
            headers={"Authorization": edit_token},
        )

        get_response3 = await test_client.get(f"/pastes/{paste_id}")
        assert get_response3.json()["content"] == "Version 4"
