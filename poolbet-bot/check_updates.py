import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN")
url = f"https://api.telegram.org/bot{token}/getUpdates"
res = requests.get(url).json()

if res["ok"]:
    updates = res["result"]
    print(f"Total Updates: {len(updates)}")
    for u in updates[-5:]:
        print(f"Update: {u}")
else:
    print(f"Error: {res}")
