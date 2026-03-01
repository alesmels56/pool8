import os
from dotenv import load_dotenv

load_dotenv()
t = os.getenv('BOT_TOKEN')
if not t:
    print("TOKEN NOT FOUND")
else:
    print(f"LEN: {len(t)}")
    print(f"START: {t[:10]}")
    print(f"END: {t[-5:]}")

# Test if we can reach Telegram
import requests
try:
    res = requests.get(f"https://api.telegram.org/bot{t}/getMe").json()
    print(f"getMe: {res}")
except Exception as e:
    print(f"Error: {e}")
