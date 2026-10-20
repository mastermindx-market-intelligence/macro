"""Grid-tile fields for the China Income-Vector strategy card (no I/O, no pandas)."""
from __future__ import annotations


def sample_tile(bt: dict | None) -> dict:
    """Drawdown-count tile fields from a china_allocation backtest; empty fields without one."""
    if bt is None:
        return {"bear_n": None, "win_start": None}
    return {"income": None, "bear_n": len(bt.get("bear_episodes") or []),
            "win_start": bt.get("start")}
