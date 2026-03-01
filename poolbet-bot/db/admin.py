"""
db/admin.py — Funzioni per la gestione della tesoreria e statistiche piattaforma.
"""
import asyncpg
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

async def get_platform_balance(pool: asyncpg.Pool) -> Decimal:
    """Restituisce il saldo attuale della tesoreria (profitti)."""
    val = await pool.fetchval("SELECT profit_balance_usdt FROM platform_stats WHERE id = 1")
    return Decimal(str(val)) if val is not None else Decimal("0")

async def add_platform_profit(pool: asyncpg.Pool, amount: Decimal, conn: asyncpg.Connection = None, source_user_id: int = None) -> None:
    """
    Aggiunge un profitto (fee, o perdita) alla tesoreria.
    Se c'è un source_user_id e l'utente è stato invitato da qualcuno (referred_by),
    il 20% di questa fee viene accreditata al referrer come "rendita passiva".
    """
    connection = conn
    should_close = False
    if not connection:
        connection = await pool.acquire()
        should_close = True

    try:
        final_platform_profit = amount
        
        # Gestione Referral Passive Income
        if source_user_id:
            referrer_id = await connection.fetchval("SELECT referred_by FROM users WHERE user_id = $1", source_user_id)
            if referrer_id:
                # Diamo il 20% delle commissioni del bot all'affiliato
                referral_cut = amount * Decimal("0.20")
                if referral_cut > 0:
                    final_platform_profit = amount - referral_cut
                    
                    # Accredita commissione al referrer
                    await connection.execute(
                        "UPDATE users SET balance_usdt = balance_usdt + $1, bonus_credits = bonus_credits + $1 WHERE user_id = $2",
                        referral_cut, referrer_id
                    )
                    
                    # Memorizza la transazione referenziale
                    await connection.execute(
                        """
                        INSERT INTO transactions (user_id, type, amount, status, note)
                        VALUES ($1, 'commission', $2, 'confirmed', 'Commissione Referral (Passive Income)')
                        """,
                        referrer_id, referral_cut
                    )
                    logger.info(f"Distribuita commissione {referral_cut} USDT a referrer {referrer_id} da user {source_user_id}")
        
        # Accredito in Tesoreria 
        query = "UPDATE platform_stats SET profit_balance_usdt = profit_balance_usdt + $1, updated_at = CURRENT_TIMESTAMP WHERE id = 1"
        await connection.execute(query, final_platform_profit)
        
    finally:
        if should_close and connection:
            await pool.release(connection)

async def withdraw_platform_profit(pool: asyncpg.Pool, amount: Decimal) -> bool:
    """Registra un prelievo dalla tesoreria (eseguito dall'admin)."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchval("SELECT profit_balance_usdt FROM platform_stats WHERE id = 1 FOR UPDATE")
            current = Decimal(str(current))
            if current < amount:
                return False
            
            await conn.execute(
                """
                UPDATE platform_stats 
                SET profit_balance_usdt = profit_balance_usdt - $1,
                    total_withdrawn_admin = total_withdrawn_admin + $1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                amount
            )
            return True

async def execute_emergency_exit(pool: asyncpg.Pool) -> Decimal:
    """
    Liquidazione forzata: chiude tutte le scommesse aperte e trasferisce i pool alla tesoreria.
    Ritorna il totale recuperato.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Somma tutti i pool totali delle scommesse aperte
            total_bets = await conn.fetchval("SELECT SUM(pool_total) FROM bets WHERE status = 'open'")
            total_bets = Decimal(str(total_bets or "0"))
            
            # 2. Somma tutti i saldi attuali di tutti gli utenti
            total_users = await conn.fetchval("SELECT SUM(balance_usdt) FROM users")
            total_users = Decimal(str(total_users or "0"))
            
            total_to_recover = total_bets + total_users
            
            if total_to_recover > 0:
                # 3. Chiudi tutte le scommesse
                await conn.execute("UPDATE bets SET status = 'closed' WHERE status = 'open'")
                
                # 4. Azzera tutti i saldi utenti
                await conn.execute("UPDATE users SET balance_usdt = 0")
                
                # 5. Trasferisci TUTTO in tesoreria per il prelievo finale
                await conn.execute(
                    "UPDATE platform_stats SET profit_balance_usdt = profit_balance_usdt + $1 WHERE id = 1",
                    total_to_recover
                )
            
            return total_to_recover


async def get_setting(pool: asyncpg.Pool, key: str, default_value: str = None) -> str:
    """Recupera un'impostazione di sistema dinamica (ritorna stringa)"""
    val = await pool.fetchval("SELECT value FROM system_settings WHERE key = $1", key)
    return val if val is not None else default_value


async def set_setting(pool: asyncpg.Pool, key: str, value: str) -> None:
    """Imposta un'impostazione di sistema dinamica (upsert)"""
    await pool.execute(
        """
        INSERT INTO system_settings (key, value) 
        VALUES ($1, $2)
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """,
        key, str(value)
    )
