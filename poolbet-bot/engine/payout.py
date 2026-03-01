"""
engine/payout.py — Distribuzione premi ai vincitori in modalità BULK (Atomica e Sicura).
Fix: Tutti gli accrediti avvengono in un'unica transazione atomica.
Se Telegram va in rate limit, i fondi sono comunque già sicuri.
"""
import asyncio
import logging
from decimal import Decimal, ROUND_DOWN

import asyncpg
from telegram import Bot
from telegram.error import RetryAfter

from db.participations import get_winners, get_winner_total
from db.bets import get_bet
from db.admin import add_platform_profit
from utils.formatting import format_prize_notification, format_bet_stats
from config import FEE_PLATFORM_TIERS, FEE_CREATOR

logger = logging.getLogger(__name__)

QUANTIZE = Decimal("0.000001")


async def run_payout(
    pool: asyncpg.Pool,
    bot: Bot,
    bet_uuid: str,
    winner_option: str,
    bet=None,
) -> None:
    """
    Distribuisce i premi ai vincitori.
    Fase 1: Calcola le quote in memoria.
    Fase 2: Bulk update su Database (Transazione unica ACIDs).
    Fase 3: Notifiche Telegram (con sleep per RetryAfter rate limit).
    """
    if bet is None:
        bet = await get_bet(pool, bet_uuid)

    pool_total   = Decimal(str(bet["pool_total"]))
    creator_id   = bet["creator_id"]
    group_chat_id = bet.get("group_chat_id")
    message_id   = bet.get("message_id")
    question     = bet["question"]

    if pool_total <= 0:
        logger.info(f"Payout skipped for bet {bet_uuid[:8]}: empty pool.")
        return

    # Calcolo Fee Piattaforma Dinamica (Tiered)
    plat_fee_pct = FEE_PLATFORM_TIERS[-1][1] # Default (ultima fascia)
    for limit, pct in FEE_PLATFORM_TIERS:
        if limit > 0 and pool_total < limit:
            plat_fee_pct = pct
            break
            
    fee_platform  = (pool_total * plat_fee_pct).quantize(QUANTIZE, rounding=ROUND_DOWN)
    creator_share = (pool_total * FEE_CREATOR).quantize(QUANTIZE, rounding=ROUND_DOWN)
    prize_netto   = pool_total - fee_platform - creator_share

    winners      = await get_winners(pool, bet_uuid, winner_option)
    winner_total = await get_winner_total(pool, bet_uuid, winner_option)

    payouts = []

    if not winners or winner_total <= 0:
        logger.warning(f"No winners for bet {bet_uuid[:8]}. Refunding pool to creator.")
        payouts.append((creator_id, prize_netto + creator_share, "Nessun vincitore — pool restituito al creatore"))
    else:
        # Calcolo quote in memoria
        distributed = Decimal("0")
        for i, winner in enumerate(winners):
            uid      = winner["user_id"]
            stake    = Decimal(str(winner["amount"]))

            is_last = (i == len(winners) - 1)
            if is_last:
                quota = prize_netto - distributed
            else:
                quota = (stake / winner_total * prize_netto).quantize(QUANTIZE, rounding=ROUND_DOWN)
                distributed += quota

            payouts.append((uid, quota, f"Premio bet {bet_uuid[:8]}: {winner_option}"))

    # FASE 2: TRANSAZIONE BULK ATOMICA
    async with pool.acquire() as conn:
        async with conn.transaction():
            for uid, amount, note in payouts:
                await conn.execute(
                    "UPDATE users SET balance_usdt = balance_usdt + $1 WHERE user_id = $2",
                    amount, uid,
                )
                await conn.execute(
                    """
                    INSERT INTO transactions (user_id, type, amount, status, note)
                    VALUES ($1, 'payout', $2, 'confirmed', $3)
                    """,
                    uid, amount, note,
                )

            # Creator share (solo se ci sono stati vincitori e non è un full refund)
            if winners and winner_total > 0 and creator_share > 0:
                await conn.execute(
                    "UPDATE users SET balance_usdt = balance_usdt + $1 WHERE user_id = $2",
                    creator_share, creator_id,
                )
                await conn.execute(
                    """
                    INSERT INTO transactions (user_id, type, amount, status, note)
                    VALUES ($1, 'fee', $2, 'confirmed', $3)
                    """,
                    creator_id, creator_share, f"Creator share bet {bet_uuid[:8]}",
                )
            
            # 3. Accredito Fee Piattaforma alla Tesoreria (e quota Referral)
            if fee_platform > 0:
                await add_platform_profit(pool=None, amount=fee_platform, conn=conn, source_user_id=creator_id)

    logger.info(f"Payout DB Bulk Transaction completed for bet {bet_uuid[:8]}.")

    # FASE 3: NOTIFICHE TELEGRAM (Throttled & Error Safe)
    if winners and winner_total > 0:
        for uid, amount, note in payouts:
            try:
                # Animazione WOW vittoria (sticker festoso)
                try:
                    await bot.send_sticker(
                        chat_id=uid,
                        sticker="CAACAgIAAxkBAAIBMmWrL1cZH2-HydAoC5fNJ5C6tGKrAAJHBAAC6WVhS_eRVKOCHK6INAQAB"
                    )
                except Exception:
                    pass
                msg = format_prize_notification(question, winner_option, amount, pool_total)
                await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
                await asyncio.sleep(0.05)  # Throttling preventivo (max 20 msg/sec)
            except RetryAfter as e:
                logger.warning(f"Rate limited by Telegram. Sleeping for {e.retry_after}s")
                await asyncio.sleep(e.retry_after)
                try:
                    await bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Could not notify winner {uid}: {e}")

    # Notifica creator share
    if winners and winner_total > 0 and creator_share > 0:
        try:
            await bot.send_message(
                chat_id=creator_id,
                text=f"💼 <b>Creator Fee incassata</b>: +{creator_share:.2f} USDT",
                parse_mode="HTML"
            )
        except Exception:
            pass

    # Aggiorna messaggio nel gruppo
    if group_chat_id and message_id:
        try:
            stats_text = format_bet_stats(bet, winner_option, winners, winner_total, pool_total, prize_netto)
            await bot.edit_message_text(
                chat_id=group_chat_id,
                message_id=message_id,
                text=stats_text,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning(f"Could not update group message for bet {bet_uuid[:8]}: {e}")

    # CLEANUP: Mark as finalized and move to history
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE bets SET status = 'finalized' WHERE uuid = $1::uuid", 
                bet_uuid
            )
            # Archiviazione (Sposta in history e cancella dalla tabella principale)
            from db.archive import archive_bet
            await archive_bet(pool, bet_uuid)
            
        logger.info(f"Bet {bet_uuid[:8]} finalized and archived after payout.")
    except Exception as e:
        logger.error(f"Failed to finalize/archive bet {bet_uuid[:8]}: {e}")

    # TRUST SCORE: Aumenta affidabilità del creatore per chiusura regolare
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET trust_score = LEAST(100, trust_score + 5),
                    total_bets_created = total_bets_created + 1,
                    total_bets_closed = total_bets_closed + 1
                WHERE user_id = $1
                """,
                creator_id
            )
    except Exception as e:
        logger.warning(f"Trust score update failed for creator {creator_id}: {e}")
