import logging
import asyncio
from decimal import Decimal
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from db.admin import get_setting
from db.users import get_balance_stats, get_user_language, record_game_result, add_xp
from utils.i18n import t
from bot.ui import answer_and_update, update_menu

logger = logging.getLogger(__name__)

# Valori di fallback (saranno sovrascritti dai settings DB)
DEFAULT_MINIGAME_EDGE = Decimal("0.05")
MIN_BET = Decimal("0.10")

def dice_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Tastiera per scegliere l'importo e la puntata: Numero esatto, Alto, Basso."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("1", callback_data="dice:pick:1"),
            InlineKeyboardButton("2", callback_data="dice:pick:2"),
            InlineKeyboardButton("3", callback_data="dice:pick:3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="dice:pick:4"),
            InlineKeyboardButton("5", callback_data="dice:pick:5"),
            InlineKeyboardButton("6", callback_data="dice:pick:6"),
        ],
        [
            InlineKeyboardButton("📉 Basso (1-3)", callback_data="dice:pick:low"),
            InlineKeyboardButton("📈 Alto (4-6)", callback_data="dice:pick:high"),
        ],
        [
            InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")
        ]
    ])

def dice_amount_keyboard(pick: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("0.50", callback_data=f"dice:bet:{pick}:0.50"),
            InlineKeyboardButton("1.0", callback_data=f"dice:bet:{pick}:1.0"),
            InlineKeyboardButton("5.0", callback_data=f"dice:bet:{pick}:5.0"),
        ],
        [
            InlineKeyboardButton("10.0", callback_data=f"dice:bet:{pick}:10.0"),
            InlineKeyboardButton("25.0", callback_data=f"dice:bet:{pick}:25.0"),
            InlineKeyboardButton("MAX", callback_data=f"dice:bet:{pick}:max"),
        ],
        [
            InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:dice")
        ]
    ])

async def show_dice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)
    
    # Calcolo Moltiplicatori Dinamici
    edge_str = await get_setting(pool, "minigame_edge", "0.05")
    edge = Decimal(edge_str)
    mult_hl = (Decimal("2.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.01"))
    mult_exact = (Decimal("6.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.01"))

    text = (
        "🎲 <b>Minigioco: Dadi</b>\n\n"
        "Scommetti sul lancio del dado:\n"
        f"🎯 <b>Numero Esatto (1-6):</b> Vinci {mult_exact}x\n"
        f"⚖️ <b>Alto (4-6) / Basso (1-3):</b> Vinci {mult_hl}x\n\n"
        "Seleziona la tua puntata:"
    )
    if update.callback_query:
        await answer_and_update(update.callback_query, context, text, reply_markup=dice_keyboard(lang))
    else:
        await update_menu(context, update.effective_chat.id, text, reply_markup=dice_keyboard(lang))

async def handle_dice_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    if len(parts) != 3: return
    pick = parts[2]
    
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, update.effective_user.id)
    
    labels = {
        "1": "Numero 1", "2": "Numero 2", "3": "Numero 3",
        "4": "Numero 4", "5": "Numero 5", "6": "Numero 6",
        "low": "Basso (1-3)", "high": "Alto (4-6)"
    }
    
    text = (
        f"🎲 <b>Hai scelto: {labels.get(pick, pick)}</b>\n\n"
        "Seleziona l'importo da puntare:"
    )
    await answer_and_update(query, context, text, reply_markup=dice_amount_keyboard(pick, lang))

_DICE_LOCKS = set()

async def handle_dice_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id in _DICE_LOCKS:
        await query.answer("Calma! Un lancio alla volta.", show_alert=True)
        return
        
    parts = query.data.split(":")
    if len(parts) != 4: return
    
    pick = parts[2]
    amount_str = parts[3]
    
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, user_id)
    
    # Check balance
    stats = await get_balance_stats(pool, user_id)
    if not stats:
        await answer_and_update(query, context, t("err_profile", lang))
        return
        
    balance = Decimal(str(stats["saldo_disponibile"]))
    
    if amount_str == "max":
        bet_amount = balance
    else:
        try:
            bet_amount = Decimal(amount_str)
        except:
            return
            
    if bet_amount < MIN_BET:
        await answer_and_update(query, context, f"❌ Puntata minima: {MIN_BET} USDT")
        return
        
    if balance < bet_amount:
        from bot.keyboards import insufficient_balance_keyboard
        await answer_and_update(query, context, t("err_insufficient", lang), reply_markup=insufficient_balance_keyboard(lang))
        return

    # Calcolo Moltiplicatori Dinamici
    edge_str = await get_setting(pool, "minigame_edge", "0.05")
    edge = Decimal(edge_str)
    mult_hl = (Decimal("2.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.01"))
    mult_exact = (Decimal("6.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.01"))
    
    # Scegli moltiplicatore in base a tipo giocata
    multiplier = mult_hl if pick in ("low", "high") else mult_exact

    _DICE_LOCKS.add(user_id)
    try:
        # Pulisco il messaggio "Persistent" sostituendolo con emoji animato del dado
        # Elimino il messaggio precendente per inserire l'animazione nativa Telegram (send_dice)
        try:
            await query.message.delete()
        except:
            pass
            
        # Invia l'animazione del dado Telegram
        dice_msg = await context.bot.send_dice(chat_id=update.effective_chat.id, emoji="🎲")
        
        # Telegram imposta il valore del dado animato!
        result_num = dice_msg.dice.value
        
        # Attesa fine animazione
        await asyncio.sleep(4.0)
        
        # Calcolo vittoria
        is_win = False
        if pick == "low" and result_num in (1, 2, 3):
            is_win = True
        elif pick == "high" and result_num in (4, 5, 6):
            is_win = True
        elif pick == str(result_num):
            is_win = True

        new_balance = await record_game_result(
            pool=pool,
            user_id=user_id,
            bet_amount=bet_amount,
            is_win=is_win,
            multiplier=multiplier
        )
        
        # XP
        xp_gain = int(bet_amount * 10)
        if xp_gain > 0:
            await add_xp(pool, user_id, xp_gain)

        if is_win:
            win_amount = bet_amount * multiplier
            final_text = (
                f"🎉 <b>HAI VINTO!</b>\n\n"
                f"È uscito: <b>{result_num}</b>\n"
                f"Hai vinto <b>{win_amount:.2f} USDT</b>!\n\n"
                f"Saldo attuale: {new_balance:.2f} USDT\n"
                f"⭐ +{xp_gain} XP"
            )
        else:
            final_text = (
                f"❌ <b>HAI PERSO!</b>\n\n"
                f"È uscito: <b>{result_num}</b>\n"
                f"Hai perso {bet_amount:.2f} USDT.\n\n"
                f"Saldo attuale: {new_balance:.2f} USDT\n"
                f"⭐ +{xp_gain} XP"
            )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Riprova", callback_data=f"dice:bet:{pick}:{amount_str}")],
            [InlineKeyboardButton("🎲 Cambia", callback_data="menu:dice"), InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")]
        ])

        # Usa update_menu resettando l'ID per forzare l'invio come nuovo messaggio Permanent
        context.user_data["menu_msg_id"] = None
        await update_menu(context, update.effective_chat.id, final_text, reply_markup=kb)

    finally:
        _DICE_LOCKS.discard(user_id)
