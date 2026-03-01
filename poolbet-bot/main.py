import asyncio
import logging
import sys
import os
import io

# Forza UTF-8 per Python
os.environ["PYTHONIOENCODING"] = "utf-8"

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    TypeHandler,
)

import re
from config import BOT_TOKEN, DATABASE_URL, REDIS_URL, WEBHOOK_URL, WEBHOOK_PORT, ADMIN_IDS
from db.connection import create_pool, close_pool
from utils.cache import init_redis
from blockchain.listener import start_listener
from scheduler.jobs import build_scheduler
from utils.logger_config import setup_logging
from utils.alerts import log_and_alert
import traceback
import json

# Setup logging rotante
logger = setup_logging("MainBot", "main.log")

# Handler imports
from bot.handlers.start import start_handler, help_handler
from bot.handlers.create_bet import (
    start_create_bet, receive_question, receive_hashtag,
    receive_media, skip_media,
    receive_option, options_done,
    receive_min_bet, receive_duration, receive_privacy, confirm_bet,
    ASK_QUESTION, ASK_HASHTAG, ASK_MEDIA, ASK_OPTIONS,
    ASK_MIN_BET, ASK_DURATION, ASK_PRIVACY, CONFIRM_BET,
)
from bot.handlers.participate import (
    handle_pick, handle_vote, handle_custom_amount_prompt, handle_custom_amount_input,
    cancel_vote, AWAITING_CUSTOM_AMOUNT,
)
from bot.handlers.close_bet import handle_close_bet, handle_confirm_close_bet, handle_winner_selection
from bot.handlers.challenge import handle_challenge_start
from bot.handlers.my_bets import list_bets_handler, handle_bets_pagination
from bot.handlers.admin import admin_router, admin_list_challenged, admin_resolve_challenge
from bot.handlers.language import language_command, handle_set_language
from bot.handlers.explore import handle_explore, explore_start_search, explore_receive_search_tag, explore_reset_search, ASK_SEARCH_TAG
from bot.handlers.ball8 import show_ball8, handle_ball8_callback
from bot.handlers.mines import show_mines, handle_mines_setup, handle_mines_play
from bot.handlers.leaderboard import show_leaderboard
from bot.handlers.wallet import (
    show_balance, show_deposit_info, show_qr, show_history, show_copy_address,
    start_withdrawal, withdrawal_amount, withdrawal_address, withdrawal_confirm,
    cancel_handler, test_faucet_handler, show_referral,
    WITHDRAW_AMOUNT, WITHDRAW_ADDRESS, WITHDRAW_CONFIRM,
)
from bot.handlers.daily import handle_daily_faucet
from bot.handlers.start import start_handler, help_handler, show_minigames_menu
from bot.handlers.language import handle_set_language
from bot.handlers.wallet import show_balance, show_deposit_info, withdrawal_amount, withdrawal_address, withdrawal_confirm, start_withdrawal, cancel_handler, show_history, test_faucet_handler, show_referral, show_copy_address, show_qr
from bot.handlers.daily import handle_daily_faucet
from bot.handlers.coinflip import show_coinflip_menu, handle_coinflip_pick, handle_coinflip_bet
from bot.handlers.dice import show_dice_menu, handle_dice_pick, handle_dice_bet
from bot.handlers.tip import start_tip, tip_receive_username, tip_receive_amount, ASK_TIP_USER, ASK_TIP_AMOUNT
from bot.handlers.groups import inline_query_handler
from utils.i18n import TRANSLATIONS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# Non sovrascrivere il logger di setup_logging
# logger = logging.getLogger(__name__)

import time
from telegram.ext import ApplicationHandlerStop

_USER_LAST_ACTION = {}
RATE_LIMIT_SECONDS = 1.0

