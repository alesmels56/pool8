import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN")
admin_id = "7640298303"

print(f"Sending test to {admin_id}...")
url = f"https://api.telegram.org/bot{token}/sendMessage"
res = requests.post(url, json={
    "chat_id": admin_id,
    "text": "TEST MESSAGE FROM DIAGNOSTIC SCRIPT"
}).json()

print(f"Result: {res}")
