"""
db/participations.py — Transazione atomica per puntate e query riepilogo.
"""
from decimal import Decimal
from typing import Optional, List, Dict
import asyncpg


async def place_bet_atomic(
    pool: asyncpg.Pool,
    user_id: int,
    bet_uuid: str,
    option: str,
    amount: Decimal,
) -> Dict:
    """
    Registra una puntata in modo completamente atomico.

    Operazioni (tutte dentro una singola transazione):
      1. SELECT ... FOR UPDATE  → lock della riga utente (previene double-spending)
      2. Verifica saldo sufficiente
      3. UPDATE users.balance_usdt -= amount
      4. UPDATE bets.pool_total   += amount
      5. INSERT participations
      6. INSERT transactions (tipo 'bet')

    Returns:
        {"success": True, "new_pool": Decimal}
        oppure lancia ValueError con messaggio leggibile.
    """
    async with pool.acquire() as conn:
        async with conn.transaction():

            # 1. Lock riga utente
            user = await conn.fetchrow(
                "SELECT balance_usdt FROM users WHERE user_id = $1 FOR UPDATE",
                user_id,
            )
            if user is None:
                raise ValueError("Utente non trovato. Usa /start per registrarti.")

            balance = Decimal(str(user["balance_usdt"]))
            if balance < amount:
                raise ValueError(
                    f"Saldo insufficiente: hai {balance:.2f} USDT, "
                    f"la puntata minima è {amount:.2f} USDT."
                )

            # 2. Verifica che la scommessa sia ancora aperta e l'utente non abbia già puntato
            bet = await conn.fetchrow(
                "SELECT status, min_bet FROM bets WHERE uuid = $1::uuid FOR UPDATE",
                bet_uuid,
            )
            if bet is None:
                raise ValueError("Scommessa non trovata.")
            if bet["status"] != "open":
                raise ValueError("Questa scommessa non è più aperta.")
            if amount < Decimal(str(bet["min_bet"])):
                raise ValueError(
                    f"La puntata minima è {bet['min_bet']:.2f} USDT."
                )

            # 3. Sottrai saldo utente
            await conn.execute(
                "UPDATE users SET balance_usdt = balance_usdt - $1 WHERE user_id = $2",
                amount, user_id,
            )

            # 4. Aggiungi al pool scommessa
            new_pool = await conn.fetchval(
                """
                UPDATE bets SET pool_total = pool_total + $1
                WHERE uuid = $2::uuid
                RETURNING pool_total
                """,
                amount, bet_uuid,
            )

            # 5. Registra partecipazione (UNIQUE constraint previene doppio inserimento)
            try:
                await conn.execute(
                    """
                    INSERT INTO participations (bet_uuid, user_id, option_voted, amount)
                    VALUES ($1::uuid, $2, $3, $4)
                    """,
                    bet_uuid, user_id, option, amount,
                )
            except asyncpg.UniqueViolationError:
                raise ValueError("Hai già partecipato a questa scommessa.")

            # 6. Scrivi nel ledger
            await conn.execute(
                """
                INSERT INTO transactions (user_id, type, amount, status, note)
                VALUES ($1, 'bet', $2, 'confirmed', $3)
                """,
                user_id, amount, f"Puntata su '{option}' — bet {bet_uuid[:8]}",
            )

    return {"success": True, "new_pool": Decimal(str(new_pool))}


async def place_seed_liquidity(
    pool: asyncpg.Pool,
    creator_id: int,
    bet_uuid: str,
    options: List[str],
    total_liquidity: Decimal,
) -> None:
    """
    Inserisce liquidità iniziale ('Pump.Fun' style) dividendo l'importo totale
    equamente tra tutte le opzioni fornite. 
    Questa liquidità appartiene al creatore.
    """
    if total_liquidity <= 0:
        return

    amount_per_option = round(total_liquidity / Decimal(len(options)), 6)
    actual_total = amount_per_option * Decimal(len(options))

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Lock e addebito utente creatore
            user = await conn.fetchrow(
                "SELECT balance_usdt FROM users WHERE user_id = $1 FOR UPDATE",
                creator_id,
            )
            if user is None:
                raise ValueError("Creatore non trovato.")
            
            balance = Decimal(str(user["balance_usdt"]))
            if balance < actual_total:
                raise ValueError(
                    f"Saldo insufficiente per la liquidità iniziale di {actual_total:.2f} USDT."
                )

            await conn.execute(
                "UPDATE users SET balance_usdt = balance_usdt - $1 WHERE user_id = $2",
                actual_total, creator_id,
            )

            # 2. Update pool_total scommessa
            await conn.execute(
                "UPDATE bets SET pool_total = pool_total + $1 WHERE uuid = $2::uuid",
                actual_total, bet_uuid,
            )

            # 3. Inserisci N partecipazioni (1 per ogni opzione)
            for opt in options:
                await conn.execute(
                    """
                    INSERT INTO participations (bet_uuid, user_id, option_voted, amount)
                    VALUES ($1::uuid, $2, $3, $4)
                    """,
                    bet_uuid, creator_id, opt, amount_per_option,
                )

            # 4. Inserisci 1 transazione riassuntiva
            await conn.execute(
                """
                INSERT INTO transactions (user_id, type, amount, status, note)
                VALUES ($1, 'seed_liquidity', $2, 'confirmed', $3)
                """,
                creator_id, actual_total, f"Liquidità iniziale scommessa {bet_uuid[:8]}"
            )


async def get_bet_summary(
    pool: asyncpg.Pool,
    bet_uuid: str,
) -> Dict[str, Dict]:
    """
    Riepilogo puntate per opzione.
    Returns: {"Opzione A": {"partecipanti": 3, "totale": Decimal("15")}, ...}
    """
    rows = await pool.fetch(
        """
        SELECT option_voted,
               COUNT(*)      AS partecipanti,
               SUM(amount)   AS totale
        FROM participations
        WHERE bet_uuid = $1::uuid
        GROUP BY option_voted
        """,
        bet_uuid,
    )
    return {
        row["option_voted"]: {
            "partecipanti": row["partecipanti"],
            "totale": Decimal(str(row["totale"])),
        }
        for row in rows
    }


async def get_winners(
    pool: asyncpg.Pool,
    bet_uuid: str,
    winner_option: str,
) -> List[asyncpg.Record]:
    """Lista di (user_id, username, amount) dei vincitori."""
    return await pool.fetch(
        """
        SELECT p.user_id, u.username, p.amount
        FROM participations p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.bet_uuid = $1::uuid AND p.option_voted = $2
        """,
        bet_uuid, winner_option,
    )


async def get_winner_total(
    pool: asyncpg.Pool,
    bet_uuid: str,
    winner_option: str,
) -> Decimal:
    """Totale puntato dai vincitori (denominatore per calcolo quota proporzionale)."""
    total = await pool.fetchval(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM participations
        WHERE bet_uuid = $1::uuid AND option_voted = $2
        """,
        bet_uuid, winner_option,
    )
    return Decimal(str(total))


async def get_all_participations(
    pool: asyncpg.Pool,
    bet_uuid: str,
) -> List[asyncpg.Record]:
    """Tutte le partecipazioni a una scommessa (usato per rimborso expired)."""
    return await pool.fetch(
        """
        SELECT p.user_id, u.username, p.amount
        FROM participations p
        JOIN users u ON p.user_id = u.user_id
        WHERE p.bet_uuid = $1::uuid
        """,
        bet_uuid,
    )
