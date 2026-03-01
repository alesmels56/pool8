"""
bot/handlers/wallet.py — Gestione saldo crediti, deposito, prelievo.
"""
import io
import logging
from decimal import Decimal, InvalidOperation
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from db.users import get_balance_stats, execute_withdrawal, get_user_language
from db.transactions import get_history, confirm_tx, fail_tx
from bot.keyboards import balance_keyboard, main_keyboard
from bot.handlers.admin import admin_only
from bot.ui import update_menu, answer_and_update, delete_user_message
from blockchain.usdt import send_usdt
from utils.formatting import format_balance_message, format_history
from utils.qr import generate_qr_bytes
from utils.deeplink import make_ref_link
from utils.i18n import t
from config import MIN_WITHDRAWAL, BOT_USERNAME
from db.admin import get_setting

logger = logging.getLogger(__name__)

# Stati ConversationHandler prelievo
WITHDRAW_AMOUNT, WITHDRAW_ADDRESS, WITHDRAW_CONFIRM = range(3)


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la schermata crediti (edit-in-place)."""
    pool = context.bot_data["pool"]
    stats = await get_balance_stats(pool, update.effective_user.id)

    if stats is None:
        text = "❌ Profilo non trovato. Usa /start per registrarti."
        if update.callback_query:
            await answer_and_update(update.callback_query, context, text)
        else:
            await update_menu(context, update.effective_chat.id, text)
        return

    text = format_balance_message(stats)
    trust = stats.get("trust_score", 50)
    trust_bar = "🟢" * (trust // 20) + "⚪" * (5 - trust // 20)
    text += f"\n\n🛡️ Affidabilità: <b>{trust}%</b> {trust_bar}"

    if update.callback_query:
        await answer_and_update(update.callback_query, context, text, reply_markup=balance_keyboard())
    else:
        await update_menu(context, update.effective_chat.id, text, reply_markup=balance_keyboard())


async def show_deposit_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra indirizzo di deposito e istruzioni (edit-in-place)."""
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)
    stats = await get_balance_stats(pool, user_id)
    if stats is None:
        if update.callback_query:
            await update.callback_query.answer("Profilo non trovato.", show_alert=True)
        return
    address = stats["wallet_address"]
    text = t("deposit_tutorial", lang, address=address)
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back_menu", lang), callback_data="wallet:balance")]])
    if update.callback_query:
        await answer_and_update(update.callback_query, context, text, reply_markup=kb)
    else:
        await update_menu(context, update.effective_chat.id, text, reply_markup=kb)


async def show_copy_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra l'indirizzo di deposito come alert cliccabile (copia)."""
    query = update.callback_query
    pool = context.bot_data["pool"]
    stats = await get_balance_stats(pool, update.effective_user.id)
    if stats is None:
        await query.answer("Profilo non trovato. Usa /start.", show_alert=True)
        return
    address = stats["wallet_address"]
    await query.answer(f"📋 Il tuo indirizzo:\n{address}", show_alert=True)


async def show_qr(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra il QR code come messaggio persistente (foto)."""
    query = update.callback_query
    pool = context.bot_data["pool"]
    stats = await get_balance_stats(pool, update.effective_user.id)
    if stats is None:
        if query:
            await query.answer("Profilo non trovato. Premi /start.", show_alert=True)
        return
    address = stats["wallet_address"]
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    lang = await get_user_language(pool, update.effective_user.id)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back_menu", lang), callback_data="wallet:balance")]])
    qr_bytes = generate_qr_bytes(address)
    import io as _io
    # Invia QR come messaggio persistente con media
    if query:
        try:
            await query.answer()
        except Exception:
            pass
    await update_menu(
        context, update.effective_chat.id,
        f"📷 <b>QR del tuo indirizzo</b>\n<code>{address}</code>",
        reply_markup=kb,
        media_file_id=None,  # QR è generato dinamicamente, va inviato come foto diretta
    )
    # Invia anche la foto QR come allegato separato (non persistente)
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=_io.BytesIO(qr_bytes),
            caption=f"<code>{address}</code>",
            parse_mode="HTML",
        )
    except Exception:
        pass


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra lo storico movimenti (edit-in-place)."""
    pool = context.bot_data["pool"]
    txs = await get_history(pool, update.effective_user.id, limit=15)
    from utils.i18n import t
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    lang = await get_user_language(pool, update.effective_user.id)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(t("btn_back_menu", lang), callback_data="wallet:balance")]])
    text = format_history(txs) if txs else "📊 Nessun movimento ancora."
    if update.callback_query:
        await answer_and_update(update.callback_query, context, text, reply_markup=kb)
    else:
        await update_menu(context, update.effective_chat.id, text, reply_markup=kb)


