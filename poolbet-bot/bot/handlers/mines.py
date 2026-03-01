"""
bot/handlers/mines.py — Handler per il minigioco "Mines" (Campo Minato).
Vantaggio della casa (House Edge): ~5% su ogni scommessa.
"""
import random
import logging
import math
import asyncio
from decimal import Decimal
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from db.admin import get_setting
from db.users import get_user_language, get_user, record_game_result
from bot.ui import update_menu
from utils.i18n import t

logger = logging.getLogger(__name__)

# Configurazione Gioco
MIN_BET = Decimal("0.1")
DEFAULT_BET = Decimal("1.0")
DEFAULT_MINES = 3
MAX_MINES = 24
GRID_SIZE = 25  # 5x5
# HOUSE_EDGE rimosso, ora dinamico dal DB via get_setting("minigame_edge")

def calculate_multiplier(mines: int, diamonds_found: int, edge: Decimal = Decimal("0.05")) -> Decimal:
    """
    Calcola il moltiplicatore puro matematicamente, e applica l'House Edge passato.
    Formula Probabilità: C(Celle_Totali - Mine, Diamanti_Trovati) / C(Celle_Totali, Diamanti_Trovati)
    Moltiplicatore Puro = 1 / Probabilità
    Moltiplicatore Reale = Moltiplicatore Puro * (1 - House Edge)
    """
    if diamonds_found == 0:
        return Decimal("1.00")
        
    safe_cells = GRID_SIZE - mines
    
    # Se per qualche motivo ha trovato più diamanti del possibile (anti-cheat)
    if diamonds_found > safe_cells:
        return Decimal("1.00")
        
    # Prob = combinazioni(safe_cells, diamonds_found) / combinazioni(GRID_SIZE, diamonds_found)
    ways_to_win = math.comb(safe_cells, diamonds_found)
    total_ways = math.comb(GRID_SIZE, diamonds_found)
    
    if ways_to_win == 0:
        return Decimal("1.00")
        
    prob = Decimal(ways_to_win) / Decimal(total_ways)
    pure_multiplier = Decimal("1.0") / prob
    
    # Applica House Edge (margine banco)
    real_multiplier = pure_multiplier * (Decimal("1.0") - edge)
    
    # Arrotonda a 2 decimali, minimo 1.01 (eccetto per m=0 che è 1.00)
    return max(Decimal("1.01"), round(real_multiplier, 2))


def mines_setup_keyboard(current_bet: Decimal, current_mines: int, lang: str = "it") -> InlineKeyboardMarkup:
    """Tastiera per impostare la partita a Mines."""
    # Riga 1: Bombe
    row_mines = [
        InlineKeyboardButton("➖", callback_data="mines:setup:mines:-1"),
        InlineKeyboardButton(f"💣 Bombe: {current_mines}", callback_data="mines:setup:info:mines"),
        InlineKeyboardButton("➕", callback_data="mines:setup:mines:+1"),
        InlineKeyboardButton("MAX", callback_data="mines:setup:mines:24"),
    ]
    # Riga 2: Puntata
    row_bet = [
        InlineKeyboardButton("➖ 1", callback_data="mines:setup:bet:-1"),
        InlineKeyboardButton("➖ 0.1", callback_data="mines:setup:bet:-0.1"),
        InlineKeyboardButton(f"💰 {current_bet:.1f}", callback_data="mines:setup:info:bet"),
        InlineKeyboardButton("➕ 0.1", callback_data="mines:setup:bet:+0.1"),
        InlineKeyboardButton("➕ 1", callback_data="mines:setup:bet:+1"),
    ]
    # Riga 3: Azioni
    row_actions = [
        InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main"),
        InlineKeyboardButton(t("btn_play", lang), callback_data="mines:play:start"),
    ]
    return InlineKeyboardMarkup([row_mines, row_bet, row_actions])


