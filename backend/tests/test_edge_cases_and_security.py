from datetime import timedelta
from uuid import uuid4

import pytest
from backend.src.core.rate_limit import login_rate_limiter
from backend.src.core.security import create_access_token
from backend.src.domain.inventory.models import (
    SKU,
    Category,
    InventoryLevel,
    Location,
    LocationType,
    Product,
)
from backend.src.domain.users.models import Tenant, User, UserRole
from backend.src.domain.users.service import UserService
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ==============================================================================
# 1. Inventory Negative Scenarios & Constraint Boundary Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_ship_insufficient_stock_fails(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Attempting to ship more stock than is on-hand must fail with 422 ValidationException."""
    loc = Location(tenant_id=test_tenant.id, name="Test Loc", type=LocationType.WAREHOUSE)
    cat = Category(tenant_id=test_tenant.id, name="Test Cat")
    prod = Product(tenant_id=test_tenant.id, category=cat, name="Test Product")
    sku = SKU(tenant_id=test_tenant.id, product=prod, sku_code="SKU-BOUND-01")
    db_session.add_all([loc, cat, prod, sku])
    await db_session.flush()

    level = InventoryLevel(
        tenant_id=test_tenant.id,
        sku_id=sku.id,
        location_id=loc.id,
        on_hand=5,
        reserved=0,
        version=1,
    )
    db_session.add(level)
    await db_session.commit()

    # Attempt to ship 10 units when only 5 exist
    resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Ship",
            "sku_id": str(sku.id),
            "location_id": str(loc.id),
            "quantity_change": 10,
            "reason": "Exceeding on-hand stock test",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 400 or resp.status_code == 422
    err_body = resp.json()["error"]
    assert err_body["code"] == "VALIDATION_ERROR"
    assert "Insufficient on-hand stock" in err_body["message"]

    # Verify database level remained untouched at 5
    lvl_res = await db_session.execute(
        select(InventoryLevel)
        .where(InventoryLevel.sku_id == sku.id, InventoryLevel.location_id == loc.id)
        .execution_options(populate_existing=True)
    )
    assert lvl_res.scalar_one().on_hand == 5


