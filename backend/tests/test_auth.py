from datetime import timedelta
from uuid import uuid4

import pytest
from backend.src.core.errors import ConflictException
from backend.src.core.security import (
    create_access_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
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


def test_password_strength_validation() -> None:
    """Verify password complexity rules."""
    # Too short
    with pytest.raises(ValueError, match="at least 8 characters"):
        validate_password_strength("Short1!")

    # Missing uppercase
    with pytest.raises(ValueError, match="uppercase"):
        validate_password_strength("lowercase123!")

    # Missing lowercase
    with pytest.raises(ValueError, match="lowercase"):
        validate_password_strength("UPPERCASE123!")

    # Missing digit/special
    with pytest.raises(ValueError, match="digit or special"):
        validate_password_strength("NoDigitsOrSpecial")

    # Valid passwords
    validate_password_strength("ValidPassword123!")
    validate_password_strength("Strong_Pass99")


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
async def test_register_organization_success(async_client: AsyncClient) -> None:
    """Verify POST /auth/register creates tenant + admin user and returns token."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Apex Distribution",
            "email": "owner@apex.com",
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "owner@apex.com"
    assert data["user"]["role"] == UserRole.ADMIN.value
    assert data["user"]["is_active"] is True


@pytest.mark.asyncio
async def test_register_organization_duplicate_email(
    async_client: AsyncClient, test_admin_user: User
) -> None:
    """Verify registering with already-existing email returns 409 Conflict."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Duplicate Corp",
            "email": test_admin_user.email,
            "password": "StrongPassword123!",
        },
    )
    assert response.status_code == 409
    error_data = response.json()
    assert error_data["error"]["code"] == "CONFLICT"
    assert "already exists" in error_data["error"]["message"]


@pytest.mark.asyncio
async def test_register_organization_weak_password(async_client: AsyncClient) -> None:
    """Verify registering with weak password fails schema validation (422)."""
    response = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Weak Pass Corp",
            "email": "weak@apex.com",
            "password": "simple",
        },
    )
    assert response.status_code == 422
    error_data = response.json()
    assert error_data["error"]["code"] == "VALIDATION_ERROR"


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
async def test_login_inactive_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_tenant: Tenant,
) -> None:
    """Verify login of deactivated account returns 401."""
    inactive_user = await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="inactive@acme.com",
        password="Password123!",
    )
    inactive_user.is_active = False
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@acme.com", "password": "Password123!"},
    )
    assert response.status_code == 401
    error_data = response.json()
    assert error_data["error"]["code"] == "UNAUTHORIZED"
    assert "inactive" in error_data["error"]["message"].lower()


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
async def test_logout_endpoint(async_client: AsyncClient, admin_token: str) -> None:
    """Verify POST /auth/logout acknowledges session disposal."""
    # Authenticated logout
    response = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully."

    # Unauthenticated logout must fail with 401
    unauth_resp = await async_client.post("/api/v1/auth/logout")
    assert unauth_resp.status_code == 401


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
async def test_token_expiry_handling(async_client: AsyncClient, test_admin_user: User) -> None:
    """Verify that expired JWT token returns 401 Unauthorized with descriptive message."""
    expired_token = create_access_token(
        {
            "sub": str(test_admin_user.id),
            "tenant_id": str(test_admin_user.tenant_id),
            "role": test_admin_user.role,
            "email": test_admin_user.email,
        },
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )

    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    error_data = response.json()
    assert error_data["error"]["code"] == "UNAUTHORIZED"
    assert "expired" in error_data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_token_malformed(async_client: AsyncClient) -> None:
    """Verify that a malformed JWT token returns 401 Unauthorized."""
    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert response.status_code == 401
    error_data = response.json()
    assert error_data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_token_user_deactivated_after_issuance(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_viewer_user: User,
    viewer_token: str,
) -> None:
    """Verify that if a user is deactivated after token issuance, requests are rejected with 401."""
    test_viewer_user.is_active = False
    await db_session.commit()

    response = await async_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 401
    error_data = response.json()
    assert error_data["error"]["code"] == "UNAUTHORIZED"
    assert "inactive" in error_data["error"]["message"].lower()


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


@pytest.mark.asyncio
async def test_admin_user_management(
    async_client: AsyncClient,
    admin_token: str,
    viewer_token: str,
) -> None:
    """Verify Admin user CRUD and RBAC protection."""
    # 1. Viewer cannot list users
    viewer_list = await async_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert viewer_list.status_code == 403

    # 2. Admin can list users
    admin_list = await async_client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] >= 1

    # 3. Admin can create new user
    create_resp = await async_client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "staff@acme.com",
            "password": "SecurePassword123!",
            "role": UserRole.WAREHOUSE_STAFF.value,
        },
    )
    assert create_resp.status_code == 201
    created_user_id = create_resp.json()["id"]
    assert create_resp.json()["role"] == UserRole.WAREHOUSE_STAFF.value

    # 4. Admin can get specific user details
    get_user_resp = await async_client.get(
        f"/api/v1/users/{created_user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_user_resp.status_code == 200
    assert get_user_resp.json()["email"] == "staff@acme.com"

    # 5. Admin can deactivate user
    deactivate_resp = await async_client.patch(
        f"/api/v1/users/{created_user_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(
    async_client: AsyncClient,
    test_admin_user: User,
    admin_token: str,
) -> None:
    """Verify Admin cannot deactivate their own administrative account."""
    response = await async_client.patch(
        f"/api/v1/users/{test_admin_user.id}/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"is_active": False},
    )
    assert response.status_code == 400
    error_data = response.json()
    assert error_data["error"]["code"] == "VALIDATION_ERROR"
    assert "cannot deactivate their own account" in error_data["error"]["message"]


@pytest.mark.asyncio
async def test_cross_tenant_isolation(
    async_client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    """Verify Admin from Tenant A cannot view or manipulate user from Tenant B."""
    tenant_b = await UserService.create_tenant(db_session, name="Tenant Bravo")
    user_b = await UserService.create_user(
        db_session,
        tenant_id=tenant_b.id,
        email="bravo@other.com",
        password="Password123!",
        role=UserRole.ADMIN,
    )
    await db_session.commit()

    # Admin A attempts to fetch user_b -> must return 404 Not Found
    response = await async_client.get(
        f"/api/v1/users/{user_b.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
    error_data = response.json()
    assert error_data["error"]["code"] == "NOT_FOUND"

    # Non-existent user UUID also returns 404
    random_uuid = uuid4()
    not_found_resp = await async_client.get(
        f"/api/v1/users/{random_uuid}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert not_found_resp.status_code == 404

