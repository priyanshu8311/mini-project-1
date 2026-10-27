"""005_sync_schemas_and_indexes

Revision ID: 005_schemas_and_indexes
Revises: 004_skus_supplier_id
Create Date: 2026-10-27 08:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_schemas_and_indexes"
down_revision: str | Sequence[str] | None = "004_skus_supplier_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "categories",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "demand_forecasts",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.create_index(op.f("ix_demand_forecasts_sku_id"), "demand_forecasts", ["sku_id"], unique=False)
    op.create_index(op.f("ix_demand_forecasts_tenant_id"), "demand_forecasts", ["tenant_id"], unique=False)
    op.alter_column(
        "integration_configs",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "inventory_levels",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.create_index(op.f("ix_inventory_levels_location_id"), "inventory_levels", ["location_id"], unique=False)
    op.create_index(op.f("ix_inventory_levels_sku_id"), "inventory_levels", ["sku_id"], unique=False)
    op.alter_column(
        "inventory_transactions",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.create_index(op.f("ix_inventory_transactions_location_id"), "inventory_transactions", ["location_id"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_sku_id"), "inventory_transactions", ["sku_id"], unique=False)
    op.create_index(op.f("ix_inventory_transactions_user_id"), "inventory_transactions", ["user_id"], unique=False)
    op.alter_column(
        "locations",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "po_items",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.create_index(op.f("ix_po_items_sku_id"), "po_items", ["sku_id"], unique=False)
    op.alter_column(
        "products",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "purchase_orders",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "sales_history",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.create_index(op.f("ix_sales_history_location_id"), "sales_history", ["location_id"], unique=False)
    op.create_index(op.f("ix_sales_history_sku_id"), "sales_history", ["sku_id"], unique=False)
    op.create_index(op.f("ix_sales_history_tenant_id"), "sales_history", ["tenant_id"], unique=False)
    op.alter_column(
        "skus",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "tenants",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "tenants",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "skus",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_sales_history_tenant_id"), table_name="sales_history")
    op.drop_index(op.f("ix_sales_history_sku_id"), table_name="sales_history")
    op.drop_index(op.f("ix_sales_history_location_id"), table_name="sales_history")
    op.alter_column(
        "sales_history",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "purchase_orders",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "products",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_po_items_sku_id"), table_name="po_items")
    op.alter_column(
        "po_items",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "locations",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_inventory_transactions_user_id"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_sku_id"), table_name="inventory_transactions")
    op.drop_index(op.f("ix_inventory_transactions_location_id"), table_name="inventory_transactions")
    op.alter_column(
        "inventory_transactions",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_inventory_levels_sku_id"), table_name="inventory_levels")
    op.drop_index(op.f("ix_inventory_levels_location_id"), table_name="inventory_levels")
    op.alter_column(
        "inventory_levels",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "integration_configs",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_demand_forecasts_tenant_id"), table_name="demand_forecasts")
    op.drop_index(op.f("ix_demand_forecasts_sku_id"), table_name="demand_forecasts")
    op.alter_column(
        "demand_forecasts",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "categories",
        "created_at",
        existing_type=sa.DateTime(),
        type_=postgresql.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
