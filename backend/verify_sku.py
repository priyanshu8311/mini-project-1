import asyncio
from backend.src.core.database import AsyncSessionLocal
from backend.src.domain.inventory.service import CatalogService
from backend.src.domain.inventory.schemas import SKUCreate
from backend.src.domain.users.models import Organization
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as session:
        # Get first tenant
        r = await session.execute(select(Organization))
        org = r.scalars().first()
        if not org:
            print("No organization found")
            return
        print(f"Testing for org: {org.name} ({org.id})")
        
        # Test creating SKU with product_name and NO category_id
        payload = SKUCreate(
            sku_code="TEST-BULB-001",
            product_name="LED Bulb Test",
            category_id=None,
            unit_cost=9.98,
            sales_price=11.98,
            lead_time_days=5
        )
        try:
            sku = await CatalogService.create_sku(session, org.id, payload)
            await session.commit()
            print(f"SUCCESS! SKU created: {sku.sku_code}, ID: {sku.id}, Product ID: {sku.product_id}")
        except Exception as e:
            print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
