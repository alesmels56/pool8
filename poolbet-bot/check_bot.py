import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

async def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    print(f"Token: {token[:10]}...", flush=True)
    
    bot = Bot(token)
    try:
        me = await bot.get_me()
        print(f"✅ Bot Connesso!", flush=True)
        print(f"   Nome: {me.first_name}", flush=True)
        print(f"   Username: @{me.username}", flush=True)
        print(f"   ID: {me.id}", flush=True)
    except Exception as e:
        print(f"❌ Errore get_me: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