def mines_game_keyboard(grid_state: list, game_over: bool, is_win: bool, win_amount: Decimal, lang: str = "it") -> InlineKeyboardMarkup:
    """
    Genera la griglia 5x5 in base allo stato attuale.
    grid_state: lista di 25 stringhe ('?' = nascosto, 'D' = diamante rivelato, 'M' = mina rivelata, 'X' = mina esplosa)
    """
    keyboard = []
    
    # Riempi 5 righe da 5 bottoni
    for r in range(5):
        row = []
        for c in range(5):
            idx = r * 5 + c
            state = grid_state[idx]
            
            if state == '?':
                text = "❓"
                callback = f"mines:click:{idx}" if not game_over else "mines:ignore"
            elif state == 'D':
                text = "💎"
                callback = "mines:ignore"
            elif state == 'M':
                text = "💣"  # mina non cliccata ma rivelata a fine gioco
                callback = "mines:ignore"
            elif state == 'X':
                text = "💥"  # mina cliccata!
                callback = "mines:ignore"
            else:
                text = " "
                callback = "mines:ignore"
                
            row.append(InlineKeyboardButton(text, callback_data=callback))
        keyboard.append(row)
        
    # Aggiungi il bottone di CASHOUT in basso (o bottone Rigioca se Game Over)
    if game_over:
        if is_win:
             txt = f"✅ Vinto {win_amount:.2f} USDT!"
        else:
             txt = "❌ BOOM! Riproviamo?"
             
        keyboard.append([InlineKeyboardButton(txt, callback_data="mines:setup:restart")])
        keyboard.append([InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")])
    else:
        # Se non game over, mostra Cashout se ho trovato almeno 1 diamante
        found = grid_state.count('D')
        if found > 0:
             keyboard.append([InlineKeyboardButton(f"💸 Cashout ({win_amount:.2f} USDT)", callback_data="mines:play:cashout")])
        else:
             keyboard.append([InlineKeyboardButton("Scegli una cella...", callback_data="mines:ignore")])
             
    return InlineKeyboardMarkup(keyboard)


def _format_mines_setup_msg(bet: Decimal, mines: int, balance: Decimal, lang: str) -> str:
    """Messaggio schermata di setup."""
    return (
        f"💣 <b>POOLBET MINES</b>\n\n"
        f"Scopri i diamanti per aumentare il premio, ma fermati prima di beccare una bomba!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Saldo Disponibile: <b>{balance:.2f} USDT</b>\n"
        f"💎 Puntata: <b>{bet:.1f} USDT</b>\n"
        f"💣 Bombe: <b>{mines} / 25</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

def _format_mines_play_msg(bet: Decimal, mines: int, multiplier: Decimal, next_multiplier: Decimal, balance: Decimal, lang: str) -> str:
    """Messaggio durante la partita."""
    win = bet * multiplier
    return (
        f"💣 <b>MINES IN CORSO...</b>\n\n"
        f"💰 Puntata: <b>{bet:.2f} USDT</b> (Bombe: {mines})\n"
        f"📈 Moltiplicatore: <b>{multiplier:.2f}X</b>\n"
        f"💸 Vincita Attuale: <b>{win:.2f} USDT</b>\n\n"
        f"<i>💎 Prossima cella sicura pagherà: {next_multiplier:.2f}X</i>\n"
    )

async def show_mines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entry point: schermata setup."""
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
    
    if "mines" not in context.user_data or context.user_data["mines"].get("state") == "playing":
        # Se era 'playing' forse il bot si è riavviato, lo consideriamo fallito, facciamo new game setup
        context.user_data["mines"] = {
            "state": "setup",
            "bet": DEFAULT_BET,
            "mines": DEFAULT_MINES
        }
        
    game_data = context.user_data["mines"]
    game_data["state"] = "setup" # forziamo status sicuro
    
    text = _format_mines_setup_msg(game_data["bet"], game_data["mines"], balance, lang)
    reply_markup = mines_setup_keyboard(game_data["bet"], game_data["mines"], lang)
    await update_menu(context, update.effective_chat.id, text, reply_markup=reply_markup)


async def handle_mines_setup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce selezione puntata e bombe pre-partita e reset (restart)."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")  # mines:setup:action:value (or mines:setup:restart)
    if len(parts) < 3:
        return
        
    action = parts[2]
    val = parts[3] if len(parts) > 3 else None
    
    if context.user_data.get("mines_lock"):
        return

    user_id = update.effective_user.id
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, user_id)
    user = await get_user(pool, user_id)
    if user is None:
        await query.answer("Utente non trovato. Premi /start.", show_alert=True)
        return
    balance = Decimal(str(user["balance_usdt"]))
    
    if "mines" not in context.user_data:
        context.user_data["mines"] = {"state": "setup", "bet": DEFAULT_BET, "mines": DEFAULT_MINES}
        
    game_data = context.user_data["mines"]
    
    if action == "mines":
        if val == "24":
             game_data["mines"] = 24
        else:
             game_data["mines"] = max(1, min(24, game_data["mines"] + int(val)))
             
    elif action == "bet":
        game_data["bet"] = max(MIN_BET, game_data["bet"] + Decimal(val))
    
    elif action == "restart":
        # È stato cliccato il bottone Riproviamo a fine game:
        # Resettiamo solo lo stato, mantenendo memorie di bet e bombe precedenti
        game_data["state"] = "setup"
        if "secret" in game_data: del game_data["secret"]
        if "ui" in game_data: del game_data["ui"]
        
    context.user_data["mines"] = game_data
    text = _format_mines_setup_msg(game_data["bet"], game_data["mines"], balance, lang)
    reply_markup = mines_setup_keyboard(game_data["bet"], game_data["mines"], lang)
    await update_menu(context, update.effective_chat.id, text, reply_markup=reply_markup)


async def handle_mines_play(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Gestisce l'avvio e le azioni di gioco (START, CASHOUT, CLICK)."""
    query = update.callback_query
    
    parts = query.data.split(":")  # mines:play:action hoặc mines:click:id
    cmd = parts[1]
    
    user_id = update.effective_user.id
    pool = context.bot_data["pool"]
    lang = await get_user_language(pool, user_id)
    
    if "mines" not in context.user_data:
        await query.answer("Sessione scaduta.", show_alert=True)
        return
        
    if context.user_data.get("mines_lock"):
        await query.answer("⏳ Elaboreazione in corso...", show_alert=False)
        return

    context.user_data["mines_lock"] = True
    try:
        game_data = context.user_data["mines"]
        
        if cmd == "play" and len(parts) > 2 and parts[2] == "start":
            await _start_mines_game(update, context, game_data, pool, user_id, lang)
            return
            
        elif cmd == "play" and len(parts) > 2 and parts[2] == "cashout":
            await _cashout_mines_game(update, context, game_data, pool, user_id, lang)
            return
            
        elif cmd == "click":
            idx = int(parts[2])
            await _click_mines_cell(update, context, game_data, pool, user_id, lang, idx)
            return
            
        elif cmd == "ignore":
            await query.answer()
    finally:
        context.user_data["mines_lock"] = False


async def _start_mines_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_data: dict, pool, user_id: int, lang: str):
    """Sottrae saldo e crea la mappa segreta."""
    query = update.callback_query
    bet = Decimal(str(game_data["bet"]))
    mines_count = game_data["mines"]
    
    # 1. Deduce saldo registrando la transazione negativa "bet"
    # Poiché record_game_result si aspetta is_win e scale/aggiunge, lo usiamo 'ingannandolo' per prelevare
    user = await get_user(pool, user_id)
    if user is None:
        await query.answer("Errore registrazione. Premi /start.", show_alert=True)
        return
    if Decimal(str(user["balance_usdt"])) < bet:
        from bot.keyboards import insufficient_balance_keyboard
        from bot.ui import answer_and_update
        await answer_and_update(query, context, "❌ Saldo insufficiente!", reply_markup=insufficient_balance_keyboard(lang))
        return
        
    try:
        # Registriamo SOLO la spesa (loss finta momentanea). Se vince dopo, creditiamo la vincita
        await record_game_result(pool, user_id, bet, False, Decimal("0.0"))
    except Exception as e:
        logger.error(f"Errore prelievo mines: {e}")
        await query.answer("Errore prelievo.", show_alert=True)
        return
        
    # Saldo aggiornato
    user_updated = await get_user(pool, user_id)
    if user_updated is None: return
    new_balance = Decimal(str(user_updated["balance_usdt"]))
    
    # 2. Genera griglia
    # Un array di 25 posizioni, M = Mina, SAFE = Diamante
    secret_grid = ['SAFE'] * GRID_SIZE
    bomb_positions = random.sample(range(GRID_SIZE), mines_count)
    for pos in bomb_positions:
        secret_grid[pos] = 'M'
        
    # UI grid -> 25 volte '?'
    ui_grid = ['?'] * GRID_SIZE
    
    # Init stato giocante
    game_data["state"] = "playing"
    game_data["secret"] = secret_grid
    game_data["ui"] = ui_grid
    game_data["multiplier"] = Decimal("1.00")
    game_data["diamonds_found"] = 0
    # 3. Calcolo Moltiplicatore Iniziale con Edge Dinamico
    edge_str = await get_setting(pool, "minigame_edge", "0.05")
    edge = Decimal(edge_str)
    
    next_mult = calculate_multiplier(mines_count, 1, edge)
    
    text = _format_mines_play_msg(bet, mines_count, Decimal("1.00"), next_mult, new_balance, lang)
    reply_markup = mines_game_keyboard(ui_grid, game_over=False, is_win=False, win_amount=bet, lang=lang)
    await update_menu(context, update.effective_chat.id, text, reply_markup=reply_markup)


async def _click_mines_cell(update: Update, context: ContextTypes.DEFAULT_TYPE, game_data: dict, pool, user_id: int, lang: str, idx: int):
    """Gestisce il click su una casella durante il gioco."""
    query = update.callback_query
    
    if game_data.get("state") != "playing":
        await query.answer("Partita terminata.", show_alert=True)
        return
        
    ui_grid = game_data["ui"]
    secret_grid = game_data["secret"]
    
    if ui_grid[idx] != '?':
        await query.answer() # già cliccato
        return
        
    is_bomb = (secret_grid[idx] == 'M')
    
    if is_bomb:
        # ------------- BOOM! PERSO -------------
        await query.answer("💥 HAI BECCATO UNA BOMBA!", show_alert=True)
        
        # Svela tutta la griglia
        for i in range(GRID_SIZE):
            if i == idx:
                 ui_grid[i] = 'X' # Bomba esplosa
            elif secret_grid[i] == 'M':
                 ui_grid[i] = 'M' # Bomba non esplosa
            elif ui_grid[i] == '?':
                 ui_grid[i] = 'D' # Rivela i diamanti persi (visivo)
                 
        game_data["state"] = "lost"
        
        # Il bet è già stato scalato dal DB allo start. Nulla da detrarre.
        # Il saldo attuale è quello già privato della puntata
        user_updated = await get_user(pool, user_id)
        bal = Decimal(str(user_updated["balance_usdt"]))
        
        text = f"💥 <b>BOOM! HAI PERSO!</b> 💥\n\n💸 <b>{game_data['bet']:.2f} USDT</b> trattenuti dal banco.\n💰 Nuovo Saldo: <b>{bal:.2f} USDT</b>"
        reply_markup = mines_game_keyboard(ui_grid, game_over=True, is_win=False, win_amount=Decimal("0"), lang=lang)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    
    else:
        # ------------- DIAMANTE TROVATO! -------------
        await query.answer("💎 Diamante trovato!")
        ui_grid[idx] = 'D'
        game_data["diamonds_found"] += 1
        
        # House Edge Dinamico
        edge_str = await get_setting(pool, "minigame_edge", "0.05")
        edge = Decimal(edge_str)
        
        current_mult = calculate_multiplier(game_data["mines"], game_data["diamonds_found"], edge)
        game_data["multiplier"] = current_mult
        game_data["pending_win"] = Decimal(str(game_data["bet"])) * current_mult
        
        # Verifica vittoria totale (ha cliccato tutti i diamanti)
        safe_cells = GRID_SIZE - game_data["mines"]
        if game_data["diamonds_found"] >= safe_cells:
            # Autocashout max win
            await _cashout_mines_game(update, context, game_data, pool, user_id, lang, max_win=True)
            return

        next_mult = calculate_multiplier(game_data["mines"], game_data["diamonds_found"] + 1, edge)
        
        text = _format_mines_play_msg(
             game_data["bet"], 
             game_data["mines"], 
             game_data["multiplier"], 
             next_mult, 
             Decimal("0"), # irrilevante qui
             lang
        )
        reply_markup = mines_game_keyboard(ui_grid, False, False, game_data["pending_win"], lang)
        await update_menu(context, update.effective_chat.id, text, reply_markup=reply_markup)


async def _cashout_mines_game(update: Update, context: ContextTypes.DEFAULT_TYPE, game_data: dict, pool, user_id: int, lang: str, max_win=False):
    """Accredita la vincita allo user se si ferma in tempo."""
    query = update.callback_query
    
    if game_data.get("state") != "playing":
        await query.answer("Partita non attiva.", show_alert=True)
        return
        
    game_data["state"] = "won"
    # Riveliamo il resto per fargli vedere le bombe "schivate" (trasparenza / fairplay)
    ui_grid = game_data["ui"]
    secret_grid = game_data["secret"]
    for i in range(GRID_SIZE):
        if ui_grid[i] == '?':
            if secret_grid[i] == 'M':
                ui_grid[i] = 'M'
            else:
                ui_grid[i] = 'D'
                
    win_amount = game_data["pending_win"]
    msg_al = "Hai completato la griglia!" if max_win else f"Hai incassato a {game_data['multiplier']:.2f}X"
    await query.answer(f"💰 CASHOUT: {win_amount:.2f} USDT! {msg_al}", show_alert=True)
    
    # Accredito vincita pura ('payout')
    # Poiché 'record_game_result' fa `+ payout - bet`, e noi avevamo già fatto `- bet` usando `loss`,
    # se noi chiamassimo record_game_result con payout normale, risottrarrebbe la bet. 
    # Dobbiamo accreditare MANUALMENTE il solo importo di payout tramite una query
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Leggiamo lock and update
                record = await conn.fetchrow("SELECT balance_usdt FROM users WHERE user_id=$1 FOR UPDATE", user_id)
                if record is None:
                    raise ValueError("User missing during cashout")
                bal = Decimal(str(record["balance_usdt"]))
                new_balance = bal + win_amount
                await conn.execute("UPDATE users SET balance_usdt=$1 WHERE user_id=$2", new_balance, user_id)
                
                # Log payout transazione
                await conn.execute(
                    """
                    INSERT INTO transactions (user_id, type, amount, status, note)
                    VALUES ($1, 'payout', $2, 'confirmed', 'Cashout Minigame Mines')
                    """,
                    user_id, win_amount
                )
    except Exception as e:
        logger.error(f"Errore Cashout Mines: {e}")
        await query.answer("Errore nel cashout! Contatta l'assistenza.", show_alert=True)
        return
    
    # Fine. Mostriamo UI aggiornata.
    text = (
        f"🎉 <b>VINCITA INASSATA!</b>\n\n"
        f"💸 Moltiplicatore: <b>{game_data['multiplier']:.2f}X</b>\n"
        f"💰 Vincita: <b>{win_amount:.2f} USDT</b> (su bet di {game_data['bet']:.2f})\n\n"
        f"<i>Il premio è stato accreditato nel tuo saldo!</i>"
    )
    reply_markup = mines_game_keyboard(ui_grid, game_over=True, is_win=True, win_amount=win_amount, lang=lang)
    await update_menu(context, update.effective_chat.id, text, reply_markup=reply_markup)
