import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def migrate():
    print(f"Connecting to {DATABASE_URL}...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Creating table platform_stats...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS platform_stats (
                id SERIAL PRIMARY KEY,
                profit_balance_usdt DECIMAL(20, 6) DEFAULT 0,
                total_withdrawn_admin DECIMAL(20, 6) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await conn.execute("""
            INSERT INTO platform_stats (id, profit_balance_usdt) 
            VALUES (1, 0) 
            ON CONFLICT (id) DO NOTHING;
        """)
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
