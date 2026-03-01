import requests
import os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BOT_TOKEN")
res = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
if res["ok"]:
    print(f"USERNAME: @{res['result']['username']}")
    print(f"NAME: {res['result']['first_name']}")
else:
    print(f"ERROR: {res}")
