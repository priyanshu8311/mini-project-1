from decimal import Decimal

import pytest
from backend.src.core.security import create_access_token
from backend.src.domain.inventory.models import LocationType, TransactionType
from backend.src.domain.inventory.schemas import (
    CategoryCreate,
    InventoryTransactionCreate,
    LocationCreate,
    SKUCreate,
)
from backend.src.domain.inventory.service import CatalogService, InventoryService
from backend.src.domain.users.models import Tenant, User, UserRole
from backend.src.domain.users.service import UserService
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def catalog_setup(db_session: AsyncSession, test_tenant: Tenant):
    """Setup a test category, warehouse, store, and SKU."""
    cat = await CatalogService.create_category(
        db_session, test_tenant.id, CategoryCreate(name="Industrial Components")
    )
    wh = await CatalogService.create_location(
        db_session,
        test_tenant.id,
        LocationCreate(name="Central Depot", type=LocationType.WAREHOUSE),
    )
    store = await CatalogService.create_location(
        db_session,
        test_tenant.id,
        LocationCreate(name="Northside Branch", type=LocationType.STORE),
    )
    sku = await CatalogService.create_sku(
        db_session,
        test_tenant.id,
        SKUCreate(
            sku_code="IND-BEAR-001",
            product_name="Precision Ball Bearing",
            category_id=cat.id,
            unit_cost=Decimal("12.50"),
            sales_price=Decimal("24.00"),
            lead_time_days=4,
        ),
    )
    await db_session.commit()
    return {"category": cat, "warehouse": wh, "store": store, "sku": sku}


