import asyncio
import os
from dotenv import load_dotenv
from db.connection import create_pool, close_pool
from db.users import register_user, get_user, get_user_language
from blockchain.wallet import generate_wallet_for_user

async def test_registration():
    load_dotenv()
    pool = await create_pool()
    user_id = 7640298303 # Admin ID
    
    print(f"Testing registration for {user_id}...")
    try:
        # 1. Register
        wallet = generate_wallet_for_user(user_id % (2**31))
        await register_user(pool, user_id, "testadmin", wallet)
        print("Registration call finished.")
        
        # 2. Verify
        user = await get_user(pool, user_id)
        print(f"User Record: {user}")
        
        # 3. Language
        lang = await get_user_language(pool, user_id)
        print(f"Language: {lang}")
        
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        await close_pool(pool)

if __name__ == "__main__":
    asyncio.run(test_registration())
