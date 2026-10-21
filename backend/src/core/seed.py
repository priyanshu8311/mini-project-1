# ruff: noqa: E402
"""Database seeding script for initializing demo tenant, roles, catalog, and inventory ledger."""

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# Ensure project root and backend dir are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from backend.src.core.database import AsyncSessionLocal, Base, engine
from backend.src.core.security import hash_password
from backend.src.domain.inventory.models import (
    SKU,
    Category,
    InventoryTransaction,
    Location,
    LocationType,
    TransactionType,
)
from backend.src.domain.inventory.schemas import (
    CategoryCreate,
    InventoryTransactionCreate,
    LocationCreate,
    SKUCreate,
)
from backend.src.domain.inventory.service import CatalogService, InventoryService
from backend.src.domain.users.models import Tenant, User, UserRole


async def seed_database() -> None:
    """Seed initial development data into the database."""
    # Ensure tables exist in database before seeding
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # 1. Check or create demo tenant
        tenant_res = await db.execute(
            select(Tenant).where(Tenant.name == "Demo Enterprise Corp")
        )
        tenant = tenant_res.scalar_one_or_none()
        if not tenant:
            tenant = Tenant(name="Demo Enterprise Corp")
            db.add(tenant)
            await db.flush()
            await db.refresh(tenant)
            print(f"[OK] Created Demo Tenant: {tenant.name} ({tenant.id})")
        else:
            print(f"[*] Demo Tenant already exists: {tenant.name} ({tenant.id})")

        # 2. Check or create users
        users_config = [
            ("admin@demo.com", "AdminPassword123!", UserRole.ADMIN.value),
            ("manager@demo.com", "ManagerPassword123!", UserRole.INVENTORY_MANAGER.value),
            ("staff@demo.com", "StaffPassword123!", UserRole.WAREHOUSE_STAFF.value),
            ("viewer@demo.com", "ViewerPassword123!", UserRole.VIEWER.value),
        ]
        created_users: dict[str, User] = {}
        for email, password, role in users_config:
            user_res = await db.execute(
                select(User).where(User.tenant_id == tenant.id, User.email == email)
            )
            user = user_res.scalar_one_or_none()
            if not user:
                user = User(
                    tenant_id=tenant.id,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    is_active=True,
                )
                db.add(user)
                await db.flush()
                await db.refresh(user)
                print(f"[OK] Created User: {email} [{role}]")
            else:
                print(f"[*] User already exists: {email} [{role}]")
            created_users[role] = user

        # 3. Check or create locations
        loc_res = await db.execute(select(Location).where(Location.tenant_id == tenant.id))
        existing_locs = {loc.name: loc for loc in loc_res.scalars().all()}

        if "Main Distribution Center" in existing_locs:
            wh = existing_locs["Main Distribution Center"]
        else:
            wh = await CatalogService.create_location(
                db,
                tenant.id,
                LocationCreate(
                    name="Main Distribution Center",
                    type=LocationType.WAREHOUSE,
                    address="100 Logistics Blvd, Dock 4",
                ),
            )
        if "Retail Store Downtown" in existing_locs:
            store = existing_locs["Retail Store Downtown"]
        else:
            store = await CatalogService.create_location(
                db,
                tenant.id,
                LocationCreate(
                    name="Retail Store Downtown",
                    type=LocationType.STORE,
                    address="450 Main Street, Suite 10",
                ),
            )
        print(f"[OK] Locations configured: {wh.name}, {store.name}")

        # 4. Check or create Category & SKUs
        cat_res = await db.execute(
            select(Category).where(
                Category.tenant_id == tenant.id,
                Category.name == "Consumer Electronics",
            )
        )
        cat = cat_res.scalar_one_or_none()
        if not cat:
            cat = await CatalogService.create_category(
                db,
                tenant.id,
                CategoryCreate(name="Consumer Electronics"),
            )
            print(f"[OK] Created Category: {cat.name}")
        else:
            print(f"[*] Category already exists: {cat.name}")

        sku_res = await db.execute(select(SKU).where(SKU.tenant_id == tenant.id))
        existing_skus = {s.sku_code: s for s in sku_res.scalars().all()}

        if "ELEC-WIDG-001" not in existing_skus:
            sku1 = await CatalogService.create_sku(
                db,
                tenant.id,
                SKUCreate(
                    sku_code="ELEC-WIDG-001",
                    product_name="Pro Wireless Mouse",
                    category_id=cat.id,
                    unit_cost=Decimal("25.00"),
                    sales_price=Decimal("49.99"),
                    lead_time_days=5,
                ),
            )
        else:
            sku1 = existing_skus["ELEC-WIDG-001"]

        if "ELEC-KEYB-002" not in existing_skus:
            sku2 = await CatalogService.create_sku(
                db,
                tenant.id,
                SKUCreate(
                    sku_code="ELEC-KEYB-002",
                    product_name="Mechanical RGB Keyboard",
                    category_id=cat.id,
                    unit_cost=Decimal("45.00"),
                    sales_price=Decimal("89.99"),
                    lead_time_days=7,
                ),
            )
        else:
            sku2 = existing_skus["ELEC-KEYB-002"]
        print(f"[OK] SKUs configured: {sku1.sku_code}, {sku2.sku_code}")

        # 5. Seed Initial Ledger Transactions (Establish initial balances if not already present)
        tx_check = await db.execute(
            select(InventoryTransaction).where(InventoryTransaction.tenant_id == tenant.id)
        )
        if not tx_check.scalars().first():
            admin_user = created_users[UserRole.ADMIN.value]

            # Receive stock at warehouse
            await InventoryService.record_transaction(
                db,
                tenant.id,
                admin_user.id,
                InventoryTransactionCreate(
                    transaction_type=TransactionType.RECEIVE,
                    sku_id=sku1.id,
                    location_id=wh.id,
                    quantity_change=100,
                    reference_id="PO-INIT-001",
                    reason="Initial inventory seed into warehouse",
                ),
            )
            await InventoryService.record_transaction(
                db,
                tenant.id,
                admin_user.id,
                InventoryTransactionCreate(
                    transaction_type=TransactionType.RECEIVE,
                    sku_id=sku2.id,
                    location_id=wh.id,
                    quantity_change=50,
                    reference_id="PO-INIT-002",
                    reason="Initial inventory seed into warehouse",
                ),
            )

            # Transfer a portion to downtown store
            await InventoryService.record_transaction(
                db,
                tenant.id,
                admin_user.id,
                InventoryTransactionCreate(
                    transaction_type=TransactionType.TRANSFER,
                    sku_id=sku1.id,
                    location_id=wh.id,
                    target_location_id=store.id,
                    quantity_change=25,
                    reference_id="TRF-INIT-001",
                    reason="Store opening inventory transfer",
                ),
            )
            print("[OK] Recorded initial ledger transactions (Receive + Transfer)")
        else:
            print("[*] Ledger transactions already exist; skipping duplicate seed.")

        await db.commit()
        print("[SUCCESS] Database seeding completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_database())
