import logging
import asyncio
from telegram import Bot
from config import BOT_TOKEN, ADMIN_IDS

logger = logging.getLogger(__name__)

async def send_admin_alert(message: str):
    """
    Invia un messaggio di allerta a tutti gli amministratori.
    Usato per segnalare crash o errori critici nei worker.
    """
    if not BOT_TOKEN or not ADMIN_IDS:
        logger.warning("BOT_TOKEN o ADMIN_IDS non configurati. Impossibile inviare alert.")
        return

    bot = Bot(token=BOT_TOKEN)
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=f"🚨 <b>CRITICAL SYSTEM ALERT</b>\n\n{message}",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Impossibile inviare alert all'admin {admin_id}: {e}")

def log_and_alert(message: str, logger_instance=None):
    """
    Logga l'errore e tenta di inviare un alert (async).
    """
    if logger_instance:
        logger_instance.error(message)
    else:
        logger.error(message)
    
    # Crea un task per l'invio asincrono senza bloccare l'esecuzione corrente
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(send_admin_alert(message))
        else:
            asyncio.run(send_admin_alert(message))
    except Exception as e:
        logger.error(f"Errore durante l'invio dell'alert di backup: {e}")
