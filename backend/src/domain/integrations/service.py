import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.config import settings
from backend.src.core.errors import NotFoundException, UnauthorizedException, ValidationException
from backend.src.domain.integrations.crypto import (
    decrypt_credential,
    encrypt_credential,
    verify_shopify_hmac,
)
from backend.src.domain.integrations.models import IntegrationConfig
from backend.src.domain.integrations.schemas import (
    ShopifyConfigCreate,
    ShopifyConfigResponse,
    ShopifyConfigUpdate,
    ShopifyConnectionTestResponse,
    ShopifySyncStockRequest,
    ShopifySyncStockResponse,
    ShopifyWebhookProcessResult,
)
from backend.src.domain.integrations.shopify_client import (
    ShopifyAPIError,
    ShopifyClient,
)
from backend.src.domain.inventory.models import (
    SKU,
    InventoryLevel,
    InventoryTransaction,
    Location,
    TransactionType,
)
from backend.src.domain.inventory.schemas import InventoryTransactionCreate
from backend.src.domain.inventory.service import InventoryService
from backend.src.domain.users.models import User

logger = logging.getLogger(__name__)


class ShopifyService:
    """Domain service managing Shopify credentials, outbound sync, and inbound order webhooks."""

    PROVIDER_NAME = "shopify"

    @staticmethod
    def _mask_token(token: str) -> str:
        if not token or len(token) <= 8:
            return "shpat_****"
        return f"{token[:6]}...{token[-4:]}"

    @staticmethod
    async def get_config_entity(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> IntegrationConfig | None:
        """Retrieve raw integration entity for tenant."""
        result = await db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.tenant_id == tenant_id,
                IntegrationConfig.provider == ShopifyService.PROVIDER_NAME,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_config(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> ShopifyConfigResponse:
        """Fetch masked Shopify store integration configuration."""
        config = await ShopifyService.get_config_entity(db, tenant_id)
        if not config:
            raise NotFoundException("Shopify Integration Configuration")

        decrypted_token = decrypt_credential(config.api_key_encrypted)
        masked = ShopifyService._mask_token(decrypted_token)

        cfg_settings = config.settings or {}
        default_loc_id = (
            UUID(cfg_settings["default_location_id"])
            if cfg_settings.get("default_location_id")
            else None
        )

        return ShopifyConfigResponse(
            id=config.id,
            tenant_id=config.tenant_id,
            provider=config.provider,
            shop_domain=cfg_settings.get("shop_domain", ""),
            shopify_location_id=cfg_settings.get("shopify_location_id"),
            default_location_id=default_loc_id,
            auto_sync_stock=cfg_settings.get("auto_sync_stock", True),
            has_webhook_secret=bool(cfg_settings.get("webhook_secret")),
            is_active=True,
            masked_access_token=masked,
            last_sync_at=config.last_sync_at,
            created_at=config.created_at,
        )

    @staticmethod
    async def save_or_update_config(
        db: AsyncSession,
        tenant_id: UUID,
        payload: ShopifyConfigCreate | ShopifyConfigUpdate,
    ) -> ShopifyConfigResponse:
        """Securely persist or update Shopify credentials using AES-256-GCM encryption."""
        config = await ShopifyService.get_config_entity(db, tenant_id)

        # Validate local default location if provided
        if payload.default_location_id:
            loc_res = await db.execute(
                select(Location).where(
                    Location.id == payload.default_location_id,
                    Location.tenant_id == tenant_id,
                )
            )
            if not loc_res.scalar_one_or_none():
                raise NotFoundException("Location", payload.default_location_id)

        if not config:
            if not isinstance(payload, ShopifyConfigCreate) or not payload.access_token:
                raise ValidationException(
                    "access_token is required when creating a new Shopify connection.",
                    details=[{"field": "access_token", "issue": "Required field"}],
                )

            encrypted_key = encrypt_credential(payload.access_token)
            cfg_dict = {
                "shop_domain": payload.shop_domain,
                "shopify_location_id": payload.shopify_location_id,
                "default_location_id": str(payload.default_location_id)
                if payload.default_location_id
                else None,
                "auto_sync_stock": payload.auto_sync_stock,
                "webhook_secret": payload.webhook_secret,
            }
            config = IntegrationConfig(
                tenant_id=tenant_id,
                provider=ShopifyService.PROVIDER_NAME,
                api_key_encrypted=encrypted_key,
                settings=cfg_dict,
                last_sync_at=None,
            )
            db.add(config)
        else:
            existing_settings = config.settings or {}
            # Update token only if provided
            if payload.access_token:
                config.api_key_encrypted = encrypt_credential(payload.access_token)

            # Update settings selectively
            if payload.shop_domain is not None:
                existing_settings["shop_domain"] = payload.shop_domain
            if payload.shopify_location_id is not None:
                existing_settings["shopify_location_id"] = payload.shopify_location_id
            if payload.default_location_id is not None:
                existing_settings["default_location_id"] = str(payload.default_location_id)
            if payload.auto_sync_stock is not None:
                existing_settings["auto_sync_stock"] = payload.auto_sync_stock
            if payload.webhook_secret is not None:
                existing_settings["webhook_secret"] = payload.webhook_secret

            config.settings = existing_settings

        await db.flush()
        await db.refresh(config)

        return await ShopifyService.get_config(db, tenant_id)

    @staticmethod
    async def get_decrypted_client(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> tuple[ShopifyClient, IntegrationConfig]:
        """Instantiate ShopifyClient with decrypted credentials in memory."""
        config = await ShopifyService.get_config_entity(db, tenant_id)
        if not config:
            raise NotFoundException("Shopify Integration Configuration")

        decrypted_token = decrypt_credential(config.api_key_encrypted)
        cfg_settings = config.settings or {}
        shop_domain = cfg_settings.get("shop_domain")
        if not shop_domain:
            raise ValidationException(
                "Shop domain not configured for this tenant.",
                details=[{"field": "shop_domain", "issue": "Missing configuration"}],
            )

        client = ShopifyClient(
            shop_domain=shop_domain,
            access_token=decrypted_token,
        )
        return client, config

    @staticmethod
    async def test_connection(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> ShopifyConnectionTestResponse:
        """Test authentication and connectivity against the Shopify Admin API."""
        client, _ = await ShopifyService.get_decrypted_client(db, tenant_id)
        try:
            shop_data = await client.get_shop()
            return ShopifyConnectionTestResponse(
                success=True,
                shop_name=shop_data.get("name"),
                shop_domain=shop_data.get("domain") or client.shop_domain,
                currency=shop_data.get("currency"),
                message="Successfully authenticated and connected to Shopify store.",
            )
        except ShopifyAPIError as err:
            return ShopifyConnectionTestResponse(
                success=False,
                shop_domain=client.shop_domain,
                message=f"Shopify connection test failed: {err.message}",
            )

    @staticmethod
    async def sync_sku_stock_to_shopify(
        db: AsyncSession,
        tenant_id: UUID,
        payload: ShopifySyncStockRequest,
    ) -> ShopifySyncStockResponse:
        """Push available on-hand stock for a SKU to the connected Shopify store."""
        client, config = await ShopifyService.get_decrypted_client(db, tenant_id)
        cfg_settings = config.settings or {}

        # 1. Fetch SKU
        sku_res = await db.execute(
            select(SKU).where(SKU.id == payload.sku_id, SKU.tenant_id == tenant_id)
        )
        sku = sku_res.scalar_one_or_none()
        if not sku:
            raise NotFoundException("SKU", payload.sku_id)

        # 2. Determine local location
        target_loc_id = payload.location_id
        if not target_loc_id and cfg_settings.get("default_location_id"):
            target_loc_id = UUID(cfg_settings["default_location_id"])

        if not target_loc_id:
            loc_res = await db.execute(
                select(Location.id)
                .where(Location.tenant_id == tenant_id)
                .order_by(Location.created_at.asc())
                .limit(1)
            )
            target_loc_id = loc_res.scalar_one_or_none()

        if not target_loc_id:
            raise ValidationException(
                "No location available to resolve stock from.",
                details=[{"field": "location_id", "issue": "Missing location"}],
            )

        # 3. Fetch Inventory Level
        lvl_res = await db.execute(
            select(InventoryLevel).where(
                InventoryLevel.tenant_id == tenant_id,
                InventoryLevel.sku_id == sku.id,
                InventoryLevel.location_id == target_loc_id,
            )
        )
        level = lvl_res.scalar_one_or_none()
        on_hand = level.on_hand if level else 0
        reserved = level.reserved if level else 0
        available = max(0, on_hand - reserved)

        # 4. Determine Shopify inventory_item_id and shopify_location_id
        shopify_item_id = payload.shopify_inventory_item_id

        if not shopify_item_id:
            raise ValidationException(
                f"SKU {sku.sku_code} requires shopify_inventory_item_id to sync stock.",
                details=[{"field": "shopify_inventory_item_id", "issue": "Mapping required"}],
            )

        shopify_loc_id = cfg_settings.get("shopify_location_id")
        if not shopify_loc_id:
            # Try to fetch merchant's primary location from Shopify
            locs = await client.get_locations()
            if locs:
                shopify_loc_id = locs[0].get("id")
            if not shopify_loc_id:
                raise ValidationException(
                    "Shopify location ID not configured and could not be discovered.",
                    details=[{"field": "shopify_location_id", "issue": "Location required"}],
                )

        # 5. Push to Shopify
        await client.set_inventory_level(
            location_id=shopify_loc_id,
            inventory_item_id=shopify_item_id,
            available=available,
        )

        # 6. Update last sync timestamp
        now = datetime.now(UTC)
        config.last_sync_at = now
        await db.flush()

        return ShopifySyncStockResponse(
            success=True,
            sku_code=sku.sku_code,
            on_hand=on_hand,
            available=available,
            shopify_inventory_item_id=int(shopify_item_id),
            synced_at=now,
            message=f"Successfully synced available stock ({available}) to Shopify.",
        )

    @staticmethod
    async def process_order_webhook(
        db: AsyncSession,
        raw_body: bytes,
        headers: dict[str, str],
        topic: str,
        tenant_id: UUID | None = None,
    ) -> ShopifyWebhookProcessResult:
        """Verify HMAC-SHA256 signature and atomically record sales in inventory ledger."""
        # 1. Extract signature and shop domain from headers (case-insensitive)
        hmac_header = next(
            (v for k, v in headers.items() if k.lower() == "x-shopify-hmac-sha256"),
            None,
        )
        shop_domain = next(
            (v for k, v in headers.items() if k.lower() == "x-shopify-shop-domain"),
            None,
        )

        if not hmac_header:
            raise UnauthorizedException("Missing X-Shopify-Hmac-Sha256 webhook signature header.")

        # 2. Resolve IntegrationConfig and Tenant
        config: IntegrationConfig | None = None
        if tenant_id:
            config = await ShopifyService.get_config_entity(db, tenant_id)
        elif shop_domain:
            clean_domain = shop_domain.strip().lower()
            query = select(IntegrationConfig).where(
                IntegrationConfig.provider == ShopifyService.PROVIDER_NAME
            )
            result = await db.execute(query)
            all_configs = result.scalars().all()
            for c in all_configs:
                if c.settings and c.settings.get("shop_domain", "").lower() == clean_domain:
                    config = c
                    tenant_id = c.tenant_id
                    break

        # 3. Determine webhook secret
        webhook_secret = settings.SHOPIFY_WEBHOOK_SECRET
        if config and config.settings and config.settings.get("webhook_secret"):
            webhook_secret = config.settings["webhook_secret"]

        # 4. Cryptographic HMAC validation
        if not verify_shopify_hmac(raw_body, hmac_header, webhook_secret):
            logger.warning(
                "Rejected Shopify webhook: signature mismatch for shop %s",
                shop_domain,
            )
            raise UnauthorizedException("Shopify webhook signature verification failed.")

        # 5. Parse JSON payload
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as exc:
            raise ValidationException(f"Invalid JSON payload: {exc}") from exc

        order_id = payload.get("id")
        if not order_id:
            raise ValidationException("Missing order id in webhook payload.")

        order_number = payload.get("order_number") or payload.get("name") or str(order_id)

        if not tenant_id or not config:
            # Signature was valid against global secret, but tenant not matched
            return ShopifyWebhookProcessResult(
                status="ignored_unmatched_tenant",
                order_id=order_id,
                order_number=str(order_number),
                processed_items=0,
                deduplicated=False,
                details=[{"message": "Valid signature but shop domain not registered to a tenant"}],
            )

        # 6. Idempotency & Deduplication Check
        # Check if we already processed transactions for this Shopify order
        order_ref_prefix = f"shopify_order_{order_id}"
        tx_check = await db.execute(
            select(InventoryTransaction.id)
            .where(
                InventoryTransaction.tenant_id == tenant_id,
                InventoryTransaction.reference_id.like(f"{order_ref_prefix}%"),
            )
            .limit(1)
        )
        if tx_check.scalar_one_or_none():
            logger.info(
                "Duplicate Shopify webhook delivery detected for order %s. Skipping.",
                order_id,
            )
            return ShopifyWebhookProcessResult(
                status="success_deduplicated",
                order_id=order_id,
                order_number=str(order_number),
                processed_items=0,
                deduplicated=True,
                details=[{"message": f"Order {order_id} was previously processed."}],
            )

        # 7. Resolve default location & authorized user for audit ledger
        cfg_settings = config.settings or {}
        default_loc_id = (
            UUID(cfg_settings["default_location_id"])
            if cfg_settings.get("default_location_id")
            else None
        )

        if not default_loc_id:
            loc_res = await db.execute(
                select(Location.id)
                .where(Location.tenant_id == tenant_id)
                .order_by(Location.created_at.asc())
                .limit(1)
            )
            default_loc_id = loc_res.scalar_one_or_none()

        if not default_loc_id:
            raise ValidationException(
                "Tenant has no location configured to deduct stock for orders."
            )

        user_res = await db.execute(
            select(User.id)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.asc())
            .limit(1)
        )
        system_user_id = user_res.scalar_one_or_none()
        if not system_user_id:
            raise ValidationException("Tenant has no active user for ledger attribution.")

        # 8. Process each line item
        processed_count = 0
        details = []

        line_items = payload.get("line_items", [])
        for item in line_items:
            line_id = item.get("id")
            sku_code = item.get("sku")
            quantity = item.get("quantity", 1)

            if not sku_code:
                details.append({
                    "line_id": line_id,
                    "status": "skipped",
                    "reason": "Missing SKU code on line item",
                })
                continue

            # Find matching SKU
            sku_record = await db.execute(
                select(SKU).where(
                    SKU.tenant_id == tenant_id,
                    SKU.sku_code == sku_code.strip(),
                )
            )
            sku = sku_record.scalar_one_or_none()

            if not sku:
                details.append({
                    "sku": sku_code,
                    "status": "unmatched",
                    "reason": f"SKU {sku_code} not found in system catalog",
                })
                continue

            ref_id = f"shopify_order_{order_id}_{line_id}"
            tx_create = InventoryTransactionCreate(
                sku_id=sku.id,
                location_id=default_loc_id,
                transaction_type=TransactionType.SHIP,
                quantity_change=-abs(int(quantity)),
                reference_id=ref_id,
                reason=f"Shopify Order #{order_number} ({item.get('title') or sku_code})",
            )

            try:
                await InventoryService.record_transaction(
                    db=db,
                    tenant_id=tenant_id,
                    user_id=system_user_id,
                    payload=tx_create,
                )
                processed_count += 1
                details.append({
                    "sku": sku_code,
                    "quantity": quantity,
                    "status": "decremented",
                })
            except Exception as exc:
                logger.error(
                    "Failed to record inventory sale for SKU %s on order %s: %s",
                    sku_code,
                    order_id,
                    exc,
                )
                details.append({
                    "sku": sku_code,
                    "quantity": quantity,
                    "status": "failed",
                    "error": str(exc),
                })

        return ShopifyWebhookProcessResult(
            status="processed",
            order_id=order_id,
            order_number=str(order_number),
            processed_items=processed_count,
            deduplicated=False,
            details=details,
        )
