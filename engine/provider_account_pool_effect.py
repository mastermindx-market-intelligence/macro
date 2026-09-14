"""Effect-safe rollover gate for a provider account pool."""

from engine.provider_account_pool_checks import normalize_id


def rollover_allowed(failure_class: str, effect_state: str) -> bool:
    """Return true only for a proven pre-effect member refusal."""
    failure = normalize_id(failure_class, "failure_class")
    effect = normalize_id(effect_state, "effect_state")
    return effect == "no_effect" and failure in {"usage_limit", "account_rejected"}
