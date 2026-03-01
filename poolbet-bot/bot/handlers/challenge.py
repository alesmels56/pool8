"""
bot/handlers/challenge.py — Gestione contestazioni risultati (Optimistic Resolution).
"""
import logging
from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes

from db.bets import get_bet, set_bet_challenged
from db.users import get_user, get_user_language
from db.admin import get_setting
from utils.i18n import t
from config import CHALLENGE_STAKE

logger = logging.getLogger(__name__)

async def handle_challenge_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback: bet_challenge_start:<uuid>
    L'utente clicca su "Contesta Risultato".
    """
    query = update.callback_query
    await query.answer()

    bet_uuid = query.data.split(":", 1)[1]
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]

    bet = await get_bet(pool, bet_uuid)
    lang = await get_user_language(pool, user_id)

    if not bet:
        await query.answer("❌ Scommessa non trovata.", show_alert=True)
        return

    if bet["creator_id"] == user_id:
        await query.answer(t("err_challenge_self", lang), show_alert=True)
        return

    if bet["status"] != "resolving":
        await query.answer("⚠️ Non è più possibile contestare questa scommessa.", show_alert=True)
        return

    # Recupera costo contestazione (default da config, sovrascrivibile da DB)
    stake_str = await get_setting(pool, "challenge_stake_amount", str(CHALLENGE_STAKE))
    stake = Decimal(stake_str)

    user = await get_user(pool, user_id)
    if Decimal(str(user["balance_usdt"])) < stake:
        await query.answer(t("err_challenge_funds", lang).format(amount=stake), show_alert=True)
        return

    # Addebito stake e marca come contestata (Atomo)
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Addebito utente
            await conn.execute(
                "UPDATE users SET balance_usdt = balance_usdt - $1 WHERE user_id = $2",
                stake, user_id
            )
            # 2. Registra transazione
            await conn.execute(
                """
                INSERT INTO transactions (user_id, type, amount, status, note)
                VALUES ($1, 'bet', $2, 'confirmed', $3)
                """,
                user_id, -stake, f"Stake per contestazione bet {bet_uuid[:8]}"
            )
            # 3. Aggiorna scommessa
            success = await set_bet_challenged(pool, bet_uuid, user_id, stake)
    
    if success:
        await query.edit_message_text(
            t("challenge_started", lang),
            parse_mode="HTML"
        )
        logger.info(f"Bet {bet_uuid[:8]} challenged by user {user_id} with stake {stake} USDT")
        
        # Notifica Admin
        from config import ADMIN_IDS
        if ADMIN_IDS:
             await context.bot.send_message(
                 chat_id=ADMIN_IDS[0],
                 text=f"⚖️ <b>CONTESTAZIONE RICEVUTA</b>\n\nBet: {bet_uuid}\nChallenger: {user_id}\n\nL'admin deve ora risolvere manualmente la disputa tramite pannello admin.",
                 parse_mode="HTML"
             )
    else:
        await query.answer("⚠️ Errore durante la contestazione.", show_alert=True)
