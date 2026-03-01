import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    url = os.getenv("DATABASE_URL")
    print(f"Connecting to {url}")
    pool = await asyncpg.create_pool(url)
    async with pool.acquire() as conn:
        # Drop constraint
        await conn.execute("ALTER TABLE transactions DROP CONSTRAINT IF EXISTS transactions_type_check;")
        # Re-add with 'tip'
        await conn.execute("ALTER TABLE transactions ADD CONSTRAINT transactions_type_check CHECK (type IN ('deposit', 'withdrawal', 'bet', 'payout', 'fee', 'refund', 'bonus', 'seed_liquidity', 'tip'));")
        
        # Also fix schema.sql definition for future DB resets
    print("Migrazione completata!")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(migrate())