async def debug_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logga ogni aggiornamento in entrata, blocca lo spam e gli utenti bannati."""
    try:
        user = update.effective_user
        if not user:
            return

        uid = user.id
        msg_text = "None"
        if update.message and update.message.text:
            msg_text = update.message.text
        elif update.callback_query:
            msg_text = f"CB:{update.callback_query.data}"
            
        logger.info(f">>> [UPDATE DETECTED] From: {uid} | Data: {msg_text}")
        
        # 1. Rate Limiting Anti-Spam (0.3 action / sec, skip for admins)
        now = time.time()
        last_action = _USER_LAST_ACTION.get(uid, 0)
        if uid not in ADMIN_IDS and (now - last_action < 0.3):
            logger.warning(f"RATE LIMIT: Dropping spam from {uid}")
            raise ApplicationHandlerStop
        _USER_LAST_ACTION[uid] = now
        
        # Check Ban
        pool = context.bot_data.get("pool")
        if pool:
            is_banned = await pool.fetchval("SELECT is_banned FROM users WHERE user_id = $1", uid)
            if is_banned:
                logger.warning(f"BLOCKED: Banned user {uid} attempted to interact.")
                # Opzionale: rispondi al ban
                if update.message:
                    await update.message.reply_text("🚫 <b>SEI STATO BANNATO DA POOLBET BOT</b>", parse_mode="HTML")
                elif update.callback_query:
                    await update.callback_query.answer("🚫 Account Bannato", show_alert=True)
                raise ApplicationHandlerStop
                
    except ApplicationHandlerStop:
        raise
    except Exception as e:
        logger.error(f">>> [DEBUG] Error in debug_update_handler: {e}")

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Logga errori non gestiti e avvisa l'admin."""
    error_msg = f"Exception while handling an update: {context.error}"
    log_and_alert(error_msg, logger)

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Si è verificato un errore interno. Riprova più tardi."
            )
        except:
            pass

def _build_regex(key: str) -> str:
    """Costruisce una regex che include le traduzioni per tutte le lingue per una data chiave."""
    all_translated = []
    for lang_dict in TRANSLATIONS.values():
        if key in lang_dict:
            val = lang_dict[key]
            # Pulizia minima: rimuove whitespace extra
            all_translated.append(val.strip())
    
    unique_vals = list(set(all_translated))
    if not unique_vals:
        return "^$"
    
    # re.escape è sicuro, ma permettiamo match flessibile per whitespace
    escaped = [re.escape(v) for v in unique_vals]
    pattern = "^(" + "|".join(escaped) + ")$"
    logger.debug(f"Regex for {key}: {pattern}")
    return pattern

