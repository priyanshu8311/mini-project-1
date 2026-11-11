import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(async_client: AsyncClient) -> None:
    """Verify that the health check endpoint returns 200 and expected payload."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "environment" in data


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient) -> None:
    """Verify that the root /health endpoint returns expected targeted payload."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "smart-inventory-api",
    }


@pytest.mark.asyncio
async def test_docs_and_openapi_endpoints(async_client: AsyncClient) -> None:
    """Verify that OpenAPI schema and Swagger docs are accessible and return 200."""
    openapi_res = await async_client.get("/api/v1/openapi.json")
    assert openapi_res.status_code == 200
    schema = openapi_res.json()
    assert "openapi" in schema
    assert "paths" in schema
    assert "/health" in schema["paths"]
    assert "/api/v1/health" in schema["paths"]

    docs_res = await async_client.get("/api/v1/docs")
    assert docs_res.status_code == 200
    assert "swagger-ui" in docs_res.text.lower()


@pytest.mark.asyncio
async def test_not_found_standard_error(async_client: AsyncClient) -> None:
    """Verify that non-existent routes return the standardized error envelope."""
    response = await async_client.get("/api/v1/unknown-endpoint")
    assert response.status_code == 404
    error_payload = response.json()
    assert "error" in error_payload
    assert error_payload["error"]["code"] == "NOT_FOUND"
    assert "message" in error_payload["error"]
