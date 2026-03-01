import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN")

print(f"--- DIAGNOSTIC START ---")
print(f"Token: {token[:10]}...")

# 1. Reset Webhook just in case
print("Resetting webhook...")
requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=True")

# 2. Get Me
me = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
print(f"Bot Identity: {me}")

# 3. Listen loop (raw)
print("Listening for 30 seconds... SEND A MESSAGE TO THE BOT NOW (@poolr_bot)")
start_time = time.time()
offset = 0
while time.time() - start_time < 30:
    try:
        res = requests.get(f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=5").json()
        if res["ok"] and res["result"]:
            for update in res["result"]:
                print(f"RECEIVED UPDATE: {update}")
                offset = update["update_id"] + 1
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1)

print("Diagnostic finished.")