# ── Flusso Prelievo ───────────────────────────────────────

async def start_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1 prelievo: chiede l'importo."""
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)
    stats = await get_balance_stats(pool, user_id)
    if stats is None:
        if update.callback_query:
            await answer_and_update(update.callback_query, context, t("err_profile", lang))
        return ConversationHandler.END
    balance = Decimal(str(stats["saldo_disponibile"]))

    if balance < MIN_WITHDRAWAL:
        text = (
            f"❌ <b>Saldo insufficiente per il prelievo.</b>\n\n"
            f"Minimo richiesto: <b>{MIN_WITHDRAWAL:.2f} USDT</b>\n"
            f"Il tuo saldo: <b>{balance:.2f} USDT</b>"
        )
        if update.callback_query:
            await answer_and_update(update.callback_query, context, text)
        return ConversationHandler.END

    fee_str = await get_setting(pool, "withdraw_fee", "1.0")
    fee_withdrawal = Decimal(fee_str)

    text = (
        f"💸 <b>Prelievo</b>\n\n"
        f"Il tuo saldo: <b>{balance:.2f} USDT</b>\n"
        f"Fee prelievo: <b>{fee_withdrawal:.2f} USDT</b> (gas Polygon)\n\n"
        f"Inserisci l'importo da prelevare (min {MIN_WITHDRAWAL:.2f} USDT):"
    )
    if update.callback_query:
        await answer_and_update(update.callback_query, context, text)
    else:
        await update_menu(context, update.effective_chat.id, text)
    return WITHDRAW_AMOUNT


async def withdrawal_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: riceve l'importo, chiede l'indirizzo destinatario."""
    try:
        amount = Decimal(update.message.text.strip().replace(",", "."))
        if amount <= 0:
            raise InvalidOperation
    except InvalidOperation:
        await update.message.reply_text("❌ Importo non valido. Inserisci un numero positivo (es. 25.00):")
        return WITHDRAW_AMOUNT

    pool = context.bot_data["pool"]
    stats = await get_balance_stats(pool, update.effective_user.id)
    balance = Decimal(str(stats["saldo_disponibile"]))
    
    fee_str = await get_setting(pool, "withdraw_fee", "1.0")
    fee_withdrawal = Decimal(fee_str)
    
    gross = amount + fee_withdrawal

    if balance < gross:
        await update.message.reply_text(
            f"❌ Saldo insufficiente.\n"
            f"Importo + fee: {gross:.2f} USDT | Saldo: {balance:.2f} USDT"
        )
        return WITHDRAW_AMOUNT

    context.user_data["withdraw_amount"] = str(amount)
    context.user_data["withdraw_gross"] = str(gross)
    context.user_data["withdraw_fee"] = str(fee_withdrawal)

    await update.message.reply_text(
        f"📥 Inserisci l'indirizzo Polygon (0x...) su cui ricevere <b>{amount:.2f} USDT</b>:",
        parse_mode="HTML",
    )
    return WITHDRAW_ADDRESS


async def withdrawal_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3: riceve indirizzo, mostra riepilogo con fee."""
    address = update.message.text.strip()
    if not address.startswith("0x") or len(address) != 42:
        await update.message.reply_text("❌ Indirizzo non valido. Deve essere un address Polygon (0x...):")
        return WITHDRAW_ADDRESS

    context.user_data["withdraw_address"] = address
    amount = Decimal(context.user_data["withdraw_amount"])
    gross = Decimal(context.user_data["withdraw_gross"])
    fee_withdrawal = Decimal(context.user_data.get("withdraw_fee", "1.0"))

    from bot.keyboards import confirm_keyboard
    await update.message.reply_text(
        f"⚠️ <b>Conferma Prelievo</b>\n\n"
        f"Importo: <b>{amount:.2f} USDT</b>\n"
        f"Fee rete: <b>{fee_withdrawal:.2f} USDT</b>\n"
        f"<b>Riceverai: {amount:.2f} USDT</b>\n\n"
        f"Destinatario: <code>{address}</code>",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("withdraw"),
    )
    return WITHDRAW_CONFIRM


