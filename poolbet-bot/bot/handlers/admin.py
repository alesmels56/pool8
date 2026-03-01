"""
bot/handlers/admin.py — Comandi amministrativi per la gestione del bot.
Whitelist: solo gli user_id in ADMIN_IDS (config.py) possono usarli.
"""
import logging
from decimal import Decimal, InvalidOperation

from telegram import Update
from telegram.ext import ContextTypes

from db.users import get_user, get_balance_stats
from db.bets import list_user_bets, get_expired_bets, reset_all_bets_db, get_bet
from db.transactions import write_tx
from db.participations import get_bet_summary, get_all_participations
from engine.payout import run_payout
from db.admin import get_platform_balance, withdraw_platform_profit, execute_emergency_exit, get_setting, set_setting, add_platform_profit
from bot.keyboards import admin_keyboard
from blockchain.usdt import send_usdt, get_usdt_balance
from eth_account import Account
from config import ADMIN_IDS, COLD_WALLET_ADDRESS, HOT_WALLET_PRIVATE_KEY

logger = logging.getLogger(__name__)

# Stati per la conversazione admin interattiva
ADMIN_ASK_ID, ADMIN_ASK_AMOUNT, ADMIN_ASK_NOTE = range(100, 103)



async def safe_admin_edit(update: Update, text: str, reply_markup=None) -> None:
    """Edita un messaggio admin in modo sicuro, gestendo errori di contenuto identico."""
    from telegram.error import BadRequest
    try:
        # Usa il parse mode HTML di default per coerenza
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif update.message:
            await update.message.reply_text(text, parse_mode="HTML", reply_markup=reply_markup)
        else:
            logger.warning("safe_admin_edit: update has no callback_query nor message")
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.error(f"Error in safe_admin_edit: {e}")
            raise e

def admin_only(func):
    """Decorator: blocca l'esecuzione se l'utente non è nella whitelist admin."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("⛔ Accesso non autorizzato.", show_alert=True)
            elif update.message:
                await update.message.reply_text("⛔ Accesso non autorizzato.")
            logger.warning(f"Unauthorized admin access attempt by user {user_id}")
            return
        return await func(update, context)
    return wrapper


def admin_back_keyboard() -> InlineKeyboardMarkup:
    """Tastino per tornare al menu admin root."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Pannello Admin", callback_data="admin:back")]])


@admin_only
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /admin_stats — statistiche globali del bot.
    """
    pool = context.bot_data["pool"]

    total_users = await pool.fetchval("SELECT COUNT(*) FROM users")
    open_bets   = await pool.fetchval("SELECT COUNT(*) FROM bets WHERE status = 'open'")
    closed_bets = await pool.fetchval("SELECT COUNT(*) FROM bets WHERE status = 'closed'")
    total_pool  = await pool.fetchval("SELECT COALESCE(SUM(pool_total), 0) FROM bets WHERE status IN ('open','closed','finalized')")
    total_vol   = await pool.fetchval("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'deposit' AND status = 'confirmed'")
    total_payout = await pool.fetchval("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = 'payout'")
    pending_w   = await pool.fetchval("SELECT COUNT(*) FROM transactions WHERE type = 'withdrawal' AND status = 'pending'")

    msg = (
        f"📊 <b>Statistiche PoolBet Bot</b>\n\n"
        f"👥 Utenti registrati:    <b>{total_users}</b>\n"
        f"🎲 Scommesse aperte:     <b>{open_bets}</b>\n"
        f"⏱ Scommesse scadute:     <b>{closed_bets}</b>\n"
        f"💰 Pool totale storico:  <b>{total_pool:.2f} USDT</b>\n"
        f"📥 Volume depositi:     <b>{total_vol:.2f} USDT</b>\n"
        f"📤 Volume payout:       <b>{total_payout:.2f} USDT</b>\n"
        f"⏳ Prelievi in attesa:   <b>{pending_w}</b>"
    )

    if update.callback_query:
        await safe_admin_edit(update, msg, admin_keyboard())
    else:
        await update.message.reply_text(msg, parse_mode="HTML")


@admin_only
async def admin_credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /admin_credita <user_id> <amount> [nota]
    Accredita manualmente crediti a un utente (es. per supporto o rimborso).
    """
    pool = context.bot_data["pool"]
    args = context.args  # ["123456", "10.00", "nota opzionale"]

    if len(args) < 2:
        await update.message.reply_text(
            "Uso: /admin_credita <user_id> <amount> [nota]\nEs: /admin_credita 123456789 10.00 Rimborso manuale"
        )
        return

    try:
        target_id = int(args[0])
        amount    = Decimal(args[1])
        note      = " ".join(args[2:]) if len(args) > 2 else "Credito manuale admin"
    except (ValueError, InvalidOperation):
        await update.message.reply_text("❌ Parametri non validi.")
        return

    user = await get_user(pool, target_id)
    if user is None:
        await update.message.reply_text(f"❌ Utente {target_id} non trovato.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET balance_usdt = balance_usdt + $1 WHERE user_id = $2",
                amount, target_id,
            )
            await write_tx(pool, target_id, "bonus", amount, status="confirmed", note=f"[ADMIN] {note}")

    logger.info(f"Admin {update.effective_user.id} credited {amount} USDT to user {target_id}")
    await update.message.reply_text(
        f"✅ Accreditati <b>{amount:.2f} USDT</b> all'utente <code>{target_id}</code>.\nNota: {note}",
        parse_mode="HTML",
    )

    # Notifica l'utente
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"🎁 <b>Credito accreditato!</b>\n\n+{amount:.2f} USDT\n<i>{note}</i>",
            parse_mode="HTML",
        )
    except Exception:
        pass