def register_handlers(app: Application) -> None:
    logger.info(">>> [DEBUG] Registering handlers...")
    
    # Logger Globale - Priorità Massima (group=-1)
    app.add_handler(TypeHandler(Update, debug_update_handler), group=-1)
    # Error Handler
    app.add_error_handler(global_error_handler)

    # Command Handlers
    app.add_handler(CommandHandler("start", start_handler))
    logger.info("Registered /start")
    from bot.handlers.admin import (
        admin_router, admin_stats, admin_credit, admin_user_info, 
        admin_list_expired, admin_reset_bets, admin_top_users, 
        admin_broadcast, admin_treasury, admin_exit_strategy,
        admin_callback_handler,
        admin_ban, admin_unban, admin_debit, admin_delete_bet,
        admin_set_setting, admin_settings_menu, whoami_handler,
        admin_recv_id, admin_recv_amount, admin_recv_note,
        ADMIN_ASK_ID, ADMIN_ASK_AMOUNT, ADMIN_ASK_NOTE
    )
    
    admin_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback_handler, pattern="^admin:")],
        states={
            ADMIN_ASK_ID:     [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_recv_id)],
            ADMIN_ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_recv_amount)],
            ADMIN_ASK_NOTE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_recv_note)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_router, pattern="^admin:back$"),
            CommandHandler("admin", admin_router)
        ],
        per_chat=False,
        name="admin_actions"
    )
    app.add_handler(admin_conv)
    
    app.add_handler(CommandHandler("admin", admin_router))
    app.add_handler(CommandHandler("admin_stats", admin_stats))
    app.add_handler(CommandHandler("admin_credita", admin_credit))
    app.add_handler(CommandHandler("admin_utente", admin_user_info))
    app.add_handler(CommandHandler("admin_scadute", admin_list_expired))
    app.add_handler(CommandHandler("admin_reset", admin_reset_bets))
    app.add_handler(CommandHandler("admin_top", admin_top_users))
    app.add_handler(CommandHandler("admin_broadcast", admin_broadcast))
    app.add_handler(CommandHandler("admin_treasury", admin_treasury))
    app.add_handler(CommandHandler("admin_exit", admin_exit_strategy))
    
    app.add_handler(CommandHandler("admin_ban", admin_ban))
    app.add_handler(CommandHandler("admin_unban", admin_unban))
    app.add_handler(CommandHandler("admin_debita", admin_debit))
    app.add_handler(CommandHandler("admin_delete_bet", admin_delete_bet))
    app.add_handler(CommandHandler("admin_set_setting", admin_set_setting))
    app.add_handler(CommandHandler("admin_settings", admin_settings_menu))
    app.add_handler(CommandHandler("admin_contese", admin_list_challenged))
    app.add_handler(CommandHandler("admin_risolvi", admin_resolve_challenge))
    
    app.add_handler(CommandHandler("whoami", whoami_handler))
    
    app.add_handler(CommandHandler("faucet", test_faucet_handler))

    app.add_handler(MessageHandler(filters.Regex(_build_regex("menu_balance")), show_balance))

    withdraw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_withdrawal, pattern="^wallet:withdraw$")],
        states={
            WITHDRAW_AMOUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_amount)],
            WITHDRAW_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdrawal_address)],
            WITHDRAW_CONFIRM: [CallbackQueryHandler(withdrawal_confirm, pattern="^(confirm:withdraw|cancel)$")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_handler, pattern="^cancel$"),
            CommandHandler("start", start_handler),
        ],
        per_chat=False,
    )
    app.add_handler(withdraw_conv)

    create_bet_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(_build_regex("menu_create")), start_create_bet),
            CallbackQueryHandler(start_create_bet, pattern="^menu:create$"),
        ],
        states={
            ASK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)],
            ASK_HASHTAG:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_hashtag)],
            ASK_MEDIA: [
                MessageHandler((filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, receive_media),
                CallbackQueryHandler(skip_media, pattern="^media:skip$"),
            ],
            ASK_OPTIONS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_option), CallbackQueryHandler(options_done, pattern="^options_done$")],
            ASK_MIN_BET:  [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_min_bet)],
            ASK_DURATION: [CallbackQueryHandler(receive_duration, pattern="^duration:")],
            ASK_PRIVACY:  [CallbackQueryHandler(receive_privacy, pattern="^privacy:")],
            CONFIRM_BET:  [CallbackQueryHandler(confirm_bet, pattern="^(confirm:bet|cancel)$")],
        },
        fallbacks=[CallbackQueryHandler(cancel_handler, pattern="^cancel$")],
        per_chat=False,
    )
    app.add_handler(create_bet_conv)

    # ── BET ACTIONS — PRIORITY GROUP -2 (never swallowed by ConversationHandlers) ──
    app.add_handler(CallbackQueryHandler(handle_pick,            pattern="^bet_pick:"),  group=-2)
    app.add_handler(CallbackQueryHandler(handle_vote,            pattern="^bet_vote:"),  group=-2)
    app.add_handler(CallbackQueryHandler(handle_close_bet,       pattern="^bet_close:"), group=-2)
    app.add_handler(CallbackQueryHandler(handle_confirm_close_bet, pattern="^confirm:close_bet:"), group=-2)
    app.add_handler(CallbackQueryHandler(handle_winner_selection, pattern="^bet_winner:"), group=-2)
    app.add_handler(CallbackQueryHandler(handle_challenge_start,  pattern="^bet_challenge_start:"), group=-2)

    app.add_handler(CallbackQueryHandler(show_balance,      pattern="^wallet:balance$"))
    app.add_handler(CallbackQueryHandler(show_deposit_info, pattern="^wallet:deposit_info$"))
    app.add_handler(CallbackQueryHandler(show_qr,           pattern="^wallet:qr$"))
    app.add_handler(CallbackQueryHandler(show_history,      pattern="^wallet:history$"))

    custom_amount_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_custom_amount_prompt, pattern="^bet_custom:")],
        states={AWAITING_CUSTOM_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_amount_input)]},
        fallbacks=[CallbackQueryHandler(cancel_vote, pattern="^cancel$")],
        per_chat=False,
    )
    app.add_handler(custom_amount_conv, group=-2)

    app.add_handler(CallbackQueryHandler(cancel_vote, pattern="^cancel_vote$"))
    app.add_handler(CallbackQueryHandler(handle_bets_pagination, pattern="^mybets:"))
    app.add_handler(CallbackQueryHandler(handle_set_language, pattern="^setlang:"))
    app.add_handler(CallbackQueryHandler(handle_explore, pattern="^explore:(page|ignore)"))
    app.add_handler(CallbackQueryHandler(explore_reset_search, pattern="^explore:reset_search$"))
    
    explore_search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(explore_start_search, pattern="^explore:search$")],
        states={ASK_SEARCH_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, explore_receive_search_tag)]},
        fallbacks=[
            CallbackQueryHandler(cancel_handler, pattern="^cancel$"),
            CommandHandler("start", start_handler),
        ],
        per_chat=False,
    )
    app.add_handler(explore_search_conv)

    tip_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_tip, pattern="^wallet:tip$")],
        states={
            ASK_TIP_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, tip_receive_username)],
            ASK_TIP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, tip_receive_amount)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_handler, pattern="^cancel$"),
            CommandHandler("start", start_handler),
        ],
        per_chat=False,
    )
    app.add_handler(tip_conv)
    
    app.add_handler(CallbackQueryHandler(show_ball8, pattern="^menu:ball8$"))
    app.add_handler(CallbackQueryHandler(handle_ball8_callback, pattern="^ball8:"))
    app.add_handler(CallbackQueryHandler(show_mines, pattern="^menu:mines$"))
    app.add_handler(CallbackQueryHandler(handle_mines_setup, pattern="^mines:setup:"))
    app.add_handler(CallbackQueryHandler(handle_mines_play, pattern="^mines:(play:|click:|ignore)"))
    
    app.add_handler(CallbackQueryHandler(show_minigames_menu, pattern="^menu:minigames$"))
    app.add_handler(CallbackQueryHandler(show_coinflip_menu, pattern="^menu:coinflip$"))
    app.add_handler(CallbackQueryHandler(handle_coinflip_pick, pattern="^coin:pick:"))
    app.add_handler(CallbackQueryHandler(handle_coinflip_bet, pattern="^coin:bet:"))
    
    app.add_handler(CallbackQueryHandler(show_dice_menu, pattern="^menu:dice$"))
    app.add_handler(CallbackQueryHandler(handle_dice_pick, pattern="^dice:pick:"))
    app.add_handler(CallbackQueryHandler(handle_dice_bet, pattern="^dice:bet:"))

    app.add_handler(CallbackQueryHandler(show_qr,            pattern="^wallet:qr$"))
    app.add_handler(CallbackQueryHandler(show_referral,      pattern="^wallet:referral$"))
    app.add_handler(CallbackQueryHandler(show_copy_address,  pattern="^wallet:copy_address$"))
    app.add_handler(CallbackQueryHandler(show_leaderboard,   pattern="^menu:leaderboard$"))
    app.add_handler(CallbackQueryHandler(handle_daily_faucet,pattern="^daily:faucet$"))
    app.add_handler(CallbackQueryHandler(list_bets_handler, pattern="^menu:mybets$"))
    app.add_handler(CallbackQueryHandler(handle_explore,    pattern="^menu:explore$"))
    app.add_handler(CallbackQueryHandler(help_handler,      pattern="^menu:help$"))
    app.add_handler(CallbackQueryHandler(help_handler,      pattern="^menu:main$"))

    app.add_handler(MessageHandler(filters.Regex(_build_regex("menu_explore")), handle_explore))
    app.add_handler(MessageHandler(filters.Regex(_build_regex("btn_game_8ball")), show_ball8))
    app.add_handler(MessageHandler(filters.Regex(_build_regex("btn_game_mines")), show_mines))
    app.add_handler(MessageHandler(filters.Regex(_build_regex("menu_mybets")),  list_bets_handler))
    app.add_handler(MessageHandler(filters.Regex(_build_regex("menu_help")),    help_handler))
    
    from telegram.ext import InlineQueryHandler
    app.add_handler(InlineQueryHandler(inline_query_handler))
    
    logger.info(">>> [DEBUG] Handlers registered.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks here.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python traceback list of strings, which we can join together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some un-escaped tags which telegram will ignore
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"🚨 <b>An exception was raised while handling an update</b>\n"
        f"<pre>update = {json.dumps(update_str, indent=2, ensure_ascii=False)[:1000]}</pre>\n\n"
        f"<pre>context.chat_data = {json.dumps(str(context.chat_data), indent=2, ensure_ascii=False)}</pre>\n\n"
        f"<pre>context.user_data = {json.dumps(str(context.user_data), indent=2, ensure_ascii=False)}</pre>\n\n"
        f"<pre>{tb_string[:3000]}</pre>"
    )

    # Finally, send the message to the first admin
    from config import ADMIN_IDS
    if ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_IDS[0], text=message, parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Could not send error message to admin: {e}")

