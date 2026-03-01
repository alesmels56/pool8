import asyncio
import os
import asyncpg
from dotenv import load_dotenv

async def check_db():
    load_dotenv()
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    print("--- DB AUDIT ---")
    
    # 1. Tables
    tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    print(f"Tables: {[t['table_name'] for t in tables]}")
    
    # 2. Columns for users
    cols = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users'")
    print(f"Users columns: {[(c['column_name'], c['data_type']) for c in cols]}")

    # 3. Columns for bets
    cols = await conn.fetch("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'bets'")
    print(f"Bets columns: {[(c['column_name'], c['data_type']) for c in cols]}")

    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_db())