@admin_only
async def admin_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /admin_utente <user_id> — dettaglio saldo e scommesse di un utente.
    """
    pool = context.bot_data["pool"]
    args = context.args

    if len(args) < 1:
        await update.message.reply_text("Uso: /admin_utente <user_id>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id non valido.")
        return

    stats = await get_balance_stats(pool, target_id)
    if stats is None:
        await update.message.reply_text(f"❌ Utente {target_id} non trovato.")
        return

    bets = await list_user_bets(pool, target_id)
    open_count   = sum(1 for b in bets if b["status"] == "open")
    closed_count = sum(1 for b in bets if b["status"] == "finalized")

    await update.message.reply_text(
        f"👤 <b>Utente {target_id}</b>\n\n"
        f"💳 Saldo:          <b>{stats['saldo_disponibile']:.2f} USDT</b>\n"
        f"📥 Tot. depositato: {stats['totale_depositato']:.2f} USDT\n"
        f"📤 Tot. prelevato:  {stats['totale_prelevato']:.2f} USDT\n"
        f"🎁 Bonus:          {stats['bonus_accumulati']:.2f} USDT\n"
        f"🎲 Bet create:     {len(bets)} ({open_count} aperte, {closed_count} chiuse)\n"
        f"🏦 Wallet:         <code>{stats['wallet_address']}</code>",
        parse_mode="HTML",
    )


@admin_only
async def admin_list_expired(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_scadute — lista scommesse scadute non processate."""
    pool = context.bot_data["pool"]
    expired = await get_expired_bets(pool)

    if not expired:
        await safe_admin_edit(update, "✅ Nessuna scommessa scaduta in coda.", admin_keyboard())
        return

    lines = [f"⏱ <b>Scommesse scadute ({len(expired)})</b>\n"]
    for b in expired:
        lines.append(
            f"• <code>{str(b['uuid'])[:8]}</code> — Pool: {b['pool_total']:.2f} USDT"
        )
    msg = "\n".join(lines)
    await safe_admin_edit(update, msg, admin_keyboard())


@admin_only
async def admin_reset_bets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_reset — sposta tutte le scommesse attive a 'expired'."""
    pool = context.bot_data["pool"]
    count = await reset_all_bets_db(pool)
    await safe_admin_edit(update, f"✅ Reset completato. <b>{count}</b> scommesse segnate come 'expired'.", admin_keyboard())


@admin_only
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_broadcast <messaggio> — invia a tutti gli utenti registrati."""
    import asyncio
    pool = context.bot_data["pool"]
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /admin_broadcast <messaggio>")
        return

    msg_text = " ".join(args)
    users = await pool.fetch("SELECT user_id FROM users")
    
    await update.message.reply_text(f"🚀 Invio broadcast a {len(users)} utenti...")
    
    success = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u["user_id"], text=f"📢 <b>AVVISO ADMIN</b>\n\n{msg_text}", parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.05) # Rate limit protection
        except Exception:
            pass
    
    await update.message.reply_text(f"🏁 Broadcast completato: {success}/{len(users)} messaggi inviati.")


