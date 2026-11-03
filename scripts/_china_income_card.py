"""Grid-tile fields for the China Income-Vector strategy card (no I/O, no pandas)."""
from __future__ import annotations

from datetime import datetime


def sample_tile(bt: dict | None) -> dict:
    """Drawdown-count tile fields from a china_allocation backtest; empty fields without one."""
    if bt is None:
        return {"bear_n": None, "win_start": None}
    return {"income": None, "bear_n": len(bt.get("bear_episodes") or []),
            "win_start": bt.get("start")}


def as_of_label(iso) -> str | None:
    """'YYYY-MM-DD' -> 'Oct 16, 2026' (the label shape the other grid cards carry); else None."""
    if not isinstance(iso, str):
        return None
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%b %d, %Y")
    except ValueError:
        return None
