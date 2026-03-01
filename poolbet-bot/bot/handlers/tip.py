import logging
from decimal import Decimal
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler

from db.users import get_balance_stats, get_user_language, send_tip, get_user
from utils.i18n import t
from bot.ui import update_menu, delete_user_message

logger = logging.getLogger(__name__)

ASK_TIP_USER, ASK_TIP_AMOUNT = range(2)

async def start_tip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inizia il flusso per inviare una mancia."""
    query = update.callback_query
    await query.answer()

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel")]
    ])
    
    await update_menu(context, update.effective_chat.id, t("tip_ask_username", lang), reply_markup=kb)
    return ASK_TIP_USER

async def tip_receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve l'username del destinatario."""
    text_input = update.message.text.strip()
    await delete_user_message(update.message)
    
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)
    
    # Salvo l'username in context per dopo
    clean_username = text_input.replace("@", "")
    context.user_data["tip_receiver"] = clean_username
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel")]
    ])
    
    msg_formatted = t("tip_ask_amount", lang).replace("{username}", clean_username)
    await update_menu(context, update.effective_chat.id, msg_formatted, reply_markup=kb)
    return ASK_TIP_AMOUNT

async def tip_receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve l'importo e finalizza la mancia."""
    text_input = update.message.text.strip()
    await delete_user_message(update.message)
    
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)
    receiver_username = context.user_data.get("tip_receiver")
    
    try:
        amount = Decimal(text_input.replace(",", "."))
        if amount <= 0:
            raise ValueError
    except:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel")]])
        await update_menu(context, update.effective_chat.id, "❌ Importo non valido. Riprova:", reply_markup=kb)
        return ASK_TIP_AMOUNT
        
    # Esegue transazione
    success, msg_key, receiver_id, net_amount = await send_tip(pool, user_id, receiver_username, amount)
    
    if not success:
        # Errore (insufficient funds, self tip, etc.)
        err_msg = t(msg_key, lang)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back_menu", lang), callback_data="wallet:balance")]])
        await update_menu(context, update.effective_chat.id, err_msg, reply_markup=kb)
        context.user_data.pop("tip_receiver", None)
        return ConversationHandler.END
        
    # Successo
    success_msg = t("tip_success", lang).replace("{amount}", f"{amount:.2f}").replace("{username}", receiver_username)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back_menu", lang), callback_data="wallet:balance")]])
    await update_menu(context, update.effective_chat.id, success_msg, reply_markup=kb)
    
    # Invia notifica al destinatario
    if receiver_id and net_amount:
        try:
            receiver_lang = await get_user_language(pool, receiver_id)
            sender_record = await get_user(pool, user_id)
            sender_username = sender_record["username"] if sender_record and sender_record["username"] else str(user_id)
            
            notif_msg = t("tip_received", receiver_lang).replace("{amount}", f"{net_amount:.2f}").replace("{sender}", sender_username)
            # Send notification directly as a new message to the receiver
            await context.bot.send_message(chat_id=receiver_id, text=notif_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send tip notification to {receiver_id}: {e}")
            
    context.user_data.pop("tip_receiver", None)
    return ConversationHandler.END
