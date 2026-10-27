from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from backend.src.domain.inventory.schemas import PaginationMeta


class SalesHistoryRecordCreate(BaseModel):
    """Payload to record historical sales volume."""

    sku_id: UUID
    location_id: UUID
    sales_date: date
    quantity_sold: int = Field(..., ge=0, description="Number of units sold")
    channel: str = Field(default="Direct", max_length=50, description="Sales channel e.g. Shopify, POS, Direct")


class SalesHistoryRecordResponse(BaseModel):
    """Historical sales record output."""

    id: UUID
    tenant_id: UUID
    sku_id: UUID
    location_id: UUID
    sales_date: date
    quantity_sold: int
    channel: str
    created_at: datetime
    sku_code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class DemandForecastResponse(BaseModel):
    """Individual SKU demand forecast prediction."""

    id: UUID
    tenant_id: UUID
    sku_id: UUID
    forecast_date: date
    predicted_demand: int
    confidence_lower: int
    confidence_upper: int
    generated_at: datetime
    sku_code: str | None = None
    product_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedDemandForecastsResponse(BaseModel):
    """Paginated demand forecasts envelope."""

    data: list[DemandForecastResponse]
    meta: PaginationMeta


class ForecastRunRequest(BaseModel):
    """Payload to trigger a batch forecasting run."""

    sku_ids: list[UUID] | None = Field(
        default=None,
        description="Optional list of specific SKU IDs to forecast. If empty, forecasts all active tenant SKUs.",
    )
    horizon_days: int = Field(
        default=30,
        ge=1,
        le=90,
        description="Forecast horizon in days (default 30, max 90)",
    )


class ForecastJobResponse(BaseModel):
    """Result of an ML forecast batch run."""

    job_id: str
    status: str
    total_skus_processed: int
    generated_forecasts_count: int
    message: str
    mape: float | None = None


class ReorderRecommendation(BaseModel):
    """ML-driven inventory replenishment recommendation."""

    sku_id: UUID
    sku_code: str
    product_name: str | None = None
    current_stock: int
    predicted_daily_demand: float
    lead_time_days: int
    suggested_reorder_point: int
    suggested_order_qty: int
    days_of_supply: float
    urgency: str
