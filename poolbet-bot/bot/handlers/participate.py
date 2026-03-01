"""
bot/handlers/participate.py — Flusso puntata a 3 step:
  1. bet_pick:<uuid>:<option>  → mostra saldo utente + selezione importo
  2. bet_vote:<uuid>:<option>:<amount>  → piazza la puntata
  3. bet_custom:<uuid>:<option>  → chiede importo libero in testo
"""
import logging
from decimal import Decimal, InvalidOperation
import json
from typing import List

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from db.bets import get_bet, increment_option_vote
from db.participations import place_bet_atomic, get_bet_summary
from db.users import get_user, get_user_language
from bot.keyboards import bet_message_keyboard, amount_selection_keyboard
from bot.ui import update_menu, delete_user_message
from utils.formatting import format_bet_message
from config import BOT_USERNAME
from utils.i18n import t, TRANSLATIONS

logger = logging.getLogger(__name__)

# Stato per importo personalizzato
AWAITING_CUSTOM_AMOUNT = 900


def _get_options(bet) -> List[str]:
    """Estrae le chiavi delle opzioni gestendo sia dict che stringa JSON."""
    options_raw = bet["options"]
    if isinstance(options_raw, str):
        try:
            options_dict = json.loads(options_raw)
        except Exception:
            options_dict = {}
    else:
        options_dict = options_raw
    return list(options_dict.keys())


# ──────────────────────────────────────────────────────────────
# STEP 1: utente sceglie un'opzione → mostra saldo + selezione importo
# ──────────────────────────────────────────────────────────────

async def handle_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback: bet_pick:<uuid>:<option_idx>
    Mostra la tastiera di scelta importo nel messaggio persistente.
    """
    query = update.callback_query
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    try:
        await query.answer()
    except Exception:
        pass

    try:
        parts = query.data.split(":", 2)
        if len(parts) != 3:
            return
        _, bet_uuid, option_idx_str = parts
        option_idx = int(option_idx_str)

        pool = context.bot_data["pool"]
        lang = await get_user_language(pool, user_id)
        
        bet = await get_bet(pool, bet_uuid)
        if bet is None:
            await update_menu(context, chat_id, t("err_bet_not_found", lang))
            return
        if bet["status"] != "open":
            # Potremmo tradurre anche questo, per ora usiamo err_generic o un fallback
            await update_menu(context, chat_id, "⏱ Questa scommessa non è più aperta.")
            return

        options = _get_options(bet)
        if option_idx < 0 or option_idx >= len(options):
            await update_menu(context, chat_id, t("err_invalid_option", lang))
            return
        option = options[option_idx]

        user = await get_user(pool, user_id)
        if user is None:
            await update_menu(context, chat_id, t("err_profile", lang))
            return

        balance = float(user["balance_usdt"])
        min_bet = float(bet["min_bet"])

        if balance < min_bet:
            from bot.keyboards import insufficient_balance_keyboard
            await update_menu(
                context, chat_id,
                t("err_insufficient", lang) + "\n\n"
                f"Il tuo saldo: <b>{balance:.2f} USDT</b>\n"
                f"Minimo richiesto: <b>{min_bet:.2f} USDT</b>",
                reply_markup=insufficient_balance_keyboard(lang),
            )
            return

        keyboard = amount_selection_keyboard(bet_uuid, option_idx, min_bet, balance)
        text = (
            f"🎯 <b>Hai scelto: {option}</b>\n\n"
            f"💳 Il tuo saldo: <b>{balance:.2f} USDT</b>\n"
            f"📉 Puntata minima: <b>{min_bet:.2f} USDT</b>\n\n"
            f"Quanto vuoi scommettere?"
        )
        logger.info(f"handle_pick: showing amount selection for chat_id={chat_id} option={option}")
        await update_menu(context, chat_id, text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"handle_pick EXCEPTION: {e}", exc_info=True)
        try:
            pool = context.bot_data["pool"]
            lang = await get_user_language(pool, user_id)
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")]])
            error_text = t("err_generic", lang).format(error=str(e)[:100])
            await update_menu(context, chat_id, error_text, reply_markup=kb)
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────
# STEP 2a: importo da scorciatoia (Min / Metà / Max)
# ──────────────────────────────────────────────────────────────

async def handle_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback: bet_vote:<uuid>:<option_idx>:<amount>
    Piazza la puntata con l'importo selezionato.
    """
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":", 3)
    if len(parts) != 4:
        return

    _, bet_uuid, option_idx_str, amount_str = parts
    try:
        option_idx = int(option_idx_str)
        amount = Decimal(amount_str)
    except (ValueError, InvalidOperation):
        await query.answer("❌ Dati non validi.", show_alert=True)
        return

    pool = context.bot_data["pool"]
    bet = await get_bet(pool, bet_uuid)
    if bet is None:
        await query.answer("❌ Scommessa non trovata.", show_alert=True)
        return

    options = _get_options(bet)
    if option_idx < 0 or option_idx >= len(options):
        await query.answer("❌ Opzione non valida.", show_alert=True)
        return
    option = options[option_idx]

    user_id = update.effective_user.id
    await _execute_bet(query, update, context, pool, user_id, bet_uuid, option, amount)


