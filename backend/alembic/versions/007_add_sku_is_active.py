"""007_add_sku_is_active

Revision ID: 007_add_sku_is_active
Revises: 006_nullable_tx_user
Create Date: 2026-11-17 19:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_add_sku_is_active"
down_revision: str | Sequence[str] | None = "006_nullable_tx_user"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add is_active boolean column with default True to skus table."""
    op.add_column(
        "skus",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    """Remove is_active column from skus table."""
    op.drop_column("skus", "is_active")
