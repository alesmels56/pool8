import logging
import random
import asyncio
from decimal import Decimal
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from db.admin import get_setting
from db.users import get_balance_stats, get_user_language, record_game_result, add_xp
from utils.i18n import t
from bot.ui import answer_and_update, update_menu

logger = logging.getLogger(__name__)

# Valori di fallback
MIN_BET = Decimal("0.10")

def coinflip_keyboard(lang: str) -> InlineKeyboardMarkup:
    """Tastiera per scegliere l'importo e la puntata (Testa/Croce)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🪙 Testa", callback_data="coin:pick:heads"),
            InlineKeyboardButton("🪙 Croce", callback_data="coin:pick:tails"),
        ],
        [
            InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")
        ]
    ])

def coinflip_amount_keyboard(side: str, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("0.50", callback_data=f"coin:bet:{side}:0.50"),
            InlineKeyboardButton("1.0", callback_data=f"coin:bet:{side}:1.0"),
            InlineKeyboardButton("5.0", callback_data=f"coin:bet:{side}:5.0"),
        ],
        [
            InlineKeyboardButton("10.0", callback_data=f"coin:bet:{side}:10.0"),
            InlineKeyboardButton("25.0", callback_data=f"coin:bet:{side}:25.0"),
            InlineKeyboardButton("MAX", callback_data=f"coin:bet:{side}:max"),
        ],
        [
            InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:coinflip")
        ]
    ])

async def show_coinflip_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostra la schermata iniziale del Coin Flip."""
    pool = context.bot_data["pool"]
    user_id = update.effective_user.id
    lang = await get_user_language(pool, user_id)
    
    # Calcolo Moltiplicatore Dinamico
    edge_str = await get_setting(pool, "minigame_edge", "0.05")
    edge = Decimal(edge_str)
    multiplier = (Decimal("2.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.01"))

    text = (
        "🪙 <b>Testa o Croce</b>\n\n"
        "Semplice e veloce:\n"
        "1️⃣ Scegli Testa o Croce\n"
        "2️⃣ Scegli l'importo da puntare\n"
        f"3️⃣ Se indovini vinci <b>{multiplier}x</b>!"
    )
    if update.callback_query:
        await answer_and_update(update.callback_query, context, text, reply_markup=coinflip_keyboard(lang))
    else:
        await update_menu(context, update.effective_chat.id, text, reply_markup=coinflip_keyboard(lang))

async def handle_coinflip_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    if len(parts) != 3: return
    side = parts[2]
    
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, update.effective_user.id)
    
    side_label = "Testa" if side == "heads" else "Croce"
    text = (
        f"🪙 <b>Hai scelto: {side_label}</b>\n\n"
        "Seleziona l'importo da puntare:"
    )
    await answer_and_update(query, context, text, reply_markup=coinflip_amount_keyboard(side, lang))

# A global memory lock to prevent double-betting while rolling
_COINFLIP_LOCKS = set()

async def handle_coinflip_bet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id in _COINFLIP_LOCKS:
        await query.answer("Calma! Un lancio alla volta.", show_alert=True)
        return
    
    parts = query.data.split(":")
    if len(parts) != 4: return
    
    side = parts[2]
    amount_str = parts[3]
    
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, user_id)
    
    # 1. Recupero saldo
    stats = await get_balance_stats(pool, user_id)
    if not stats:
        await answer_and_update(query, context, t("err_profile", lang))
        return
        
    balance = Decimal(str(stats["saldo_disponibile"]))
    
    # 2. Parsa amount
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

    _COINFLIP_LOCKS.add(user_id)
    try:
        # Animazione
        anim_text = "🪙 <b>Lancio in corso...</b>\n\n<i>La moneta sta roteando in aria...</i>"
        try:
            await query.edit_message_text(anim_text, parse_mode="HTML")
        except:
            pass
            
        await asyncio.sleep(2.0)
        
        # Risoluzione
        result_side = random.choice(["heads", "tails"])
        is_win = (side == result_side)
        
        # Calcolo Moltiplicatore Dinamico
        edge_str = await get_setting(pool, "minigame_edge", "0.05")
        edge = Decimal(edge_str)
        multiplier = (Decimal("2.0") * (Decimal("1.0") - edge)).quantize(Decimal("0.01"))

        # Transazione atomica (record_game_result scala la bet e se is_win riaccredita bet*multiplier)
        new_balance = await record_game_result(
            pool=pool,
            user_id=user_id,
            bet_amount=bet_amount,
            is_win=is_win,
            multiplier=multiplier
        )
        
        # Aggiungo XP (10 XP ogni USDT giocato)
        xp_gain = int(bet_amount * 10)
        if xp_gain > 0:
            await add_xp(pool, user_id, xp_gain)
            
        # Payout UI
        side_res_label = "Testa" if result_side == "heads" else "Croce"
        
        if is_win:
            win_amount = bet_amount * multiplier
            final_text = (
                f"🎉 <b>HAI VINTO!</b>\n\n"
                f"È uscito: <b>{side_res_label}</b>\n"
                f"La tua puntata di {bet_amount:.2f} USDT è diventata <b>{win_amount:.2f} USDT</b>!\n\n"
                f"Saldo attuale: {new_balance:.2f} USDT\n"
                f"⭐ +{xp_gain} XP"
            )
        else:
            final_text = (
                f"❌ <b>HAI PERSO!</b>\n\n"
                f"È uscito: <b>{side_res_label}</b>\n"
                f"Hai perso {bet_amount:.2f} USDT.\n\n"
                f"Saldo attuale: {new_balance:.2f} USDT\n"
                f"⭐ +{xp_gain} XP"
            )
            
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Riprova", callback_data=f"coin:bet:{side}:{amount_str}")],
            [InlineKeyboardButton("🪙 Cambia", callback_data="menu:coinflip"), InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")]
        ])
        
        # Uso update_menu per evitare errori di timeout di edit vecchi
        await update_menu(context, update.effective_chat.id, final_text, reply_markup=kb)
        
    finally:
        _COINFLIP_LOCKS.discard(user_id)
