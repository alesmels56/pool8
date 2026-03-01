import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

async def debug_db():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    
    print("--- BETS TABLE ---")
    bets = await conn.fetch("SELECT uuid, question, is_public, status, creator_id FROM bets")
    for b in bets:
        print(dict(b))
        
    print("\n--- USERS TABLE ---")
    users = await conn.fetch("SELECT user_id, username FROM users LIMIT 5")
    for u in users:
        print(dict(u))
        
    print("\n--- EXPLORE QUERY TEST ---")
    rows = await conn.fetch("""
        SELECT b.uuid, b.question, b.pool_total, b.expires_at, b.status, u.username as creator_username, u.trust_score,
               (SELECT COUNT(*) FROM participations WHERE bet_uuid = b.uuid) AS participants_count,
               b.media_file_id, b.media_type, b.options, b.hashtags
        FROM bets b
        JOIN users u ON b.creator_id = u.user_id
        WHERE b.status = 'open' AND b.is_public = TRUE
        ORDER BY b.created_at DESC
    """)
    print(f"Explore results: {len(rows)}")
    for r in rows:
        print(dict(r))
        
    await conn.close()

if __name__ == "__main__":
    asyncio.run(debug_db())
