from engine.provider_account_pool import AccountPoolError


def normalize_id(value: object, field: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        raise AccountPoolError(f"{field} is required")
    return text


def valid_percent(value: int | None) -> bool:
    return value is None or (not isinstance(value, bool) and isinstance(value, int) and 0 <= value <= 100)
