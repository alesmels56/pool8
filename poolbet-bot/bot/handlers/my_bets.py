"""
bot/handlers/my_bets.py — Visualizzazione e paginazione delle scommesse dell'utente.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from db.bets import list_user_bets
from bot.keyboards import bet_message_keyboard
from bot.ui import update_menu, answer_and_update

logger = logging.getLogger(__name__)

BETS_PER_PAGE = 5


async def list_bets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: genera la prima pagina delle scommesse o mostra lista vuota."""
    if update.callback_query:
        await update.callback_query.answer()
    await _send_bets_page(update, context, page=0)


async def handle_bets_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Callback per i bottoni avanti/indietro della paginazione."""
    query = update.callback_query

    parts = query.data.split(":")
    if len(parts) != 2:
        await query.answer()
        return

    try:
        page = int(parts[1])
    except ValueError:
        await query.answer()
        return

    await _send_bets_page(update, context, page=page, is_callback=True)


async def _send_bets_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int, is_callback: bool = False):
    """Costruisce e invia/modifica una pagina della lista scommesse."""
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    from db.users import get_user_language
    lang = await get_user_language(pool, user_id)
    bets = await list_user_bets(pool, user_id)

    if not bets:
        text = "📋 <b>Le tue Scommesse</b>\n\nNon hai ancora creato o partecipato ad alcuna scommessa."
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")]])
        if is_callback:
            await answer_and_update(update.callback_query, context, text, reply_markup=markup)
        else:
            await update_menu(context, chat_id, text, reply_markup=markup)
        return

    total_pages = (len(bets) + BETS_PER_PAGE - 1) // BETS_PER_PAGE
    page = max(0, min(page, total_pages - 1))

    start_idx = page * BETS_PER_PAGE
    end_idx = start_idx + BETS_PER_PAGE
    page_bets = bets[start_idx:end_idx]

    lines = [f"📋 <b>Le tue Scommesse</b> (Pagina {page+1}/{total_pages})\n"]

    from config import BOT_USERNAME
    from utils.deeplink import make_bet_link

    for b in page_bets:
        status_icon = {"open": "🟢", "closed": "🔴", "finalized": "✅", "expired": "⏱"}.get(b["status"], "•")
        # Identifica il creatore vs partecipante
        role = "👑 Creatore" if b["creator_id"] == user_id else "👤 Partecipante"
        p_count = b["participants_count"]
        link = make_bet_link(BOT_USERNAME, str(b["uuid"]))

        lines.append(
            f"{status_icon} <b>{b['question']}</b>\n"
            f"   💰 Pool: {b['pool_total']:.2f} USDT | 👥 Partecipanti: {p_count}\n"
            f"   🎭 Ruolo: {role} | 🔗 <a href='{link}'>Apri Scommessa</a>\n"
        )

    text = f"{update.effective_user.first_name}, " + "\n".join(lines)

    # Bottoni paginazione
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("◀ Precedente", callback_data=f"mybets:{page-1}"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton("Successivo ▶", callback_data=f"mybets:{page+1}"))

    from utils.i18n import t
    markup_rows = [buttons] if buttons else []
    markup_rows.append([InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")])

    reply_markup = InlineKeyboardMarkup(markup_rows)

    if is_callback:
        await answer_and_update(update.callback_query, context, text, reply_markup=reply_markup)
    else:
        await update_menu(context, chat_id, text, reply_markup=reply_markup)
