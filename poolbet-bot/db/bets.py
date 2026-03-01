"""
db/bets.py — Query per il ciclo di vita delle scommesse.
"""
import json
from decimal import Decimal
from typing import Optional, List
import asyncpg


async def create_bet(
    pool: asyncpg.Pool,
    creator_id: int,
    question: str,
    options: List[str],
    min_bet: Decimal,
    expires_at,
    media_file_id: Optional[str] = None,
    media_type: Optional[str] = None,
    is_public: bool = True,
    hashtags: str = "",
) -> str:
    """
    Crea una nuova scommessa. Restituisce l'UUID generato.
    options è una lista di stringhe; viene convertita in JSONB {opzione: 0}.
    """
    options_dict = {opt: 0 for opt in options}
    return await pool.fetchval(
        """
        INSERT INTO bets (creator_id, media_file_id, media_type, question, options, min_bet, expires_at, is_public, hashtags)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9)
        RETURNING uuid::text
        """,
        creator_id,
        media_file_id,
        media_type,
        question,
        json.dumps(options_dict),
        min_bet,
        expires_at,
        is_public,
        hashtags,
    )


async def get_bet(pool: asyncpg.Pool, uuid: str) -> Optional[dict]:
    """Legge una scommessa con username del creatore (per deep-link)."""
    row = await pool.fetchrow(
        """
        SELECT b.*, u.username AS creator_username, u.trust_score
        FROM bets b
        JOIN users u ON b.creator_id = u.user_id
        WHERE b.uuid = $1::uuid
        """,
        uuid,
    )
    return _parse_bet_record(row) if row else None


async def list_user_bets(
    pool: asyncpg.Pool,
    user_id: int,
) -> List[dict]:
    """Lista scommesse in cui l'utente è coinvolto (creatore o partecipante)."""
    rows = await pool.fetch(
        """
        SELECT DISTINCT b.uuid, b.question, b.pool_total, b.expires_at, b.status, b.winner_option, b.creator_id, b.created_at,
               (SELECT COUNT(*) FROM participations WHERE bet_uuid = b.uuid) AS participants_count
        FROM bets b
        LEFT JOIN participations p ON b.uuid = p.bet_uuid
        WHERE b.creator_id = $1 OR p.user_id = $1
        ORDER BY b.created_at DESC
        """,
        user_id,
    )
    return [_parse_bet_record(r) for r in rows]


def _parse_bet_record(row: asyncpg.Record) -> dict:
    """Helper per convertire record in dict e parsare options JSONB."""
    if not row:
        return {}
    d = dict(row)
    if "options" in d and isinstance(d["options"], str):
        try:
            d["options"] = json.loads(d["options"])
        except Exception:
            d["options"] = {}
    return d


async def set_message_info(
    pool: asyncpg.Pool,
    uuid: str,
    group_chat_id: int,
    message_id: int,
) -> None:
    """Salva il riferimento al messaggio nel gruppo per future edit."""
    await pool.execute(
        "UPDATE bets SET group_chat_id = $1, message_id = $2 WHERE uuid = $3::uuid",
        group_chat_id, message_id, uuid,
    )


async def finalize_bet_optimistic(
    pool: asyncpg.Pool,
    uuid: str,
    winner_option: str,
    challenge_hours: int = 24,
) -> bool:
    """
    Segna la scommessa in 'resolving' con un vincitore proposto.
    Inizia il periodo di contestazione.
    """
    result = await pool.execute(
        """
        UPDATE bets
        SET status = 'resolving', 
            winner_option = $1,
            challenge_period_end = NOW() + ($3 || ' hours')::interval
        WHERE uuid = $2::uuid AND status IN ('open', 'closed')
        """,
        winner_option, uuid, str(challenge_hours),
    )
    return result == "UPDATE 1"


async def set_bet_challenged(
    pool: asyncpg.Pool,
    uuid: str,
    challenger_id: int,
    stake: Decimal,
) -> bool:
    """Marca la scommessa come contestata."""
    result = await pool.execute(
        """
        UPDATE bets
        SET status = 'challenged',
            is_challenged = TRUE,
            challenger_id = $1,
            challenge_stake = $2
        WHERE uuid = $3::uuid AND status = 'resolving'
        """,
        challenger_id, stake, uuid,
    )
    return result == "UPDATE 1"


