"""
db/users.py — Query CRUD per la tabella users e Credit System.
"""
from decimal import Decimal
from typing import Optional
import asyncpg
from config import BONUS_THRESHOLD, BONUS_PCT, MIN_WITHDRAWAL
from db.admin import add_platform_profit, get_setting
from utils.cache import cache_get, cache_set, cache_delete


async def register_user(
    pool: asyncpg.Pool,
    user_id: int,
    username: Optional[str],
    wallet_address: str,
    referred_by: Optional[int] = None,
) -> None:
    """Registra un nuovo utente (idempotente: aggiorna username se già esiste)."""
    await pool.execute(
        """
        INSERT INTO users (user_id, username, wallet_address, referred_by)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
        """,
        user_id, username, wallet_address, referred_by,
    )


async def get_user(pool: asyncpg.Pool, user_id: int) -> Optional[asyncpg.Record]:
    """Restituisce il record utente (con cache)."""
    cache_key = f"user:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    user = await pool.fetchrow(
        "SELECT * FROM users WHERE user_id = $1",
        user_id,
    )
    if user:
        await cache_set(cache_key, dict(user), ttl_seconds=600) # Cache 10 min
    return user


async def get_user_by_wallet(pool: asyncpg.Pool, wallet_address: str) -> Optional[asyncpg.Record]:
    """Lookup utente tramite wallet address (usato dal Blockchain Listener)."""
    return await pool.fetchrow(
        "SELECT user_id, username FROM users WHERE wallet_address = $1",
        wallet_address,
    )


async def set_user_language(pool: asyncpg.Pool, user_id: int, lang: str) -> None:
    """Aggiorna la lingua preferita dell'utente (e pulisce cache)."""
    await pool.execute(
        "UPDATE users SET language = $1 WHERE user_id = $2",
        lang, user_id,
    )
    await cache_delete(f"user:{user_id}")
    await cache_delete(f"lang:{user_id}")


async def get_user_language(pool: asyncpg.Pool, user_id: int) -> str:
    """Restituisce la lingua dell'utente (con cache). Default 'en'."""
    cache_key = f"lang:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    lang = await pool.fetchval(
        "SELECT language FROM users WHERE user_id = $1",
        user_id,
    )
    lang = lang if lang else "en"
    await cache_set(cache_key, lang, ttl_seconds=3600)
    return lang


async def credit_deposit(
    pool: asyncpg.Pool,
    user_id: int,
    amount: Decimal,
    tx_hash: str,
) -> Decimal:
    """
    Accredita un deposito USDT confermato on-chain.
    Calcola e applica il bonus ricarica se il deposito supera BONUS_THRESHOLD.
    Restituisce il bonus applicato (0 se nessun bonus).

    IDEMPOTENTE: se tx_hash è già presente nel ledger, il deposito viene
    ignorato silenziosamente (previene doppio accredito in caso di restart
    del Blockchain Listener o riconnessione WebSocket).
    """
    bonus = amount * BONUS_PCT if amount >= BONUS_THRESHOLD else Decimal("0")

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Guard idempotenza: controlla se questa tx è già stata processata
            already = await conn.fetchval(
                "SELECT 1 FROM transactions WHERE tx_hash = $1 AND type = 'deposit'",
                tx_hash,
            )
            if already:
                return Decimal("-1")  # -1 segnala che era già a ledger (per non inviare doppia notifica)
            await conn.execute(
                """
                UPDATE users
                SET balance_usdt   = balance_usdt + $1 + $2,
                    total_deposited = total_deposited + $1,
                    bonus_credits   = bonus_credits + $2
                WHERE user_id = $3
                """,
                amount, bonus, user_id,
            )
            await conn.execute(
                """
                INSERT INTO transactions (user_id, type, amount, tx_hash, status, note)
                VALUES ($1, 'deposit', $2, $3, 'confirmed', $4)
                """,
                user_id, amount, tx_hash,
                f"Deposito + bonus {bonus:.6f}" if bonus > 0 else "Deposito",
            )
            if bonus > 0:
                await conn.execute(
                    """
                    INSERT INTO transactions (user_id, type, amount, tx_hash, status, note)
                    VALUES ($1, 'bonus', $2, NULL, 'confirmed', 'Bonus ricarica 5%')
                    """,
                    user_id, bonus,
                )

    return bonus


async def get_balance_stats(pool: asyncpg.Pool, user_id: int) -> Optional[asyncpg.Record]:
    """
    Restituisce statistiche complete dei crediti per la schermata saldo:
    saldo_disponibile, totale_depositato, totale_prelevato, bonus_accumulati,
    crediti_spesi_in_scommesse.
    """
    return await pool.fetchrow(
        """
        SELECT
            balance_usdt                                                    AS saldo_disponibile,
            total_deposited                                                 AS totale_depositato,
            total_withdrawn                                                 AS totale_prelevato,
            bonus_credits                                                   AS bonus_accumulati,
            GREATEST(0, total_deposited - total_withdrawn
                     + bonus_credits - balance_usdt)                       AS crediti_spesi,
            wallet_address,
            COALESCE(trust_score, 50)                                       AS trust_score,
            COALESCE(total_bets_created, 0)                                 AS total_bets_created,
            COALESCE(total_bets_closed, 0)                                  AS total_bets_closed,
            COALESCE(xp, 0)                                                 AS xp,
            COALESCE(login_streak, 0)                                       AS login_streak
        FROM users
        WHERE user_id = $1
        """,
        user_id,
    )


