import pytest
from backend.src.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_cors_preflight_new_vercel_domain():
    """Verify CORS preflight succeeds for the new Vercel domain."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://inventorymanage-orpin.vercel.app",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization, content-type",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "https://inventorymanage-orpin.vercel.app"
        )
        assert response.headers.get("access-control-allow-credentials") == "true"
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "POST" in allow_methods or "*" in allow_methods


@pytest.mark.asyncio
async def test_cors_preflight_localhost():
    """Verify CORS preflight succeeds for local development origins."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert response.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.asyncio
async def test_cors_preflight_disallowed_origin():
    """Verify disallowed origins do not get CORS headers or are rejected."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://evil-unauthorized-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
        # Disallowed origins either return 400 or don't return allow-origin header
        assert response.headers.get("access-control-allow-origin") is None
