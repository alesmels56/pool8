"""
engine/refund.py — Rimborso partecipanti per scommesse scadute (expired).
Fix: Bulk Transaction per aggiornamenti saldi atomici.
"""
import asyncio
import logging
from decimal import Decimal

import asyncpg
from telegram import Bot
from telegram.error import RetryAfter
from db.archive import archive_bet

from db.participations import get_all_participations
from db.bets import mark_expired
from db.admin import add_platform_profit
from config import EXPIRED_REFUND_PCT

logger = logging.getLogger(__name__)


async def run_refund(
    pool: asyncpg.Pool,
    bot: Bot,
    bet_uuid: str,
    bet=None,
) -> None:
    """
    Esegue il rimborso per una scommessa scaduta.
    Fase 1: Calcolo quote rimborso e update stato DB atomico.
    Fase 2: Throttled Telegram notification.
    """
    participations = await get_all_participations(pool, bet_uuid)

    if not participations:
        await mark_expired(pool, bet_uuid)
        return

    question = bet["question"] if bet else f"Scommessa {bet_uuid[:8]}"
    group_chat_id = bet.get("group_chat_id") if bet else None
    message_id = bet.get("message_id") if bet else None

    refunds = []
    
    # Fase 1: Calcolo rimborsi in memoria
    for p in participations:
        uid = p["user_id"]
        amount = Decimal(str(p["amount"]))
        refund = (amount * EXPIRED_REFUND_PCT).quantize(Decimal("0.000001"))
        penalty = amount - refund
        note = f"Rimborso 90% scommessa scaduta {bet_uuid[:8]}"
        refunds.append((uid, refund, penalty, note, amount))

    # Fase 2: TRANSAZIONE BULK ATOMICA
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Segna subito come expired per evitare doppi prelievi d'ufficio
            await conn.execute("UPDATE bets SET status = 'expired' WHERE uuid = $1", bet_uuid)

            # Inserisce massivamente gli accrediti e logga
            for uid, refund, _, note, _ in refunds:
                await conn.execute(
                    "UPDATE users SET balance_usdt = balance_usdt + $1 WHERE user_id = $2",
                    refund, uid,
                )
                await conn.execute(
                    """
                    INSERT INTO transactions (user_id, type, amount, status, note)
                    VALUES ($1, 'refund', $2, 'confirmed', $3)
                    """,
                    uid, refund, note,
                )
            
            # 3. Accredito Penali Totali alla Tesoreria della Piattaforma
            total_penalty = sum(p for _, _, p, _, _ in refunds)
            if total_penalty > 0:
                await add_platform_profit(pool=None, amount=total_penalty, conn=conn)

    logger.info(f"Refund DB Bulk Transaction completed for expired bet {bet_uuid[:8]}. Users refunded: {len(refunds)}")

    # Fase 3: NOTIFICHE TELEGRAM (Throttled & Error Safe)
    for uid, refund, penalty, _, original_amount in refunds:
        try:
            texto = (
                f"⏱ <b>Scommessa scaduta</b>\n\n"
                f"❓ {question}\n\n"
                f"Rimborso accreditato: <b>+{refund:.2f} USDT</b> (90% della tua puntata)\n"
                f"Penale trattenuta: <b>{penalty:.2f} USDT</b>"
            )
            await bot.send_message(chat_id=uid, text=texto, parse_mode="HTML")
            await asyncio.sleep(0.05)  # Throttling preventivo (max 20 msg/sec)
        except RetryAfter as e:
            logger.warning(f"Rate limited by Telegram. Sleeping for {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            try:
                await bot.send_message(chat_id=uid, text=texto, parse_mode="HTML")
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"Could not notify user {uid} about refund: {e}")

    # Aggiorna messaggio nel gruppo
    if group_chat_id and message_id:
        try:
            await bot.edit_message_text(
                chat_id=group_chat_id,
                message_id=message_id,
                text=(
                    f"⏱ <b>SCOMMESSA SCADUTA</b>\n\n"
                    f"❓ {question}\n\n"
                    f"Il creatore non ha selezionato un vincitore.\n"
                    f"Fondi rimborsati ({int(EXPIRED_REFUND_PCT * 100)}%) a {len(refunds)} partecipant{'e' if len(refunds) == 1 else 'i'}."
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Could not update group message for expired bet {bet_uuid[:8]}: {e}")

    # CLEANUP: Mark as expired and move to history
    try:
        async with pool.acquire() as conn:
            # Assicuratevi che lo stato sia expired prima dell'archiviazione
            await conn.execute("UPDATE bets SET status = 'expired' WHERE uuid = $1::uuid", bet_uuid)
            await archive_bet(pool, bet_uuid)
        logger.info(f"Bet {bet_uuid[:8]} archived after refund.")
    except Exception as e:
        logger.error(f"Failed to archive bet {bet_uuid[:8]} during cleanup: {e}")

    # TRUST SCORE: Penalizza creatore per scommessa scaduta (non chiusa)
    if bet and bet.get("creator_id"):
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE users
                    SET trust_score = GREATEST(0, trust_score - 20),
                        total_bets_created = total_bets_created + 1
                    WHERE user_id = $1
                    """,
                    bet["creator_id"]
                )
        except Exception as e:
            logger.warning(f"Trust score penalty failed for creator {bet['creator_id']}: {e}")