@pytest.mark.asyncio
async def test_zero_quantity_transaction_rejected(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Transactions with quantity_change == 0 must be rejected to prevent ledger bloat."""
    loc = Location(tenant_id=test_tenant.id, name="Loc 1", type=LocationType.STORE)
    cat = Category(tenant_id=test_tenant.id, name="Cat 1")
    prod = Product(tenant_id=test_tenant.id, category=cat, name="Prod 1")
    sku = SKU(tenant_id=test_tenant.id, product=prod, sku_code="SKU-ZERO-01")
    db_session.add_all([loc, cat, prod, sku])
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Receive",
            "sku_id": str(sku.id),
            "location_id": str(loc.id),
            "quantity_change": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code in (400, 422)
    assert "Quantity change cannot be zero" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_transfer_same_location_rejected(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Inter-location transfers with identical source and target location must be rejected."""
    loc = Location(tenant_id=test_tenant.id, name="Sole Location", type=LocationType.WAREHOUSE)
    cat = Category(tenant_id=test_tenant.id, name="Cat 2")
    prod = Product(tenant_id=test_tenant.id, category=cat, name="Prod 2")
    sku = SKU(tenant_id=test_tenant.id, product=prod, sku_code="SKU-SAME-LOC")
    db_session.add_all([loc, cat, prod, sku])
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Transfer",
            "sku_id": str(sku.id),
            "location_id": str(loc.id),
            "target_location_id": str(loc.id),
            "quantity_change": 10,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code in (400, 422)
    assert "Source and destination locations must be distinct" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_transfer_missing_target_location_rejected(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Transfer transaction without target_location_id must fail."""
    loc = Location(tenant_id=test_tenant.id, name="Loc Alpha", type=LocationType.WAREHOUSE)
    cat = Category(tenant_id=test_tenant.id, name="Cat Alpha")
    prod = Product(tenant_id=test_tenant.id, category=cat, name="Prod Alpha")
    sku = SKU(tenant_id=test_tenant.id, product=prod, sku_code="SKU-NO-TARGET")
    db_session.add_all([loc, cat, prod, sku])
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Transfer",
            "sku_id": str(sku.id),
            "location_id": str(loc.id),
            "quantity_change": 5,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code in (400, 422)
    assert "target_location_id is required" in resp.json()["error"]["message"]


# ==============================================================================
# 2. Multi-Tenant Cross-Access Prevention (IDOR Checks)
# ==============================================================================
@pytest.mark.asyncio
async def test_cross_tenant_location_access_blocked(
    async_client: AsyncClient,
    test_tenant: Tenant,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    """Tenant A cannot execute transactions referencing Tenant B's location."""
    # Create Tenant B and Tenant B's Location
    tenant_b = Tenant(name="Tenant B")
    db_session.add(tenant_b)
    await db_session.flush()

    loc_b = Location(tenant_id=tenant_b.id, name="Foreign Warehouse", type=LocationType.WAREHOUSE)
    # Create Tenant A's SKU
    cat_a = Category(tenant_id=test_tenant.id, name="Cat A")
    prod_a = Product(tenant_id=test_tenant.id, category=cat_a, name="Prod A")
    sku_a = SKU(tenant_id=test_tenant.id, product=prod_a, sku_code="SKU-TENANT-A")
    db_session.add_all([loc_b, cat_a, prod_a, sku_a])
    await db_session.commit()

    # Tenant A attempts to receive stock at Tenant B's location
    resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Receive",
            "sku_id": str(sku_a.id),
            "location_id": str(loc_b.id),
            "quantity_change": 20,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


# ==============================================================================
# 3. Role-Based Access Control (RBAC) Comprehensive Matrix
# ==============================================================================
@pytest.mark.asyncio
async def test_rbac_authorization_matrix(
    async_client: AsyncClient,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Verify that every endpoint strictly enforces PRD role permissions."""
    # Create Viewer user
    viewer_user = await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="auditor@tenant.com",
        password="AuditorPass2026!",
        role=UserRole.VIEWER,
    )
    # Create Warehouse Staff user
    staff_user = await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="staff@tenant.com",
        password="StaffPass2026!",
        role=UserRole.WAREHOUSE_STAFF,
    )
    await db_session.commit()

    viewer_tok = create_access_token(
        {
            "sub": str(viewer_user.id),
            "tenant_id": str(test_tenant.id),
            "role": UserRole.VIEWER.value,
        }
    )
    staff_tok = create_access_token(
        {
            "sub": str(staff_user.id),
            "tenant_id": str(test_tenant.id),
            "role": UserRole.WAREHOUSE_STAFF.value,
        }
    )

    viewer_hdr = {"Authorization": f"Bearer {viewer_tok}"}
    staff_hdr = {"Authorization": f"Bearer {staff_tok}"}

    # 1. Viewer cannot create transactions -> 403
    tx_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Receive",
            "sku_id": str(uuid4()),
            "location_id": str(uuid4()),
            "quantity_change": 1,
        },
        headers=viewer_hdr,
    )
    assert tx_resp.status_code == 403

    # 2. Viewer cannot configure integrations -> 403
    int_resp = await async_client.post(
        "/api/v1/integrations/shopify/config",
        json={"shop_domain": "store.myshopify.com", "access_token": "shpat_1234567890"},
        headers=viewer_hdr,
    )
    assert int_resp.status_code == 403

    # 3. Warehouse Staff cannot invite/manage users -> 403
    usr_resp = await async_client.post(
        "/api/v1/users",
        json={"email": "newbie@tenant.com", "password": "Password123!", "role": "Viewer"},
        headers=staff_hdr,
    )
    assert usr_resp.status_code == 403

    # 4. Warehouse Staff cannot modify Shopify configuration -> 403
    staff_int = await async_client.post(
        "/api/v1/integrations/shopify/config",
        json={"shop_domain": "store.myshopify.com", "access_token": "shpat_1234567890"},
        headers=staff_hdr,
    )
    assert staff_int.status_code == 403


# ==============================================================================
# 4. Authentication Security, Deactivation, & Token Tampering
# ==============================================================================
@pytest.mark.asyncio
async def test_deactivated_user_token_rejected(
    async_client: AsyncClient,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Tokens for deactivated users must be immediately rejected with 401 Unauthorized."""
    admin = await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="admin.boss@tenant.com",
        password="Password123!",
        role=UserRole.ADMIN,
    )
    user = await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="fired.employee@tenant.com",
        password="Password123!",
        role=UserRole.WAREHOUSE_STAFF,
    )
    await db_session.commit()

    token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(test_tenant.id), "role": user.role}
    )

    # Deactivate user
    await UserService.update_user_status(
        db_session,
        user.id,
        test_tenant.id,
        is_active=False,
        actor_user_id=admin.id,
    )
    await db_session.commit()

    # Request with former employee's token
    resp = await async_client.get(
        "/api/v1/inventory/levels",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401
    assert "User account is inactive" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_expired_jwt_rejected(async_client: AsyncClient, test_admin_user: User) -> None:
    """Expired JWT access token returns HTTP 401."""
    expired_token = create_access_token(
        {
            "sub": str(test_admin_user.id),
            "tenant_id": str(test_admin_user.tenant_id),
            "role": test_admin_user.role,
        },
        expires_delta=timedelta(minutes=-10),  # expired 10 minutes ago
    )

    resp = await async_client.get(
        "/api/v1/inventory/levels",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp.status_code == 401
    assert "token has expired" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_tampered_jwt_signature_rejected(
    async_client: AsyncClient,
    admin_token: str,
) -> None:
    """Tampered token signature returns HTTP 401."""
    parts = admin_token.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.tampered_signature"

    resp = await async_client.get(
        "/api/v1/inventory/levels",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp.status_code == 401
    assert "Invalid authentication token" in resp.json()["error"]["message"]


# ==============================================================================
# 5. Rate Limiting Protection (Brute Force Login Mitigation)
# ==============================================================================
@pytest.mark.asyncio
async def test_login_brute_force_rate_limit(async_client: AsyncClient) -> None:
    """Exceeding 5 login attempts per minute from the same IP must trigger 429 Too Many Requests."""
    login_rate_limiter.reset()

    # 5 failed login attempts
    for _ in range(5):
        resp = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "hacker@test.com", "password": "WrongPassword1!"},
        )
        assert resp.status_code == 401

    # 6th attempt should be blocked by rate limiter
    blocked_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "hacker@test.com", "password": "WrongPassword1!"},
    )
    assert blocked_resp.status_code == 429
    assert blocked_resp.headers.get("Retry-After") is not None
    assert blocked_resp.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
