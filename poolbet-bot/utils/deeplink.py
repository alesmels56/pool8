"""
utils/deeplink.py — Generazione e parsing dei deep-link per le scommesse.
"""
from typing import Optional, Tuple


def make_bet_link(bot_username: str, bet_uuid: str) -> str:
    """Genera il link virale per una scommessa."""
    return f"https://t.me/{bot_username}?start=bet_{bet_uuid}"


def make_ref_link(bot_username: str, user_id: int) -> str:
    """Genera il link referral unico per l'utente."""
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


def parse_start_param(param: str) -> Optional[Tuple[str, str]]:
    """
    Parsa il parametro del comando /start.
    Ritorna ("bet", uuid) se riconosce 'bet_' seguito da un UUID.
    """
    if not param:
        return None
    
    # Caso Bet
    if "bet_" in param:
        parts = param.split("bet_")
        if len(parts) >= 2:
            potential_uuid = parts[1][:36]
            if len(potential_uuid) == 36 and potential_uuid.count("-") == 4:
                return ("bet", potential_uuid)
    
    # Caso Referral
    if "ref_" in param:
        parts = param.split("ref_")
        if len(parts) >= 2:
            try:
                ref_id = int(parts[1])
                return ("ref", str(ref_id))
            except ValueError:
                pass
                
    return None
