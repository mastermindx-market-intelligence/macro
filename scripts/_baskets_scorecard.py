"""Subset of the ignition scoreboard that the HK / Canada basket pages print (no I/O)."""
from __future__ import annotations

_KEYS = ("market", "n_graded", "n_alerts", "alert_precision_4w", "by_state", "asof_range")


def scorecard_subset(ignition: dict | None) -> dict:
    """Return the printable scoreboard keys, or {} when nothing has been graded yet."""
    sc = ignition.get("scoreboard") if isinstance(ignition, dict) else None
    if not isinstance(sc, dict) or not sc.get("n_graded"):
        return {}
    return {k: sc[k] for k in _KEYS if k in sc}
