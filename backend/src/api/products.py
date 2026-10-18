from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import get_current_tenant_id, require_roles
from backend.src.core.database import get_db_session
from backend.src.domain.inventory.schemas import (
    CategoryCreate,
    CategoryResponse,
    PaginatedResponse,
    ProductCreate,
    ProductResponse,
    SKUCreate,
    SKUResponse,
    SKUUpdate,
)
from backend.src.domain.inventory.service import CatalogService
from backend.src.domain.users.models import UserRole

products_router = APIRouter(prefix="/products", tags=["Product & SKU Management"])

CATALOG_WRITE_ROLES = [UserRole.ADMIN.value, UserRole.INVENTORY_MANAGER.value]


# --- SKUs ---
@products_router.get(
    "/skus",
    response_model=PaginatedResponse[SKUResponse],
    status_code=status.HTTP_200_OK,
    summary="List and filter SKUs with pagination",
)
async def list_skus(
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=50, ge=1, le=100, description="Items per page"),
    search: str | None = Query(default=None, description="Search by SKU code or product name"),
    category_id: UUID | None = Query(default=None, description="Filter by category ID"),
    sort_by: str = Query(default="created_at", description="Sort column"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order"),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedResponse[SKUResponse]:
    """Retrieve a paginated list of SKUs for the authenticated tenant."""
    data, meta = await CatalogService.list_skus(
        db=db,
        tenant_id=tenant_id,
        page=page,
        limit=limit,
        search=search,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedResponse(data=data, meta=meta)


@products_router.post(
    "/skus",
    response_model=SKUResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(CATALOG_WRITE_ROLES))],
    summary="Create a new SKU variant",
)
async def create_sku(
    payload: SKUCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> SKUResponse:
    """Create a new SKU under the tenant organization."""
    return await CatalogService.create_sku(
        db=db,
        tenant_id=tenant_id,
        payload=payload,
    )


@products_router.get(
    "/skus/{id}",
    response_model=SKUResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single SKU details",
)
async def get_sku(
    id: UUID,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> SKUResponse:
    """Retrieve detailed SKU attributes by primary key."""
    return await CatalogService.get_sku_by_id(
        db=db,
        tenant_id=tenant_id,
        sku_id=id,
    )


@products_router.put(
    "/skus/{id}",
    response_model=SKUResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(CATALOG_WRITE_ROLES))],
    summary="Update SKU variant details",
)
async def update_sku(
    id: UUID,
    payload: SKUUpdate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> SKUResponse:
    """Update editable attributes of an existing SKU."""
    return await CatalogService.update_sku(
        db=db,
        tenant_id=tenant_id,
        sku_id=id,
        payload=payload,
    )


# --- Categories ---
@products_router.get(
    "/categories",
    response_model=list[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all product categories",
)
async def list_categories(
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> list[CategoryResponse]:
    """Retrieve all hierarchical product categories for the tenant."""
    categories = await CatalogService.list_categories(db=db, tenant_id=tenant_id)
    return [CategoryResponse.model_validate(cat) for cat in categories]


@products_router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(CATALOG_WRITE_ROLES))],
    summary="Create a product category",
)
async def create_category(
    payload: CategoryCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> CategoryResponse:
    """Create a new product category."""
    category = await CatalogService.create_category(
        db=db,
        tenant_id=tenant_id,
        payload=payload,
    )
    return CategoryResponse.model_validate(category)


# --- Products ---
@products_router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(CATALOG_WRITE_ROLES))],
    summary="Create a product master record",
)
async def create_product(
    payload: ProductCreate,
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
) -> ProductResponse:
    """Create a product record grouping SKUs."""
    product = await CatalogService.create_product(
        db=db,
        tenant_id=tenant_id,
        payload=payload,
    )
    return ProductResponse.model_validate(product)
