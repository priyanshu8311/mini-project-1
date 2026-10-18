import enum
import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.src.core.database import BaseModel


class UserRole(enum.StrEnum):
    """System roles defined in PRD and DATABASE.md."""

    ADMIN = "Admin"
    INVENTORY_MANAGER = "Inventory Manager"
    PURCHASER = "Purchaser"
    WAREHOUSE_STAFF = "Warehouse Staff"
    ANALYST = "Analyst"
    VIEWER = "Viewer"


class Tenant(BaseModel):
    """Tenant model for multi-tenant data isolation."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class User(BaseModel):
    """User identity and authorization model."""

    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.VIEWER.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")

    # Constraints
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_users_tenant_id_email"),)