@admin_only
async def admin_top_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_top — classifica top 10 utenti per saldo."""
    pool = context.bot_data["pool"]
    rows = await pool.fetch("SELECT user_id, username, balance_usdt FROM users ORDER BY balance_usdt DESC LIMIT 10")
    
    lines = ["🏆 <b>Top 10 Utenti (per Saldo)</b>\n"]
    for i, r in enumerate(rows, 1):
        name = r["username"] if r["username"] else f"ID:{r['user_id']}"
        lines.append(f"{i}. <code>{name}</code> — <b>{r['balance_usdt']:.2f} USDT</b>")
    
    msg = "\n".join(lines)
    await safe_admin_edit(update, msg, admin_keyboard())
    
@admin_only
async def admin_treasury(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_treasury — visualizza i profitti della piattaforma."""
    pool = context.bot_data["pool"]
    profit = await get_platform_balance(pool)
    
    # Saldo on-chain per confronto
    master_addr = Account.from_key(HOT_WALLET_PRIVATE_KEY).address
    on_chain = get_usdt_balance(master_addr)
    
    msg = (
        f"🏦 <b>Tesoreria Piattaforma</b>\n\n"
        f"💰 Profitti accumulati: <b>{profit:.2f} USDT</b>\n"
        f"🔗 Saldo Hot Wallet:   <b>{on_chain:.2f} USDT</b>\n\n"
        f"<i>I profitti includono fee scommesse, perdite minigioco e penali.</i>"
    )
    if update.callback_query:
        await safe_admin_edit(update, msg, admin_keyboard())
    else:
        await update.message.reply_text(msg, parse_mode="HTML")

@admin_only
async def admin_exit_strategy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_exit — liquidazione pool e prelievo totale tesoreria."""
    pool = context.bot_data["pool"]
    
    if not COLD_WALLET_ADDRESS:
        await update.message.reply_text("❌ COLD_WALLET_ADDRESS non configurato nel .env")
        return

    await update.message.reply_text("⚠️ <b>AVVIO EXIT STRATEGY...</b>\nLiquidazione scommesse in corso...", parse_mode="HTML")
    
    # 1. Liquidazione scommesse aperte
    recovered = await execute_emergency_exit(pool)
    
    # 2. Recupero totale profitto (inclusi i liquidati)
    total_profit = await get_platform_balance(pool)
    
    if total_profit <= 0:
        await update.message.reply_text(f"✅ Liquidazione completata. Recuperati {recovered:.2f} USDT.\nTesoreria vuota, nessun prelievo necessario.")
        return

    # 3. Trasferimento On-Chain
    try:
        tx_hash = send_usdt(COLD_WALLET_ADDRESS, total_profit)
        # 4. Aggiorna DB
        await withdraw_platform_profit(pool, total_profit)
        
        await update.message.reply_text(
            f"🚀 <b>EXIT STRATEGY COMPLETATA!</b>\n\n"
            f"📥 Liquidazione Totale (Pool + Saldi): <b>{recovered:.2f} USDT</b>\n"
            f"💸 Inviati al Cold Wallet: <b>{total_profit:.2f} USDT</b>\n\n"
            f"🔗 TX Hash: <code>{tx_hash}</code>",
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Exit Strategy Failed during on-chain transfer: {e}")
        await update.message.reply_text(f"❌ Errore durante il trasferimento on-chain: {e}")


@admin_only
async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Menu principale /admin con la lista dei comandi cliccabili.
    """
    msg = (
        "⚙️ <b>Pannello Amministratore</b>\n\n"
        "Premi su uno dei comandi per eseguirlo:\n"
        "📊 /admin_stats — Statistiche globali\n"
        "💳 /admin_credita — Accredita fondi manuali\n"
        "👤 /admin_utente — Dettaglio utente\n"
        "⏱ /admin_scadute — Scommesse in coda\n"
        "🗑 /admin_reset — Reset forzato scommesse\n"
        "🏆 /admin_top — Classifica top users\n"
        "🏦 /admin_treasury — Profitti e Cold Wallet\n"
        "🚀 /admin_exit — Attiva Exit Strategy\n"
        "📢 /admin_broadcast — Invia messaggi a tutti\n\n"
        "<i>Nuovi Comandi (Lavori in corso):</i>\n"
        "🚫 /admin_ban — Blocca un utente\n"
        "✅ /admin_unban — Sblocca un utente\n"
        "📉 /admin_debita — Rimuovi fondi utente\n"
        "🔥 /admin_delete_bet — Elimina scommessa in corso\n"
    )
    
    await safe_admin_edit(update, msg, admin_keyboard())

