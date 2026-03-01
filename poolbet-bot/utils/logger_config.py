import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(name: str, log_file: str = "bot.log", level=logging.INFO):
    """
    Configura il logging con RotatingFileHandler per evitare file troppo grandi.
    """
    # Assicurati che la cartella logs esista
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    log_path = os.path.join("logs", log_file)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Formattatore
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Handler per Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler per File Rotante (10MB per file, max 5 backup)
    file_handler = RotatingFileHandler(
        log_path, 
        maxBytes=10*1024*1024, 
        backupCount=5, 
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
