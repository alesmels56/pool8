"""
bot/keyboards.py — Tutte le tastiere interattive del bot.
ReplyKeyboardMarkup (fissa) e InlineKeyboardMarkup (contestuale).
"""
from typing import List, Dict
from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
)


from utils.i18n import t

def main_keyboard(lang: str = "it") -> ReplyKeyboardMarkup:
    """Tastiera principale sempre visibile (2x2 bottoni)."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(t("menu_balance", lang)), KeyboardButton(t("menu_create", lang))],
            [KeyboardButton(t("menu_explore", lang)), KeyboardButton(t("btn_game_8ball", lang))],
            [KeyboardButton(t("menu_mybets", lang)), KeyboardButton(t("btn_game_mines", lang))],
            [KeyboardButton(t("menu_help", lang))],
        ],
        resize_keyboard=True,
    )


def main_inline_keyboard(lang: str = "it") -> InlineKeyboardMarkup:
    """Versione Inline del menu principale (più garantita per la visualizzazione)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("menu_balance", lang), callback_data="wallet:balance"),
            InlineKeyboardButton(t("menu_create", lang),  callback_data="menu:create"),
        ],
        [
            InlineKeyboardButton(t("menu_explore", lang), callback_data="menu:explore"),
            InlineKeyboardButton(t("menu_minigames", lang), callback_data="menu:minigames"),
        ],
        [
            InlineKeyboardButton(t("menu_mybets", lang),  callback_data="menu:mybets"),
            InlineKeyboardButton(t("menu_leaderboard", lang), callback_data="menu:leaderboard"),
        ],
        [
            InlineKeyboardButton(t("menu_help", lang),   callback_data="menu:help"),
        ]
    ])

def minigames_keyboard(lang: str = "it") -> InlineKeyboardMarkup:
    """Tastiera per selezionare quale minigioco giocare."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_game_8ball", lang), callback_data="menu:ball8"),
            InlineKeyboardButton(t("btn_game_mines", lang), callback_data="menu:mines"),
        ],
        [
            InlineKeyboardButton(t("btn_game_coinflip", lang), callback_data="menu:coinflip"),
            InlineKeyboardButton(t("btn_game_dice", lang), callback_data="menu:dice"),
        ],
        [
            InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main"),
        ]
    ])


def balance_keyboard(lang: str = "it") -> InlineKeyboardMarkup:
    """Tasti azione nella schermata saldo crediti."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_withdraw", lang),       callback_data="wallet:withdraw"),
            InlineKeyboardButton(t("btn_history", lang),        callback_data="wallet:history"),
        ],
        [
            InlineKeyboardButton(t("btn_copy_addr", lang),      callback_data="wallet:copy_address"),
            InlineKeyboardButton(t("btn_qr", lang),             callback_data="wallet:qr"),
        ],
        [
            InlineKeyboardButton(t("btn_deposit_info", lang),   callback_data="wallet:deposit_info"),
            InlineKeyboardButton(t("btn_referral", lang),       callback_data="wallet:referral"),
        ],
        [
            InlineKeyboardButton(t("btn_daily", lang),          callback_data="daily:faucet"),
            InlineKeyboardButton(t("btn_tip", lang),            callback_data="wallet:tip"),
        ],
        [
            InlineKeyboardButton(t("btn_back_menu", lang),      callback_data="menu:main"),
        ],
    ])


def insufficient_balance_keyboard(lang: str = "it") -> InlineKeyboardMarkup:
    """Tastiera mostrata quando il saldo è insufficiente per compiere un'azione."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("btn_deposit_info", lang), callback_data="wallet:deposit_info"),
            InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main")
        ]
    ])

def bet_message_keyboard(
    bet_uuid: str,
    options: List[str],
    summary: Dict[str, Dict],
    bot_username: str,
    lang: str = "it",
) -> InlineKeyboardMarkup:
    """Tastiera inline del messaggio scommessa.
    Usa l'indice dell'opzione invece del testo per evitare il limite di 64 byte.
    """
    option_buttons = []
    for i, opt in enumerate(options):
        count = summary.get(opt, {}).get("partecipanti", 0)
        option_buttons.append(
            InlineKeyboardButton(
                text=f"{opt} ({count} 👥)",
                callback_data=f"bet_pick:{bet_uuid}:{i}",
            )
        )

    rows = [option_buttons[i:i+2] for i in range(0, len(option_buttons), 2)]

    share_url = f"https://t.me/{bot_username}?start=bet_{bet_uuid}"
    rows.append([
        InlineKeyboardButton(
            t("btn_share", lang),
            url=f"https://t.me/share/url?url={share_url}"
        )
    ])
    # NOTE: No back button here — callers add navigation as needed.

    return InlineKeyboardMarkup(rows)


def challenge_keyboard(bet_uuid: str, lang: str = "it") -> InlineKeyboardMarkup:
    """Tasto per contestare un risultato durante il periodo di 'resolving'."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t("btn_challenge", lang), callback_data=f"bet_challenge_start:{bet_uuid}")
    ]])