@admin_only
async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_ban <user_id> — Banna un utente dal bot."""
    pool = context.bot_data["pool"]
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /admin_ban <user_id>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id non valido.")
        return

    res = await pool.execute("UPDATE users SET is_banned = TRUE WHERE user_id = $1", target_id)
    if res == "UPDATE 0":
        await update.message.reply_text("❌ Utente non trovato.")
    else:
        logger.info(f"Admin {update.effective_user.id} banned user {target_id}")
        await update.message.reply_text(f"🚫 Utente {target_id} bannato con successo.")

@admin_only
async def admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_unban <user_id> — Rimuove il ban da un utente."""
    pool = context.bot_data["pool"]
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /admin_unban <user_id>")
        return

    try:
        target_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ user_id non valido.")
        return

    res = await pool.execute("UPDATE users SET is_banned = FALSE WHERE user_id = $1", target_id)
    if res == "UPDATE 0":
        await update.message.reply_text("❌ Utente non trovato.")
    else:
        logger.info(f"Admin {update.effective_user.id} unbanned user {target_id}")
        await update.message.reply_text(f"✅ Utente {target_id} sbloccato con successo.")

@admin_only
async def admin_debit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_debita <user_id> <amount> [nota] — Sottrae fondi manualmente."""
    pool = context.bot_data["pool"]
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("Uso: /admin_debita <user_id> <amount> [nota]")
        return

    try:
        target_id = int(args[0])
        amount    = Decimal(args[1])
        note      = " ".join(args[2:]) if len(args) > 2 else "Addebito manuale admin"
    except (ValueError, InvalidOperation):
        await update.message.reply_text("❌ Parametri non validi.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            current_bal = await conn.fetchval("SELECT balance_usdt FROM users WHERE user_id = $1", target_id)
            if current_bal is None:
                await update.message.reply_text(f"❌ Utente {target_id} non trovato.")
                return
            if current_bal < amount:
                await update.message.reply_text(f"❌ Utente ha solo {current_bal} USDT. Impossibile sottrarre {amount}.")
                return

            await conn.execute("UPDATE users SET balance_usdt = balance_usdt - $1 WHERE user_id = $2", amount, target_id)
            await write_tx(pool, target_id, "bet", amount, status="confirmed", note=f"[ADMIN DEBIT] {note}")

    logger.info(f"Admin {update.effective_user.id} debited {amount} from user {target_id}")
    await update.message.reply_text(f"📉 Sottratti <b>{amount:.2f} USDT</b> all'utente <code>{target_id}</code>.\nNota: {note}", parse_mode="HTML")

@admin_only
async def admin_delete_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_delete_bet <uuid> — Rimborsa partecipanti ed elimina una scommessa."""
    pool = context.bot_data["pool"]
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /admin_delete_bet <uuid>")
        return

    bet_uuid = args[0]
    
    # Da implementare il rimborso iterativo se la bet è aperta.
    # Per ora semplicemente segniamo status = 'expired' che sblocca i fondi al bot eventuale
    res = await pool.execute("UPDATE bets SET status = 'expired' WHERE uuid::text = $1 AND status = 'open'", bet_uuid)
    
    if res == "UPDATE 0":
        await update.message.reply_text("❌ Bet non trovata o non è in stato 'open'. Usa prima questa logica per rimborsarla.")
    else:
        logger.info(f"Admin {update.effective_user.id} forced expiration on bet {bet_uuid}")
        await update.message.reply_text(f"🔥 Scommessa <code>{bet_uuid}</code> annullata (scaduta forzatamente).", parse_mode="HTML")

