"""Quick check: print all bets and their status from the DB."""
import asyncio
import asyncpg
import os
import json
from dotenv import load_dotenv

load_dotenv()

async def main():
    pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"), statement_cache_size=0)
    rows = await pool.fetch("SELECT uuid::text, status, min_bet, options FROM bets ORDER BY created_at DESC LIMIT 10")
    for r in rows:
        opts = r["options"]
        if isinstance(opts, str):
            opts = json.loads(opts)
        print(f"UUID={r['uuid']} | STATUS={r['status']} | MIN_BET={r['min_bet']} | OPTIONS={list(opts.keys())}")
    await pool.close()

asyncio.run(main())
