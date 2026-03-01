import asyncio
import logging
from telegram import Bot
from db.connection import create_pool
from blockchain.listener import start_listener
from config import BOT_TOKEN
from utils.logger_config import setup_logging
from utils.alerts import log_and_alert

logger = setup_logging("WorkerBlockchain", "blockchain.log")
# Assicura che i log del modulo blockchain (listener) vadano nello stesso file
logging.getLogger("blockchain").setLevel(logging.INFO)
for h in logger.handlers:
    logging.getLogger("blockchain").addHandler(h)

async def run_worker():
    logger.info(">>> [WORKER] Starting Blockchain Listener Worker...")
    
    retry_count = 0
    while True:
        try:
            pool = await create_pool()
            bot = Bot(token=BOT_TOKEN)
            
            await start_listener(pool, bot)
            
            # Se esce dal listener senza eccezioni (raro)
            await asyncio.sleep(60)
            
        except Exception as e:
            retry_count += 1
            error_msg = f"WorkerBlockchain CRASHED (Retry {retry_count}): {e}"
            log_and_alert(error_msg, logger)
            
            # Backoff esponenziale
            wait_time = min(60 * 5, 5 * retry_count) 
            logger.info(f"Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info(">>> [WORKER] Blockchain Listener Worker stopped by user.")
    except Exception as e:
        log_and_alert(f"WorkerBlockchain FATAL EXIT: {e}", logger)
