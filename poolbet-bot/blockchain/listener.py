"""
blockchain/listener.py — WebSocket listener per eventi Transfer USDT su Polygon.
Monitora il contratto USDT e accredita crediti agli utenti quando ricevono fondi.
"""
import asyncio
import logging
from decimal import Decimal

from web3 import Web3, HTTPProvider
from telegram import Bot

import asyncpg
from blockchain.usdt import ERC20_ABI, raw_to_usdt, USDT_DECIMALS
from db.users import get_user_by_wallet, credit_deposit
from config import POLYGON_RPC_HTTP, USDT_CONTRACT_ADDRESS

logger = logging.getLogger(__name__)


import traceback

async def start_listener(pool: asyncpg.Pool, bot: Bot) -> None:
    """
    Avvia il listener WebSocket per eventi Transfer USDT su Polygon.
    Loop infinito con reconnect automatico in caso di errore.
    """
    while True:
        try:
            await _run_listener(pool, bot)
        except Exception:
            logger.error(f"Blockchain listener error:\n{traceback.format_exc()}")
            logger.info("Reconnecting in 10s...")
            await asyncio.sleep(10)


async def _run_listener(pool: asyncpg.Pool, bot: Bot) -> None:
    """Loop principale del listener via HTTP Polling per massima stabilità (Web3 Sync)."""
    # Usiamo il provider HTTP sincrono che abbiamo verificato funzionare via CLI
    w3 = Web3(HTTPProvider(POLYGON_RPC_HTTP))
    
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(USDT_CONTRACT_ADDRESS),
        abi=ERC20_ABI,
    )

    logger.info("Blockchain listener connected to Polygon via Sync HTTP Polling.")

    # Inizializza l'ultimo blocco processato (sync call in thread)
    last_block = await asyncio.to_thread(w3.eth.get_block_number)
    
    while True:
        try:
            current_block = await asyncio.to_thread(w3.eth.get_block_number)
            if current_block > last_block:
                logger.info(f"Checking blocks {last_block+1} to {current_block}")
                # Recupera gli eventi Transfer dal last_block al current_block
                # Usiamo get_logs invece di create_filter per evitare problemi con i provider
                entries = await asyncio.to_thread(
                    contract.events.Transfer.get_logs,
                    from_block=last_block + 1,
                    to_block=current_block
                )
                for event in entries:
                    try:
                        await _handle_transfer_event(event, pool, bot)
                    except Exception as he:
                        logger.error(f"Error handling event: {he}")
                
                last_block = current_block
        except Exception as e:
            if "429" in str(e):
                logger.warning("RPC Rate Limit (429) hit. Waiting 60s...")
                await asyncio.sleep(60)
            else:
                logger.error(f"Polling error:\n{traceback.format_exc()}")
            
        await asyncio.sleep(30)  # Polling ogni 30 secondi (più conservativo per Polygon)


async def _handle_transfer_event(event, pool: asyncpg.Pool, bot: Bot) -> None:
    """
    Gestisce un singolo evento Transfer.
    Controlla se il destinatario è un utente registrato e accredita i crediti.
    """
    args = event.get("args", {})
    to_address = args.get("to")
    raw_value = args.get("value")
    
    # In Web3 v7, transaction_hash might be an AttributeDict or HexBytes
    tx_hash_raw = event.get("transactionHash") or event.get("transaction_hash")
    tx_hash = tx_hash_raw.hex() if hasattr(tx_hash_raw, "hex") else str(tx_hash_raw)
    amount = raw_to_usdt(raw_value)

    if amount <= Decimal("0"):
        return

    # Cerca l'utente per wallet address
    user = await get_user_by_wallet(pool, to_address)
    if user is None:
        return  # Non è un nostro utente

    user_id = user["user_id"]
    logger.info(f"Deposit detected: {amount} USDT → user {user_id} (tx: {tx_hash})")

    # Accredita crediti con eventuale bonus
    bonus = await credit_deposit(pool, user_id, amount, tx_hash)

    # Se bonus è -1 significa che la tx era già a ledger (idempotente)
    if bonus == Decimal("-1"):
        logger.info(f"Deposit tx {tx_hash} already processed. Skipping notification.")
        return

    # Notifica l'utente via Telegram
    msg = (
        f"✅ <b>Deposito confermato!</b>\n\n"
        f"💰 Accreditato: <b>+{amount:.2f} USDT</b>"
    )
    if bonus > Decimal("0"):
        msg += f"\n🎁 Bonus ricarica: <b>+{bonus:.2f} USDT</b>"
    msg += f"\n\n🔗 Tx: <code>{tx_hash}</code>"

    try:
        await bot.send_message(
            chat_id=user_id,
            text=msg,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.warning(f"Could not notify user {user_id}: {e}")
