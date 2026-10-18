import pytest
from backend.src.core.errors import ConflictException
from backend.src.core.security import hash_password, verify_password
from backend.src.domain.users.models import Tenant, User, UserRole
from backend.src.domain.users.service import UserService
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def test_password_hashing() -> None:
    """Verify that bcrypt generates different salts and verifies correctly."""
    plain = "SuperSecurePass123!"
    hash1 = hash_password(plain)
    hash2 = hash_password(plain)

    assert hash1 != hash2  # Salt is unique
    assert verify_password(plain, hash1) is True
    assert verify_password(plain, hash2) is True
    assert verify_password("WrongPass", hash1) is False


@pytest.mark.asyncio
async def test_tenant_user_uniqueness(db_session: AsyncSession, test_tenant: Tenant) -> None:
    """Verify unique constraint on (tenant_id, email)."""
    tenant2 = await UserService.create_tenant(db_session, name="Second Corp")
    await db_session.commit()

    # User in tenant 1
    await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="shared@domain.com",
        password="Password123!",
    )
    await db_session.commit()

    # Same email in tenant 2 must succeed (tenant isolation)
    user2 = await UserService.create_user(
        db_session,
        tenant_id=tenant2.id,
        email="shared@domain.com",
        password="Password123!",
    )
    await db_session.commit()
    assert user2.tenant_id == tenant2.id

    # Duplicate email in tenant 1 must fail with conflict
    with pytest.raises(ConflictException):
        await UserService.create_user(
            db_session,
            tenant_id=test_tenant.id,
            email="shared@domain.com",
            password="Password123!",
        )


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, test_admin_user: User) -> None:
    """Verify login returns 200, JWT token, and user profile."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": test_admin_user.email, "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_admin_user.email
    assert data["user"]["role"] == UserRole.ADMIN.value


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, test_admin_user: User) -> None:
    """Verify login with incorrect password returns 401 with standard error format."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": test_admin_user.email, "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert "Invalid email or password" in data["error"]["message"]


@pytest.mark.asyncio
async def test_login_rate_limiting(async_client: AsyncClient, test_admin_user: User) -> None:
    """Verify that 6th rapid login attempt triggers 429 Too Many Requests."""
    for _ in range(5):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": test_admin_user.email, "password": "WrongPassword!"},
        )
        assert resp.status_code == 401

    # 6th attempt must be rate-limited
    sixth_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": test_admin_user.email, "password": "WrongPassword!"},
    )
    assert sixth_resp.status_code == 429
    assert "Retry-After" in sixth_resp.headers
    error_data = sixth_resp.json()
    assert error_data["error"]["code"] == "RATE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_get_me_authenticated(
    async_client: AsyncClient,
    test_admin_user: User,
    admin_token: str,
) -> None:
    """Verify GET /users/me returns authenticated user's details."""
    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_admin_user.id)
    assert data["email"] == test_admin_user.email
    assert data["role"] == UserRole.ADMIN.value


@pytest.mark.asyncio
async def test_get_me_unauthenticated(async_client: AsyncClient) -> None:
    """Verify GET /users/me without token returns 401."""
    response = await async_client.get("/api/v1/users/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_rbac_admin_endpoint(
    async_client: AsyncClient,
    admin_token: str,
    viewer_token: str,
) -> None:
    """Verify RBAC: Admin succeeds (200), Viewer is rejected (403)."""
    # 1. Admin access
    admin_resp = await async_client.get(
        "/api/v1/users/admin-test",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_resp.status_code == 200
    assert "Admin authorization granted" in admin_resp.json()["message"]

    # 2. Viewer access (must be 403 Forbidden)
    viewer_resp = await async_client.get(
        "/api/v1/users/admin-test",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert viewer_resp.status_code == 403
    error_data = viewer_resp.json()
    assert error_data["error"]["code"] == "FORBIDDEN"
    assert "not authorized" in error_data["error"]["message"]