async def execute_withdrawal(
    pool: asyncpg.Pool,
    user_id: int,
    gross_amount: Decimal,
    fee_amount: Decimal,
) -> Optional[int]:
    """
    Esegue il prelievo in modo atomico.
    gross_amount = importo richiesto + fee_amount.
    Restituisce l'id della transazione creata, oppure None se saldo insufficiente.
    """
    net_amount = gross_amount - fee_amount

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Lock riga utente
            record = await conn.fetchrow(
                "SELECT balance_usdt, bonus_credits FROM users WHERE user_id = $1 FOR UPDATE",
                user_id,
            )
            if record is None:
                return None
            balance = Decimal(str(record["balance_usdt"]))
            bonus = Decimal(str(record["bonus_credits"]))
            # Saldo prelevabile = saldo totale - bonus non prelevabili
            withdrawable = balance - bonus
            if withdrawable < gross_amount:
                return None


            await conn.execute(
                """
                UPDATE users
                SET balance_usdt    = balance_usdt - $1,
                    total_withdrawn = total_withdrawn + $2
                WHERE user_id = $3
                """,
                gross_amount, net_amount, user_id,
            )
            tx_id = await conn.fetchval(
                """
                INSERT INTO transactions (user_id, type, amount, status, note)
                VALUES ($1, 'withdrawal', $2, 'pending', $3)
                RETURNING id
                """,
                user_id, net_amount,
                f"Prelievo {net_amount:.2f} USDT (fee {fee_amount:.2f})"
            )
            # Add implicit profit to platform
            await add_platform_profit(pool=None, amount=fee_amount, conn=conn, source_user_id=user_id)

    return tx_id


async def check_low_balance(
    pool: asyncpg.Pool,
    user_id: int,
    min_bet: Decimal,
) -> bool:
    """
    Restituisce True se l'utente ha saldo insufficiente per la puntata minima.
    Usato per mostrare CTA di ricarica.
    """
    record = await pool.fetchrow(
        "SELECT balance_usdt FROM users WHERE user_id = $1",
        user_id,
    )
    if record is None:
        return True
    return Decimal(str(record["balance_usdt"])) < min_bet

async def add_xp(pool: asyncpg.Pool, user_id: int, amount: int) -> int:
    """Aggiunge XP a un utente e restituisce il nuovo totale."""
    new_xp = await pool.fetchval(
        "UPDATE users SET xp = xp + $1 WHERE user_id = $2 RETURNING xp",
        amount, user_id
    )
    return new_xp if new_xp else 0

async def claim_daily_faucet(pool: asyncpg.Pool, user_id: int) -> tuple[Decimal, int, int]:
    """
    Gestisce la logica del faucet giornaliero.
    Restituisce (bonus_ricevuto, nuova_streak, xp_guadagnati).
    Garantisce che possa essere riscosso solo una volta al giorno (UTC base).
    Restituisce (0, 0, 0) se è già stato riscosso oggi.
    """
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT last_login, login_streak FROM users WHERE user_id = $1", user_id
        )
        if not record:
            return Decimal("0"), 0, 0

        from datetime import datetime, date
        today = datetime.utcnow().date()
        last = record["last_login"]
        streak = record["login_streak"]

        if last and last.date() == today:
            # Già riscosso oggi
            return Decimal("0"), streak, 0

        # Calcola nuova streak
        if last and last.date() == (today - datetime.timedelta(days=1)).date():
            streak += 1  # Giorno consecutivo
        else:
            streak = 1  # Streak persa o primo giorno

        # Calcola premio (max 0.50 al 7° giorno consecutivo)
        bonus_val = min(0.10 * streak, 0.50)
        bonus = Decimal(str(bonus_val))
        xp_gain = 50 * streak

        await conn.execute(
            """
            UPDATE users SET 
                bonus_credits = bonus_credits + $1,
                balance_usdt = balance_usdt + $1,
                login_streak = $2,
                last_login = timezone('utc', now()),
                xp = xp + $3
            WHERE user_id = $4
            """,
            bonus, streak, xp_gain, user_id
        )
        await conn.execute(
            """
            INSERT INTO transactions (user_id, type, amount, status, note, tx_hash)
            VALUES ($1, 'bonus', $2, 'confirmed', $3, NULL)
            """,
            user_id, bonus, f"🎁 Daily Faucet (Giorno {streak})"
        )
    return bonus, streak, xp_gain