async def post_init(app: Application) -> None:
    """Inizializzazione post-startup: DB, Redis, Scheduler, Listener."""
    logger.info(">>> [DEBUG] Initializing app components (post_init)...")
    
    # Database
    pool = await create_pool()
    app.bot_data["pool"] = pool
    logger.info(">>> [DEBUG] Database connected.")

    # Redis
    await init_redis(REDIS_URL)

    # Scheduler - DISABILITATO (ora in worker_scheduler.py)
    if os.getenv("RUN_SCHEDULER", "false").lower() == "true":
        scheduler = build_scheduler(pool, app.bot)
        scheduler.start()
        app.bot_data["scheduler"] = scheduler
    else:
        logger.info(">>> [DEBUG] Scheduler NOT started (Decoupled Mode).")

    # Blockchain Listener - DISABILITATO (ora in worker_blockchain.py)
    if os.getenv("RUN_BLOCKCHAIN", "false").lower() == "true":
        asyncio.create_task(start_listener(pool, app.bot))
    else:
        logger.info(">>> [DEBUG] Blockchain Listener NOT started (Decoupled Mode).")

    # Notifica Admin
    from config import ADMIN_IDS
    if ADMIN_IDS:
        try:
            await app.bot.send_message(chat_id=ADMIN_IDS[0], text="🚀 *Bot ONLINE e Pronto!*", parse_mode="Markdown")
            logger.info(f">>> [DEBUG] Startup message sent to admin {ADMIN_IDS[0]}")
        except Exception as e:
            logger.warning(f">>> [DEBUG] Could not send startup message: {e}")

