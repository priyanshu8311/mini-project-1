import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.core.database import BaseModel

if TYPE_CHECKING:
    from backend.src.domain.users.models import User


class LocationType(enum.StrEnum):
    """Types of physical inventory locations."""

    WAREHOUSE = "Warehouse"
    STORE = "Store"


class Category(BaseModel):
    """Hierarchical product category model."""

    __tablename__ = "categories"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="subcategories",
    )
    subcategories: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="category",
    )


class Product(BaseModel):
    """Product master record grouping variants/SKUs."""

    __tablename__ = "products"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_unit: Mapped[str] = mapped_column(String(50), nullable=False, default="piece")

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="products")
    skus: Mapped[list["SKU"]] = relationship(
        "SKU",
        back_populates="product",
        cascade="all, delete-orphan",
    )


class SKU(BaseModel):
    """Stock Keeping Unit (SKU) representing a specific product variant."""

    __tablename__ = "skus"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sku_code: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    unit_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    sales_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="skus")

    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint("tenant_id", "sku_code", name="uq_skus_tenant_id_sku_code"),
        Index("idx_sku_code", "tenant_id", "sku_code"),
    )


class Location(BaseModel):
    """Physical inventory location: warehouse or store."""

    __tablename__ = "locations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=LocationType.WAREHOUSE.value,
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)


class TransactionType(enum.StrEnum):
    """Supported inventory ledger transaction types."""

    RECEIVE = "Receive"
    SHIP = "Ship"
    ADJUST = "Adjust"
    TRANSFER = "Transfer"


class InventoryLevel(BaseModel):
    """Current stock snapshot per SKU and location."""

    __tablename__ = "inventory_levels"

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
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available: Mapped[int] = mapped_column(
        Integer,
        Computed("on_hand - reserved", persisted=True),
    )
    reorder_point: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reorder_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU")
    location: Mapped["Location"] = relationship("Location")

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "sku_id",
            "location_id",
            name="uq_inventory_levels_tenant_sku_loc",
        ),
        CheckConstraint("on_hand >= 0", name="ck_inventory_levels_on_hand_non_negative"),
        CheckConstraint("reserved >= 0", name="ck_inventory_levels_reserved_non_negative"),
        Index("idx_inv_levels_tenant_sku", "tenant_id", "sku_id"),
        Index("idx_inv_levels_tenant_loc", "tenant_id", "location_id"),
    )


class InventoryTransaction(BaseModel):
    """Append-only audit ledger recording every inventory quantity change."""

    __tablename__ = "inventory_transactions"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    sku: Mapped["SKU"] = relationship("SKU")
    location: Mapped["Location"] = relationship("Location")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "quantity_change != 0",
            name="ck_inventory_transactions_qty_not_zero",
        ),
        Index("idx_inv_tx_created", "tenant_id", "sku_id", "created_at"),
        Index("idx_inv_tx_tenant_loc", "tenant_id", "location_id"),
    )