@admin_only
async def admin_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra i valori correnti delle system_settings."""
    pool = context.bot_data["pool"]
    tip_fee = await get_setting(pool, "tip_fee", "0.05")
    withdraw_fee = await get_setting(pool, "withdraw_fee", "1.0")
    minigame_edge = await get_setting(pool, "minigame_edge", "0.05")
    
    msg = (
        "⚙️ <b>Impostazioni di Sistema Correnti</b>\n\n"
        f"🔸 <b>tip_fee</b> (Tassa mance): <code>{tip_fee}</code>\n"
        f"🔸 <b>withdraw_fee</b> (Costo ritiro fisso): <code>{withdraw_fee}</code>\n"
        f"🔸 <b>minigame_edge</b> (Margine casa): <code>{minigame_edge}</code>\n\n"
        "Per modificare un valore, usa il comando testuale:\n"
        "<code>/admin_set_setting &lt;key&gt; &lt;value&gt;</code>\n\n"
        "<i>Esempio:</i>\n<code>/admin_set_setting tip_fee 0.10</code>"
    )
    if update.callback_query:
        await safe_admin_edit(update, msg, admin_keyboard())
    else:
        await update.message.reply_text(msg, parse_mode="HTML")

@admin_only
async def admin_set_setting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_set_setting <key> <value> — Imposta un valore in system_settings."""
    pool = context.bot_data["pool"]
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /admin_set_setting <key> <value>")
        return
        
    key = args[0]
    value = args[1]
    
    await set_setting(pool, key, value)
    logger.info(f"Admin {update.effective_user.id} updated setting {key} to {value}")
    await update.message.reply_text(f"✅ Impostazione di sistema aggiornata:\n<code>{key}</code> = <b>{value}</b>", parse_mode="HTML")

@admin_only
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce i click sui bottoni della tastiera admin_keyboard."""
    query = update.callback_query
    if not query:
        return

    # Rispondi sempre al callback per togliere lo stato di caricamento (spinning icon)
    await query.answer()

    # Estrai azione
    data_parts = query.data.split(":")
    if len(data_parts) < 2:
        return
        
    action = data_parts[1]
    logger.info(f"Admin Action Triggered: {action} by user {update.effective_user.id}")
    
    # Simula i context.args per riutilizzare le funzioni esistenti se necessario
    context.args = []
    
    if action == "stats":
        await admin_stats(update, context)
    elif action == "treasury":
        await admin_treasury(update, context)
    elif action == "top":
        await admin_top_users(update, context)
    elif action == "scadute":
        await admin_list_expired(update, context)
    elif action in ["credita", "debita", "ban"]:
        # Avvia la procedura guidata
        context.user_data["admin_action"] = action
        await safe_admin_edit(update, f"🎯 <b>Azione: {action.upper()}</b>\n\nInserisci l'ID Telegram dell'utente:", reply_markup=admin_back_keyboard())
        return ADMIN_ASK_ID
    elif action == "broadcast":
        await safe_admin_edit(update,
            "📢 Per inviare un broadcast, usa il comando:\n`/admin_broadcast <Il tuo messaggio qui>`", 
            reply_markup=admin_back_keyboard()
        )
    elif action == "unban":
        await safe_admin_edit(update,
            "✅ Per sbannare, usa:\n`/admin_unban <user_id>`", 
            reply_markup=admin_back_keyboard()
        )
    elif action == "delete_bet":
        await safe_admin_edit(update,
            "🔥 Per eliminare una scommessa, usa:\n`/admin_delete_bet <uuid>`", 
            reply_markup=admin_back_keyboard()
        )
    elif action == "settings":
        await admin_settings_menu(update, context)
    elif action == "back":
        await admin_router(update, context)
        from telegram.ext import ConversationHandler
        return ConversationHandler.END
    else:
        logger.warning(f"Unhandled admin action: {action}")

# --- Handlers per la Conversazione Interattiva ---

@admin_only
async def admin_recv_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve l'ID utente per l'azione selezionata."""
    user_input = update.message.text.strip()
    action = context.user_data.get("admin_action")
    
    if not user_input.isdigit():
        await update.message.reply_text("❌ L'ID deve essere un numero. Riprova:")
        return ADMIN_ASK_ID
    
    target_id = int(user_input)
    context.user_data["admin_target"] = target_id
    
    if action == "ban":
        # Passa direttamente alla conferma o esegui
        context.args = [str(target_id)]
        await admin_ban(update, context)
        return ConversationHandler.END
    
    await update.message.reply_text(f"💰 Inserisci l'<b>importo</b> in USDT per <b>{action}</b>:")
    return ADMIN_ASK_AMOUNT

