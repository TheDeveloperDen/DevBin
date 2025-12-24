"""Security tests for SQL injection and code injection prevention."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.security
class TestSQLInjectionPrevention:
    """Tests to ensure SQL injection attacks are prevented."""

    async def test_paste_id_sql_injection_attempt(
            self, test_client: AsyncClient, bypass_headers
    ):
        """GET /pastes/{id} should safely handle SQL injection attempts in ID."""
        # Various SQL injection payloads
        sql_injection_payloads = [
            "' OR '1'='1",
            "1' OR '1' = '1",
            "' OR 1=1--",
            "admin'--",
            "' UNION SELECT NULL--",
            "1'; DROP TABLE pastes--",
        ]

        for payload in sql_injection_payloads:
            response = await test_client.get(f"/pastes/{payload}", headers=bypass_headers)

            # Should return 404 or 422, not expose database errors
            assert response.status_code in [404, 422]
            data = response.json()

            # Should not contain SQL error messages
            response_str = str(data).lower()
            assert "sql" not in response_str
            assert "syntax error" not in response_str
            assert "database" not in response_str

    async def test_paste_content_sql_injection_attempt(
            self, test_client: AsyncClient, bypass_headers
    ):
        """POST /pastes should safely handle SQL injection in content fields."""
        sql_payload = "'; DROP TABLE pastes; --"

        paste_data = {
            "title": sql_payload,
            "content": sql_payload,
            "content_language": "plain_text",
        }

        response = await test_client.post("/pastes", json=paste_data, headers=bypass_headers)

        # Should succeed (SQLAlchemy should parameterize queries)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data

        # Verify the paste was created with the payload as content (not executed)
        paste_id = data["id"]
        get_response = await test_client.get(f"/pastes/{paste_id}", headers=bypass_headers)
        assert get_response.status_code == 200
        retrieved_data = get_response.json()
        assert retrieved_data["title"] == sql_payload
        assert retrieved_data["content"] == sql_payload

    async def test_legacy_paste_name_injection_attempt(
            self, test_client: AsyncClient, bypass_headers
    ):
        """GET /pastes/legacy/{name} should prevent injection via paste name."""
        # Path traversal + SQL injection
        malicious_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "'; DROP TABLE pastes--",
            "test' OR '1'='1",
        ]

        for name in malicious_names:
            response = await test_client.get(f"/pastes/legacy/{name}", headers=bypass_headers)

            # Should return 404 or 422, not expose errors
            assert response.status_code in [404, 422]


@pytest.mark.asyncio
@pytest.mark.security
class TestPathTraversalPrevention:
    """Tests to ensure path traversal attacks are prevented."""

    async def test_paste_id_path_traversal_attempt(
            self, test_client: AsyncClient, bypass_headers
    ):
        """Paste ID should not allow path traversal."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for payload in path_traversal_payloads:
            response = await test_client.get(f"/pastes/{payload}", headers=bypass_headers)

            # Should return 404 or 422
            assert response.status_code in [404, 422]
