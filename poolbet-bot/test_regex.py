from utils.i18n import TRANSLATIONS
def _build_regex(key: str) -> str:
    try:
        vals = [d[key] for d in TRANSLATIONS.values() if key in d]
        escaped = [v.replace("+", r"\+") for v in vals]
        return "^(" + "|".join(escaped) + ")$"
    except Exception as e:
        return f"ERROR: {e}"

print(f"Result for menu_balance: {_build_regex('menu_balance')}")
print(f"Result for non_existent: {_build_regex('non_existent')}")
