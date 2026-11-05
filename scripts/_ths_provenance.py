"""Membership provenance for the 同花顺 basket browser (stdlib only; no network)."""
from __future__ import annotations

import json
from pathlib import Path


def _count(val):
    return val if isinstance(val, int) and not isinstance(val, bool) else None


def _receipt(path: Path) -> dict | None:
    try:
        row = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(row, dict) or not isinstance(row.get("date"), str):
        return None
    return {"date": row["date"], "complete": row.get("complete") is True,
            "concepts_attempted": _count(row.get("concepts_attempted")),
            "concepts_fetched": _count(row.get("concepts_fetched"))}


def membership_provenance(membership, receipts_dir) -> dict | None:
    """Which membership file the page computes from, and how the weekly re-scrapes went.

    Returns {"observed", "newest_scrape", "last_complete_scrape"}, or None when the
    membership has no usable version string. A missing or unreadable receipts directory
    keeps the membership date and leaves both scrape fields None.
    """
    if not isinstance(membership, dict):
        return None
    observed = membership.get("version")
    if not isinstance(observed, str) or not observed.strip():
        return None
    out = {"observed": observed.strip(), "newest_scrape": None, "last_complete_scrape": None}
    try:
        files = sorted(Path(receipts_dir).glob("scrape_*.json"))
    except (OSError, TypeError):
        return out
    rows = sorted((r for r in map(_receipt, files) if r is not None), key=lambda r: r["date"])
    if rows:
        out["newest_scrape"] = rows[-1]
        done = [r["date"] for r in rows if r["complete"]]
        out["last_complete_scrape"] = done[-1] if done else None
    return out
