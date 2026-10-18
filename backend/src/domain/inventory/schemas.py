from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.src.domain.inventory.models import LocationType, TransactionType


class PaginationMeta(BaseModel):
    """Pagination metadata conforming to API.md."""

    total: int
    page: int
    limit: int
    total_pages: int


class PaginatedResponse[T](BaseModel):
    """Standardized list envelope conforming to API.md."""

    data: list[T]
    meta: PaginationMeta


# --- Categories ---
class CategoryCreate(BaseModel):
    """Payload to create a product category."""

    name: str = Field(..., min_length=2, max_length=255)
    parent_id: UUID | None = None


class CategoryResponse(BaseModel):
    """Category detail response."""

    id: UUID
    tenant_id: UUID
    parent_id: UUID | None
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Products ---
class ProductCreate(BaseModel):
    """Payload to create a parent product."""

    category_id: UUID
    name: str = Field(..., min_length=2, max_length=255)
    description: str | None = None
    base_unit: str = Field(default="piece", max_length=50)


class ProductResponse(BaseModel):
    """Product master record response."""

    id: UUID
    tenant_id: UUID
    category_id: UUID
    name: str
    description: str | None
    base_unit: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- SKUs ---
class SKUCreate(BaseModel):
    """Payload to create a SKU variant."""

    sku_code: str = Field(..., min_length=2, max_length=100, description="Unique SKU code")
    product_id: UUID | None = Field(
        default=None,
        description="ID of existing product if linking to one",
    )
    product_name: str | None = Field(
        default=None,
        description="Name of product if creating product inline with SKU",
    )
    category_id: UUID | None = Field(
        default=None,
        description="Category ID if creating product inline with SKU",
    )
    supplier_id: UUID | None = None
    unit_cost: Decimal = Field(
        default=Decimal("0.00"), ge=0, description="Unit cost in base currency"
    )
    sales_price: Decimal = Field(default=Decimal("0.00"), ge=0, description="Selling price")
    lead_time_days: int = Field(default=7, ge=0, description="Supplier lead time in days")


class SKUUpdate(BaseModel):
    """Payload to update an existing SKU."""

    sku_code: str | None = Field(default=None, min_length=2, max_length=100)
    supplier_id: UUID | None = None
    unit_cost: Decimal | None = Field(default=None, ge=0)
    sales_price: Decimal | None = Field(default=None, ge=0)
    lead_time_days: int | None = Field(default=None, ge=0)


class SKUResponse(BaseModel):
    """SKU variant detail response."""

    id: UUID
    tenant_id: UUID
    product_id: UUID
    sku_code: str
    supplier_id: UUID | None
    unit_cost: Decimal
    sales_price: Decimal
    lead_time_days: int
    created_at: datetime
    product_name: str | None = None
    category_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Locations ---
class LocationCreate(BaseModel):
    """Payload to create an inventory physical location."""

    name: str = Field(..., min_length=2, max_length=255)
    type: LocationType = LocationType.WAREHOUSE
    address: str | None = None


class LocationResponse(BaseModel):
    """Location record response."""

    id: UUID
    tenant_id: UUID
    name: str
    type: str
    address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Inventory Levels & Transactions (Ledger) ---
class InventoryLevelResponse(BaseModel):
    """Snapshot of stock on hand, reserved, and available per SKU and location."""

    id: UUID
    tenant_id: UUID
    sku_id: UUID
    location_id: UUID
    on_hand: int
    reserved: int
    available: int
    reorder_point: int
    reorder_quantity: int
    version: int
    created_at: datetime
    sku_code: str | None = None
    product_name: str | None = None
    location_name: str | None = None
    location_type: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InventoryTransactionCreate(BaseModel):
    """Payload to record an atomic inventory ledger transaction."""

    transaction_type: TransactionType
    sku_id: UUID
    location_id: UUID
    target_location_id: UUID | None = Field(
        default=None,
        description="Required destination location when transaction_type is Transfer",
    )
    quantity_change: int = Field(
        ...,
        description="Stock adjustment quantity. Must be non-zero.",
    )
    reference_id: str | None = Field(
        default=None,
        max_length=100,
        description="Reference identifier e.g. PO #, Sales Order #, RMA #",
    )
    reason: str | None = Field(
        default=None,
        max_length=255,
        description="Audit memo / reason for stock modification",
    )


class InventoryTransactionResponse(BaseModel):
    """Immutable ledger record representing an inventory adjustment."""

    id: UUID
    tenant_id: UUID
    sku_id: UUID
    location_id: UUID
    user_id: UUID
    transaction_type: str
    quantity_change: int
    reference_id: str | None
    reason: str | None
    created_at: datetime
    sku_code: str | None = None
    product_name: str | None = None
    location_name: str | None = None
    user_email: str | None = None

    model_config = ConfigDict(from_attributes=True)

