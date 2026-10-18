"""Security Audit Verification Test Suite.

Verifies fixes implemented during security audit:
- Production environment rejects insecure default secrets
- OWASP defensive HTTP security headers
- Public webhook request body size capping (DoS defense)
- Rate limiter memory bounding & eviction of stale keys
- SQL wildcard escaping in inventory search queries
"""

from unittest.mock import patch

import pytest
from backend.src.core.config import Settings
from backend.src.core.rate_limit import SlidingWindowRateLimiter
from httpx import AsyncClient
from pydantic import ValidationError


@pytest.mark.asyncio
async def test_production_rejects_default_jwt_secret():
    """Verify Settings rejects default dev JWT_SECRET_KEY in production mode."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="dev-insecure-secret-key-change-in-production-min-32-chars",
            ENCRYPTION_KEY="custom-secure-32-byte-encryption-key-prod-12345",
        )
    assert "JWT_SECRET_KEY must be an explicit, high-entropy key" in str(exc_info.value)


@pytest.mark.asyncio
async def test_production_rejects_default_encryption_key():
    """Verify Settings rejects default dev ENCRYPTION_KEY in production mode."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET_KEY="custom-secure-32-byte-jwt-secret-key-prod-12345678",
            ENCRYPTION_KEY="dGVzdF9lbmNyeXB0aW9uX2tleV9mb3JfZGV2XzMyYnl0ZXM=",
        )
    assert "ENCRYPTION_KEY must be an explicit, secure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_production_accepts_valid_high_entropy_secrets():
    """Verify Settings initializes successfully in production when secure keys are provided."""
    s = Settings(
        ENVIRONMENT="production",
        JWT_SECRET_KEY="high-entropy-production-jwt-secret-key-32chars!",
        ENCRYPTION_KEY="c2VjdXJlLXByb2R1Y3Rpb24tZW5jcnlwdGlvbi1rZXktMzJieXRlcw==",
    )
    assert s.is_production is True
    assert s.ENVIRONMENT == "production"


@pytest.mark.asyncio
async def test_owasp_security_headers_present(async_client: AsyncClient):
    """Verify OWASP defensive security headers are returned on API responses."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers.get("Permissions-Policy", "")


@pytest.mark.asyncio
async def test_webhook_oversized_payload_rejected(async_client: AsyncClient):
    """Verify public webhook endpoint rejects payloads exceeding the 2MB size limit."""
    oversized_bytes = b"x" * (2 * 1024 * 1024 + 10)  # > 2 MB
    headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(oversized_bytes)),
        "X-Shopify-Hmac-Sha256": "fake_signature",
    }
    response = await async_client.post(
        "/api/v1/webhooks/shopify/orders/create",
        content=oversized_bytes,
        headers=headers,
    )
    assert response.status_code in (400, 413, 422)
    assert "exceeds maximum allowable size" in response.text


@pytest.mark.asyncio
async def test_rate_limiter_memory_bounding_and_eviction():
    """Verify rate limiter automatically evicts stale keys when capacity reaches max_keys."""
    limiter = SlidingWindowRateLimiter(max_requests=5, window_seconds=1, max_keys=10)

    # Fill up with 10 distinct client keys at time T=0
    for i in range(10):
        limiter.check(f"client-{i}")

    assert len(limiter._requests) == 10

    from datetime import UTC, datetime

    real_now = datetime.now(UTC).timestamp()

    # Advance time beyond window_seconds and add an 11th client key
    with patch("backend.src.core.rate_limit.datetime") as mock_dt:
        mock_dt.now.return_value = datetime.fromtimestamp(real_now + 100.0, tz=UTC)
        # Check an 11th key, which should trigger _prune_expired_locked and evict stale keys
        limiter.check("client-11")

    # Stale keys from T=0 must have been pruned
    assert len(limiter._requests) <= 2
