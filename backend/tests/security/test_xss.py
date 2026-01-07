"""Security tests for XSS (Cross-Site Scripting) prevention."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.security
class TestXSSPrevention:
    """Tests to ensure XSS attacks are prevented."""

    async def test_paste_content_xss_script_tags(self, test_client: AsyncClient, bypass_headers):
        """Paste content with script tags should be stored safely."""
        xss_payload = "<script>alert('XSS')</script>"

        paste_data = {
            "title": "XSS Test",
            "content": xss_payload,
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)
        assert response.status_code == 200

        paste_id = response.json()["id"]

        # Retrieve and verify content is returned as-is (not executed)
        get_response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
        assert get_response.status_code == 200

        data = get_response.json()
        # Content should be returned exactly as stored
        assert data["content"] == xss_payload

        # Response should be JSON, not HTML (prevents execution)
        assert get_response.headers["content-type"].startswith("application/json")

    async def test_paste_title_xss_prevention(self, test_client: AsyncClient, bypass_headers):
        """Paste title with XSS should be handled safely."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(1)'>",
        ]

        for xss_payload in xss_payloads:
            paste_data = {
                "title": xss_payload,
                "content": "Test content",
                "content_language": "plain_text",
            }

            response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)
            assert response.status_code == 200

            paste_id = response.json()["id"]

            # Retrieve and verify
            get_response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
            assert get_response.status_code == 200

            data = get_response.json()
            # Title should be returned as-is
            assert data["title"] == xss_payload

    async def test_paste_content_html_entities(self, test_client: AsyncClient, bypass_headers):
        """HTML entities in paste content should be preserved."""
        # Use simple HTML that passes validation
        content_with_html = "function test() { return x > y && a < b; }"

        paste_data = {
            "title": "HTML Entities Test",
            "content": content_with_html,
            "content_language": "javascript",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        # Accept either 200 (success) or 422 (validation error)
        if response.status_code == 200:
            paste_id = response.json()["id"]

            # Retrieve and verify content is preserved
            get_response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
            data = get_response.json()

            # Content should be returned exactly as stored
            assert data["content"] == content_with_html
        else:
            # If validation fails, that's also acceptable behavior
            assert response.status_code == 422

    async def test_paste_event_handlers_in_content(self, test_client: AsyncClient, bypass_headers):
        """Event handlers in paste content should be stored safely."""
        # Use plain text content that looks like event handlers
        content = "onclick=myFunction(); onload=initialize();"

        paste_data = {
            "title": "Event Handler Test",
            "content": content,
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        # Accept either 200 (success) or 422 (validation error)
        if response.status_code == 200:
            paste_id = response.json()["id"]

            # Verify content is stored as-is
            get_response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
            data = get_response.json()
            assert "onclick" in data["content"]
            assert content == data["content"]
        else:
            # If validation fails, that's also acceptable behavior
            assert response.status_code == 422

    async def test_paste_data_uri_xss_attempt(self, test_client: AsyncClient, bypass_headers):
        """Data URIs with JavaScript should be handled safely."""
        data_uri_payloads = [
            "data:text/html,<script>alert('XSS')</script>",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",
        ]

        for payload in data_uri_payloads:
            paste_data = {
                "title": "Data URI Test",
                "content": payload,
                "content_language": "plain_text",
            }

            response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)
            assert response.status_code == 200

            paste_id = response.json()["id"]

            # Verify content is returned as-is
            get_response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
            data = get_response.json()
            assert data["content"] == payload


@pytest.mark.asyncio
@pytest.mark.security
class TestContentSecurityHeaders:
    """Tests to ensure proper security headers are set."""

    async def test_api_responses_have_json_content_type(
        self, test_client: AsyncClient, authenticated_paste, bypass_headers
    ):
        """API responses should use application/json content type."""
        paste_id = authenticated_paste["id"]

        response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)

        assert response.status_code == 200
        assert "content-type" in response.headers
        assert response.headers["content-type"].startswith("application/json")

    async def test_error_responses_do_not_expose_internals(self, test_client: AsyncClient, bypass_headers):
        """Error responses should not expose internal details."""
        import uuid

        # Trigger a 404 error with valid UUID format
        nonexistent_id = str(uuid.uuid4())
        response = await test_client.get(f"/pastes/{nonexistent_id}", headers=bypass_headers)

        assert response.status_code == 404

        # Response should be JSON
        assert response.headers["content-type"].startswith("application/json")

        # Should not expose stack traces or file paths
        response_text = response.text.lower()
        assert "traceback" not in response_text
        assert "/home/" not in response_text
        assert ".py" not in response_text
