import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShopifyConfigBase(BaseModel):
    """Base schema for Shopify store integration configuration."""

    shop_domain: str = Field(
        ...,
        description="Shopify store domain (e.g. my-store.myshopify.com)",
        examples=["my-store.myshopify.com"],
    )
    shopify_location_id: str | None = Field(
        default=None,
        description="Shopify primary fulfillment location ID",
    )
    default_location_id: UUID | None = Field(
        default=None,
        description="Local system location ID to sync stock from and record orders to",
    )
    auto_sync_stock: bool = Field(
        default=True,
        description="Whether to push real-time stock updates to Shopify",
    )
    webhook_secret: str | None = Field(
        default=None,
        description="Optional dedicated webhook signing secret",
    )

    @field_validator("shop_domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        clean = v.strip().lower()
        # Strip https:// or http:// if user pasted full URL
        clean = re.sub(r"^https?://", "", clean).rstrip("/")
        if not re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+$", clean):
            raise ValueError("Invalid shop domain format. Expected e.g. store.myshopify.com")
        return clean


class ShopifyConfigCreate(ShopifyConfigBase):
    """Payload to configure or update Shopify credentials."""

    access_token: str = Field(
        ...,
        min_length=10,
        description="Shopify Admin API private access token (e.g. shpat_...)",
    )


class ShopifyConfigUpdate(BaseModel):
    """Partial update payload for Shopify integration settings."""

    shop_domain: str | None = None
    access_token: str | None = Field(default=None, min_length=10)
    shopify_location_id: str | None = None
    default_location_id: UUID | None = None
    auto_sync_stock: bool | None = None
    webhook_secret: str | None = None

    @field_validator("shop_domain")
    @classmethod
    def validate_domain(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean = v.strip().lower()
        clean = re.sub(r"^https?://", "", clean).rstrip("/")
        if not re.match(r"^[a-zA-Z0-9][-a-zA-Z0-9]*(\.[a-zA-Z0-9][-a-zA-Z0-9]*)+$", clean):
            raise ValueError("Invalid shop domain format. Expected e.g. store.myshopify.com")
        return clean


class ShopifyConfigResponse(BaseModel):
    """Response schema for Shopify store integration settings (never exposes plain access token)."""

    id: UUID
    tenant_id: UUID
    provider: str = "shopify"
    shop_domain: str
    shopify_location_id: str | None = None
    default_location_id: UUID | None = None
    auto_sync_stock: bool = True
    has_webhook_secret: bool = False
    is_active: bool = True
    masked_access_token: str
    last_sync_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShopifyConnectionTestResponse(BaseModel):
    """Response payload when testing Shopify connectivity."""

    success: bool
    shop_name: str | None = None
    shop_domain: str | None = None
    currency: str | None = None
    message: str


class ShopifySyncStockRequest(BaseModel):
    """Payload to trigger a manual or automated inventory level push to Shopify."""

    sku_id: UUID
    location_id: UUID | None = None
    shopify_inventory_item_id: int | None = Field(
        default=None,
        description="Optional explicit Shopify inventory item ID (overrides SKU metadata)",
    )


class ShopifySyncStockResponse(BaseModel):
    """Response payload from stock synchronization operation."""

    success: bool
    sku_code: str
    on_hand: int
    available: int
    shopify_inventory_item_id: int
    synced_at: datetime
    message: str


class ShopifyOrderLineItem(BaseModel):
    """Single item in a Shopify order webhook payload."""

    id: int
    sku: str | None = None
    quantity: int = 1
    title: str | None = None
    variant_id: int | None = None
    name: str | None = None


class ShopifyOrderWebhookPayload(BaseModel):
    """Shopify orders/create and orders/paid webhook payload structure."""

    id: int
    name: str | None = None  # e.g., "#1001"
    order_number: int | None = None
    financial_status: str | None = None
    fulfillment_status: str | None = None
    line_items: list[ShopifyOrderLineItem] = []
    created_at: str | None = None

    model_config = ConfigDict(extra="ignore")


class ShopifyWebhookProcessResult(BaseModel):
    """Result summary of webhook consumption."""

    status: str
    order_id: int
    order_number: str | None = None
    processed_items: int
    deduplicated: bool = False
    details: list[dict] = []
