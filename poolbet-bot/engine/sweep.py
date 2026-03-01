"""
engine/sweep.py — Auto-sweep del hot wallet verso il cold wallet se il saldo supera la soglia.
"""
import logging
from decimal import Decimal

from blockchain.usdt import get_usdt_balance, send_usdt
from blockchain.wallet import get_hot_wallet_address
from config import HOT_WALLET_SWEEP_THRESHOLD, COLD_WALLET_ADDRESS, HOT_WALLET_PRIVATE_KEY

logger = logging.getLogger(__name__)

# Mantieni sempre questo minimo nel hot wallet per i prelievi in corso
HOT_WALLET_MINIMUM = Decimal("500")


async def check_sweep() -> None:
    """
    Controlla il saldo del hot wallet e invia l'eccesso al cold wallet.
    Eseguito ogni ora dallo Scheduler.
    """
    hot_address = get_hot_wallet_address()
    balance = get_usdt_balance(hot_address)

    logger.info(f"Hot wallet balance: {balance:.2f} USDT (threshold: {HOT_WALLET_SWEEP_THRESHOLD})")

    if balance <= HOT_WALLET_SWEEP_THRESHOLD:
        return

    sweep_amount = balance - HOT_WALLET_MINIMUM
    if sweep_amount <= 0:
        return

    logger.info(f"Sweeping {sweep_amount:.2f} USDT to cold wallet {COLD_WALLET_ADDRESS}")

    try:
        tx_hash = send_usdt(
            to_address=COLD_WALLET_ADDRESS,
            amount_usdt=sweep_amount,
            private_key=HOT_WALLET_PRIVATE_KEY,
        )
        logger.info(f"Sweep completed. Tx: {tx_hash}")
    except Exception as e:
        logger.error(f"Sweep failed: {e}")
