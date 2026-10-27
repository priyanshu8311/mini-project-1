import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.src.domain.inventory.schemas import PaginationMeta
from backend.src.domain.purchasing.models import OrderStatus


class POItemCreate(BaseModel):
    """Line item creation payload for a purchase order."""

    sku_id: UUID
    quantity_ordered: int = Field(..., gt=0, description="Quantity to order (must be positive)")
    unit_cost: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Negotiated purchase unit cost",
    )


class POItemResponse(BaseModel):
    """Line item representation returned to clients."""

    id: UUID
    po_id: UUID
    sku_id: UUID
    quantity_ordered: int
    quantity_received: int
    unit_cost: Decimal
    created_at: datetime
    sku_code: str | None = None
    product_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PurchaseOrderCreate(BaseModel):
    """Payload to create a new purchase order."""

    supplier_id: UUID | None = Field(default=None, description="Optional supplier UUID")
    expected_date: date | None = Field(default=None, description="Expected delivery date")
    items: list[POItemCreate] = Field(
        ...,
        min_length=1,
        description="Line items for this purchase order",
    )


class PurchaseOrderUpdate(BaseModel):
    """Payload to update an existing purchase order."""

    supplier_id: UUID | None = None
    status: OrderStatus | None = None
    expected_date: date | None = None


class POReceiveItem(BaseModel):
    """Quantity to receive for a specific purchase order line item."""

    po_item_id: UUID
    quantity_to_receive: int = Field(
        ...,
        gt=0,
        description="Quantity received in this shipment",
    )


class POReceiveRequest(BaseModel):
    """Payload to record receipt of purchase order goods into inventory."""

    location_id: UUID = Field(
        ...,
        description="Destination warehouse or store location receiving the stock",
    )
    items: list[POReceiveItem] = Field(
        ...,
        min_length=1,
        description="List of line items and quantities being received",
    )


class PurchaseOrderResponse(BaseModel):
    """Full purchase order response including line items."""

    id: UUID
    tenant_id: UUID
    supplier_id: UUID | None
    status: str
    expected_date: date | None
    created_at: datetime
    items: list[POItemResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PaginatedPurchaseOrdersResponse(BaseModel):
    """Paginated purchase orders envelope."""

    data: list[PurchaseOrderResponse]
    meta: PaginationMeta


class UrgencyLevel(enum.StrEnum):
    """Urgency level for automated purchase recommendations."""

    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class PurchasingSuggestionItem(BaseModel):
    """Automated reorder recommendation based on safety stock and demand forecasts."""

    sku_id: UUID
    sku_code: str
    product_name: str | None = None
    location_id: UUID | None = None
    location_name: str | None = None
    current_on_hand: int
    reorder_point: int
    lead_time_days: int
    suggested_reorder_quantity: int
    unit_cost: Decimal
    supplier_id: UUID | None = None
    urgency: UrgencyLevel
