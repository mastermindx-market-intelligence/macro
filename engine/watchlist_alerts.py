"""engine/watchlist_alerts.py — Thin loader for alert_triage.

Reads the committed data/alerts/watchlist_alerts.jsonl produced by
scripts/run_watchlist_sentinel.py and exposes a load_events() function
matching the contract expected by engine/alert_triage._jsonl_raw().

This module contains no sentinel logic — that lives in
engine/watchlist_sentinel.py — but it is not silent about corruption:
a non-blank line that fails to parse, or parses to a non-object value,
raises ValueError so alert_triage can surface READ_UNAVAILABLE instead
of mistaking a truncated feed for a healthy empty one. The error is a
single fixed sanitized message; it never quotes the offending row, its
line number, or the file path.
"""
from __future__ import annotations

import json
from pathlib import Path

from lib import config

# One sanitized message for every corrupt-row case (malformed JSON or
# non-object row): fixed text only — no row contents, no path.
_CORRUPT = "watchlist alert store is unreadable: corrupt or non-object record"


def _path() -> Path:
    return config.data_dir() / "alerts" / "watchlist_alerts.jsonl"


def load_events() -> list[dict]:
    """Return all watchlist buy-zone-enter events from the committed JSONL.

    Returns [] when the file is absent (sentinel never ran), empty, or
    holds only blank lines. Present object rows are returned unchanged
    and in file order.

    Raises ValueError when the file exists but any non-blank line is
    malformed JSON or parses to a non-object value, so a corrupt store
    is never reported as a silently truncated feed. The exception
    message is the fixed sanitized module constant _CORRUPT — no row
    contents and no path are included.
    """
    p = _path()
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            raise ValueError(_CORRUPT) from None
        if not isinstance(event, dict):
            raise ValueError(_CORRUPT)
        out.append(event)
    return out
