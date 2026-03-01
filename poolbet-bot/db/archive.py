import logging
import asyncpg
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def archive_old_data(pool: asyncpg.Pool, days: int = 30):
    """
    Moves old finalized/expired data to history tables to keep active tables small.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Archive Bets
            print(f"Archiving bets older than {cutoff}...")
            # We copy then delete to ensure referential integrity during the move
            await conn.execute("""
                INSERT INTO history_bets 
                SELECT * FROM bets 
                WHERE status IN ('finalized', 'expired') AND expires_at < $1
                ON CONFLICT DO NOTHING;
            """, cutoff)
            
            # 2. Archive Participations (linked to already archived bets)
            await conn.execute("""
                INSERT INTO history_participations
                SELECT p.* FROM participations p
                JOIN history_bets hb ON p.bet_uuid = hb.uuid
                ON CONFLICT DO NOTHING;
            """)
            
            # 3. Archive Transactions
            await conn.execute("""
                INSERT INTO history_transactions
                SELECT * FROM transactions
                WHERE (status IN ('confirmed', 'failed')) AND created_at < $1
                ON CONFLICT DO NOTHING;
            """, cutoff)
            
            # 4. Delete from active tables
            # Delete participations first (FK)
            deleted_parts = await conn.fetchval("""
                DELETE FROM participations
                WHERE bet_uuid IN (SELECT uuid FROM history_bets);
            """)
            
            deleted_bets = await conn.fetchval("""
                DELETE FROM bets
                WHERE status IN ('finalized', 'expired') AND expires_at < $1;
            """, cutoff)
            
            deleted_txs = await conn.fetchval("""
                DELETE FROM transactions
                WHERE (status IN ('confirmed', 'failed')) AND created_at < $1;
            """, cutoff)
            
            logger.info(f"Archiving complete: moved bets, participations, and transactions.")
            return True
