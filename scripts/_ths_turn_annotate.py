"""Copy basket_turn_cn.json turn rows onto 同花顺 (THS) basket rows (W28G SPEC 4).

Shared by both annotation points in scripts/build_baskets_china_ths.py: the in-memory pass
that runs before the page renders, and the end-of-run pass over baskets_ths.json. Pure
apart from load_turn_states' single file read; never raises on a missing or malformed
artifact.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_turn_states(path) -> dict:
    """Per-basket turn rows of a basket_turn_cn.json artifact; {} when absent or unreadable."""
    try:
        art = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    states = art.get("baskets") if isinstance(art, dict) else None
    return states if isinstance(states, dict) else {}


def annotate_turn_states(baskets, turn_states) -> int:
    """Write each matching basket's turn fields in place; return how many rows were annotated.

    A row whose id is not in `turn_states` is left untouched. Running it twice with the same
    states writes the same values (idempotent).
    """
    if not isinstance(turn_states, dict):
        return 0
    n = 0
    for b in baskets or []:
        if not isinstance(b, dict):
            continue
        bid = b.get("id")
        st = turn_states.get(bid) if isinstance(bid, str) and bid else None
        if not isinstance(st, dict):
            continue
        b["turn_state"] = st.get("state", "NONE")
        b["turn_dd_252"] = st.get("dd_252")
        b["turn_evidence"] = st.get("evidence", [])
        b["turn_days_in_state"] = st.get("days_in_state")
        n += 1
    return n
