"""
bot/handlers/start.py — Handler /start con supporto deep-link bet_<UUID>.
"""
import logging
from decimal import Decimal
from telegram import Update
from telegram.ext import ContextTypes

from db.users import register_user, get_user, get_user_language, credit_referral_bonus
from db.bets import get_bet
from db.participations import get_bet_summary
from blockchain.wallet import generate_wallet_for_user
from bot.keyboards import main_keyboard, main_inline_keyboard, bet_message_keyboard, close_bet_keyboard, minigames_keyboard
from bot.ui import update_menu, answer_and_update, delete_user_message
from utils.formatting import format_bet_message
from utils.deeplink import parse_start_param
from utils.i18n import t
from config import BOT_USERNAME

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Gestisce /start con e senza parametro deep-link.
    """
    print(f">>> [DEBUG START.PY] Calling start_handler for {update.effective_user.id}", flush=True)
    logger.info(f"START HANDLER TRIGGERED by user {update.effective_user.id}")
    user = update.effective_user
    pool = context.bot_data["pool"]

    # Controlla parametro deep-link
    args = context.args
    referred_by = None
    parsed = None
    if args:
        parsed = parse_start_param(args[0])
        if parsed and parsed[0] == "ref":
            try:
                ref_id = int(parsed[1])
                if ref_id != user.id:
                    referred_by = ref_id
            except: pass

    # Registra utente (idempotente)
    logger.info(f"Checking existence for user {user.id}...")
    existing = await get_user(pool, user.id)
    if existing is None:
        logger.info(f"User {user.id} NOT found. Generating wallet...")
        wallet_address = generate_wallet_for_user(user.id % (2**31))
        logger.info(f"Registering user {user.id} with wallet {wallet_address}...")
        await register_user(pool, user.id, user.username, wallet_address, referred_by)
        logger.info(f"New user registered: {user.id} (ref: {referred_by})")
        if referred_by:
            try:
                logger.info(f"Applying referral bonus for {referred_by}...")
                from db.users import credit_referral_bonus
                await credit_referral_bonus(pool, referred_by, Decimal("1.00"))
                logger.info(f"Referral bonus applied for {referred_by}.")
                await context.bot.send_message(
                    chat_id=referred_by,
                    text=(
                        f"👥 <b>Nuovo referral!</b>\n"
                        f"Un utente si è iscritto con il tuo link.\n"
                        f"🎁 Hai ricevuto <b>+1.00 USDT</b> di bonus (spendibile, non prelevabile)!"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Referral bonus failed for {referred_by}: {e}")
    else:
        logger.info(f"User {user.id} already exists.")
    
    logger.info(f"Retrieving language for user {user.id}...")
    lang = await get_user_language(pool, user.id)
    logger.info(f"Language for user {user.id} is: {lang}")

    # Se deep-link scommessa, mostrala e interrompi
    if parsed and parsed[0] == "bet":
        try:
            await _show_bet_card(update, context, pool, parsed[1], lang)
            return
        except Exception as e:
            logger.exception(f"Errore caricamento bet card: {e}")

    # Messaggio di benvenuto — invialo e salvane l'ID come menu persistente
    welcome_msg = t("welcome_text", lang)
    
    # Ticker Big Wins
    try:
        from db.transactions import get_global_big_wins
        big_wins = await get_global_big_wins(pool, 3)
        if big_wins:
            ticker_parts = []
            for bw in big_wins:
                user_label = f"@{bw['username']}" if bw['username'] else f"ID:{bw['user_id']}"
                ticker_parts.append(f"{user_label} ({bw['amount']:.1f} USDT)")
            
            ticker_text = t("welcome_ticker", lang, ticker=" | ".join(ticker_parts))
            welcome_msg = ticker_text + welcome_msg
    except Exception as e:
        logger.warning(f"Errore ticker big wins: {e}")

    msg = await update_menu(
        context,
        update.effective_chat.id,
        welcome_msg,
        reply_markup=main_inline_keyboard(lang),
    )
    logger.info(f"Welcome sent to user {user.id}, menu_msg_id={msg.message_id if msg else None}")


async def _show_bet_card(update: Update, context: ContextTypes.DEFAULT_TYPE, pool, bet_uuid: str, lang: str = "it") -> None:
    """Mostra la scheda scommessa con log robusti per debugging."""
    try:
        logger.info(f"Start _show_bet_card for {bet_uuid}")
        
        # 1. Recupero dal DB
        bet = await get_bet(pool, bet_uuid)
        if bet is None:
            logger.warning(f"Bet {bet_uuid} non trovata nel database.")
            await update.effective_message.reply_text(t("bet_not_found", lang))
            return
        
        # 2. Parsing opzioni (sicurezza per JSON/JSONB)
        options_raw = bet["options"]
        if isinstance(options_raw, str):
            import json
            options_dict = json.loads(options_raw)
        else:
            options_dict = options_raw
        
        options = list(options_dict.keys())
        logger.info(f"Bet {bet_uuid} options: {options}")

        # 3. Sommario partecipazioni
        summary = await get_bet_summary(pool, bet_uuid)
        logger.info(f"Bet {bet_uuid} summary: {summary}")

        # 4. Formattazione testo
        try:
            text = format_bet_message(bet, summary, lang)
        except Exception as fe:
            logger.error(f"Errore format_bet_message: {fe}")
            text = f"❓ <b>{bet['question']}</b>\n\n(Errore formattazione dettagli)"

        # 5. Costruzione Tastiera
        try:
            keyboard = bet_message_keyboard(bet_uuid, options, summary, BOT_USERNAME, lang)
            
            # Aggiungi bottone "Torna al menu"
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            extra_rows = list(keyboard.inline_keyboard)
            extra_rows.append([InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")])
            keyboard = InlineKeyboardMarkup(extra_rows)

            # Bottone chiusura per il creatore
            if update.effective_user.id == bet["creator_id"]:
                close_btn = [[InlineKeyboardButton(t("btn_close_bet", lang), callback_data=f"bet_close:{bet_uuid}")]]
                new_inline = list(keyboard.inline_keyboard) + close_btn
                keyboard = InlineKeyboardMarkup(new_inline)
        except Exception as ke:
            logger.error(f"Errore creazione tastiera: {ke}")
            keyboard = main_inline_keyboard(lang)

        # 6. Invio Messaggio (Media o Testo)
        media_id = bet.get("media_file_id")
        media_type = bet.get("media_type")
        try:
            if media_id:
                if media_type == "video":
                    await update.effective_message.reply_video(
                        video=media_id,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
                else:
                    await update.effective_message.reply_photo(
                        photo=media_id,
                        caption=text,
                        parse_mode="HTML",
                        reply_markup=keyboard,
                    )
            else:
                await update.effective_message.reply_text(
                    text,
                    parse_mode="HTML",
                    reply_markup=keyboard,
                )
        except Exception as me:
            logger.error(f"Errore invio media: {me}. Provo fallback testo.")
            await update.effective_message.reply_text(
                text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            
    except Exception as e:
        logger.exception(f"ECCEZIONE CRITICA in _show_bet_card: {e}")
        # Propaga l'errore per essere catturato dall'handler principale
        raise e


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra il menu principale (edit-in-place)."""
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, update.effective_user.id)
    if update.callback_query:
        await answer_and_update(
            update.callback_query, context,
            t("welcome_text", lang),
            reply_markup=main_inline_keyboard(lang),
        )
    else:
        await update_menu(
            context, update.effective_chat.id,
            t("welcome_text", lang),
            reply_markup=main_inline_keyboard(lang),
        )


async def show_minigames_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra il menu dei minigiochi (🕹️ Minigiochi)."""
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, update.effective_user.id)
    text = "🕹️ <b>Minigiochi Pool8</b>\n\nScegli un gioco veloce per tentare la fortuna:"
    
    if update.callback_query:
        await answer_and_update(update.callback_query, context, text, reply_markup=minigames_keyboard(lang))
    else:
        await update_menu(context, update.effective_chat.id, text, reply_markup=minigames_keyboard(lang))
