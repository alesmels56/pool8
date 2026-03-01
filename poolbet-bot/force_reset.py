import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN")

print("--- FORCED RESET ---")
# 1. Kill any existing webhook
res_del = requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=True").json()
print(f"Delete Webhook: {res_del}")

# 2. Verify getMe
me = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
print(f"Identity: {me}")

# 3. Pull updates for 10 seconds and LOG EVERYTHING
print("Polling manually... Send /start to the bot NOW.")
start = time.time()
offset = 0
while time.time() - start < 20:
    r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=5").json()
    if r.get("ok"):
        for u in r["result"]:
            print(f"RAW UPDATE: {u}")
            offset = u["update_id"] + 1
    else:
        print(f"Polling Error: {r}")
    time.sleep(1)

print("Diagnostic over.")
