"""
utils/formatting.py — Formattatori messaggi per il bot (Markdown/HTML).
"""
from decimal import Decimal
from typing import Dict, List


def _get_progress_bar(percentage: float, length: int = 10) -> str:
    """Genera una barra di progresso visuale tipo ██████░░░░."""
    filled = int(round(percentage / 100 * length))
    return "█" * filled + "░" * (length - filled)


def format_bet_message(bet, summary: Dict[str, Dict], lang: str = "it") -> str:
    """Formato del messaggio scommessa nel gruppo con visual UX potenziata."""
    from utils.i18n import t
    pool_total = Decimal(str(bet["pool_total"])) if not isinstance(bet["pool_total"], Decimal) else bet["pool_total"]
    expires = bet["expires_at"].strftime("%d/%m/%Y %H:%M") if hasattr(bet["expires_at"], "strftime") else str(bet["expires_at"])
    creator = f"@{bet['creator_username']}" if bet.get("creator_username") else (bet.get("creator_name") or "—")
    status = bet.get("status", "open")
    
    # Etichette tradotte
    status_label = {
        "open": "🟢 APERTA", 
        "closed": "🔴 CHIUSA", 
        "finalized": "✅ CONCLUSA", 
        "expired": "⏱ SCADUTA"
    }.get(status, status.upper())

    lines = [
        f"⚽ <b>SCOMMESSA {status_label}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    
    if pool_total >= Decimal("100"):
        lines.append("🔥 <b>HOT BET</b> 🔥")
        
    lines.append(f"❓ {bet['question']}")
    
    # Hashtag
    hashtags_str = str(bet.get('hashtags', ''))
    if hashtags_str and hashtags_str.strip():
        lines.append(f"🏷️ <i>{hashtags_str}</i>")
        
    trust = bet.get("trust_score", 50)
    trust_bar = "🟢" * (trust // 20) + "⚪" * (5 - trust // 20)
    
    lines.extend([
        f"👤 Creatore: {creator} (🛡️ 🛡️ <b>{trust}%</b> {trust_bar})",
        f"💰 Pool Totale: <b>{pool_total:.2f} USDT</b>",
    ])

    if status == "open":
        from datetime import datetime
        now = datetime.utcnow()
        expires_dt = bet["expires_at"]
        if expires_dt > now:
            diff = expires_dt - now
            hours, rem = divmod(diff.total_seconds(), 3600)
            minutes, _ = divmod(rem, 60)
            time_left = f"{int(hours)}h {int(minutes)}m"
            lines.append(f"⏳ Scade tra: {time_left}")
        else:
            lines.append("⏳ Scade: <i>imminente</i>")
    else:
        lines.append(f"⏱ Scaduta il: {expires} UTC")

    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # Margine casa (usiamo 5% di default se non specificato, ma l'engine usa quello del DB)
    house_edge = Decimal("0.05") 
    pool_netto = pool_total * (Decimal("1") - house_edge)

    for option, data in summary.items():
        count = data.get("partecipanti", 0)
        total = data.get("totale", Decimal("0"))
        
        # Calcolo Percentuale e Barra
        pct = (total / pool_total * 100) if pool_total > 0 else 0
        bar = _get_progress_bar(float(pct))
        
        # Calcolo Odds (Quota)
        if total > 0:
            quota = (pool_netto / total).quantize(Decimal("0.01"))
            odds_str = f"📈 Quota: <b>x{quota}</b>"
        else:
            odds_str = "📈 Quota: <b>TBD</b>"

        lines.append(f"🔹 <b>{option}</b>")
        lines.append(f"<code>{bar}</code> {pct:.1f}%")
        lines.append(f"  {count} 👥 — {total:.2f} USDT | {odds_str}")
        lines.append("") # Spacer

    if not summary:
        lines.append("  <i>Nessuna puntata ancora — sii il primo!</i>")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("👇 <b>Scommetti ora:</b>")

    return "\n".join(lines)


def format_balance_message(stats) -> str:
    """Formato schermata saldo crediti."""
    saldo = Decimal(str(stats["saldo_disponibile"]))
    depositato = Decimal(str(stats["totale_depositato"]))
    prelevato = Decimal(str(stats["totale_prelevato"]))
    bonus = Decimal(str(stats["bonus_accumulati"]))
    spesi = Decimal(str(stats["crediti_spesi"]))
    prelevabile = max(Decimal("0"), saldo - bonus)
    xp = stats.get("xp", 0)
    streak = stats.get("login_streak", 0)
    livello = int((xp / 100) ** 0.5) + 1 if xp > 0 else 1

    return (
        f"💳 <b>I TUOI CREDITI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Saldo Totale:    <b>{saldo:.2f} USDT</b>\n"
        f"💸 Prelevabile:     <b>{prelevabile:.2f} USDT</b>\n"
        f"🎁 Bonus (non prel.): <b>{bonus:.2f} USDT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 Tot. depositato: {depositato:.2f} USDT\n"
        f"📉 Tot. prelevato:  {prelevato:.2f} USDT\n"
        f"🎲 Usati in bet:    {spesi:.2f} USDT\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ Livello VIP: <b>{livello}</b> ({xp} XP)\n"
        f"🔥 Login Streak: <b>{streak} giorni</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 <b>Indirizzo ricarica (Polygon):</b>\n"
        f"<code>{stats['wallet_address']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Prelievo min: 10 USDT | Fee: 0.50 USDT\n"
    )



def format_history(txs: List) -> str:
    """Formato storico movimenti."""
    icons = {
        "deposit": "📥", "withdrawal": "📤", "bet": "🎲",
        "payout": "🏆", "fee": "💼", "refund": "↩️", "bonus": "🎁",
    }
    lines = ["📊 <b>Ultimi movimenti</b>\n━━━━━━━━━━━━━━━━━━━━"]
    for tx in txs:
        icon = icons.get(tx["type"], "•")
        sign = "+" if tx["type"] in ("deposit", "payout", "refund", "bonus") else "−"
        date = tx["created_at"].strftime("%d/%m %H:%M") if hasattr(tx["created_at"], "strftime") else ""
        note = f" <i>({tx['note']})</i>" if tx.get("note") else ""
        lines.append(f"{icon} {sign}{Decimal(str(tx['amount'])):.2f} USDT  <code>{date}</code>{note}")
    return "\n".join(lines)


def format_prize_notification(question: str, winner: str, quota: Decimal, pool: Decimal) -> str:
    """Notifica vittoria inviata al vincitore."""
    return (
        f"🏆 <b>Hai vinto!</b>\n\n"
        f"❓ {question}\n"
        f"✅ Vincitore: <b>{winner}</b>\n\n"
        f"💰 Pool totale: {pool:.2f} USDT\n"
        f"🎉 Il tuo premio: <b>+{quota:.2f} USDT</b>\n\n"
        f"I crediti sono già nel tuo saldo! 🚀"
    )

def format_bet_stats(bet, winner_option: str, winners: list, winner_total: Decimal, pool_total: Decimal, prize_netto: Decimal) -> str:
    """Statistiche finali scritte nel gruppo dopo la chiusura."""
    lines = [
        f"🏆 <b>SCOMMESSA CONCLUSA</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"❓ {bet['question']}",
        f"✅ Opzione Vincente: <b>{winner_option}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"💰 Pool Finale: <b>{pool_total:.2f} USDT</b>",
        f"🥇 Vincitori: {len(winners)}"
    ]

    if winner_total > 0:
        win_ratio = (prize_netto / winner_total).quantize(Decimal("0.01"))
        lines.append(f"📈 Moltiplicatore: <b>x{win_ratio}</b>")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("I premi sono stati accreditati sui saldi dei vincitori! 💸")
    return "\n".join(lines)