async def withdrawal_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 4: esegue il prelievo atomico e invia tx on-chain."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Prelievo annullato.")
        return ConversationHandler.END

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    gross = Decimal(context.user_data["withdraw_gross"])
    address = context.user_data["withdraw_address"]
    amount = Decimal(context.user_data["withdraw_amount"])

    fee_withdrawal = Decimal(context.user_data.get("withdraw_fee", "1.0"))

    # Sottrai dal DB (atomico)
    tx_id = await execute_withdrawal(pool, user_id, gross, fee_withdrawal)
    if tx_id is None:
        await query.edit_message_text("❌ Errore: saldo insufficiente al momento della conferma.")
        return ConversationHandler.END

    await query.edit_message_text("⏳ Prelievo in elaborazione, invio on-chain...")

    try:
        tx_hash = send_usdt(address, amount)
        await confirm_tx(pool, tx_id, tx_hash)
        await query.edit_message_text(
            f"✅ <b>Prelievo inviato!</b>\n\n"
            f"Inviati: <b>{amount:.2f} USDT</b>\n"
            f"🔗 Tx: <code>{tx_hash}</code>\n\n"
            "<i>I fondi arriveranno tra pochi minuti.</i>",
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Withdrawal uncertainty for user {user_id}: {e}")
        # NON facciamo il rollback del saldo! Il rischio di double-spend è troppo alto.
        # Segnamo come errore da verificare manualmente.
        await fail_tx(pool, tx_id) 
        await query.edit_message_text(
            "⚠️ <b>Attenzione: comunicazione instabile.</b>\n\n"
            "La richiesta è stata registrata ma non abbiamo ricevuto conferma istantanea dalla blockchain.\n"
            "<b>NON riprovare.</b> Un amministratore verificherà lo stato entro 24h e ripristinerà il saldo se il trasferimento non è andato a buon fine.",
            parse_mode="HTML",
        )

    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Annulla qualsiasi ConversationHandler."""
    pool = context.bot_data.get("pool")
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id) if pool else "it"
    
    msg = t("err_cancelled", lang)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg)
    else:
        await update.message.reply_text(msg, reply_markup=main_keyboard())
@admin_only
async def test_faucet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando /faucet per accreditare 100 USDT di test all'utente."""
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    amount = Decimal("100.00")

    from db.transactions import write_tx
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET balance_usdt = balance_usdt + $1 WHERE user_id = $2",
                amount, user_id,
            )
            await write_tx(pool, user_id, "bonus", amount, status="confirmed", note="FAUCET TEST")

    await update.message.reply_text(
        f"🎁 <b>Test Faucet Attivo!</b>\n\n"
        f"Ti sono stati accreditati <b>{amount:.2f} USDT</b> per il testing.\n"
        f"Controlla il tuo saldo nel menu!",
        parse_mode="HTML",
    )


async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra il link referral personale dell'utente."""
    if update.callback_query:
        await update.callback_query.answer()

    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang_record = await pool.fetchval("SELECT language FROM users WHERE user_id = $1", user_id)
    lang = lang_record or "it"

    ref_link = make_ref_link(BOT_USERNAME, user_id)

    # Conta quanti inviti ha già fatto
    invited_count = await pool.fetchval(
        "SELECT COUNT(*) FROM users WHERE referred_by = $1", user_id
    )

    text = (
        t("referral_text", lang).format(link=ref_link) +
        f"\n\n👥 Amici già invitati: <b>{invited_count}</b>"
    )

    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Torna al Saldo", callback_data="wallet:balance")
    ]])

    await update.effective_message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )

