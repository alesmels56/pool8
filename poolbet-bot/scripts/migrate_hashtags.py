import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    url = os.getenv("DATABASE_URL")
    conn = await asyncpg.connect(url)
    try:
        await conn.execute("ALTER TABLE bets ADD COLUMN IF NOT EXISTS hashtags TEXT;")
        print("Migrazione completata: colonna hashtags aggiunta.")
    except Exception as e:
        print(f"Errore migrazione: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
