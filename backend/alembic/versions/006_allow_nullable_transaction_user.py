"""006_allow_nullable_transaction_user

Revision ID: 006_nullable_tx_user
Revises: 005_schemas_and_indexes
Create Date: 2026-11-17 14:30:00.000000

"""

from collections.abc import Sequence

from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_nullable_tx_user"
down_revision: str | Sequence[str] | None = "005_schemas_and_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow user_id in inventory_transactions to be nullable with ondelete SET NULL."""
    # Drop existing foreign key constraint if exists
    try:
        op.drop_constraint(
            "fk_inventory_transactions_user_id_users",
            "inventory_transactions",
            type_="foreignkey",
        )
    except Exception:
        pass

    # Alter column to be nullable
    op.alter_column(
        "inventory_transactions",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Recreate foreign key with ondelete SET NULL
    op.create_foreign_key(
        "fk_inventory_transactions_user_id_users",
        "inventory_transactions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Revert user_id to NOT NULL with ondelete RESTRICT."""
    op.drop_constraint(
        "fk_inventory_transactions_user_id_users",
        "inventory_transactions",
        type_="foreignkey",
    )
    op.alter_column(
        "inventory_transactions",
        "user_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_foreign_key(
        "fk_inventory_transactions_user_id_users",
        "inventory_transactions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
