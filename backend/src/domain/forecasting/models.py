import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.core.database import BaseModel

if TYPE_CHECKING:
    from backend.src.domain.inventory.models import SKU, Location


class SalesHistory(BaseModel):
    """Historical sales time-series used for training demand forecasting models."""

    __tablename__ = "sales_history"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sales_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU")
    location: Mapped["Location"] = relationship("Location")

    __table_args__ = (Index("idx_sales_history_ml", "tenant_id", "sku_id", "sales_date"),)


class DemandForecast(BaseModel):
    """Machine learning demand predictions output by Prophet / XGBoost pipeline."""

    __tablename__ = "demand_forecasts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_demand: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_lower: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_upper: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU")

    __table_args__ = (
        Index("idx_demand_forecasts_sku_date", "tenant_id", "sku_id", "forecast_date"),
    )
