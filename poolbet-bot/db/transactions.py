"""
db/transactions.py — Ledger audit: scrittura e lettura storico movimenti.
"""
from typing import Optional, List
import asyncpg


async def write_tx(
    pool: asyncpg.Pool,
    user_id: int,
    type_: str,
    amount,
    tx_hash: Optional[str] = None,
    status: str = "pending",
    note: Optional[str] = None,
) -> int:
    """Scrive una voce nel ledger e restituisce l'id della transazione."""
    return await pool.fetchval(
        """
        INSERT INTO transactions (user_id, type, amount, tx_hash, status, note)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        user_id, type_, amount, tx_hash, status, note,
    )


async def confirm_tx(
    pool: asyncpg.Pool,
    tx_id: int,
    tx_hash: str,
) -> None:
    """Aggiorna status a 'confirmed' e salva il tx_hash on-chain."""
    await pool.execute(
        """
        UPDATE transactions
        SET status = 'confirmed', tx_hash = $1
        WHERE id = $2
        """,
        tx_hash, tx_id,
    )


async def fail_tx(pool: asyncpg.Pool, tx_id: int) -> None:
    """Segna una transazione come fallita."""
    await pool.execute(
        "UPDATE transactions SET status = 'failed' WHERE id = $1",
        tx_id,
    )


async def get_history(
    pool: asyncpg.Pool,
    user_id: int,
    limit: int = 15,
) -> List[asyncpg.Record]:
    """
    Storico movimenti di un utente (ultimi N), ordinati per data decrescente.
    Usato per la schermata 📊 Storico.
    """
    return await pool.fetch(
        """
        SELECT type, amount, tx_hash, status, note, created_at
        FROM transactions
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id, limit,
    )


async def get_global_big_wins(pool: asyncpg.Pool, limit: int = 3) -> List[asyncpg.Record]:
    """
    Recupera le vincite record più recenti della piattaforma per il ticker social.
    """
    return await pool.fetch(
        """
        SELECT t.amount, u.username, u.user_id, t.created_at
        FROM transactions t
        JOIN users u ON t.user_id = u.user_id
        WHERE t.type = 'payout' AND t.status = 'confirmed'
        ORDER BY t.amount DESC, t.created_at DESC
        LIMIT $1
        """,
        limit
    )
