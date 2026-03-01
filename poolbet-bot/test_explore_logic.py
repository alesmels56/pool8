import asyncio
import os
import asyncpg
import json
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

# Mocking t function
def t(key, lang="it"):
    return key

# Import formatting
import sys
sys.path.append(os.getcwd())
from utils.formatting import format_bet_message
from db.bets import get_open_bets
from db.participations import get_bet_summary

async def test_full_explore():
    from db.connection import create_pool
    pool = await create_pool()
    
    print("Fetching open bets...")
    open_bets = await get_open_bets(pool, limit=2, offset=0)
    print(f"Bets found: {len(open_bets)}")
    
    if not open_bets:
        print("Empty feed test.")
        return

    bet = open_bets[0]
    print(f"Testing bet: {bet['uuid']}")
    
    bet_uuid = str(bet["uuid"])
    summary = await get_bet_summary(pool, bet_uuid)
    print(f"Summary: {summary}")
    
    try:
        text = format_bet_message(bet, summary, "it")
        print("\n--- FORMATTED MESSAGE ---\n")
        print(text)
        print("\n--- END MESSAGE ---\n")
    except Exception as e:
        print(f"CRITICAL ERROR IN format_bet_message: {e}")
        import traceback
        traceback.print_exc()

    await pool.close()

if __name__ == "__main__":
    asyncio.run(test_full_explore())
