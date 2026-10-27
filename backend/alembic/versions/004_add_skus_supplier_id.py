"""add supplier_id to skus table

Revision ID: 004_skus_supplier_id
Revises: 003_inventory_ledger_tables
Create Date: 2026-10-21 07:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_skus_supplier_id"
down_revision: str | None = "003_inventory_ledger_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "skus",
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("skus", "supplier_id")
