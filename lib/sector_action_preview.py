"""Canonical Sector action-board preview partition.

This is the existing builder's tier split, shared with the native projection.
It has no loader, configuration, clock, or authorization side effects.
"""
from __future__ import annotations

_SC_PAYLOAD_URL = "premiumdata/sector_central.json"

_ACTNOW_LANES = [
    ("buy_now", "ab-buy-fold", False),
    ("buy_soon", "ab-soon-fold", False),
    ("on_the_run", "ab-run-fold", False),
    ("take_profits", "ab-trim-fold", False),
    ("hold", "dash-hold-fold", True),
    ("avoid", "dash-hold-fold", True),
]


def partition_actnow(action_board: dict, preview: int):
    """Yield the canonical per-lane preview and remainder; hold/avoid share a budget."""
    preview = max(0, int(preview))
    hold_shown = 0
    for key, dest, wrap in _ACTNOW_LANES:
        rows = list(action_board.get(key) or [])
        budget = max(0, preview - hold_shown) if key == "avoid" else preview
        shown = rows[:budget]
        if key == "hold":
            hold_shown = len(shown)
        yield key, dest, wrap, shown, rows[len(shown):]


def split_actnow(action_board: dict | None, preview: int, *, gated: bool = True):
    """Tier-preview split for the Act-Now board. Returns (pgate, locked).

    Pure in `action_board` — the caller hands the SAME dict to the page render,
    which re-derives its own preview slices in-template from `pgate` so the lane
    headings and empty-state branches keep reading the FULL lists (the counts and
    the state are what stays free; only the names are paid).

    `locked` is the [{lane, rows, wrap}] list the include consumes in its
    rows-only shape, keyed by the `.actbody` id each row was sliced out of.

    Returns (None, []) when nothing is withheld anywhere — a board at or under
    the preview cap ships whole, because a wall over nothing is worse than no
    wall, and an ungated page must stay byte-identical to the pre-gate one.
    """
    if not gated or not isinstance(action_board, dict):
        return None, []
    preview = max(0, int(preview))
    locked: list[dict] = []
    total = 0
    for key, dest, wrap, shown, withheld in partition_actnow(action_board, preview):
        total += len(shown) + len(withheld)
        if withheld:
            locked.append({"lane": dest, "rows": withheld, "wrap": wrap})
    if not locked:
        return None, []
    n_locked = sum(len(L["rows"]) for L in locked)
    pgate = {
        "tier": "essential",
        "payload": _SC_PAYLOAD_URL,
        "preview": preview,
        "actnow": {"preview": preview, "locked": n_locked, "total": total},
    }
    return pgate, locked

