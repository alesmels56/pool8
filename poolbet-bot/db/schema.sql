-- ============================================================
-- PoolBet Bot — Schema PostgreSQL v1.1
-- Esegui: psql -d poolbet -f db/schema.sql
-- ============================================================

-- Abilita generazione UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- SYSTEM SETTINGS: configurabili dall'admin a runtime
-- ============================================================
CREATE TABLE IF NOT EXISTS system_settings (
    key          TEXT PRIMARY KEY,
    value        TEXT NOT NULL,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- USERS: profili utente, saldi interni, ledger crediti
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id          BIGINT PRIMARY KEY,                          -- Telegram User ID
    username         TEXT,
    balance_usdt     DECIMAL(18, 6) DEFAULT 0
                         CHECK (balance_usdt >= 0),              -- Crediti interni, mai negativi
    wallet_address   TEXT UNIQUE NOT NULL,                       -- Indirizzo Polygon HD derivato
    total_deposited  DECIMAL(18, 6) DEFAULT 0,                   -- Totale USDT depositati (storico)
    total_withdrawn  DECIMAL(18, 6) DEFAULT 0,                   -- Totale USDT prelevati (storico)
    bonus_credits    DECIMAL(18, 6) DEFAULT 0,                   -- Bonus ricarica accumulati
    language         VARCHAR(2) DEFAULT 'en',                    -- Lingua scelta ('en'/'it')
    referred_by      BIGINT REFERENCES users(user_id),           -- Referral ID
    trust_score      INTEGER DEFAULT 50,                         -- Reputazione (0-100)
    total_bets_created INTEGER DEFAULT 0,
    total_bets_closed  INTEGER DEFAULT 0,
    xp               INT DEFAULT 0,                              -- Punti esperienza
    login_streak     INT DEFAULT 0,                              -- Giorni consecutivi
    last_login       TIMESTAMP,                                  -- Ultimo accesso (faucet)
    is_banned        BOOLEAN DEFAULT FALSE,                      -- Ban per admin control
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- BETS: scommesse create dagli utenti
-- ============================================================
CREATE TABLE IF NOT EXISTS bets (
    uuid             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id       BIGINT NOT NULL REFERENCES users(user_id),
    media_file_id    TEXT,                                       -- ID File Telegram (Foto/Video)
    media_type       TEXT,                                       -- 'photo' or 'video'
    question         TEXT NOT NULL,
    options          JSONB NOT NULL,                             -- {"Opzione A": 0, "Opzione B": 0}
    pool_total       DECIMAL(18, 6) DEFAULT 0
                         CHECK (pool_total >= 0),
    min_bet          DECIMAL(18, 6) NOT NULL
                         CHECK (min_bet > 0),
    status           TEXT DEFAULT 'open'
                         CHECK (status IN ('open', 'closed', 'resolving', 'challenged', 'finalized', 'expired')),
    winner_option    TEXT,                                       -- NULL finché non finalizzata
    challenge_period_end TIMESTAMP,                              -- Fine del periodo di contestazione
    is_challenged    BOOLEAN DEFAULT FALSE,                      -- Se la scommessa è stata contestata
    challenger_id    BIGINT REFERENCES users(user_id),           -- Chi ha contestato
    challenge_stake  DECIMAL(18, 6),                             -- Stake messo dal challenger
    group_chat_id    BIGINT,                                     -- Chat Telegram dove è stata pubblicata
    message_id       BIGINT,                                     -- ID messaggio per edit_message_text
    is_public        BOOLEAN DEFAULT TRUE,                       -- Visibilità in Esplora
    hashtags         TEXT,                                       -- Tag per ricerca
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at       TIMESTAMP NOT NULL
);

-- ============================================================
-- PARTICIPATIONS: ogni singola puntata
-- ============================================================
CREATE TABLE IF NOT EXISTS participations (
    id               SERIAL PRIMARY KEY,
    bet_uuid         UUID NOT NULL REFERENCES bets(uuid),
    user_id          BIGINT NOT NULL REFERENCES users(user_id),
    option_voted     TEXT NOT NULL,
    amount           DECIMAL(18, 6) NOT NULL
                         CHECK (amount > 0),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (bet_uuid, user_id, option_voted)                     -- Un utente = una puntata per ogni opzione
);

-- ============================================================
-- TRANSACTIONS: ledger completo per audit e storico utente
-- ============================================================
CREATE TABLE IF NOT EXISTS transactions (
    id           SERIAL PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users(user_id),
    type         TEXT NOT NULL
                     CHECK (type IN ('deposit', 'withdrawal', 'bet', 'payout', 'fee', 'refund', 'bonus', 'seed_liquidity')),
    amount       DECIMAL(18, 6) NOT NULL,
    tx_hash      TEXT,                                           -- Hash Polygon (solo per depositi/prelievi)
    status       TEXT DEFAULT 'pending'
                     CHECK (status IN ('pending', 'confirmed', 'failed')),
    note         TEXT,                                           -- Riferimento opzionale (es. bet_uuid)
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDICI per performance delle query frequenti
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_bets_status       ON bets(status);
CREATE INDEX IF NOT EXISTS idx_bets_expires_at   ON bets(expires_at);
CREATE INDEX IF NOT EXISTS idx_bets_creator      ON bets(creator_id);
CREATE INDEX IF NOT EXISTS idx_part_bet_uuid     ON participations(bet_uuid);
CREATE INDEX IF NOT EXISTS idx_part_user_id      ON participations(user_id);
CREATE INDEX IF NOT EXISTS idx_tx_user_id        ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_tx_type           ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_users_wallet      ON users(wallet_address);
-- Tabella per tracciare i profitti accumulati dalla piattaforma
CREATE TABLE IF NOT EXISTS platform_stats (
    id SERIAL PRIMARY KEY,
    profit_balance_usdt DECIMAL(20, 6) DEFAULT 0,
    total_withdrawn_admin DECIMAL(20, 6) DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inizializza la riga unica (se non esiste)
INSERT INTO platform_stats (id, profit_balance_usdt) 
VALUES (1, 0) 
ON CONFLICT (id) DO NOTHING;

-- Final cleanup

-- ============================================================
-- HISTORY TABLES: for long-term storage of old data
-- ============================================================
CREATE TABLE IF NOT EXISTS history_bets (LIKE bets INCLUDING ALL);
CREATE TABLE IF NOT EXISTS history_participations (LIKE participations INCLUDING ALL);
CREATE TABLE IF NOT EXISTS history_transactions (LIKE transactions INCLUDING ALL);
