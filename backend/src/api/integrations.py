from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import require_roles
from backend.src.core.database import get_db_session
from backend.src.domain.integrations.schemas import (
    ShopifyConfigCreate,
    ShopifyConfigResponse,
    ShopifyConnectionTestResponse,
    ShopifySyncStockRequest,
    ShopifySyncStockResponse,
)
from backend.src.domain.integrations.service import ShopifyService
from backend.src.domain.users.models import User, UserRole

integrations_router = APIRouter(prefix="/integrations", tags=["Integrations"])

MANAGE_ROLES = [UserRole.ADMIN.value, UserRole.INVENTORY_MANAGER.value]


@integrations_router.get(
    "/shopify/config",
    response_model=ShopifyConfigResponse,
    summary="Get current Shopify store integration configuration",
)
async def get_shopify_config(
    current_user: User = Depends(require_roles(MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> ShopifyConfigResponse:
    """Retrieve Shopify integration settings for the authenticated tenant.

    Requires Admin or Inventory Manager role. Sensitive tokens are masked.
    """
    return await ShopifyService.get_config(db, current_user.tenant_id)


@integrations_router.post(
    "/shopify/config",
    response_model=ShopifyConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Save or update Shopify store integration configuration",
)
async def save_shopify_config(
    payload: ShopifyConfigCreate,
    current_user: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: AsyncSession = Depends(get_db_session),
) -> ShopifyConfigResponse:
    """Configure or update Shopify Admin API credentials for the authenticated tenant.

    Restricted strictly to Admin users. The access token is encrypted via AES-256-GCM.
    """
    return await ShopifyService.save_or_update_config(db, current_user.tenant_id, payload)


@integrations_router.post(
    "/shopify/test",
    response_model=ShopifyConnectionTestResponse,
    summary="Test connectivity to connected Shopify store",
)
async def test_shopify_connection(
    current_user: User = Depends(require_roles(MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> ShopifyConnectionTestResponse:
    """Verify stored credentials by calling the Shopify Admin API."""
    return await ShopifyService.test_connection(db, current_user.tenant_id)


@integrations_router.post(
    "/shopify/sync",
    response_model=ShopifySyncStockResponse,
    summary="Sync SKU stock level to Shopify",
)
async def sync_sku_stock_to_shopify(
    payload: ShopifySyncStockRequest,
    current_user: User = Depends(require_roles(MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> ShopifySyncStockResponse:
    """Manually or programmatically push on-hand available stock for a SKU to Shopify."""
    return await ShopifyService.sync_sku_stock_to_shopify(db, current_user.tenant_id, payload)
