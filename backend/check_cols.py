import asyncio
from backend.src.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'skus'")
        )
        cols = [r[0] for r in result.fetchall()]
        print("SKUS COLUMNS:", cols)

if __name__ == "__main__":
    asyncio.run(check())
