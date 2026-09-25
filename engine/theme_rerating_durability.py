"""Named durability evidence for Finviz source-local subthemes.

This module joins two already-owned, separable observations:
- price participation / concentration from engine.theme_repricing_context;
- analyst estimate-revision breadth from engine.theme_revisions.

It deliberately does NOT collapse them into a score. The output is a matrix-style
descriptive state that tells a consumer whether price and revisions agree, disagree, or
remain unmeasured. It creates no theme identity, member roster, event truth, ranking,
entry gate, sizing, escalation, exit order or trade authority.

Catalysts, valuation, bottlenecks, options/crowding and macro regime remain independent
evidence legs owned elsewhere. Their absence here must not be read as a negative.
"""
from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

import pandas as pd

from engine import theme_revisions

SCHEMA = "theme_rerating_durability.v1"

AUTHORITY = {
    "context_only": True,
    "display_only": True,
    "not_a_signal": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "may_trade": False,
}

_PRICE_POSITIVE = {
    "broad_price_repricing",
    "early_diffusion",
    "mixed_positive",
}
_PRICE_FRAGILE = {
    "single_name_impulse",
    "narrow_leadership",
}
_PRICE_WEAK = {
    "leadership_break",
    "fading",
    "mixed_negative",
}


def _finite(value):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def revision_state(revision: Mapping | None) -> str:
    """Plain revision confirmation state from the incumbent revision owner."""
    if not revision or int(revision.get("n_covered") or 0) < theme_revisions.MIN_MEMBERS_COV:
        return "insufficient"
    breadth = _finite(revision.get("breadth"))
    broadening = str(revision.get("broadening_state") or "")
    proxy = str(revision.get("broadening_proxy_state") or "")

    if breadth is None:
        return "insufficient"
    if broadening == "RISING" and breadth > 0:
        return "broadening_confirmed"
    if broadening == "ROLLING" and breadth > 0:
        return "positive_but_rolling"
    if breadth > theme_revisions.FLAT_BAND:
        if broadening == "INSUFFICIENT_HISTORY" and proxy == "RISING":
            return "positive_level_proxy_broadening"
        return "positive_level"
    if breadth < -theme_revisions.FLAT_BAND:
        return "negative"
    return "flat"


def joint_state(price_shape: str | None, revisions: str) -> str:
    """Named two-axis relation; never a recommendation or scalar score."""
    shape = str(price_shape or "insufficient_data")
    if shape == "insufficient_data":
        return "price_insufficient"
    if revisions == "insufficient":
        if shape in _PRICE_FRAGILE:
            return "fragile_price_unconfirmed"
        if shape in _PRICE_POSITIVE:
            return "price_only_unconfirmed"
        if shape in _PRICE_WEAK:
            return "price_weak_revisions_unknown"
        return "mixed_unconfirmed"

    if shape in {"broad_price_repricing", "early_diffusion"}:
        if revisions == "broadening_confirmed":
            return "price_and_revisions_confirming"
        if revisions in {"positive_level", "positive_level_proxy_broadening"}:
            return "price_leads_positive_revisions"
        if revisions in {"negative", "positive_but_rolling"}:
            return "price_revision_divergence"

    if shape in _PRICE_FRAGILE:
        if revisions == "broadening_confirmed":
            return "revisions_ahead_of_price_diffusion"
        if revisions in {"negative", "positive_but_rolling"}:
            return "fragile_and_revision_weak"
        return "fragile_price_with_revision_support"

    if shape in _PRICE_WEAK:
        if revisions in {"negative", "positive_but_rolling"}:
            return "joint_weakening"
        if revisions == "broadening_confirmed":
            return "price_weak_revisions_resilient"
        if revisions in {"positive_level", "positive_level_proxy_broadening"}:
            return "price_weak_revisions_still_positive"

    return "mixed"


def _repricing_by_key(repricing: Mapping) -> dict[str, Mapping]:
    rows = repricing.get("subthemes") or []
    return {
        str(row.get("key")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("key")
    }


def build_durability(
    tree: Sequence[Mapping],
    repricing: Mapping,
    latest_revisions: pd.DataFrame,
    revision_history: pd.DataFrame | None,
) -> dict:
    """Join Finviz subthemes to incumbent revision breadth using the same member roster.

    The caller controls source dates for the supplied revision frames. This function is
    pure over those frames and does not read or write the revisions store.
    """
    by_key = _repricing_by_key(repricing)
    rows: list[dict] = []

    for theme_row in tree:
        theme = str(theme_row.get("theme") or theme_row.get("key") or "").strip()
        for sub in theme_row.get("subsectors", []) or []:
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            name = str(sub.get("name") or key).strip()
            members = [
                str(ticker).strip().upper()
                for ticker in sub.get("members", []) or []
                if str(ticker).strip()
            ]
            price = by_key.get(key) or {}
            try:
                rev = theme_revisions.theme_revisions_for(
                    key,
                    name,
                    members,
                    latest_revisions,
                    revision_history,
                )
            except Exception:
                rev = None
            rev_state = revision_state(rev)
            state = joint_state(price.get("shape"), rev_state)
            rows.append({
                "key": key,
                "theme": theme,
                "name": name,
                "n_members": len(members),
                "price": {
                    "shape": price.get("shape"),
                    "price_leader": price.get("price_leader"),
                    "durability_status": (
                        (price.get("durability_evidence") or {}).get("status")
                    ),
                },
                "revisions": {
                    "state": rev_state,
                    "breadth": (rev or {}).get("breadth"),
                    "breadth_cov": (rev or {}).get("breadth_cov"),
                    "breadth_accel": (rev or {}).get("breadth_accel"),
                    "broadening_state": (rev or {}).get("broadening_state"),
                    "broadening_proxy": bool((rev or {}).get("broadening_proxy")),
                    "broadening_proxy_state": (rev or {}).get("broadening_proxy_state"),
                    "est_drift_90d": (rev or {}).get("est_drift_90d"),
                    "n_covered": int((rev or {}).get("n_covered") or 0),
                    "coverage": (rev or {}).get("coverage"),
                },
                "joint_state": state,
                "decision_authority": {
                    "can_support_buy_decision": False,
                    "can_support_exit_decision": False,
                },
                "missing_named_legs": [
                    "catalyst_structure",
                    "valuation",
                    "crowding_fragility",
                    "macro_regime",
                ],
            })

    return {
        "schema": SCHEMA,
        "authority": dict(AUTHORITY),
        "method": {
            "composition": "named_price_and_revision_legs_no_fused_score",
            "revision_owner": "engine.theme_revisions.theme_revisions_for",
            "price_owner": "engine.theme_repricing_context",
            "revision_role": "confirmation_and_runway_not_entry",
        },
        "joint_state_counts": dict(sorted(Counter(
            row["joint_state"] for row in rows
        ).items())),
        "revision_state_counts": dict(sorted(Counter(
            row["revisions"]["state"] for row in rows
        ).items())),
        "subthemes": rows,
        "n_subthemes": len(rows),
    }
