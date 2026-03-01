import asyncio
import logging
from telegram import Bot
from db.connection import create_pool
from scheduler.jobs import build_scheduler
from config import BOT_TOKEN
from utils.logger_config import setup_logging
from utils.alerts import log_and_alert

logger = setup_logging("WorkerScheduler", "scheduler.log")

async def run_worker():
    logger.info(">>> [WORKER] Starting Scheduler Worker...")
    
    try:
        pool = await create_pool()
        bot = Bot(token=BOT_TOKEN)
        
        scheduler = build_scheduler(pool, bot)
        scheduler.start()
        
        logger.info(">>> [WORKER] Scheduler Worker is ONLINE!")
        
        # Keep running
        while True:
            await asyncio.sleep(3600)
            
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler shutting down...")
        if 'scheduler' in locals():
            scheduler.shutdown()
    except Exception as e:
        error_msg = f"WorkerScheduler FATAL ERROR: {e}"
        log_and_alert(error_msg, logger)
        raise

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except Exception as e:
        # Già loggato sopra ma per sicurezza
        pass
