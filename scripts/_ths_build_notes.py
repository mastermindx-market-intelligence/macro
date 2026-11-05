"""Build notes the 同花顺 basket browser prints from its own payload (no I/O)."""
from __future__ import annotations

_KEYS = ("construction", "history_note")


def build_notes(payload: dict | None) -> list[str]:
    """Return the non-blank construction / history_note strings, in that order."""
    if not isinstance(payload, dict):
        return []
    out = []
    for key in _KEYS:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
    return out
