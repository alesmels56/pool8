"""
scheduler/jobs.py — APScheduler jobs: controllo scommesse scadute e sweep hot wallet.
"""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from db.bets import get_expired_bets
from db.archive import archive_old_data
from engine.payout import run_payout
from config import SCHEDULER_EXPIRED_INTERVAL_SEC, SCHEDULER_SWEEP_INTERVAL_H

logger = logging.getLogger(__name__)


async def job_check_resolving_bets(pool, bot) -> None:
    """
    Controlla scommesse in 'resolving' il cui periodo di contestazione è scaduto.
    Se NON sfidate, le finalizza e paga.
    """
    try:
        # Trova scommesse in resolving che hanno superato il challenge_period_end e NON sono challenged
        resolving = await pool.fetch(
            """
            SELECT * FROM bets 
            WHERE status = 'resolving' 
              AND challenge_period_end <= NOW()
              AND is_challenged = FALSE
            """
        )
        for bet in resolving:
            logger.info(f"Challenge period expired for bet {bet['uuid']}. Auto-payout starting.")
            # run_payout si occuperà di aggiornare a 'finalized' alla fine
            await run_payout(pool, bot, str(bet["uuid"]), bet["winner_option"], bet)
    except Exception as e:
        logger.error(f"Error in job_check_resolving_bets: {e}")


async def job_check_expired_bets(pool, bot) -> None:
    """
    Controlla ogni 60 secondi se ci sono scommesse scadute non processate.
    Per ogni scommessa scaduta: la segna come expired e rimborsa i partecipanti.
    """
    try:
        expired = await get_expired_bets(pool)
        for bet in expired:
            logger.info(f"Processing expired bet: {bet['uuid']}")
            await run_refund(pool, bot, str(bet["uuid"]), bet)
    except Exception as e:
        logger.error(f"Error in job_check_expired_bets: {e}")


async def job_sweep_wallet() -> None:
    """Controlla ogni ora se il hot wallet supera la soglia e invia l'eccesso al cold wallet."""
    try:
        await check_sweep()
    except Exception as e:
        logger.error(f"Error in job_sweep_wallet: {e}")


async def job_archive_data(pool) -> None:
    """Sposta i dati vecchi nelle tabelle history per performance."""
    try:
        await archive_old_data(pool, days=30)
    except Exception as e:
        logger.error(f"Error in job_archive_data: {e}")


def build_scheduler(pool, bot) -> AsyncIOScheduler:
    """
    Costruisce e configura lo scheduler con i due job principali.
    Da chiamare in main.py dopo aver creato il pool DB.
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        lambda: asyncio.create_task(job_check_expired_bets(pool, bot)),
        trigger="interval",
        seconds=SCHEDULER_EXPIRED_INTERVAL_SEC,
        id="check_expired_bets",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: asyncio.create_task(job_check_resolving_bets(pool, bot)),
        trigger="interval",
        seconds=300, # Ogni 5 minuti
        id="check_resolving_bets",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: asyncio.create_task(job_sweep_wallet()),
        trigger="interval",
        hours=SCHEDULER_SWEEP_INTERVAL_H,
        id="sweep_hot_wallet",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: asyncio.create_task(job_archive_data(pool)),
        trigger="interval",
        hours=24,
        id="archive_old_data",
        replace_existing=True,
    )

    return scheduler