async def get_expired_bets(pool: asyncpg.Pool) -> List[asyncpg.Record]:
    """
    Restituisce tutte le scommesse scadute non ancora processate.
    Usato dallo Scheduler ogni 60 secondi.
    """
    return await pool.fetch(
        """
        SELECT uuid, creator_id, question, pool_total, group_chat_id, message_id
        FROM bets
        WHERE expires_at < NOW() AND status = 'open'
        """,
    )


async def mark_expired(pool: asyncpg.Pool, uuid: str) -> None:
    """Segna la scommessa come expired."""
    await pool.execute(
        "UPDATE bets SET status = 'expired' WHERE uuid = $1::uuid",
        uuid,
    )


async def get_open_bets(pool: asyncpg.Pool, limit: int = 5, offset: int = 0) -> List[dict]:
    """Lista tutte le scommesse aperte nel sistema (esplorazione pubblica)."""
    rows = await pool.fetch(
        """
        SELECT b.uuid, b.question, b.pool_total, b.expires_at, b.status, u.username as creator_username, u.trust_score,
               (SELECT COUNT(*) FROM participations WHERE bet_uuid = b.uuid) AS participants_count,
               b.media_file_id, b.media_type, b.options, b.hashtags
        FROM bets b
        JOIN users u ON b.creator_id = u.user_id
        WHERE b.status = 'open' AND b.is_public = TRUE
        ORDER BY (b.pool_total >= 100) DESC, b.created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset
    )
    return [_parse_bet_record(r) for r in rows]

async def get_open_bets_by_tag(pool: asyncpg.Pool, tag: str, limit: int = 5, offset: int = 0) -> List[dict]:
    """Lista scommesse pubbliche aperte che contengono lo specifico hashtag."""
    search_term = f"%{tag}%"
    rows = await pool.fetch(
        """
        SELECT b.uuid, b.question, b.pool_total, b.expires_at, b.status, u.username as creator_username, u.trust_score,
               (SELECT COUNT(*) FROM participations WHERE bet_uuid = b.uuid) AS participants_count,
               b.media_file_id, b.media_type, b.options, b.hashtags
        FROM bets b
        JOIN users u ON b.creator_id = u.user_id
        WHERE b.status = 'open' AND b.is_public = TRUE AND b.hashtags ILIKE $3
        ORDER BY (b.pool_total >= 100) DESC, b.created_at DESC
        LIMIT $1 OFFSET $2
        """,
        limit, offset, search_term
    )
    return [_parse_bet_record(r) for r in rows]


async def increment_option_vote(
    pool: asyncpg.Pool,
    uuid: str,
    option: str,
) -> None:
    """
    Incrementa il contatore voti di un'opzione nel campo JSONB options.
    Chiamato dopo aver registrato la partecipazione.
    """
    await pool.execute(
        """
        UPDATE bets
        SET options = jsonb_set(
            options,
            ARRAY[$1],
            (COALESCE(options->$1, '0')::int + 1)::text::jsonb
        )
        WHERE uuid = $2::uuid
        """,
        option, uuid,
    )


async def reset_all_bets_db(pool: asyncpg.Pool) -> int:
    """
    Resetta tutte le scommesse 'open' o 'closed' portandole a 'expired'.
    Restituisce il numero di righe modificate.
    """
    res = await pool.execute(
        "UPDATE bets SET status = 'expired' WHERE status IN ('open', 'closed')"
    )
    # res e' una stringa tipo "UPDATE 15"
    try:
        return int(res.split(" ")[1])
    except (IndexError, ValueError):
        return 0


async def get_random_open_bet(pool: asyncpg.Pool) -> Optional[dict]:
    """
    Restituisce una scommessa aperta a caso (per il pulsante Shuffle).
    """
    row = await pool.fetchrow(
        """
        SELECT b.uuid, b.question, b.pool_total, b.expires_at, b.status, u.username as creator_username, u.trust_score,
               (SELECT COUNT(*) FROM participations WHERE bet_uuid = b.uuid) AS participants_count,
               b.media_file_id, b.media_type, b.options, b.hashtags
        FROM bets b
        JOIN users u ON b.creator_id = u.user_id
        WHERE b.status = 'open' AND b.is_public = TRUE
        ORDER BY RANDOM()
        LIMIT 1
        """
    )
    return _parse_bet_record(row) if row else None
