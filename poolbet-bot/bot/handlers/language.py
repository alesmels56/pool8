"""
bot/handlers/language.py — Gestione preferenza lingua dell'utente.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db.users import set_user_language, get_user_language
from utils.i18n import t
from bot.keyboards import main_keyboard

logger = logging.getLogger(__name__)


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Invia la tastiera per scegliere la lingua."""
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    
    current_lang = await get_user_language(pool, user_id)
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇮🇹 Italiano", callback_data="setlang:it"),
            InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en"),
        ],
        [
            InlineKeyboardButton("🇫🇷 Français", callback_data="setlang:fr"),
            InlineKeyboardButton("🇩🇪 Deutsch", callback_data="setlang:de"),
        ],
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="setlang:es"),
            InlineKeyboardButton("🇵🇹 Português", callback_data="setlang:pt"),
        ]
    ])
    
    await update.message.reply_text(
        text=t("lang_prompt", current_lang),
        reply_markup=keyboard,
    )


async def handle_set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback triggered quando l'utente sceglie una lingua."""
    query = update.callback_query
    await query.answer()

    # Formato: setlang:<lang>
    _, lang = query.data.split(":")
    if lang not in ["it", "en", "fr", "de", "es", "pt"]:
        return

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    
    # Salva su DB
    await set_user_language(pool, user_id, lang)
    
    # Conferma e invia la main_keyboard aggiornata con la nuova lingua
    # Per farlo dobbiamo inviare un nuovo messaggio perché edit_message_text 
    # non supporta ReplyKeyboardMarkup
    await query.edit_message_text(text=t("lang_updated", lang))
    
    await context.bot.send_message(
        chat_id=user_id,
        text="👋",
        reply_markup=main_keyboard(lang)
    )
