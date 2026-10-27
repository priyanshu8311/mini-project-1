"""create catalog and locations tables

Revision ID: 002_catalog_locations
Revises: 001_auth_tables
Create Date: 2026-10-18 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_catalog_locations"
down_revision: str | None = "001_auth_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create categories table
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_categories_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name="fk_categories_parent_id_categories",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_categories_tenant_id", "categories", ["tenant_id"], unique=False)

    # 2. Create products table
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_unit", sa.String(length=50), nullable=False, server_default="piece"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_products_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_products_category_id_categories",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"], unique=False)
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)

    # 3. Create skus table
    op.create_table(
        "skus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku_code", sa.String(length=100), nullable=False),
        sa.Column(
            "unit_cost", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"
        ),
        sa.Column(
            "sales_price", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"
        ),
        sa.Column("lead_time_days", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_skus_tenant_id_tenants",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_skus_product_id_products",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("tenant_id", "sku_code", name="uq_skus_tenant_id_sku_code"),
    )
    op.create_index("ix_skus_tenant_id", "skus", ["tenant_id"], unique=False)
    op.create_index("ix_skus_product_id", "skus", ["product_id"], unique=False)
    op.create_index("idx_sku_code", "skus", ["tenant_id", "sku_code"], unique=False)

    # 4. Create locations table
    op.create_table(
        "locations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False, server_default="Warehouse"),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_locations_tenant_id_tenants",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_locations_tenant_id", "locations", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_table("locations")
    op.drop_index("idx_sku_code", table_name="skus")
    op.drop_table("skus")
    op.drop_table("products")
    op.drop_table("categories")
