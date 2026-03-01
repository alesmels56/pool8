import asyncio
import os
import asyncpg
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

async def create_test_bet():
    pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    
    # Get first user
    user = await pool.fetchrow("SELECT user_id FROM users LIMIT 1")
    if not user:
        print("No users found. Start the bot first.")
        return

    user_id = user["user_id"]
    
    # Create a public bet
    expires_at = datetime.utcnow() + timedelta(days=1)
    options = '{"Sì": 0, "No": 0}'
    
    await pool.execute(
        """
        INSERT INTO bets (creator_id, question, options, min_bet, expires_at, is_public, hashtags, status)
        VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8)
        """,
        user_id,
        "Il bot funzionerà perfettamente dopo questo fix? 🚀",
        options,
        1.0,
        expires_at,
        True,
        "#test #fix",
        "open"
    )
    print("Test bet created successfully!")
    await pool.close()

if __name__ == "__main__":
    asyncio.run(create_test_bet())
