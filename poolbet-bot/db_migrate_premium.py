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
        print("Expanding users table with Premium columns...")
        await conn.execute("""
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS referred_by BIGINT REFERENCES users(user_id),
            ADD COLUMN IF NOT EXISTS trust_score INT DEFAULT 50,
            ADD COLUMN IF NOT EXISTS total_bets_created INT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS total_bets_closed INT DEFAULT 0;
        """)
        
        print("Expanding bets table with hashtags...")
        await conn.execute("""
            ALTER TABLE bets 
            ADD COLUMN IF NOT EXISTS hashtags TEXT[];
        """)
        
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
