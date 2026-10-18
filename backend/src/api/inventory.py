from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import get_current_user, require_roles
from backend.src.core.database import get_db_session
from backend.src.domain.inventory.schemas import (
    InventoryLevelResponse,
    InventoryTransactionCreate,
    InventoryTransactionResponse,
    PaginatedResponse,
)
from backend.src.domain.inventory.service import InventoryService
from backend.src.domain.users.models import User, UserRole

inventory_router = APIRouter(prefix="/inventory", tags=["Inventory Operations & Ledger"])

INVENTORY_TRANSACTION_ROLES = [
    UserRole.ADMIN.value,
    UserRole.INVENTORY_MANAGER.value,
    UserRole.WAREHOUSE_STAFF.value,
]


@inventory_router.get(
    "/levels",
    response_model=PaginatedResponse[InventoryLevelResponse],
    status_code=status.HTTP_200_OK,
    summary="List and filter inventory stock levels per SKU and location",
)
async def list_inventory_levels(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    sku_id: UUID | None = Query(default=None, description="Filter by SKU ID"),
    location_id: UUID | None = Query(default=None, description="Filter by Location ID"),
    stock_status: str | None = Query(
        default=None,
        pattern="^(low|out_of_stock|in_stock)$",
        description="Filter by stock threshold: low, out_of_stock, in_stock",
    ),
    search: str | None = Query(
        default=None,
        description="Search by SKU code, product name, or location name",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[InventoryLevelResponse]:
    """Retrieve current physical, reserved, and available stock levels."""
    data, meta = await InventoryService.list_inventory_levels(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        limit=limit,
        sku_id=sku_id,
        location_id=location_id,
        stock_status=stock_status,
        search=search,
    )
    return PaginatedResponse(data=data, meta=meta)


@inventory_router.post(
    "/transactions",
    response_model=InventoryTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an atomic inventory ledger transaction",
)
async def create_inventory_transaction(
    payload: InventoryTransactionCreate,
    current_user: User = Depends(require_roles(INVENTORY_TRANSACTION_ROLES)),
    db: AsyncSession = Depends(get_db_session),
) -> InventoryTransactionResponse:
    """Record an atomic stock adjustment, receipt, shipment, or inter-location transfer."""
    return await InventoryService.record_transaction(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        payload=payload,
    )


@inventory_router.get(
    "/transactions",
    response_model=PaginatedResponse[InventoryTransactionResponse],
    status_code=status.HTTP_200_OK,
    summary="List paginated inventory transactions audit trail",
)
async def list_inventory_transactions(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    sku_id: UUID | None = Query(default=None, description="Filter by SKU ID"),
    location_id: UUID | None = Query(default=None, description="Filter by Location ID"),
    transaction_type: str | None = Query(
        default=None,
        description="Filter by transaction type: Receive, Ship, Adjust, Transfer",
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[InventoryTransactionResponse]:
    """Retrieve immutable audit ledger records for the authenticated tenant."""
    data, meta = await InventoryService.list_transactions(
        db=db,
        tenant_id=current_user.tenant_id,
        page=page,
        limit=limit,
        sku_id=sku_id,
        location_id=location_id,
        transaction_type=transaction_type,
    )
    return PaginatedResponse(data=data, meta=meta)
