import asyncio
import logging
from uuid import UUID

from backend.src.core.database import AsyncSessionLocal
from backend.src.domain.integrations.schemas import ShopifySyncStockRequest
from backend.src.domain.integrations.service import ShopifyService

logger = logging.getLogger(__name__)


async def sync_sku_stock_to_shopify(
    tenant_id: UUID,
    sku_id: UUID,
    location_id: UUID,
    new_available_quantity: int,
) -> dict:
    """Asynchronously sync an inventory level change to Shopify."""
    logger.info(
        "Initiating background stock sync to Shopify for tenant=%s, sku=%s, qty=%d",
        tenant_id,
        sku_id,
        new_available_quantity,
    )
    async with AsyncSessionLocal() as session:
        try:
            res = await ShopifyService.sync_stock_to_shopify(
                db=session,
                tenant_id=tenant_id,
                payload=ShopifySyncStockRequest(
                    sku_id=sku_id,
                    location_id=location_id,
                    available_quantity=new_available_quantity,
                ),
            )
            return {
                "status": "SUCCESS" if res.success else "FAILED",
                "synced_at": res.synced_at.isoformat() if res.synced_at else None,
                "message": res.message,
            }
        except Exception as e:
            logger.error("Failed background Shopify sync for SKU %s: %s", sku_id, e)
            return {
                "status": "ERROR",
                "error": str(e),
            }


def sync_sku_stock_to_shopify_sync(
    tenant_id: UUID,
    sku_id: UUID,
    location_id: UUID,
    new_available_quantity: int,
) -> dict:
    """Synchronous entry point for background task workers."""
    return asyncio.run(
        sync_sku_stock_to_shopify(
            tenant_id=tenant_id,
            sku_id=sku_id,
            location_id=location_id,
            new_available_quantity=new_available_quantity,
        )
    )
