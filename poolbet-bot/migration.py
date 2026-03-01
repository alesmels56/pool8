import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("Manca DATABASE_URL")
        return
    print(f"Connecting to {url}")
    pool = await asyncpg.create_pool(url)
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS xp INT DEFAULT 0;")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS login_streak INT DEFAULT 0;")
        await conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;")
    print("Migrazione completata!")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(migrate())