@admin_only
async def admin_recv_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve l'importo."""
    user_input = update.message.text.strip().replace(",", ".")
    try:
        amount = Decimal(user_input)
        if amount <= 0: raise ValueError
    except:
        await update.message.reply_text("❌ Importo non valido. Inserisci un numero positivo:")
        return ADMIN_ASK_AMOUNT
    
    context.user_data["admin_amount"] = str(amount)
    await update.message.reply_text("📝 Inserisci una <b>nota/causale</b> (opzionale):")
    return ADMIN_ASK_NOTE

@admin_only
async def admin_recv_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Riceve la nota e finalizza."""
    note = update.message.text.strip()
    action = context.user_data.get("admin_action")
    target_id = context.user_data.get("admin_target")
    amount = context.user_data.get("admin_amount")
    
    # Simula gli argomenti per le funzioni esistenti
    context.args = [str(target_id), amount, note]
    
    if action == "credita":
        await admin_credit(update, context)
    elif action == "debita":
        await admin_debit(update, context)
    
    return ConversationHandler.END


async def whoami_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando diagnostico per vedere il proprio ID."""
    uid = update.effective_user.id
    is_admin = uid in ADMIN_IDS
    msg = (
        f"🆔 Il tuo ID Telegram: <code>{uid}</code>\n"
        f"👑 Admin Whitelist: {'✅ Sì' if is_admin else '❌ No'}\n\n"
        f"Se l'ID risulta '❌ No', aggiungi <code>{uid}</code> alla variabile <code>ADMIN_IDS</code> nel file <code>.env</code> e riavvia il bot."
    )
    await update.message.reply_text(msg, parse_mode="HTML")
@admin_only
async def admin_list_challenged(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin_contese — Lista scommesse contestate."""
    pool = context.bot_data["pool"]
    rows = await pool.fetch("SELECT * FROM bets WHERE status = 'challenged'")
    
    if not rows:
        await safe_admin_edit(update, "✅ Nessuna contestazione attiva.", admin_keyboard())
        return

    lines = ["⚖️ <b>Scommesse Contestate</b>\n"]
    for r in rows:
        lines.append(f"• <code>{str(r['uuid'])[:8]}</code> — Challenger: {r['challenger_id']}")
    
    msg = "\n".join(lines) + "\n\nUsa `/admin_risolvi <uuid> <vincitore|sfidante>`"
    await safe_admin_edit(update, msg, admin_keyboard())

@admin_only
async def admin_resolve_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /admin_risolvi <uuid> <winner|challenger>
    Risolve una disputa.
    'winner' conferma il creator (challenger perde stake).
    'challenger' dà ragione allo sfidante (creator perde reputazione/bond se implementato).
    """
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /admin_risolvi <uuid> <vincitore|sfidante>")
        return

    bet_uuid = args[0]
    decision = args[1].lower() # 'vincitore' o 'sfidante'
    pool = context.bot_data["pool"]

    bet = await get_bet(pool, bet_uuid)
    if not bet or bet["status"] != "challenged":
        await update.message.reply_text("❌ Bet non trovata o non in stato 'challenged'.")
        return

    if decision in ["vincitore", "winner"]:
        # Vince il creator. Procedi con il payout normale.
        await update.message.reply_text(f"⚖️ Disputa risolta: **Vince il Creator**. Avvio payout...")
        
        # In caso di sfida persa, lo stake dello sfidante va nel profitto piattaforma
        async with pool.acquire() as conn:
            await add_platform_profit(pool=None, amount=bet["challenge_stake"], conn=conn, source_user_id=bet["challenger_id"])

        await run_payout(pool, context.bot, bet_uuid, bet["winner_option"], bet)
    elif decision in ["sfidante", "challenger"]:
        # Vince lo sfidante. Rimborsa tutti o gestisci diversamente.
        # Per ora: Rimborsa tutti i partecipanti TRANNE il creator, e premia il challenger con lo stake.
        await update.message.reply_text(f"⚖️ Disputa risolta: **Vince lo Sfidante**. Rimborso in corso...")
        # In una versione avanzata potresti voler cambiare l'opzione vincente, ma qui facciamo un refund punitivo per il creator
        from engine.refund import run_refund
        await run_refund(pool, context.bot, bet_uuid, bet)
        # Premia il challenger rimborsandogli lo stake + bonus se vuoi
        await pool.execute("UPDATE users SET balance_usdt = balance_usdt + $1 WHERE user_id = $2", bet["challenge_stake"], bet["challenger_id"])
    else:
        await update.message.reply_text("❌ Decisione non valida. Usa 'vincitore' o 'sfidante'.")