# ──────────────────────────────────────────────────────────────
# STEP 2b: importo personalizzato — testo libero
# ──────────────────────────────────────────────────────────────

async def handle_custom_amount_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Callback: bet_custom:<uuid>:<option_idx>
    Chiede all'utente di digitare un importo personalizzato.
    """
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":", 2)
    if len(parts) != 3: return ConversationHandler.END
    
    _, bet_uuid, option_idx_str = parts
    try:
        option_idx = int(option_idx_str)
    except ValueError:
        return ConversationHandler.END

    pool = context.bot_data["pool"]
    bet = await get_bet(pool, bet_uuid)
    if bet is None:
        await query.answer("❌ Scommessa non trovata.", show_alert=True)
        return ConversationHandler.END

    options = _get_options(bet)

    if option_idx < 0 or option_idx >= len(options):
        await query.answer("❌ Opzione non valida.", show_alert=True)
        return ConversationHandler.END
    option = options[option_idx]

    user_id = update.effective_user.id
    user = await get_user(pool, user_id)
    balance = float(user["balance_usdt"]) if user else 0.0

    context.user_data["pending_bet"] = {"uuid": bet_uuid, "option": option}

    text = (
        f"✏️ <b>Importo personalizzato</b>\n\n"
        f"💳 Saldo disponibile: <b>{balance:.2f} USDT</b>\n\n"
        f"Scrivi l'importo da puntare su <b>{option}</b>:"
    )

    # Always send new message (edit fails if explore deleted the original)
    try:
        await update.effective_chat.send_message(text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"handle_custom_amount_prompt: failed to send: {e}")

    return AWAITING_CUSTOM_AMOUNT


async def handle_custom_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve il testo dell'importo e piazza la puntata."""
    text = update.message.text.strip().replace(",", ".")
    try:
        amount = Decimal(text)
        if amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await update.message.reply_text(
            "❌ Inserisci un numero positivo (es. 12.50):"
        )
        return AWAITING_CUSTOM_AMOUNT

    pending = context.user_data.pop("pending_bet", None)
    if not pending:
        await update.message.reply_text("❌ Sessione scaduta. Riprova dalla scommessa.")
        return ConversationHandler.END

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id

    try:
        result = await place_bet_atomic(
            pool,
            user_id=user_id,
            bet_uuid=pending["uuid"],
            option=pending["option"],
            amount=amount,
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return ConversationHandler.END

    await increment_option_vote(pool, pending["uuid"], pending["option"])
    new_pool = result["new_pool"]
    logger.info(f"Custom bet: user {user_id} → {pending['option']} {amount} USDT. Pool: {new_pool}")

    user = await get_user(pool, user_id)
    new_balance = float(user["balance_usdt"]) if user else 0.0

    await update.message.reply_text(
        f"✅ <b>Puntata confermata!</b>\n\n"
        f"🎯 Opzione: <b>{pending['option']}</b>\n"
        f"💸 Importo: <b>{amount:.2f} USDT</b>\n"
        f"💰 Pool aggiornato: <b>{new_pool:.2f} USDT</b>\n"
        f"💳 Saldo residuo: <b>{new_balance:.2f} USDT</b>",
        parse_mode="HTML",
    )

    # Aggiorna anche il messaggio nel gruppo se esiste
    bet = await get_bet(pool, pending["uuid"])
    if bet and bet.get("group_chat_id") and bet.get("message_id"):
        await _update_group_message(
            context.bot, pool, pending["uuid"], bet, new_pool,
            bet["group_chat_id"], bet["message_id"]
        )

    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────
# Helper: esegui puntata e aggiorna messaggi
# ──────────────────────────────────────────────────────────────

async def _execute_bet(query, update, context, pool, user_id, bet_uuid, option, amount):
    """Logica comune di piazzamento puntata per scorciatoia e testo libero."""
    try:
        result = await place_bet_atomic(pool, user_id=user_id, bet_uuid=bet_uuid,
                                        option=option, amount=amount)
    except ValueError as e:
        await query.answer(str(e), show_alert=True)
        return

    await increment_option_vote(pool, bet_uuid, option)
    new_pool = result["new_pool"]

    # Saldo aggiornato post-puntata
    user = await get_user(pool, user_id)
    new_balance = float(user["balance_usdt"]) if user else 0.0
    username = update.effective_user.username or update.effective_user.first_name

    logger.info(f"User {user_id} voted '{option}' {amount} USDT on {bet_uuid[:8]}. Pool: {new_pool}")

    # Notifica il creatore se non è lui stesso a puntare
    bet = await get_bet(pool, bet_uuid)
    if bet["creator_id"] != user_id:
        try:
            await context.bot.send_message(
                chat_id=bet["creator_id"],
                text=f"🎲 <b>Nuova puntata!</b>\n\n👤 {username} ha scommesso <b>{amount:.2f} USDT</b> su <b>{option}</b>.\n💰 Pool aggiornato: <b>{new_pool:.2f} USDT</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not notify creator: {e}")

    # Aggiorna il messaggio corrente (DM o gruppo)
    summary = await get_bet_summary(pool, bet_uuid)
    options = _get_options(bet)
    bet_dict = dict(bet)
    bet_dict["pool_total"] = new_pool
    text = format_bet_message(bet_dict, summary)
    kb = bet_message_keyboard(bet_uuid, options, summary, BOT_USERNAME)

    # Aggiunge rigo saldo sotto il messaggio scommessa (solo in DM)
    is_private = update.effective_chat.type == "private"
    if is_private:
        text += f"\n━━━━━━━━━━━━━━━━━━━━\n💳 Il tuo saldo: <b>{new_balance:.2f} USDT</b>"

    try:
        if query.message.photo or query.message.video:
            await query.edit_message_caption(caption=text, parse_mode="HTML", reply_markup=kb)
        else:
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"Error in _execute_bet edit: {e}")
        pass

    # Aggiorna messaggio nel gruppo se diverso dalla chat corrente
    if bet.get("group_chat_id") and bet["group_chat_id"] != update.effective_chat.id:
        await _update_group_message(context.bot, pool, bet_uuid, bet, new_pool,
                                    bet["group_chat_id"], bet["message_id"])

    await query.answer(f"✅ Puntata {amount:.2f} USDT su '{option}'!", show_alert=False)


async def _update_group_message(bot, pool, bet_uuid, bet, new_pool, group_chat_id, message_id):
    """Aggiorna il messaggio della scommessa nel gruppo Telegram."""
    try:
        summary = await get_bet_summary(pool, bet_uuid)
        options = _get_options(bet)
        bet_dict = dict(bet)
        bet_dict["pool_total"] = new_pool
        text = format_bet_message(bet_dict, summary)
        kb = bet_message_keyboard(bet_uuid, options, summary, BOT_USERNAME)
        await bot.edit_message_text(
            chat_id=group_chat_id, message_id=message_id,
            text=text, parse_mode="HTML", reply_markup=kb,
        )
    except Exception as e:
        logger.warning(f"Could not update group message for {bet_uuid[:8]}: {e}")


async def cancel_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Annulla la selezione dell'importo."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Puntata annullata.")
    context.user_data.pop("pending_bet", None)
    return ConversationHandler.END
