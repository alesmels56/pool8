"""
bot/handlers/ball8.py — Handler per il minigioco Ball 8 (1-8).
FIX: Variabile user_data corretta, gestione Record asyncpg, saldo visibile.
"""
import random
import logging
import asyncio
from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db.admin import get_setting
from db.users import get_user_language, get_user
from bot.keyboards import ball8_keyboard
from utils.i18n import t

logger = logging.getLogger(__name__)

# Configurazione Gioco (Fallbacks)
DEFAULT_BET = Decimal("1.0")
MIN_BET = Decimal("0.1")

async def show_ball8(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la schermata iniziale del gioco Ball 8."""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, user_id)
    user = await get_user(pool, user_id)
    if user is None:
        await update.effective_message.reply_text("Per favore, premi /start per registrarti prima di giocare.")
        return
    balance = Decimal(str(user["balance_usdt"]))
    
    # Calcolo Moltiplicatore Dinamico
    edge_str = await get_setting(pool, "minigame_edge", "0.05")
    edge = Decimal(edge_str)
    win_multiplier = (Decimal("8.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.1"))

    # Inizializza dati gioco se non presenti
    if "ball8" not in context.user_data:
        context.user_data["ball8"] = {
            "bet": DEFAULT_BET,
            "target": 1
        }
    
    game_data = context.user_data["ball8"]
    text = _format_ball8_msg(game_data["bet"], game_data["target"], balance, lang)
    
    reply_markup = ball8_keyboard(game_data["bet"], game_data["target"], lang)
    
    if query:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        except Exception:
            await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    else:
        await update.effective_message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def handle_ball8_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce le interazioni della tastiera Ball 8."""
    query = update.callback_query
    await query.answer()
    
    if context.user_data.get("ball8_lock"):
        return

    parts = query.data.split(":")  # ball8:action:value
    action = parts[1] if len(parts) > 1 else ""
    
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, user_id)
    user = await get_user(pool, user_id)
    if user is None:
        await query.answer("Utente non trovato. Premi /start.", show_alert=True)
        return
    balance = Decimal(str(user["balance_usdt"]))

    # Recupera o inizializza i dati di gioco
    if "ball8" not in context.user_data:
        context.user_data["ball8"] = {"bet": DEFAULT_BET, "target": 1}
    game_data = context.user_data["ball8"]

    if action == "target":
        game_data["target"] = int(parts[2])
    
    elif action == "bet":
        val = parts[2]
        if val == "info":
            return
        game_data["bet"] = max(MIN_BET, game_data["bet"] + Decimal(val))
    
    elif action == "run":
        context.user_data["ball8_lock"] = True
        try:
            await _run_game(update, context, game_data, lang)
        finally:
            context.user_data["ball8_lock"] = False
        return
    
    elif action == "back":
        # Torna al menu
        from bot.keyboards import main_inline_keyboard
        await query.edit_message_text(
            t("welcome_text", lang),
            reply_markup=main_inline_keyboard(lang),
            parse_mode=ParseMode.HTML
        )
        return

    context.user_data["ball8"] = game_data
    text = _format_ball8_msg(game_data["bet"], game_data["target"], balance, lang)
    try:
        await query.edit_message_text(
            text,
            reply_markup=ball8_keyboard(game_data["bet"], game_data["target"], lang),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.warning(f"Ball8 edit failed: {e}")

async def _run_game(update: Update, context: ContextTypes.DEFAULT_TYPE, data, lang: str):
    """Esegue il round di gioco."""
    try:
        query = update.callback_query
        user_id = update.effective_user.id
        pool = context.bot_data["pool"]
        bet_amount = Decimal(str(data["bet"]))
        target = int(data["target"])
        
        # Calcolo Moltiplicatore Dinamico
        edge_str = await get_setting(pool, "minigame_edge", "0.05")
        edge = Decimal(edge_str)
        win_multiplier = (Decimal("8.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.1"))
        
        # 1. Verifica Saldo
        user = await get_user(pool, user_id)
        if user is None:
            await query.answer("Errore registrazione. Premi /start.", show_alert=True)
            return
        if Decimal(str(user["balance_usdt"])) < bet_amount:
            from bot.keyboards import insufficient_balance_keyboard
            from bot.ui import answer_and_update
            await answer_and_update(query, context, t("game_8ball_insufficient", lang), reply_markup=insufficient_balance_keyboard(lang))
            return
        
        
        # 2. Risultato Random
        result = random.randint(1, 8)
        is_win = (result == target)
        
        # 3. Transazione DB
        from db.users import record_game_result
        final_balance = await record_game_result(
            pool, 
            user_id, 
            bet_amount, 
            is_win, 
            win_multiplier
        )
        
        # 4. Feedback Visivo (Animazione emulata)
        loading_frames = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘", "🎱"]
        for frame in loading_frames:
            try:
                await query.edit_message_text(
                    f"🎰 <b>ROUND IN CORSO...</b>\n\n{frame}",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
            await asyncio.sleep(0.3)
        
        # 5. Risultato Finale
        if is_win:
            win_total = bet_amount * win_multiplier
            msg = t("game_8ball_win", lang).format(num=result, win_amount=f"{win_total:.2f}")
        else:
            msg = t("game_8ball_loss", lang).format(num=result, bet_amount=f"{bet_amount:.2f}")
        
        msg += f"\n\n💰 Nuovo Saldo: <b>{final_balance:.2f} USDT</b>"
        
        # Tastiera per giocare di nuovo o tornare
        try:
            await query.edit_message_text(
                msg, 
                reply_markup=ball8_keyboard(bet_amount, target, lang), 
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.warning(f"Ball8 result edit failed: {e}")
    except Exception as e:
        logger.exception(f"CRITICAL ERROR in _run_game: {e}")
        try:
            await update.callback_query.message.reply_text(f"❌ Errore critico nel gioco: {e}")
        except:
            pass


def _format_ball8_msg(bet: Decimal, target: int, balance: Decimal, lang: str) -> str:
    """Formatta il messaggio principale del gioco."""
    return (
        f"{t('game_8ball_title', lang)}\n\n"
        f"{t('game_8ball_descr', lang)}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Saldo Totale: <b>{balance:.2f} USDT</b>\n"
        f"{t('game_8ball_bet', lang).format(amount=f'{bet:.1f}')}\n"
        f"{t('game_8ball_target', lang).format(target=target)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
