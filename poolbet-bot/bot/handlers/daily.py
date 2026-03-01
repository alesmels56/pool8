import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from db.users import claim_daily_faucet, get_user_language
from utils.i18n import t
from bot.ui import answer_and_update, update_menu

logger = logging.getLogger(__name__)

async def handle_daily_faucet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce la riscossione del faucet giornaliero via callback."""
    query = update.callback_query
    # Il caricamento animato visivo sul bottone
    await query.answer("🎁 Controllo faucet...")

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)

    # Chiama the DB logic
    bonus, streak, xp_gain = await claim_daily_faucet(pool, user_id)

    # Prepara bottoni
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_back_menu", lang), callback_data="wallet:balance")]
    ])

    if bonus > 0:
        # Faucet riscosso con successo
        text = t("daily_success", lang).format(
            bonus=f"{bonus:.2f}",
            streak=streak,
            xp=xp_gain
        )
    else:
        # Faucet già riscosso o maxato oggi
        text = t("daily_already", lang)

    await answer_and_update(query, context, text, reply_markup=kb)