def amount_selection_keyboard(
    bet_uuid: str,
    option_idx: int,
    min_bet: float,
    user_balance: float,
    lang: str = "it",
) -> InlineKeyboardMarkup:
    """
    Schermata selezione importo dopo aver scelto un'opzione.
    Usa l'indice dell'opzione invece del testo.
    """
    half = round(max(user_balance / 2, min_bet), 2)
    maxi = round(user_balance, 2)

    def fmt(v): return f"{v:.2f}"

    rows = [
        [
            InlineKeyboardButton(
                f"📉 Min {fmt(min_bet)} USDT",
                callback_data=f"bet_vote:{bet_uuid}:{option_idx}:{fmt(min_bet)}",
            ),
            InlineKeyboardButton(
                f"⚖️ Metà {fmt(half)} USDT",
                callback_data=f"bet_vote:{bet_uuid}:{option_idx}:{fmt(half)}",
            ),
            InlineKeyboardButton(
                f"📈 Max {fmt(maxi)} USDT",
                callback_data=f"bet_vote:{bet_uuid}:{option_idx}:{fmt(maxi)}",
            ),
        ],
        [
            InlineKeyboardButton(
                t("btn_custom_amount", lang),
                callback_data=f"bet_custom:{bet_uuid}:{option_idx}",
            ),
        ],
        [
            InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel"),
        ],
    ]

    return InlineKeyboardMarkup(rows)


def close_bet_keyboard(bet_uuid: str, lang: str = "it") -> InlineKeyboardMarkup:
    """Bottone chiudi scommessa (mostrato solo al creatore)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t("btn_close_bet", lang), callback_data=f"bet_close:{bet_uuid}")
    ]])


def winner_keyboard(bet_uuid: str, options: List[str]) -> InlineKeyboardMarkup:
    """Tastiera selezione vincitore. Usa indici per sicurezza."""
    buttons = [
        [InlineKeyboardButton(f"🏆 {opt}", callback_data=f"bet_winner:{bet_uuid}:{i}")]
        for i, opt in enumerate(options)
    ]
    return InlineKeyboardMarkup(buttons)


def duration_keyboard() -> InlineKeyboardMarkup:
    """Scelta durata scommessa."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⏱ 1 Ora",     callback_data="duration:1h"),
        InlineKeyboardButton("🕐 24 Ore",   callback_data="duration:24h"),
        InlineKeyboardButton("📅 3 Giorni", callback_data="duration:3gg"),
    ]])


def confirm_keyboard(action: str, lang: str = "it") -> InlineKeyboardMarkup:
    """Conferma / Annulla generico."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t("btn_confirm", lang), callback_data=f"confirm:{action}"),
        InlineKeyboardButton(t("btn_cancel", lang),  callback_data="cancel"),
    ]])


def withdrawal_confirm_keyboard(tx_id: str) -> InlineKeyboardMarkup:
    """Conferma prelievo (fee mostrata in precedenza)."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Conferma Prelievo", callback_data=f"withdraw_confirm:{tx_id}"),
        InlineKeyboardButton("❌ Annulla",           callback_data="cancel"),
    ]])
def ball8_keyboard(current_bet: Decimal, target: int, lang: str = "it") -> InlineKeyboardMarkup:
    """Tastiera per il gioco Ball 8 con puntata e target."""
    from utils.i18n import t
    
    # Riga 1: Selezione Numero (1-4)
    row_numbers_1 = [
        InlineKeyboardButton(("✅ " if target == i else "") + str(i), callback_data=f"ball8:target:{i}")
        for i in range(1, 5)
    ]
    # Riga 2: Selezione Numero (5-8)
    row_numbers_2 = [
        InlineKeyboardButton(("✅ " if target == i else "") + str(i), callback_data=f"ball8:target:{i}")
        for i in range(5, 9)
    ]
    
    # Riga 3: Controlli Puntata
    row_bet = [
        InlineKeyboardButton("➖ 1", callback_data="ball8:bet:-1"),
        InlineKeyboardButton("➖ 0.1", callback_data="ball8:bet:-0.1"),
        InlineKeyboardButton(f"💰 {current_bet:.1f}", callback_data="ball8:bet:info"),
        InlineKeyboardButton("➕ 0.1", callback_data="ball8:bet:+0.1"),
        InlineKeyboardButton("➕ 1", callback_data="ball8:bet:+1"),
    ]
    
    # Riga 4: Azioni
    row_actions = [
        InlineKeyboardButton(t("btn_back_menu", lang), callback_data="menu:main"),
        InlineKeyboardButton(t("btn_play", lang), callback_data="ball8:run"),
    ]
    
    return InlineKeyboardMarkup([row_numbers_1, row_numbers_2, row_bet, row_actions])

def admin_keyboard() -> InlineKeyboardMarkup:
    """Tastiera interattiva per il pannello Admin."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Statistiche", callback_data="admin:stats"),
            InlineKeyboardButton("🏦 Tesoreria", callback_data="admin:treasury"),
        ],
        [
            InlineKeyboardButton("🏆 Classifica Top", callback_data="admin:top"),
            InlineKeyboardButton("⏱ Scommesse Scadute", callback_data="admin:scadute"),
        ],
        [
            InlineKeyboardButton("⚙️ Impostazioni Sistema", callback_data="admin:settings"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast"),
            InlineKeyboardButton("💳 Accredita", callback_data="admin:credita"),
        ],
        [
            InlineKeyboardButton("🚫 Ban User", callback_data="admin:ban"),
            InlineKeyboardButton("✅ Unban User", callback_data="admin:unban"),
        ],
        [
            InlineKeyboardButton("📉 Debita", callback_data="admin:debita"),
            InlineKeyboardButton("🔥 Delete Bet", callback_data="admin:delete_bet"),
        ],
        [
            InlineKeyboardButton("🔙 Menu Principale", callback_data="menu:main"),
        ]
    ])
