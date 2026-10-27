import base64
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from backend.src.core.config import settings
from backend.src.core.errors import ValidationException
from backend.src.domain.integrations.crypto import (
    decrypt_credential,
    encrypt_credential,
    verify_shopify_hmac,
)
from backend.src.domain.integrations.models import IntegrationConfig
from backend.src.domain.integrations.shopify_client import (
    ShopifyAuthError,
    ShopifyClient,
    ShopifyRateLimitError,
)
from backend.src.domain.inventory.models import (
    SKU,
    Category,
    InventoryLevel,
    InventoryTransaction,
    Location,
    LocationType,
    Product,
)
from backend.src.domain.users.models import Tenant, User
from httpx import AsyncClient, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ==============================================================================
# 1. Cryptography & Signature Verification Tests
# ==============================================================================
def test_encrypt_and_decrypt_credential() -> None:
    """Validate symmetric AES-256-GCM encryption and decryption roundtrip."""
    plain_token = "shpat_test_secret_access_token_12345"

    encrypted_1 = encrypt_credential(plain_token)
    encrypted_2 = encrypt_credential(plain_token)

    # Distinct random 12-byte nonces ensure ciphertexts are never identical
    assert encrypted_1 != encrypted_2

    # Both decrypt back to identical plaintext
    assert decrypt_credential(encrypted_1) == plain_token
    assert decrypt_credential(encrypted_2) == plain_token


def test_decrypt_credential_tamper_detection() -> None:
    """Tampering with AES-256-GCM ciphertext or tag must fail verification."""
    plain_token = "shpat_super_secret"
    encrypted = encrypt_credential(plain_token)

    raw_bytes = bytearray(base64.b64decode(encrypted))
    raw_bytes[-1] ^= 0xFF  # Flip bit in auth tag
    corrupted = base64.b64encode(raw_bytes).decode("utf-8")

    with pytest.raises(ValidationException):
        decrypt_credential(corrupted)


def test_verify_shopify_hmac() -> None:
    """Test HMAC-SHA256 signature verification."""
    secret = "my_webhook_secret_key"
    payload = b'{"id": 999, "total_price": "49.99"}'

    # Valid HMAC
    valid_hmac = base64.b64encode(
        hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).digest()
    ).decode("utf-8")
    assert verify_shopify_hmac(payload, valid_hmac, secret) is True

    # Invalid HMAC
    assert verify_shopify_hmac(payload, "invalid_signature", secret) is False

    # Missing header or secret
    assert verify_shopify_hmac(payload, None, secret) is False
    assert verify_shopify_hmac(payload, valid_hmac, "") is False