@pytest.mark.asyncio
async def test_record_receive_transaction(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
):
    """Verify receiving stock writes to ledger and updates inventory_levels atomically."""
    wh = catalog_setup["warehouse"]
    sku = catalog_setup["sku"]

    payload = {
        "transaction_type": "Receive",
        "sku_id": str(sku.id),
        "location_id": str(wh.id),
        "quantity_change": 50,
        "reference_id": "PO-1001",
        "reason": "Shipment from supplier received at dock",
    }
    response = await async_client.post(
        "/api/v1/inventory/transactions",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["transaction_type"] == "Receive"
    assert data["quantity_change"] == 50
    assert data["reference_id"] == "PO-1001"

    # Verify inventory levels snapshot
    levels_res = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku.id}&location_id={wh.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert levels_res.status_code == 200
    levels_data = levels_res.json()["data"]
    assert len(levels_data) == 1
    assert levels_data[0]["on_hand"] == 50
    assert levels_data[0]["reserved"] == 0
    assert levels_data[0]["available"] == 50
    assert levels_data[0]["version"] == 2


@pytest.mark.asyncio
async def test_record_ship_transaction(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_admin_user: User,
):
    """Verify shipping stock decrements on_hand and records a negative ledger entry."""
    wh = catalog_setup["warehouse"]
    sku = catalog_setup["sku"]

    # Initial stock: 100 units
    await InventoryService.record_transaction(
        db_session,
        test_tenant.id,
        test_admin_user.id,
        InventoryTransactionCreate(
            transaction_type=TransactionType.RECEIVE,
            sku_id=sku.id,
            location_id=wh.id,
            quantity_change=100,
        ),
    )
    await db_session.commit()

    # Ship 35 units
    ship_payload = {
        "transaction_type": "Ship",
        "sku_id": str(sku.id),
        "location_id": str(wh.id),
        "quantity_change": 35,
        "reference_id": "SO-5002",
        "reason": "Customer order fulfillment",
    }
    response = await async_client.post(
        "/api/v1/inventory/transactions",
        json=ship_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["quantity_change"] == -35

    # Check updated level
    levels_res = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku.id}&location_id={wh.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    level = levels_res.json()["data"][0]
    assert level["on_hand"] == 65
    assert level["available"] == 65


@pytest.mark.asyncio
async def test_record_ship_insufficient_stock(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_admin_user: User,
):
    """Verify attempting to ship more than on-hand stock fails with 400 Bad Request."""
    wh = catalog_setup["warehouse"]
    sku = catalog_setup["sku"]

    # Only 10 units on hand
    await InventoryService.record_transaction(
        db_session,
        test_tenant.id,
        test_admin_user.id,
        InventoryTransactionCreate(
            transaction_type=TransactionType.RECEIVE,
            sku_id=sku.id,
            location_id=wh.id,
            quantity_change=10,
        ),
    )
    await db_session.commit()

    # Try to ship 50 units
    ship_payload = {
        "transaction_type": "Ship",
        "sku_id": str(sku.id),
        "location_id": str(wh.id),
        "quantity_change": 50,
        "reason": "Oversized shipment",
    }
    response = await async_client.post(
        "/api/v1/inventory/transactions",
        json=ship_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400
    err = response.json()["error"]
    assert "Insufficient on-hand stock" in err["message"]

    # Verify stock was not changed
    levels_res = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku.id}&location_id={wh.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert levels_res.json()["data"][0]["on_hand"] == 10


@pytest.mark.asyncio
async def test_record_adjust_transaction(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_admin_user: User,
):
    """Verify stock adjustments handle positive, negative, and prevent negative totals."""
    wh = catalog_setup["warehouse"]
    sku = catalog_setup["sku"]

    # 1. Starting baseline: 20 units
    await InventoryService.record_transaction(
        db_session,
        test_tenant.id,
        test_admin_user.id,
        InventoryTransactionCreate(
            transaction_type=TransactionType.RECEIVE,
            sku_id=sku.id,
            location_id=wh.id,
            quantity_change=20,
        ),
    )
    await db_session.commit()

    # 2. Positive adjustment +15
    res1 = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Adjust",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "quantity_change": 15,
            "reason": "Found uncounted crate during cycle count",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res1.status_code == 201

    # 3. Negative adjustment -5
    res2 = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Adjust",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "quantity_change": -5,
            "reason": "Damaged goods write-off",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res2.status_code == 201

    # Total should now be 20 + 15 - 5 = 30
    level_res = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku.id}&location_id={wh.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert level_res.json()["data"][0]["on_hand"] == 30

    # 4. Adjustment attempting to reduce below 0 (-50) must fail
    res3 = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Adjust",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "quantity_change": -50,
            "reason": "Erroneous adjustment",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res3.status_code == 400
    assert "below zero" in res3.json()["error"]["message"]


@pytest.mark.asyncio
async def test_transfer_stock_between_locations(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_admin_user: User,
):
    """Verify inter-location transfer updates both levels atomically and logs ledger rows."""
    wh = catalog_setup["warehouse"]
    store = catalog_setup["store"]
    sku = catalog_setup["sku"]

    # Baseline: 80 units in warehouse
    await InventoryService.record_transaction(
        db_session,
        test_tenant.id,
        test_admin_user.id,
        InventoryTransactionCreate(
            transaction_type=TransactionType.RECEIVE,
            sku_id=sku.id,
            location_id=wh.id,
            quantity_change=80,
        ),
    )
    await db_session.commit()

    # Transfer 30 units to retail store
    transfer_payload = {
        "transaction_type": "Transfer",
        "sku_id": str(sku.id),
        "location_id": str(wh.id),
        "target_location_id": str(store.id),
        "quantity_change": 30,
        "reference_id": "TRF-7701",
        "reason": "Replenish store inventory",
    }
    response = await async_client.post(
        "/api/v1/inventory/transactions",
        json=transfer_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201

    # Verify Warehouse level: 80 - 30 = 50
    wh_res = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku.id}&location_id={wh.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert wh_res.json()["data"][0]["on_hand"] == 50

    # Verify Store level: 0 + 30 = 30
    store_res = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku.id}&location_id={store.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert store_res.json()["data"][0]["on_hand"] == 30

    # Verify Ledger contains both transactions
    tx_res = await async_client.get(
        f"/api/v1/inventory/transactions?sku_id={sku.id}&transaction_type=Transfer",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    tx_items = tx_res.json()["data"]
    assert len(tx_items) == 2
    changes = {item["quantity_change"] for item in tx_items}
    assert changes == {-30, 30}


@pytest.mark.asyncio
async def test_transfer_validation_rules(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
):
    """Verify transfer validation: target_location_id required, distinct locations, non-zero qty."""
    wh = catalog_setup["warehouse"]
    sku = catalog_setup["sku"]

    # 1. Missing target_location_id
    res1 = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Transfer",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "quantity_change": 10,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res1.status_code == 400
    assert "target_location_id is required" in res1.json()["error"]["message"]

    # 2. Source and target locations identical
    res2 = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Transfer",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "target_location_id": str(wh.id),
            "quantity_change": 10,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res2.status_code == 400
    assert "distinct" in res2.json()["error"]["message"]

    # 3. Quantity change is zero
    res3 = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Adjust",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "quantity_change": 0,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res3.status_code == 400
    assert "cannot be zero" in res3.json()["error"]["message"]


@pytest.mark.asyncio
async def test_list_inventory_levels_filters(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_admin_user: User,
):
    """Verify stock status filtering and search on inventory levels."""
    wh = catalog_setup["warehouse"]
    store = catalog_setup["store"]
    sku = catalog_setup["sku"]

    # Warehouse has stock
    await InventoryService.record_transaction(
        db_session,
        test_tenant.id,
        test_admin_user.id,
        InventoryTransactionCreate(
            transaction_type=TransactionType.RECEIVE,
            sku_id=sku.id,
            location_id=wh.id,
            quantity_change=40,
        ),
    )
    # Store initialized with 0 stock
    await InventoryService._get_or_create_level_for_update(
        db_session, test_tenant.id, sku.id, store.id
    )
    await db_session.commit()

    # Filter: in_stock
    res_in_stock = await async_client.get(
        "/api/v1/inventory/levels?stock_status=in_stock",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_in_stock.status_code == 200
    items = res_in_stock.json()["data"]
    assert all(i["on_hand"] > 0 for i in items)

    # Filter: out_of_stock
    res_out_of_stock = await async_client.get(
        "/api/v1/inventory/levels?stock_status=out_of_stock",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_out_of_stock.status_code == 200
    out_items = res_out_of_stock.json()["data"]
    assert any(i["location_id"] == str(store.id) for i in out_items)

    # Search filter by SKU code
    res_search = await async_client.get(
        "/api/v1/inventory/levels?search=IND-BEAR",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["data"]) >= 1


@pytest.mark.asyncio
async def test_cross_tenant_inventory_isolation(
    async_client: AsyncClient,
    admin_token: str,
    catalog_setup: dict,
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_admin_user: User,
):
    """Verify Tenant B cannot view or modify Tenant A's inventory levels or ledger."""
    wh = catalog_setup["warehouse"]
    sku = catalog_setup["sku"]

    # Receive stock for Tenant A
    await InventoryService.record_transaction(
        db_session,
        test_tenant.id,
        test_admin_user.id,
        InventoryTransactionCreate(
            transaction_type=TransactionType.RECEIVE,
            sku_id=sku.id,
            location_id=wh.id,
            quantity_change=50,
        ),
    )
    await db_session.commit()

    # Create Tenant B and user
    tenant_b = await UserService.create_tenant(db_session, name="Competitor Corp")
    user_b = await UserService.create_user(
        db_session,
        tenant_id=tenant_b.id,
        email="admin@competitor.com",
        password="Password123!",
        role=UserRole.ADMIN,
    )
    await db_session.commit()

    token_b = create_access_token(
        {
            "sub": str(user_b.id),
            "tenant_id": str(tenant_b.id),
            "role": user_b.role,
            "email": user_b.email,
        }
    )

    # Tenant B tries to list levels -> gets 0 items
    res_levels = await async_client.get(
        "/api/v1/inventory/levels",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_levels.status_code == 200
    assert len(res_levels.json()["data"]) == 0

    # Tenant B tries to adjust Tenant A's SKU -> 404 Not Found
    res_tx = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Adjust",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "quantity_change": 10,
        },
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_tx.status_code == 404


@pytest.mark.asyncio
async def test_rbac_inventory_transaction_permissions(
    async_client: AsyncClient,
    viewer_token: str,
    catalog_setup: dict,
):
    """Verify Viewer role is forbidden from posting inventory transactions."""
    wh = catalog_setup["warehouse"]
    sku = catalog_setup["sku"]

    response = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Receive",
            "sku_id": str(sku.id),
            "location_id": str(wh.id),
            "quantity_change": 10,
        },
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert response.status_code == 403
    assert "not authorized" in response.json()["error"]["message"]
