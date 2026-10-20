"""Payload fields the China narrative radar reads from THS membership metadata (no I/O)."""
from __future__ import annotations

_IDENTITY_KEYS = ("thesis", "thesis_zh", "ths_concept")


def _text(val):
    return val if isinstance(val, str) and val.strip() else None


def membership_as_of(raw) -> str | None:
    """The membership artifact's own "version" date, verbatim; None when absent."""
    return _text(raw.get("version")) if isinstance(raw, dict) else None


def basket_identity(bval) -> dict:
    """thesis / thesis_zh / ths_concept for one basket; None for a missing or blank value."""
    src = bval if isinstance(bval, dict) else {}
    return {key: _text(src.get(key)) for key in _IDENTITY_KEYS}
