import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.core.database import BaseModel

if TYPE_CHECKING:
    from backend.src.domain.inventory.models import SKU


class OrderStatus(enum.StrEnum):
    """Lifecycle statuses for a purchase order."""

    DRAFT = "Draft"
    SENT = "Sent"
    PARTIALLY_RECEIVED = "Partially Received"
    COMPLETED = "Completed"


class PurchaseOrder(BaseModel):
    """Purchase order issued to a supplier."""

    __tablename__ = "purchase_orders"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=OrderStatus.DRAFT.value,
    )
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    items: Mapped[list["POItem"]] = relationship(
        "POItem",
        back_populates="purchase_order",
        cascade="all, delete-orphan",
    )


class POItem(BaseModel):
    """Line item within a purchase order."""

    __tablename__ = "po_items"

    po_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skus.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity_ordered: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship(
        "PurchaseOrder",
        back_populates="items",
    )
    sku: Mapped["SKU"] = relationship("SKU")

    __table_args__ = (
        CheckConstraint(
            "quantity_received <= quantity_ordered",
            name="ck_po_items_received_le_ordered",
        ),
    )
