"""
blockchain/usdt.py — Interazione con il contratto ERC-20 USDT su Polygon.
Copre: saldo, trasferimento, stima gas.
"""
from decimal import Decimal
from typing import Optional
from web3 import Web3
from eth_account import Account
from config import (
    POLYGON_RPC_HTTP,
    USDT_CONTRACT_ADDRESS,
    HOT_WALLET_PRIVATE_KEY,
)

# ABI minimalista ERC-20 (solo le funzioni usate)
ERC20_ABI = [
    {
        "name": "transfer",
        "type": "function",
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
    },
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    },
    {
        "name": "Transfer",
        "type": "event",
        "inputs": [
            {"name": "from", "type": "address", "indexed": True},
            {"name": "to", "type": "address", "indexed": True},
            {"name": "value", "type": "uint256", "indexed": False},
        ],
    },
    {
        "name": "decimals",
        "type": "function",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
    },
]

USDT_DECIMALS = 6  # USDT su Polygon ha 6 decimali


def _get_contract():
    w3 = Web3(Web3.HTTPProvider(POLYGON_RPC_HTTP))
    return w3, w3.eth.contract(
        address=Web3.to_checksum_address(USDT_CONTRACT_ADDRESS),
        abi=ERC20_ABI,
    )


def usdt_to_raw(amount: Decimal) -> int:
    """Converte USDT decimale in unità raw (6 decimali)."""
    return int(amount * Decimal(10 ** USDT_DECIMALS))


def raw_to_usdt(raw: int) -> Decimal:
    """Converte unità raw in USDT decimale."""
    return Decimal(raw) / Decimal(10 ** USDT_DECIMALS)


def get_usdt_balance(address: str) -> Decimal:
    """Legge il saldo USDT on-chain di un address."""
    _, contract = _get_contract()
    raw = contract.functions.balanceOf(
        Web3.to_checksum_address(address)
    ).call()
    return raw_to_usdt(raw)


def send_usdt(
    to_address: str,
    amount_usdt: Decimal,
    private_key: Optional[str] = None,
) -> str:
    """
    Costruisce, firma e invia una transazione di trasferimento USDT.

    Args:
        to_address: destinatario
        amount_usdt: importo in USDT (Decimal)
        private_key: chiave privata del mittente (default: HOT_WALLET_PRIVATE_KEY)
    Returns:
        tx_hash come stringa hex
    """
    pk = private_key or HOT_WALLET_PRIVATE_KEY
    w3, contract = _get_contract()
    sender = Account.from_key(pk)

    raw_amount = usdt_to_raw(amount_usdt)
    nonce = w3.eth.get_transaction_count(sender.address)
    gas_price = w3.eth.gas_price

    tx = contract.functions.transfer(
        Web3.to_checksum_address(to_address),
        raw_amount,
    ).build_transaction({
        "from": sender.address,
        "nonce": nonce,
        "gasPrice": gas_price,
        "gas": 100_000,  # stima conservativa per transfer ERC-20 Polygon
    })

    signed = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    return tx_hash.hex()


def estimate_gas_usdt_transfer() -> Decimal:
    """
    Stima il costo in MATIC di un trasferimento USDT (per informare l'utente).
    Restituisce il valore già in MATIC (non USDT).
    """
    w3, _ = _get_contract()
    gas_price_wei = w3.eth.gas_price
    gas_units = 100_000
    cost_wei = gas_price_wei * gas_units
    cost_matic = Decimal(w3.from_wei(cost_wei, "ether"))
    return cost_matic
