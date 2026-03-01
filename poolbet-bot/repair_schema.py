import asyncio
import os
import asyncpg
from dotenv import load_dotenv

async def fix_schema():
    load_dotenv()
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    print("Repairing schema...")
    try:
        # Add columns manually to be 100% sure
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by BIGINT REFERENCES users(user_id)")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS trust_score INTEGER DEFAULT 50")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_bets_created INTEGER DEFAULT 0")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS total_bets_closed INTEGER DEFAULT 0")
        await conn.execute("ALTER TABLE bets ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE")
        await conn.execute("ALTER TABLE bets ADD COLUMN IF NOT EXISTS hashtags TEXT")
        print("Schema repaired successfully.")
    except Exception as e:
        print(f"Repair failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix_schema())
