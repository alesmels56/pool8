"""
bot/handlers/close_bet.py — Chiusura scommessa e selezione vincitore.
Solo il creatore può chiudere la propria scommessa.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from db.bets import get_bet, finalize_bet_optimistic
from db.participations import get_all_participations
from db.users import get_user_language
from bot.keyboards import winner_keyboard, challenge_keyboard
from utils.i18n import t
from config import CHALLENGE_DURATION_H, CHALLENGE_STAKE
# from engine.payout import run_payout (Moved to scheduler)

logger = logging.getLogger(__name__)


async def handle_close_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback: bet_close:<uuid>
    Verifica che sia il creatore e mostra la selezione del vincitore.
    """
    query = update.callback_query
    await query.answer()

    logger.info(f"handle_close_bet: data={query.data}, user={update.effective_user.id}")

    bet_uuid = query.data.split(":", 1)[1]
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]

    bet = await get_bet(pool, bet_uuid)
    logger.info(f"Bet lookup in handle_close_bet: {bet['uuid'] if bet else 'None'}, creator={bet['creator_id'] if bet else 'N/A'}")
    if bet is None:
        await query.answer("❌ Scommessa non trovata.", show_alert=True)
        return

    if bet["creator_id"] != user_id:
        await query.answer("❌ Solo il creatore può chiudere questa scommessa.", show_alert=True)
        return

    if bet["status"] not in ("open", "closed"):
        await query.answer(f"⚠️ Scommessa già {bet['status']}.", show_alert=True)
        return

    from bot.keyboards import confirm_keyboard
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"🔒 <b>Conferma Chiusura Scommessa</b>\n\n"
            f"❓ {bet['question']}\n\n"
            f"⚠️ <b>Attenzione:</b> sei sicuro di voler chiudere le puntate?\n"
            f"Questa azione non può essere annullata."
        ),
        parse_mode="HTML",
        reply_markup=confirm_keyboard(f"close_bet:{bet_uuid}"),
    )


async def handle_confirm_close_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback: confirm:close_bet:<uuid>
    L'utente ha confermato la chiusura, mostra la selezione vincitore.
    """
    query = update.callback_query
    await query.answer()

    # expected format: confirm:close_bet:<uuid>
    parts = query.data.split(":", 2)
    if len(parts) != 3:
        return
    _, _, bet_uuid = parts

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    bet = await get_bet(pool, bet_uuid)

    if bet is None or bet["creator_id"] != user_id:
        await query.edit_message_text("❌ Errore o permessi insufficienti.")
        return

    options_raw = bet["options"]
    if isinstance(options_raw, str):
        import json
        options_dict = json.loads(options_raw)
    else:
        options_dict = options_raw
    
    options = list(options_dict.keys())
    
    await query.edit_message_text(
        text=(
            f"🔒 <b>Scommessa Chiusa alle nuove puntate</b>\n\n"
            f"❓ {bet['question']}\n\n"
            f"Seleziona l'opzione <b>vincente</b> per distribuire il pool:"
        ),
        parse_mode="HTML",
        reply_markup=winner_keyboard(bet_uuid, options),
    )


async def handle_winner_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback: bet_winner:<uuid>:<option>
    Finalizza la scommessa e avvia il payout.
    """
    query = update.callback_query
    await query.answer()

    logger.info(f"handle_winner_selection: data={query.data}, user={update.effective_user.id}")

    parts = query.data.split(":", 2)
    if len(parts) != 3:
        logger.warning(f"Invalid winner split: {query.data}")
        return
    _, bet_uuid, winner_idx_str = parts
    try:
        winner_idx = int(winner_idx_str)
    except ValueError:
        return

    user_id = update.effective_user.id
    pool = context.bot_data["pool"]

    # Verifica nuovamente i permessi
    bet = await get_bet(pool, bet_uuid)
    if bet is None or bet["creator_id"] != user_id:
        await query.edit_message_text("❌ Errore: scommessa non trovata o permessi insufficienti.")
        return

    options_raw = bet["options"]
    if isinstance(options_raw, str):
        import json
        options_dict = json.loads(options_raw)
    else:
        options_dict = options_raw
    options = list(options_dict.keys())

    if winner_idx < 0 or winner_idx >= len(options):
        await query.answer("❌ Opzione non valida.", show_alert=True)
        return
    winner_option = options[winner_idx]

    # Finalizza nel DB (Optimistic)
    success = await finalize_bet_optimistic(pool, bet_uuid, winner_option, challenge_hours=CHALLENGE_DURATION_H)
    if not success:
        await query.edit_message_text(f"⚠️ Impossibile finalizzare: scommessa in stato '{bet['status']}'.")
        return

    lang = await get_user_language(pool, user_id)
    await query.edit_message_text(
        f"✅ {t('winner_selected', lang)}: <b>{winner_option}</b>\n\n"
        f"{t('payout_review', lang)}",
        parse_mode="HTML",
    )

    logger.info(f"Bet {bet_uuid[:8]} set to resolving by creator {user_id}. Winner: {winner_option}")

    # Notifica TUTTI i partecipanti della possibilità di contestare
    participants = await get_all_participations(pool, bet_uuid)
    for p in participants:
        p_id = p["user_id"]
        if p_id == user_id: continue # Non notificare il creator
        
        p_lang = await get_user_language(pool, p_id)
        try:
            msg = t('resolution_notification', p_lang).format(
                question=bet['question'],
                winner=winner_option,
                hours=CHALLENGE_DURATION_H,
                stake=CHALLENGE_STAKE
            )
            await context.bot.send_message(
                chat_id=p_id,
                text=msg,
                parse_mode="HTML",
                reply_markup=challenge_keyboard(bet_uuid, p_lang)
            )
        except Exception as e:
            logger.warning(f"Could not notify participant {p_id} of resolution: {e}")
