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
        print("Ensuring pg_trgm extension exists...")
        await conn.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
        
        print("Ensuring columns exist with correct types...")
        await conn.execute("ALTER TABLE bets ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE;")
        await conn.execute("ALTER TABLE bets ADD COLUMN IF NOT EXISTS media_type TEXT;")
        
        # Check if hashtags is an array and convert to text
        res = await conn.fetchrow("""
            SELECT data_type FROM information_schema.columns 
            WHERE table_name = 'bets' AND column_name = 'hashtags';
        """)
        if res:
            if res['data_type'] == 'ARRAY' or 'array' in res['data_type'].lower():
                print("Converting hashtags from ARRAY to TEXT...")
                await conn.execute("ALTER TABLE bets ALTER COLUMN hashtags TYPE TEXT USING array_to_string(hashtags, ' ');")
        else:
            print("Adding hashtags column as TEXT...")
            await conn.execute("ALTER TABLE bets ADD COLUMN hashtags TEXT;")

        print("Applying indexing optimizations...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_bets_hashtags_gin ON bets USING gin (hashtags gin_trgm_ops);")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_created_at_brin ON transactions USING brin (created_at);")
        
        print("Creating history tables...")
        await conn.execute("CREATE TABLE IF NOT EXISTS history_bets (LIKE bets INCLUDING ALL);")
        await conn.execute("CREATE TABLE IF NOT EXISTS history_participations (LIKE participations INCLUDING ALL);")
        await conn.execute("CREATE TABLE IF NOT EXISTS history_transactions (LIKE transactions INCLUDING ALL);")
        
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