def run_bot_sync():
    # ── [CRITICO] Check Manuale Token per Diagnosi ──
    import requests
    try:
        res = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe").json()
        if not res.get("ok"):
            logger.error("❌ ERROR: IL TOKEN TELEGRAM NON È VALIDO O È SCADUTO!")
            logger.error(f"Dettaglio Errore: {res.get('description', 'Nessuna descrizione available')}")
            logger.error("Per favore, richiedi un nuovo token a @BotFather e aggiorna il file .env.")
            return
        else:
            logger.info(f"✅ Token Verificato. Bot Identity: @{res['result']['username']}")
    except Exception as e:
        logger.warning(f"⚠️ Impossibile verificare il token via web: {e}. Procedo comunque...")

    if not BOT_TOKEN or "your_telegram_bot_token" in BOT_TOKEN:
        logger.error(">>> [DEBUG] CRITICAL: BOT_TOKEN invalid!")
        return

    logger.info(">>> [DEBUG] Building application...")
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_error_handler(error_handler)
    register_handlers(app)

    logger.info(">>> [DEBUG] Starting bot with app.run_polling (CLEAN START)...")
    # run_polling() è BLOCCANTE in PTB v20 e gestisce il proprio loop
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        run_bot_sync()
    except Exception as e:
        print(f">>> [DEBUG] UNHANDLED EXCEPTION IN MAIN: {e}", flush=True)
        import traceback
        traceback.print_exc()
