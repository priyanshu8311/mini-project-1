"""create inventory ledger, purchasing, forecasting, and integration tables

Revision ID: 003_inventory_ledger_tables
Revises: 002_catalog_locations
Create Date: 2026-10-18 12:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_inventory_ledger_tables"
down_revision: str | None = "002_catalog_locations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create inventory_levels table
    op.create_table(
        "inventory_levels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("on_hand", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available",
            sa.Integer(),
            sa.Computed("on_hand - reserved", persisted=True),
            nullable=False,
        ),
        sa.Column("reorder_point", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reorder_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_inventory_levels_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["skus.id"],
            name="fk_inventory_levels_sku_id_skus",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_inventory_levels_location_id_locations",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "sku_id",
            "location_id",
            name="uq_inventory_levels_tenant_sku_loc",
        ),
        sa.CheckConstraint(
            "on_hand >= 0",
            name="ck_inventory_levels_on_hand_non_negative",
        ),
        sa.CheckConstraint(
            "reserved >= 0",
            name="ck_inventory_levels_reserved_non_negative",
        ),
    )
    op.create_index(
        "ix_inventory_levels_tenant_id",
        "inventory_levels",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "idx_inv_levels_tenant_sku",
        "inventory_levels",
        ["tenant_id", "sku_id"],
        unique=False,
    )
    op.create_index(
        "idx_inv_levels_tenant_loc",
        "inventory_levels",
        ["tenant_id", "location_id"],
        unique=False,
    )

    # 2. Create inventory_transactions table (Ledger)
    op.create_table(
        "inventory_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transaction_type", sa.String(length=50), nullable=False),
        sa.Column("quantity_change", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_inventory_transactions_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["skus.id"],
            name="fk_inventory_transactions_sku_id_skus",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_inventory_transactions_location_id_locations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_inventory_transactions_user_id_users",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "quantity_change != 0",
            name="ck_inventory_transactions_qty_not_zero",
        ),
    )
    op.create_index(
        "ix_inventory_transactions_tenant_id",
        "inventory_transactions",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "idx_inv_tx_created",
        "inventory_transactions",
        ["tenant_id", "sku_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_inv_tx_tenant_loc",
        "inventory_transactions",
        ["tenant_id", "location_id"],
        unique=False,
    )

    # 3. Create purchase_orders table
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="Draft"),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_purchase_orders_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_purchase_orders_tenant_id",
        "purchase_orders",
        ["tenant_id"],
        unique=False,
    )

    # 4. Create po_items table
    op.create_table(
        "po_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("po_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity_ordered", sa.Integer(), nullable=False),
        sa.Column("quantity_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "unit_cost",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["po_id"],
            ["purchase_orders.id"],
            name="fk_po_items_po_id_purchase_orders",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["skus.id"],
            name="fk_po_items_sku_id_skus",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "quantity_received <= quantity_ordered",
            name="ck_po_items_received_le_ordered",
        ),
    )
    op.create_index(
        "ix_po_items_po_id",
        "po_items",
        ["po_id"],
        unique=False,
    )

    # 5. Create sales_history table
    op.create_table(
        "sales_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("location_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sales_date", sa.Date(), nullable=False),
        sa.Column("quantity_sold", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_sales_history_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["skus.id"],
            name="fk_sales_history_sku_id_skus",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            name="fk_sales_history_location_id_locations",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_sales_history_ml",
        "sales_history",
        ["tenant_id", "sku_id", "sales_date"],
        unique=False,
    )

    # 6. Create demand_forecasts table
    op.create_table(
        "demand_forecasts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("predicted_demand", sa.Integer(), nullable=False),
        sa.Column("confidence_lower", sa.Integer(), nullable=False),
        sa.Column("confidence_upper", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_demand_forecasts_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sku_id"],
            ["skus.id"],
            name="fk_demand_forecasts_sku_id_skus",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "idx_demand_forecasts_sku_date",
        "demand_forecasts",
        ["tenant_id", "sku_id", "forecast_date"],
        unique=False,
    )

    # 7. Create integration_configs table
    op.create_table(
        "integration_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_integration_configs_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "provider",
            name="uq_integration_configs_tenant_provider",
        ),
    )
    op.create_index(
        "ix_integration_configs_tenant_id",
        "integration_configs",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("integration_configs")
    op.drop_table("demand_forecasts")
    op.drop_table("sales_history")
    op.drop_table("po_items")
    op.drop_table("purchase_orders")
    op.drop_table("inventory_transactions")
    op.drop_table("inventory_levels")
