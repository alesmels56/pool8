import os
from dotenv import load_dotenv
from utils.i18n import TRANSLATIONS

load_dotenv()
token = os.getenv("BOT_TOKEN")
print(f"DEBUG TOKEN: {token[:10]}...{token[-5:] if token else 'None'}")
print(f"DEBUG TRANSLATIONS KEYS: {list(TRANSLATIONS.keys())}")
for lang, keys in TRANSLATIONS.items():
    print(f"DEBUG {lang} keys count: {len(keys)}")
    if 'menu_balance' in keys:
        print(f"DEBUG {lang} menu_balance: {repr(keys['menu_balance'])}")
