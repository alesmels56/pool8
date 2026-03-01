"""
blockchain/wallet.py — Generazione wallet HD (BIP44) e firma transazioni Polygon.
Ogni utente riceve un address deterministico derivato dal mnemonic master.
"""
from eth_account import Account
from eth_account.hdaccount import generate_mnemonic
from web3 import Web3
from config import POLYGON_RPC_HTTP, HOT_WALLET_MNEMONIC

Account.enable_unaudited_hdwallet_features()


def _get_web3() -> Web3:
    return Web3(Web3.HTTPProvider(POLYGON_RPC_HTTP))


def generate_wallet_for_user(user_index: int) -> str:
    """
    Deriva un address Polygon univoco per l'utente tramite HD Wallet BIP44.
    Percorso: m/44'/60'/0'/0/{user_index}

    Args:
        user_index: indice progressivo dell'utente (es. user_id % 2^31)
    Returns:
        Indirizzo Ethereum/Polygon in formato checksum (0x...)
    """
    account = Account.from_mnemonic(
        HOT_WALLET_MNEMONIC,
        account_path=f"m/44'/60'/0'/0/{user_index}",
    )
    return account.address


def get_private_key_for_user(user_index: int) -> str:
    """Deriva la chiave privata per l'indice utente (usata internamente per sweep)."""
    account = Account.from_mnemonic(
        HOT_WALLET_MNEMONIC,
        account_path=f"m/44'/60'/0'/0/{user_index}",
    )
    return account.key.hex()


def get_hot_wallet_address() -> str:
    """Restituisce l'address del hot wallet principale (indice 0)."""
    return generate_wallet_for_user(0)


def get_hot_wallet_matic_balance() -> float:
    """Legge il saldo MATIC (gas) del hot wallet."""
    w3 = _get_web3()
    address = get_hot_wallet_address()
    balance_wei = w3.eth.get_balance(address)
    return float(w3.from_wei(balance_wei, "ether"))
