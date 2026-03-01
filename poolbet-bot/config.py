"""
config.py — Costanti centralizzate del sistema PoolBet Bot.
Tutte le soglie e percentuali configurabili sono qui.
"""
import os
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

# ── Telegram ──────────────────────────────────────────────
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "PoolBetBot")

# ── Database ──────────────────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/poolbet")
REDIS_URL: str = os.getenv("REDIS_URL", "")  # redis://localhost:6379/0
DB_MIN_CONNECTIONS: int = 2
DB_MAX_CONNECTIONS: int = 10

# ── Webhooks (Alternative to Polling) ─────────────────────
WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "") # https://yourdomain.com/webhook
WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8443"))

# ── Blockchain / Polygon ──────────────────────────────────
POLYGON_RPC_HTTP: str = os.getenv("POLYGON_RPC_HTTP", "")
POLYGON_RPC_WS: str = os.getenv("POLYGON_RPC_WS", "")
HOT_WALLET_PRIVATE_KEY: str = os.getenv("HOT_WALLET_PRIVATE_KEY", "")
HOT_WALLET_MNEMONIC: str = os.getenv("HOT_WALLET_MNEMONIC", "")
COLD_WALLET_ADDRESS: str = os.getenv("COLD_WALLET_ADDRESS", "")

# ── Admin Whitelist ───────────────────────────────────────
# Array di interi per l'accesso ai comandi /admin
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()]
USDT_CONTRACT_ADDRESS: str = os.getenv(
    "USDT_CONTRACT_ADDRESS",
    "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",  # USDT Polygon mainnet
)

# ── Credit System ─────────────────────────────────────────
MIN_WITHDRAWAL: Decimal = Decimal(os.getenv("MIN_WITHDRAWAL", "10"))      # USDT minimi per prelievo
FEE_WITHDRAWAL: Decimal = Decimal(os.getenv("FEE_WITHDRAWAL", "0.50"))    # Fee fissa prelievo (gas cover)
BONUS_THRESHOLD: Decimal = Decimal(os.getenv("BONUS_THRESHOLD", "50"))    # Depositi >= X ottengono bonus
BONUS_PCT: Decimal = Decimal(os.getenv("BONUS_PCT", "0.05"))              # +5% crediti bonus

# ── Commissioni Scommessa (Modello Dinamico) ──────────────────
# Più alto è il pool, più bassa è la commissione della piattaforma.
# Formato: (Soglia Pool USDT, Percentuale Fee Piattaforma)
FEE_PLATFORM_TIERS = [
    (Decimal("100"),  Decimal("0.10")),  # Pool < 100 USDT: 10% Platform Fee
    (Decimal("500"),  Decimal("0.07")),  # Pool < 500 USDT: 7% Platform Fee
    (Decimal("2000"), Decimal("0.05")),  # Pool < 2000 USDT: 5% Platform Fee
    (Decimal("-1"),   Decimal("0.03")),  # Altrimenti: 3% Platform Fee
]

FEE_CREATOR: Decimal = Decimal("0.02")    # 2% al creatore sempre garantito
# Premio netto = pool * (1 - FEE_PLATFORM - FEE_CREATOR) = pool * 0.95

# ── Scommesse ─────────────────────────────────────────────
EXPIRED_REFUND_PCT: Decimal = Decimal("0.90")   # 90% rimborsato in caso di scadenza
EXPIRED_PENALTY_PCT: Decimal = Decimal("0.10")  # 10% trattenuto come penale
CHALLENGE_STAKE: Decimal = Decimal(os.getenv("CHALLENGE_STAKE", "5.00")) # Stake per contestare
CHALLENGE_DURATION_H: int = int(os.getenv("CHALLENGE_DURATION_H", "24")) # Durata finestra contestazione

# ── Hot Wallet Sweep ──────────────────────────────────────
HOT_WALLET_SWEEP_THRESHOLD: Decimal = Decimal(os.getenv("HOT_WALLET_SWEEP_THRESHOLD", "2000"))

# ── Scheduler ─────────────────────────────────────────────
SCHEDULER_EXPIRED_INTERVAL_SEC: int = 60   # Check scommesse scadute ogni 60s
SCHEDULER_SWEEP_INTERVAL_H: int = 1        # Sweep hot wallet ogni ora

# ── Durate scommessa predefinite (secondi) ────────────────
DURATIONS = {
    "1h": 3600,
    "24h": 86400,
    "3gg": 259200,
}
