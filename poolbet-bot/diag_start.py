"""
diag_start.py — Diagnosi rapida dell'handler _show_bet_card.
"""
import asyncio
import logging
from decimal import Decimal
from datetime import datetime
import json

# Mocking Telegram objects
class MockUser:
    def __init__(self, id, username):
        self.id = id
        self.username = username

class MockMessage:
    def __init__(self):
        self.replied_text = None
        self.reply_markup = None
    async def reply_text(self, text, parse_mode=None, reply_markup=None):
        self.replied_text = text
        self.reply_markup = reply_markup
        print(f"DEBUG: Sent Text: {text[:50]}...")
    async def reply_photo(self, photo, caption, parse_mode=None, reply_markup=None):
        self.replied_text = caption
        self.reply_markup = reply_markup
        print(f"DEBUG: Sent Photo with Caption: {caption[:50]}...")

class MockUpdate:
    def __init__(self, user_id, username):
        self.effective_user = MockUser(user_id, username)
        self.effective_message = MockMessage()

# Mocking DB and other utils
async def get_bet(pool, uuid):
    return {
        "uuid": uuid,
        "creator_id": 123,
        "creator_username": "test_creator",
        "question": "Test Question?",
        "options": json.dumps({"Sì": 0, "No": 0}),
        "pool_total": Decimal("10.00"),
        "expires_at": datetime.now(),
        "status": "open",
        "media_file_id": "file_id_123",
        "media_type": "photo"
    }

async def get_bet_summary(pool, uuid):
    return {"Sì": {"partecipanti": 1, "totale": Decimal("5.00")}}

# Import what we can
import sys
import os
sys.path.append(os.getcwd())

from utils.formatting import format_bet_message
from bot.keyboards import bet_message_keyboard
from config import BOT_USERNAME

async def test_card():
    lang = "it"
    bet_uuid = "some-uuid"
    bet = await get_bet(None, bet_uuid)
    summary = await get_bet_summary(None, bet_uuid)
    
    options = list(json.loads(bet["options"]).keys())
    
    print("Testing format_bet_message...")
    text = format_bet_message(bet, summary, lang)
    print("Text formatted successfully.")
    
    print("Testing bet_message_keyboard...")
    keyboard = bet_message_keyboard(bet_uuid, options, summary, BOT_USERNAME, lang)
    print("Keyboard created successfully.")
    
    media_id = bet.get("media_file_id")
    print(f"Media ID: {media_id}")

if __name__ == "__main__":
    asyncio.run(test_card())
