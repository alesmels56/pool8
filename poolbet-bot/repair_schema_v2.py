import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def repair():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    print("Repairing 'bets' table...")
    try:
        await conn.execute("ALTER TABLE bets ADD COLUMN IF NOT EXISTS media_type TEXT")
        print("Success: Column 'media_type' added or already exists.")
    except Exception as e:
        print(f"Error adding column: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(repair())
