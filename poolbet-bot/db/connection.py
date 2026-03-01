"""
db/connection.py — Setup del pool di connessioni asyncpg a PostgreSQL.
"""
import asyncpg
from config import DATABASE_URL, DB_MIN_CONNECTIONS, DB_MAX_CONNECTIONS


async def create_pool() -> asyncpg.Pool:
    """Crea e restituisce un asyncpg.Pool configurato."""
    pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=DB_MIN_CONNECTIONS,
        max_size=DB_MAX_CONNECTIONS,
        command_timeout=60,
        statement_cache_size=0, # Necessario per pgbouncer (Supabase) in Transaction mode
    )
    return pool


async def close_pool(pool: asyncpg.Pool) -> None:
    """Chiude il pool di connessioni in modo ordinato."""
    await pool.close()