async def record_game_result(
    pool: asyncpg.Pool,
    user_id: int,
    bet_amount: Decimal,
    is_win: bool,
    multiplier: Decimal = Decimal("7.0")
) -> Decimal:
    """
    Registra il risultato di un minigioco (Ball 8).
    Sottrae la puntata, e se vince aggiunge la vincita.
    Ritorna il nuovo saldo.
    """
    payout = bet_amount * multiplier if is_win else Decimal("0")
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Lock e check saldo
            record = await conn.fetchrow(
                "SELECT balance_usdt FROM users WHERE user_id = $1 FOR UPDATE",
                user_id,
            )
            if record is None:
                raise ValueError("User not found in database")
            current_balance = Decimal(str(record["balance_usdt"]))
            if current_balance < bet_amount:
                raise ValueError("Insufficient balance")
            
            # 2. Aggiorna Saldo
            new_balance = current_balance - bet_amount + payout
            await conn.execute(
                "UPDATE users SET balance_usdt = $1 WHERE user_id = $2",
                new_balance, user_id
            )
            
            # 3. Log Transazione (usa tipi supportati: 'bet' per spesa, 'payout' per vincita)
            await conn.execute(
                """
                INSERT INTO transactions (user_id, type, amount, status, note)
                VALUES ($1, 'bet', $2, 'confirmed', 'Puntata Minigame Ball 8')
                """,
                user_id, -bet_amount
            )
            
            if is_win:
                await conn.execute(
                    """
                    INSERT INTO transactions (user_id, type, amount, status, note)
                    VALUES ($1, 'payout', $2, 'confirmed', 'Vincita Minigame Ball 8')
                    """,
                    user_id, payout
                )
            
            # 4. Accredito Perdita alla Tesoreria e Affiliato
            if not is_win:
                await add_platform_profit(pool=None, amount=bet_amount, conn=conn, source_user_id=user_id)
            
            return new_balance


async def credit_referral_bonus(
    pool: asyncpg.Pool,
    referrer_id: int,
    bonus: Decimal = Decimal("1.00"),
) -> None:
    """
    Accredita un bonus referral NON PRELEVABILE al referrer.
    Il bonus viene aggiunto a bonus_credits (spendibile ma non prelevabile).
    """
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET bonus_credits = bonus_credits + $1, balance_usdt = balance_usdt + $1 WHERE user_id = $2",
                bonus, referrer_id,
            )
            await conn.execute(
                """
                INSERT INTO transactions (user_id, type, amount, status, note)
                VALUES ($1, 'bonus', $2, 'confirmed', 'Bonus Referral (non prelevabile)')
                """,
                referrer_id, bonus,
            )

async def send_tip(
    pool: asyncpg.Pool,
    sender_id: int,
    receiver_username: str,
    amount: Decimal
) -> tuple[bool, str, Optional[int], Optional[Decimal]]:
    """
    Invia una mancia (tip) P2P da sender_id a receiver_username.
    Detrae una fee del 5% per la piattaforma.
    Restituisce (successo_booleano, messaggio_risposta, receiver_id_se_trovato, net_amount).
    """
    clean_username = receiver_username.replace("@", "").strip()
    
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Trova ID del destinatario
            rec = await conn.fetchrow(
                "SELECT user_id FROM users WHERE username ILIKE $1",
                clean_username
            )
            if not rec:
                return False, "err_user_not_found", None, None
                
            receiver_id = rec["user_id"]
            if receiver_id == sender_id:
                return False, "err_self_tip", None, None
                
            # 2. Lock e controllo saldo mittente
            sender_rec = await conn.fetchrow(
                "SELECT balance_usdt FROM users WHERE user_id = $1 FOR UPDATE",
                sender_id
            )
            if not sender_rec or Decimal(str(sender_rec["balance_usdt"])) < amount:
                return False, "err_insufficient", None, None
                
            # Lock destinatario
            await conn.execute("SELECT 1 FROM users WHERE user_id = $1 FOR UPDATE", receiver_id)
            
            # 4. Calcolo Fee Dinamica (es. 0.05)
            tip_fee_str = await get_setting(conn, "tip_fee", "0.05")
            fee_pct = Decimal(tip_fee_str)
            fee = amount * fee_pct
            net_amount = amount - fee
            
            # 5. Aggiorna Saldi (Atomo)
            await conn.execute("UPDATE users SET balance_usdt = balance_usdt - $1 WHERE user_id = $2", amount, sender_id)
            await conn.execute("UPDATE users SET balance_usdt = balance_usdt + $1 WHERE user_id = $2", net_amount, receiver_id)
            
            # 6. Registra fee per la piattaforma e per l'affiliato
            await add_platform_profit(pool=None, amount=fee, conn=conn, source_user_id=sender_id)
            
            # 7. Genera Transazioni storiche
            await conn.execute(
                "INSERT INTO transactions (user_id, type, amount, status, note) VALUES ($1, 'tip', $2, 'confirmed', $3)",
                sender_id, -amount, f"Mancia inviata a @{clean_username}"
            )
            await conn.execute(
                "INSERT INTO transactions (user_id, type, amount, status, note) VALUES ($1, 'tip', $2, 'confirmed', $3)",
                receiver_id, net_amount, "Mancia ricevuta"
            )
            
            return True, "tip_success", receiver_id, net_amount
