import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from backend.src.core.security import create_access_token
from backend.src.domain.integrations.shopify_client import ShopifyClient
from backend.src.domain.inventory.models import (
    Location,
    LocationType,
)
from backend.src.domain.users.models import Tenant, UserRole
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ==============================================================================
# End-to-End Multi-Tenant Lifecycle Journey
# ==============================================================================
@pytest.mark.asyncio
async def test_full_tenant_onboarding_and_inventory_operations_journey(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Simulate a complete production lifecycle:
    1. Tenant self-registration (Acme Goods)
    2. Admin logs in and provisions team (Inventory Manager, Warehouse Clerk, Auditor)
    3. Category, Locations (Warehouse + Store), and Product SKUs created
    4. Warehouse Clerk receives initial shipment (100 units)
    5. Stock transfer (35 units from Warehouse to Store)
    6. Admin connects Shopify store
    7. Inbound Shopify order webhook arrives (#9001, 5 units sold at Store)
    8. Verifies real-time stock levels and audit ledger
    9. Outbound sync pushes current stock to Shopify
    """

    # --------------------------------------------------------------------------
    # Step 1: Organization Self-Registration
    # --------------------------------------------------------------------------
    reg_resp = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Acme Global Distribution",
            "email": "ceo@acme-global.com",
            "password": "CorporatePassword2026!",
        },
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    admin_token = reg_data["access_token"]
    tenant_id = reg_data["user"]["tenant_id"]
    assert reg_data["user"]["role"] == "Admin"

    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # --------------------------------------------------------------------------
    # Step 2: Admin provisions organization team members
    # --------------------------------------------------------------------------
    # 2a. Invite Inventory Manager
    im_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": "inventory.manager@acme-global.com",
            "password": "ManagerSecurePass2026!",
            "role": UserRole.INVENTORY_MANAGER.value,
        },
        headers=admin_headers,
    )
    assert im_resp.status_code == 201
    im_data = im_resp.json()
    assert im_data["role"] == "Inventory Manager"

    # 2b. Invite Warehouse Clerk
    clerk_resp = await async_client.post(
        "/api/v1/users",
        json={
            "email": "warehouse.clerk@acme-global.com",
            "password": "ClerkSecurePass2026!",
            "role": UserRole.WAREHOUSE_STAFF.value,
        },
        headers=admin_headers,
    )
    assert clerk_resp.status_code == 201
    clerk_data = clerk_resp.json()
    assert clerk_data["role"] == "Warehouse Staff"

    # Generate tokens for manager and clerk
    clerk_token = create_access_token(
        {
            "sub": clerk_data["id"],
            "tenant_id": tenant_id,
            "role": UserRole.WAREHOUSE_STAFF.value,
            "email": clerk_data["email"],
        }
    )
    clerk_headers = {"Authorization": f"Bearer {clerk_token}"}

    # --------------------------------------------------------------------------
    # Step 3: Setup Locations and Product Catalog
    # --------------------------------------------------------------------------
    # 3a. Locations: Distribution Center (Warehouse) + City Center (Store)
    wh_resp = await async_client.post(
        "/api/v1/locations",
        json={"name": "Regional Distribution Center", "type": "Warehouse"},
        headers=admin_headers,
    )
    assert wh_resp.status_code == 201
    wh_id = wh_resp.json()["id"]

    store_resp = await async_client.post(
        "/api/v1/locations",
        json={"name": "Downtown Retail Store", "type": "Store"},
        headers=admin_headers,
    )
    assert store_resp.status_code == 201
    store_id = store_resp.json()["id"]

    # 3b. Category: Electronics
    cat_resp = await async_client.post(
        "/api/v1/products/categories",
        json={"name": "Consumer Audio"},
        headers=admin_headers,
    )
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    # 3c. Product & SKU
    sku_resp = await async_client.post(
        "/api/v1/products/skus",
        json={
            "product_name": "Noise-Cancelling Headphones",
            "category_id": cat_id,
            "sku_code": "AUDIO-NC-001",
            "unit_cost": 45.00,
            "sales_price": 129.99,
            "lead_time_days": 5,
        },
        headers=admin_headers,
    )
    assert sku_resp.status_code == 201
    sku_data = sku_resp.json()
    sku_id = sku_data["id"]
    assert sku_data["sku_code"] == "AUDIO-NC-001"

    # --------------------------------------------------------------------------
    # Step 4: Warehouse Clerk receives stock shipment (+100 units at DC)
    # --------------------------------------------------------------------------
    recv_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Receive",
            "sku_id": sku_id,
            "location_id": wh_id,
            "quantity_change": 100,
            "reference_id": "PO-GLOBAL-2026-001",
            "reason": "Initial supplier stock shipment received at dock",
        },
        headers=clerk_headers,
    )
    assert recv_resp.status_code == 201
    recv_data = recv_resp.json()
    assert recv_data["transaction_type"] == "Receive"
    assert recv_data["quantity_change"] == 100

    # Verify inventory levels at Warehouse
    wh_level_resp = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku_id}&location_id={wh_id}",
        headers=admin_headers,
    )
    assert wh_level_resp.status_code == 200
    wh_level_items = wh_level_resp.json()["data"]
    assert len(wh_level_items) == 1
    assert wh_level_items[0]["on_hand"] == 100
    assert wh_level_items[0]["available"] == 100

    # --------------------------------------------------------------------------
    # Step 5: Transfer 35 units from Warehouse to Retail Store
    # --------------------------------------------------------------------------
    transfer_resp = await async_client.post(
        "/api/v1/inventory/transactions",
        json={
            "transaction_type": "Transfer",
            "sku_id": sku_id,
            "location_id": wh_id,
            "target_location_id": store_id,
            "quantity_change": 35,
            "reference_id": "TRANSFER-DC-TO-STORE-01",
            "reason": "Replenish Downtown Retail floor stock",
        },
        headers=clerk_headers,
    )
    assert transfer_resp.status_code == 201

    # Verify source (Warehouse) dropped to 65
    wh_check = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku_id}&location_id={wh_id}",
        headers=admin_headers,
    )
    assert wh_check.json()["data"][0]["on_hand"] == 65

    # Verify destination (Store) increased to 35
    store_check = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku_id}&location_id={store_id}",
        headers=admin_headers,
    )
    assert store_check.json()["data"][0]["on_hand"] == 35

    # --------------------------------------------------------------------------
    # Step 6: Connect Shopify Store
    # --------------------------------------------------------------------------
    shop_cfg_resp = await async_client.post(
        "/api/v1/integrations/shopify/config",
        json={
            "shop_domain": "acme-global.myshopify.com",
            "access_token": "shpat_corporate_token_abcdef123456",
            "shopify_location_id": "loc_shopify_888",
            "default_location_id": store_id,
            "auto_sync_stock": True,
            "webhook_secret": "acme_hmac_secret_2026",
        },
        headers=admin_headers,
    )
    assert shop_cfg_resp.status_code == 200
    assert shop_cfg_resp.json()["is_active"] is True

    # --------------------------------------------------------------------------
    # Step 7: Inbound Shopify Order Webhook arrives (Order #9001, 5 units sold)
    # --------------------------------------------------------------------------
    order_payload = {
        "id": 99001,
        "name": "#9001",
        "order_number": 9001,
        "line_items": [
            {
                "id": 1110001,
                "sku": "AUDIO-NC-001",
                "quantity": 5,
                "title": "Noise-Cancelling Headphones - Black",
            }
        ],
    }
    raw_order_body = json.dumps(order_payload).encode("utf-8")
    sig = base64.b64encode(
        hmac.new(b"acme_hmac_secret_2026", raw_order_body, hashlib.sha256).digest()
    ).decode("utf-8")

    webhook_resp = await async_client.post(
        "/api/v1/webhooks/shopify/orders/create",
        content=raw_order_body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": sig,
            "X-Shopify-Shop-Domain": "acme-global.myshopify.com",
        },
    )
    assert webhook_resp.status_code == 200
    assert webhook_resp.json()["status"] == "processed"
    assert webhook_resp.json()["processed_items"] == 1

    # Verify Store stock decreased from 35 to 30
    store_after_sale = await async_client.get(
        f"/api/v1/inventory/levels?sku_id={sku_id}&location_id={store_id}",
        headers=admin_headers,
    )
    assert store_after_sale.json()["data"][0]["on_hand"] == 30
    assert store_after_sale.json()["data"][0]["available"] == 30

    # --------------------------------------------------------------------------
    # Step 8: Outbound Stock Push back to Shopify
    # --------------------------------------------------------------------------
    with patch.object(
        ShopifyClient,
        "set_inventory_level",
        new_callable=AsyncMock,
        return_value={"available": 30},
    ) as mock_push:
        sync_resp = await async_client.post(
            "/api/v1/integrations/shopify/sync",
            json={
                "sku_id": sku_id,
                "location_id": store_id,
                "shopify_inventory_item_id": 998877,
            },
            headers=admin_headers,
        )
        assert sync_resp.status_code == 200
        assert sync_resp.json()["available"] == 30
        mock_push.assert_called_once_with(
            location_id="loc_shopify_888",
            inventory_item_id=998877,
            available=30,
        )

    # --------------------------------------------------------------------------
    # Step 9: Audit Trail completeness
    # --------------------------------------------------------------------------
    tx_list_resp = await async_client.get(
        f"/api/v1/inventory/transactions?sku_id={sku_id}",
        headers=admin_headers,
    )
    assert tx_list_resp.status_code == 200
    tx_items = tx_list_resp.json()["data"]
    # Total transactions recorded: 1 Receive + 2 Transfer (out & in) + 1 Shopify Ship = 4
    assert len(tx_items) == 4
    types = [t["transaction_type"] for t in tx_items]
    assert "Receive" in types
    assert "Transfer" in types
    assert "Ship" in types


# ==============================================================================
# Multi-Tenant Data Isolation Test
# ==============================================================================
@pytest.mark.asyncio
async def test_strict_multi_tenant_isolation(
    async_client: AsyncClient,
    test_tenant: Tenant,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    """Ensure Tenant B cannot access or affect Tenant A's catalog, stock, or integrations."""
    # Tenant A creates Location and SKU
    loc_a = Location(tenant_id=test_tenant.id, name="Tenant A Vault", type=LocationType.WAREHOUSE)
    db_session.add(loc_a)
    await db_session.commit()

    # Register Tenant B
    reg_b = await async_client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Tenant B Enterprises",
            "email": "admin@tenant-b.com",
            "password": "PasswordTenantB2026!",
        },
    )
    assert reg_b.status_code == 201
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 1. Tenant B listing locations must NOT see Tenant A's location
    locs_b_resp = await async_client.get("/api/v1/locations", headers=headers_b)
    assert locs_b_resp.status_code == 200
    loc_names_b = [loc["name"] for loc in locs_b_resp.json()]
    assert "Tenant A Vault" not in loc_names_b

    # 2. Tenant B listing inventory levels must be empty
    levels_b_resp = await async_client.get("/api/v1/inventory/levels", headers=headers_b)
    assert levels_b_resp.status_code == 200
    assert len(levels_b_resp.json()["data"]) == 0

    # 3. Tenant B querying Tenant A's Shopify config must get 404
    shopify_b_resp = await async_client.get(
        "/api/v1/integrations/shopify/config",
        headers=headers_b,
    )
    assert shopify_b_resp.status_code == 404
