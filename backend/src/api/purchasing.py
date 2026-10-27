from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import get_current_user, require_roles
from backend.src.core.database import get_db_session
from backend.src.domain.purchasing.schemas import (
    PaginatedPurchaseOrdersResponse,
    POReceiveRequest,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    PurchasingSuggestionItem,
)
from backend.src.domain.purchasing.service import PurchasingService
from backend.src.domain.users.models import User, UserRole

purchasing_router = APIRouter(prefix="/purchasing", tags=["Purchasing & Replenishment"])


@purchasing_router.get(
    "/suggestions",
    response_model=list[PurchasingSuggestionItem],
    summary="Get automated replenishment purchase recommendations",
)
async def get_purchasing_suggestions(
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[PurchasingSuggestionItem]:
    """Retrieve replenishment recommendations driven by lead times and safety stock levels."""
    return await PurchasingService.get_replenishment_suggestions(
        db=db,
        tenant_id=current_user.tenant_id,
    )


@purchasing_router.post(
    "/orders",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Purchase Order",
)
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles([
            UserRole.ADMIN.value,
            UserRole.INVENTORY_MANAGER.value,
            UserRole.PURCHASER.value,
        ])
    ),
) -> PurchaseOrderResponse:
    """Create a new purchase order with line items in Draft state."""
    return await PurchasingService.create_purchase_order(
        db=db,
        tenant_id=current_user.tenant_id,
        payload=payload,
    )


@purchasing_router.get(
    "/orders",
    response_model=PaginatedPurchaseOrdersResponse,
    summary="List paginated Purchase Orders",
)
async def list_purchase_orders(
    status: str | None = Query(default=None, description="Filter by status (Draft, Sent, Partially Received, Completed)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PaginatedPurchaseOrdersResponse:
    """List tenant purchase orders with optional status filter."""
    data, meta = await PurchasingService.list_purchase_orders(
        db=db,
        tenant_id=current_user.tenant_id,
        status=status,
        page=page,
        limit=limit,
    )
    return PaginatedPurchaseOrdersResponse(data=data, meta=meta)


@purchasing_router.get(
    "/orders/{order_id}",
    response_model=PurchaseOrderResponse,
    summary="Get Purchase Order details",
)
async def get_purchase_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PurchaseOrderResponse:
    """Fetch complete details of a specific purchase order including line items."""
    return await PurchasingService.get_purchase_order(
        db=db,
        tenant_id=current_user.tenant_id,
        po_id=order_id,
    )


@purchasing_router.put(
    "/orders/{order_id}",
    response_model=PurchaseOrderResponse,
    summary="Update Purchase Order",
)
async def update_purchase_order(
    order_id: UUID,
    payload: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles([
            UserRole.ADMIN.value,
            UserRole.INVENTORY_MANAGER.value,
            UserRole.PURCHASER.value,
        ])
    ),
) -> PurchaseOrderResponse:
    """Update metadata or lifecycle status on a purchase order."""
    return await PurchasingService.update_purchase_order(
        db=db,
        tenant_id=current_user.tenant_id,
        po_id=order_id,
        payload=payload,
    )


@purchasing_router.post(
    "/orders/{order_id}/receive",
    response_model=PurchaseOrderResponse,
    summary="Receive shipment items and atomically restock inventory ledger",
)
async def receive_purchase_order(
    order_id: UUID,
    payload: POReceiveRequest,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(
        require_roles([
            UserRole.ADMIN.value,
            UserRole.INVENTORY_MANAGER.value,
            UserRole.PURCHASER.value,
            UserRole.WAREHOUSE_STAFF.value,
        ])
    ),
) -> PurchaseOrderResponse:
    """Atomically record incoming stock into the ledger and update PO fulfillment status."""
    return await PurchasingService.receive_purchase_order(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        po_id=order_id,
        payload=payload,
    )