# ==============================================================================
# 2. Resilient Shopify API Client Unit Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_shopify_client_get_shop() -> None:
    """Verify headers and request structure on shop query."""
    client = ShopifyClient(shop_domain="test-store.myshopify.com", access_token="shpat_12345")

    mock_resp = Response(
        status_code=200,
        json={"shop": {"name": "Test Store", "currency": "USD"}},
        request=None,  # type: ignore[arg-type]
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = mock_resp
        shop = await client.get_shop()

        assert shop["name"] == "Test Store"
        assert shop["currency"] == "USD"
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert kwargs["headers"]["X-Shopify-Access-Token"] == "shpat_12345"


@pytest.mark.asyncio
async def test_shopify_client_rate_limiting_retry() -> None:
    """Verify that HTTP 429 triggers backoff and retry when safe."""
    client = ShopifyClient(
        shop_domain="test-store.myshopify.com",
        access_token="shpat_12345",
        max_retries=2,
    )

    resp_429 = Response(
        status_code=429,
        headers={"Retry-After": "0.01"},
        request=None,  # type: ignore[arg-type]
    )
    resp_200 = Response(
        status_code=200,
        json={"inventory_level": {"available": 42}},
        request=None,  # type: ignore[arg-type]
    )

    with (
        patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        mock_req.side_effect = [resp_429, resp_200]
        res = await client.set_inventory_level(
            location_id=101,
            inventory_item_id=202,
            available=42,
        )

        assert res["available"] == 42
        assert mock_req.call_count == 2
        mock_sleep.assert_called_once_with(0.01)


@pytest.mark.asyncio
async def test_shopify_client_rate_limit_exceeded() -> None:
    """Verify ShopifyRateLimitError is raised when retries are exhausted."""
    client = ShopifyClient(
        shop_domain="test-store.myshopify.com",
        access_token="shpat_12345",
        max_retries=1,
    )

    resp_429 = Response(
        status_code=429,
        headers={"Retry-After": "0.01"},
        request=None,  # type: ignore[arg-type]
    )

    with (
        patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        mock_req.side_effect = [resp_429, resp_429]
        with pytest.raises(ShopifyRateLimitError):
            await client.set_inventory_level(1, 2, 10)


@pytest.mark.asyncio
async def test_shopify_client_auth_error() -> None:
    """HTTP 401 must raise ShopifyAuthError immediately without retrying."""
    client = ShopifyClient(shop_domain="bad-store.myshopify.com", access_token="bad_token")

    resp_401 = Response(
        status_code=401,
        content=b"Invalid API key",
        request=None,  # type: ignore[arg-type]
    )

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = resp_401
        with pytest.raises(ShopifyAuthError):
            await client.get_shop()

        assert mock_req.call_count == 1


# ==============================================================================
# 3. Integration Settings & Configuration API Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_save_and_get_shopify_config(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Admin can configure Shopify store; token is encrypted and masked on retrieval."""
    payload = {
        "shop_domain": "cool-store.myshopify.com",
        "access_token": "shpat_live_secret_token_12345",
        "shopify_location_id": "999888777",
        "auto_sync_stock": True,
        "webhook_secret": "my_webhook_secret_key",
    }

    # 1. Save Config
    resp = await async_client.post(
        "/api/v1/integrations/shopify/config",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["shop_domain"] == "cool-store.myshopify.com"
    assert data["masked_access_token"] == "shpat_...2345"
    assert "shpat_live_secret_token_12345" not in json.dumps(data)

    # 2. Verify encrypted in DB
    result = await db_session.execute(
        select(IntegrationConfig).where(
            IntegrationConfig.tenant_id == test_tenant.id,
            IntegrationConfig.provider == "shopify",
        )
    )
    db_cfg = result.scalar_one()
    assert db_cfg.api_key_encrypted != "shpat_live_secret_token_12345"
    assert decrypt_credential(db_cfg.api_key_encrypted) == "shpat_live_secret_token_12345"

    # 3. Retrieve Config via GET
    get_resp = await async_client.get(
        "/api/v1/integrations/shopify/config",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["masked_access_token"] == "shpat_...2345"


@pytest.mark.asyncio
async def test_shopify_config_rbac_enforcement(
    async_client: AsyncClient,
    viewer_token: str,
) -> None:
    """Non-admin users cannot configure Shopify credentials."""
    payload = {
        "shop_domain": "unauthorized.myshopify.com",
        "access_token": "shpat_attempt_token",
    }

    # Viewer role -> 403 Forbidden
    resp = await async_client.post(
        "/api/v1/integrations/shopify/config",
        json=payload,
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403

    # Unauthenticated -> 401 Unauthorized
    resp_unauth = await async_client.post(
        "/api/v1/integrations/shopify/config",
        json=payload,
    )
    assert resp_unauth.status_code == 401


@pytest.mark.asyncio
async def test_shopify_test_connection_endpoint(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Test connection endpoint verifies connectivity via ShopifyClient."""
    # Pre-seed config
    config = IntegrationConfig(
        tenant_id=test_tenant.id,
        provider="shopify",
        api_key_encrypted=encrypt_credential("shpat_valid_token"),
        settings={"shop_domain": "demo.myshopify.com"},
    )
    db_session.add(config)
    await db_session.commit()

    with patch.object(
        ShopifyClient,
        "get_shop",
        new_callable=AsyncMock,
        return_value={"name": "Demo Apparel", "currency": "USD", "domain": "demo.myshopify.com"},
    ):
        resp = await async_client.post(
            "/api/v1/integrations/shopify/test",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["shop_name"] == "Demo Apparel"
        assert data["currency"] == "USD"


# ==============================================================================
# 4. Outbound Stock Synchronization API Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_shopify_sync_sku_stock(
    async_client: AsyncClient,
    admin_token: str,
    test_tenant: Tenant,
    db_session: AsyncSession,
) -> None:
    """Push available stock to Shopify."""
    # Setup Location, Category, Product, SKU, and InventoryLevel
    loc = Location(tenant_id=test_tenant.id, name="Main Warehouse", type=LocationType.WAREHOUSE)
    cat = Category(tenant_id=test_tenant.id, name="Apparel")
    prod = Product(tenant_id=test_tenant.id, category=cat, name="Cotton T-Shirt")
    sku = SKU(
        tenant_id=test_tenant.id,
        product=prod,
        sku_code="TSHIRT-BLK-S",
    )
    db_session.add_all([loc, cat, prod, sku])
    await db_session.flush()

    level = InventoryLevel(
        tenant_id=test_tenant.id,
        sku_id=sku.id,
        location_id=loc.id,
        on_hand=25,
        reserved=5,  # Available = 20
        version=1,
    )
    config = IntegrationConfig(
        tenant_id=test_tenant.id,
        provider="shopify",
        api_key_encrypted=encrypt_credential("shpat_valid_token"),
        settings={
            "shop_domain": "apparel.myshopify.com",
            "shopify_location_id": "778899",
            "default_location_id": str(loc.id),
        },
    )
    db_session.add_all([level, config])
    await db_session.commit()

    with patch.object(
        ShopifyClient,
        "set_inventory_level",
        new_callable=AsyncMock,
        return_value={"available": 20},
    ) as mock_set:
        resp = await async_client.post(
            "/api/v1/integrations/shopify/sync",
            json={"sku_id": str(sku.id), "shopify_inventory_item_id": 884422},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["available"] == 20
        assert data["shopify_inventory_item_id"] == 884422

        mock_set.assert_called_once_with(
            location_id="778899",
            inventory_item_id=884422,
            available=20,
        )


# ==============================================================================
# 5. Inbound Webhook Handling & Ledger Reduction Tests
# ==============================================================================
@pytest.mark.asyncio
async def test_shopify_order_webhook_success_and_ledger_reduction(
    async_client: AsyncClient,
    test_tenant: Tenant,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Valid Shopify orders/create webhook decrements stock atomically via SHIP ledger."""
    # Setup Location, Product, SKU, Inventory Level (30 on hand)
    loc = Location(tenant_id=test_tenant.id, name="Shopify Warehouse", type=LocationType.WAREHOUSE)
    cat = Category(tenant_id=test_tenant.id, name="Footwear")
    prod = Product(tenant_id=test_tenant.id, category=cat, name="Running Shoes")
    sku = SKU(tenant_id=test_tenant.id, product=prod, sku_code="RUN-SHOE-10")
    db_session.add_all([loc, cat, prod, sku])
    await db_session.flush()

    level = InventoryLevel(
        tenant_id=test_tenant.id,
        sku_id=sku.id,
        location_id=loc.id,
        on_hand=30,
        reserved=0,
        version=1,
    )
    config = IntegrationConfig(
        tenant_id=test_tenant.id,
        provider="shopify",
        api_key_encrypted=encrypt_credential("shpat_valid_token"),
        settings={
            "shop_domain": "shoes.myshopify.com",
            "default_location_id": str(loc.id),
            "webhook_secret": "custom_shop_webhook_secret",
        },
    )
    db_session.add_all([level, config])
    await db_session.commit()

    webhook_payload = {
        "id": 883921,
        "name": "#1042",
        "order_number": 1042,
        "line_items": [
            {
                "id": 992211,
                "sku": "RUN-SHOE-10",
                "quantity": 3,
                "title": "Running Shoes - Size 10",
            }
        ],
    }
    raw_body = json.dumps(webhook_payload).encode("utf-8")

    # Generate HMAC with custom webhook secret
    valid_hmac = base64.b64encode(
        hmac.new(b"custom_shop_webhook_secret", raw_body, hashlib.sha256).digest()
    ).decode("utf-8")

    target_sku_id = sku.id
    target_loc_id = loc.id

    # Send Webhook
    resp = await async_client.post(
        "/api/v1/webhooks/shopify/orders/create",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Hmac-Sha256": valid_hmac,
            "X-Shopify-Shop-Domain": "shoes.myshopify.com",
        },
    )

    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["status"] == "processed"
    assert res_data["processed_items"] == 1
    assert res_data["deduplicated"] is False

    # Verify inventory was decremented in DB from 30 to 27
    lvl_res = await db_session.execute(
        select(InventoryLevel)
        .where(
            InventoryLevel.tenant_id == test_tenant.id,
            InventoryLevel.sku_id == target_sku_id,
            InventoryLevel.location_id == target_loc_id,
        )
        .execution_options(populate_existing=True)
    )
    updated_level = lvl_res.scalar_one()
    assert updated_level.on_hand == 27

    # Verify inventory transaction ledger entry
    tx_res = await db_session.execute(
        select(InventoryTransaction).where(
            InventoryTransaction.tenant_id == test_tenant.id,
            InventoryTransaction.sku_id == target_sku_id,
            InventoryTransaction.reference_id == "shopify_order_883921_992211",
        )
    )
    tx = tx_res.scalar_one()
    assert tx.transaction_type == "Ship"
    assert tx.quantity_change == -3
    assert "#1042" in tx.reason


@pytest.mark.asyncio
async def test_shopify_order_webhook_deduplication(
    async_client: AsyncClient,
    test_tenant: Tenant,
    test_admin_user: User,
    db_session: AsyncSession,
) -> None:
    """Duplicate webhook invocations for the same order must be skipped
    to avoid double deduction.
    """
    loc = Location(tenant_id=test_tenant.id, name="Store", type=LocationType.STORE)
    cat = Category(tenant_id=test_tenant.id, name="Electronics")
    prod = Product(tenant_id=test_tenant.id, category=cat, name="Wireless Mouse")
    sku = SKU(tenant_id=test_tenant.id, product=prod, sku_code="MOUSE-WL-BLK")
    db_session.add_all([loc, cat, prod, sku])
    await db_session.flush()

    level = InventoryLevel(
        tenant_id=test_tenant.id,
        sku_id=sku.id,
        location_id=loc.id,
        on_hand=10,
        reserved=0,
        version=1,
    )
    config = IntegrationConfig(
        tenant_id=test_tenant.id,
        provider="shopify",
        api_key_encrypted=encrypt_credential("shpat_token"),
        settings={
            "shop_domain": "electronics.myshopify.com",
            "default_location_id": str(loc.id),
        },
    )
    db_session.add_all([level, config])
    await db_session.commit()

    webhook_payload = {
        "id": 771122,
        "name": "#2001",
        "order_number": 2001,
        "line_items": [
            {
                "id": 1100,
                "sku": "MOUSE-WL-BLK",
                "quantity": 2,
            }
        ],
    }
    raw_body = json.dumps(webhook_payload).encode("utf-8")
    sig = base64.b64encode(
        hmac.new(settings.SHOPIFY_WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).digest()
    ).decode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Hmac-Sha256": sig,
        "X-Shopify-Shop-Domain": "electronics.myshopify.com",
    }

    target_sku_id = sku.id
    target_loc_id = loc.id

    # First delivery: processed
    resp_1 = await async_client.post(
        "/api/v1/webhooks/shopify/orders/create",
        content=raw_body,
        headers=headers,
    )
    assert resp_1.status_code == 200
    assert resp_1.json()["deduplicated"] is False

    # Second delivery: deduplicated
    resp_2 = await async_client.post(
        "/api/v1/webhooks/shopify/orders/create",
        content=raw_body,
        headers=headers,
    )
    assert resp_2.status_code == 200
    assert resp_2.json()["deduplicated"] is True

    # On-hand stock decremented only ONCE (10 - 2 = 8)
    lvl_res = await db_session.execute(
        select(InventoryLevel)
        .where(
            InventoryLevel.sku_id == target_sku_id,
            InventoryLevel.location_id == target_loc_id,
        )
        .execution_options(populate_existing=True)
    )
    assert lvl_res.scalar_one().on_hand == 8


@pytest.mark.asyncio
async def test_shopify_order_webhook_invalid_signature_rejected(
    async_client: AsyncClient,
) -> None:
    """Webhooks with missing or forged HMAC must be rejected with HTTP 401."""
    raw_body = b'{"id": 12345}'

    # Missing header -> 401
    resp_no_header = await async_client.post(
        "/api/v1/webhooks/shopify/orders/create",
        content=raw_body,
    )
    assert resp_no_header.status_code == 401

    # Invalid HMAC -> 401
    resp_bad_sig = await async_client.post(
        "/api/v1/webhooks/shopify/orders/create",
        content=raw_body,
        headers={"X-Shopify-Hmac-Sha256": "forged_hmac_signature"},
    )
    assert resp_bad_sig.status_code == 401
