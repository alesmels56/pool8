"""
bot/handlers/explore.py — Feed pubblico delle scommesse (una per pagina).
Usa update_menu (bot/ui.py) per navigazione edit-in-place.
"""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from db.users import get_user_language
from db.bets import get_open_bets, get_open_bets_by_tag
from db.participations import get_bet_summary
from bot.keyboards import bet_message_keyboard
from bot.ui import update_menu, answer_and_update, delete_user_message
from utils.formatting import format_bet_message
from utils.i18n import t
from config import BOT_USERNAME

logger = logging.getLogger(__name__)

ASK_SEARCH_TAG = 1


async def handle_explore(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Feed scommesse pubbliche — modifica il messaggio persistente in place.
    Supporta media (foto/video), paginazione, ricerca per hashtag e Quick Filters.
    """
    query = update.callback_query
    chat_id = update.effective_chat.id
    pool = context.bot_data["pool"]

    if query:
        if query.data == "explore:ignore":
            try: await query.answer("Fine dei risultati.")
            except: pass
            return
        
        try: await query.answer()
        except: pass
        
        parts = query.data.split(":")
        action = parts[1] if len(parts) > 1 else "page"
        
        if action == "tag":
            context.user_data["search_tag"] = parts[2]
            offset = 0
        elif action == "random":
            from db.bets import get_random_open_bet
            bet = await get_random_open_bet(pool)
            if bet:
                await _render_bet_in_explore(context, chat_id, bet, 0, False, pool, update.effective_user.id)
                return
            else:
                context.user_data.pop("search_tag", None)
                offset = 0
        else:
            offset = int(parts[2]) if len(parts) > 2 else 0
    else:
        offset = 0

    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)
    search_tag = context.user_data.get("search_tag")

    # ── Carica bets ──────────────────────────────────────────────────────────
    if search_tag:
        open_bets = await get_open_bets_by_tag(pool, search_tag, limit=2, offset=offset)
    else:
        open_bets = await get_open_bets(pool, limit=2, offset=offset)

    # ── Empty feed ────────────────────────────────────────────────────────────
    if not open_bets:
        header = f"🔍 <b>Ricerca: {search_tag}</b>\n\n" if search_tag else "🌐 <b>Esplora Feed</b>\n\n"
        text = header + "<i>Non ci sono scommesse disponibili. Creane una!</i>"
        rows = [[InlineKeyboardButton("🎰 Shuffle / Casuale", callback_data="explore:random")]]
        rows.append([InlineKeyboardButton(t("btn_search_tag", lang), callback_data="explore:search")])
        if search_tag:
            rows.append([InlineKeyboardButton(t("btn_reset_search", lang), callback_data="explore:reset_search")])
        rows.append([InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")])
        await update_menu(context, chat_id, text, InlineKeyboardMarkup(rows))
        return

    bet = open_bets[0]
    has_next = len(open_bets) > 1
    await _render_bet_in_explore(context, chat_id, bet, offset, has_next, pool, user_id)


async def _render_bet_in_explore(context, chat_id, bet, offset, has_next, pool, user_id):
    """Helper per renderizzare una singola bet nell'Esplora Feed."""
    from db.participations import get_bet_summary
    from bot.keyboards import bet_message_keyboard
    from bot.ui import update_menu
    from utils.formatting import format_bet_message
    from config import BOT_USERNAME
    
    lang = await get_user_language(pool, user_id)
    search_tag = context.user_data.get("search_tag")
    bet_uuid = str(bet["uuid"])
    summary = await get_bet_summary(pool, bet_uuid)
    
    options_raw = bet["options"]
    if isinstance(options_raw, str):
        options_dict = json.loads(options_raw)
    else:
        options_dict = options_raw
    options = list(options_dict.keys())

    text = format_bet_message(bet, summary, lang)

    # ── Tastiera ──────────────────────────────────────────────────────────────
    keyboard = list(bet_message_keyboard(bet_uuid, options, summary, BOT_USERNAME, lang).inline_keyboard)

    # Quick Tags Row
    tags_row = [
        InlineKeyboardButton("#Sport ⚽", callback_data="explore:tag:#sport"),
        InlineKeyboardButton("#Fun 🎭", callback_data="explore:tag:#fun"),
        InlineKeyboardButton("#Crypto 🚀", callback_data="explore:tag:#crypto"),
    ]
    keyboard.insert(0, tags_row)

    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prec.", callback_data=f"explore:page:{offset - 1}"))
    else:
        nav_row.append(InlineKeyboardButton("⛔️ Prec.", callback_data="explore:ignore"))
    
    nav_row.append(InlineKeyboardButton("🎰 Shuffle", callback_data="explore:random"))
        
    if has_next:
        nav_row.append(InlineKeyboardButton("Succ. ➡️", callback_data=f"explore:page:{offset + 1}"))
    else:
        nav_row.append(InlineKeyboardButton("⛔️ Succ.", callback_data="explore:ignore"))

    bottom_row = [InlineKeyboardButton(t("btn_search_tag", lang), callback_data="explore:search")]
    if search_tag:
        bottom_row.append(InlineKeyboardButton(t("btn_reset_search", lang), callback_data="explore:reset_search"))

    keyboard.append(nav_row)
    keyboard.append(bottom_row)
    keyboard.append([InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")])

    markup = InlineKeyboardMarkup(keyboard)
    media_file_id = bet.get("media_file_id")
    media_type = bet.get("media_type")

    await update_menu(
        context, chat_id, text, markup,
        media_file_id=media_file_id,
        media_type=media_type,
    )


# ── Ricerca per hashtag ───────────────────────────────────────────────────────

async def explore_start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Chiede all'utente di digitare l'hashtag da cercare."""
    lang = await get_user_language(context.bot_data["pool"], update.effective_user.id)
    await answer_and_update(
        update.callback_query, context,
        t("search_prompt", lang),
    )
    return ASK_SEARCH_TAG


async def explore_receive_search_tag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve l'hashtag, avvia Explore filtrato e cancella il messaggio dell'utente."""
    await delete_user_message(update.message)
    text = update.message.text.strip().lower()

    if text == "annulla":
        await handle_explore(update, context)
        return ConversationHandler.END

    context.user_data["search_tag"] = text if text.startswith("#") else f"#{text}"
    await handle_explore(update, context)
    return ConversationHandler.END


async def explore_reset_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Rimuove il filtro hashtag e mostra il feed globale."""
    context.user_data.pop("search_tag", None)
    await handle_explore(update, context)
