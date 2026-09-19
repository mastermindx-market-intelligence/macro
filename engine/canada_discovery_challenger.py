"""Canada zero-authority discovery challenger.

This broadens research recall from the existing scored Canada candidate pool
without changing the canonical Branch-B board, rank, entry owner, or publication.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

DEFINITION = "ca_discovery_v1"

ENTRY_OPEN = "ENTRY_OPEN"
WAIT_PULLBACK = "WAIT_PULLBACK"
WAIT_CONFLUENCE = "WAIT_CONFLUENCE"
RAN_DONT_CHASE = "RAN_DONT_CHASE"
BLOCKED = "BLOCKED"
UNAVAILABLE_DATA = "UNAVAILABLE_DATA"

_OPEN = frozenset({"buy_now", "partial"})
_PULLBACK = frozenset({"wait_pullback", "hold"})
_RAN = frozenset({"extended", "topping"})
_BLOCKED = frozenset({"blocked", "avoid", "exit"})
_WAIT = frozenset({"buy_soon", "await_confluence", "watch", "bounce_wait"})

def freeze_evidence(
    candidates: Iterable[Any],
    align_map: Mapping[str, Mapping[str, Any]] | None,
    entry_signals: Mapping[str, Mapping[str, Any]] | None,
) -> tuple[tuple[str, bool, bool, str | None], ...]:
    """Snapshot only the evidence needed for discovery, never rank/score fields."""
    align = align_map or {}
    entries = entry_signals or {}
    frozen: list[tuple[str, bool, bool, str | None]] = []
    seen: set[str] = set()
    for item in candidates or ():
        row = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else item
        if not isinstance(row, Mapping):
            continue
        ticker = row.get("ticker")
        if not ticker:
            continue
        ticker = str(ticker)
        if ticker in seen:
            continue
        seen.add(ticker)
        a = align.get(ticker) or {}
        es = entries.get(ticker) or {}
        status = es.get("status")
        frozen.append((
            ticker,
            bool(a.get("aligned")),
            bool(a.get("near")),
            str(status) if status not in (None, "") else None,
        ))
    return tuple(frozen)

def _availability(
    status: str | None, *, aligned: bool, near: bool,
) -> tuple[str, str]:
    source = f"entry_signal:{status or 'missing'}"
    if status in _OPEN:
        if not aligned and not near:
            return WAIT_CONFLUENCE, f"alignment_blocked+{source}"
        return ENTRY_OPEN, source
    if status in _PULLBACK:
        return WAIT_PULLBACK, source
    if status in _RAN:
        return RAN_DONT_CHASE, source
    if status in _BLOCKED:
        return BLOCKED, source
    if status in _WAIT:
        return WAIT_CONFLUENCE, source
    return UNAVAILABLE_DATA, source


def build_candidates(
    frozen: Iterable[tuple[str, bool, bool, str | None]],
    asof: str,
) -> list[dict[str, Any]]:
    """Emit every frozen screen candidate with deterministic reasons and availability."""
    rows: list[dict[str, Any]] = []
    for ticker, aligned, near, entry_status in frozen:
        origins = ["scored_screen"]
        if aligned:
            origins.append("alignment_aligned")
        elif near:
            origins.append("alignment_near")
        availability, source = _availability(
            entry_status, aligned=aligned, near=near,
        )
        rows.append({
            "session_date": str(asof),
            "security_ref_raw": str(ticker),
            "candidate_origin": "+".join(origins),
            "availability_status": availability,
            "availability_source": source,
        })
    return rows
