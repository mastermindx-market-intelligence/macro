"""Named durability evidence for Finviz source-local subthemes.

This module joins already-owned, separable observations:
- price participation / concentration from engine.theme_repricing_context;
- analyst estimate-revision breadth from engine.theme_revisions;
- earnings/guidance context from engine.group_earnings;
- optional crowding/extension + valuation distributions assembled from their owners.

It deliberately does NOT collapse them into a score. The price+revision joint_state stays
a named two-axis read; events and fragility are parallel evidence legs. It creates no theme
identity, member roster, event truth, ranking, entry gate, sizing, escalation, exit order
or trade authority.

Catalyst structure, bottlenecks, options positioning and macro regime remain independent
evidence legs owned elsewhere. Missing evidence must not be read as negative evidence.
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


def event_confirmation_state(event: Mapping | None) -> str:
    """Directional earnings/guidance read using only Group Earnings owner outputs."""
    if not event:
        return "unavailable"
    results = event.get("results") or {}
    guidance = event.get("guidance") or {}
    beat = results.get("n_beat")
    miss = results.get("n_miss")
    band = guidance.get("band")

    if beat is None or miss is None:
        result_state = "insufficient"
    elif int(beat) > int(miss):
        result_state = "beat_skew"
    elif int(miss) > int(beat):
        result_state = "miss_skew"
    else:
        result_state = "balanced"

    guidance_state = (
        "raising"
        if band in {"RAISING", "BROAD-RAISE"}
        else "cutting"
        if band == "CUTTING"
        else "neutral"
        if band == "NEUTRAL"
        else "insufficient"
    )

    if result_state == "beat_skew" and guidance_state == "raising":
        return "earnings_and_guidance_positive"
    if result_state == "miss_skew" and guidance_state == "cutting":
        return "earnings_and_guidance_negative"
    if guidance_state == "raising":
        return "guidance_positive"
    if guidance_state == "cutting":
        return "guidance_negative"
    if result_state == "beat_skew":
        return "earnings_positive"
    if result_state == "miss_skew":
        return "earnings_negative"
    if result_state == "insufficient" and guidance_state == "insufficient":
        return "insufficient"
    return "mixed"


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
    event_context_by_key: Mapping[str, Mapping] | None = None,
    fragility_context_by_key: Mapping[str, Mapping] | None = None,
) -> dict:
    """Join Finviz subthemes to incumbent revision breadth using the same member roster.

    The caller controls source dates for the supplied revision frames. This function is
    pure over those frames and does not read or write the revisions store.
    """
    by_key = _repricing_by_key(repricing)
    event_context_by_key = event_context_by_key or {}
    fragility_context_by_key = fragility_context_by_key or {}
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
            event = event_context_by_key.get(key) or {}
            event_state = event_confirmation_state(event)
            fragility = fragility_context_by_key.get(key) or {}
            rows.append({
                "key": key,
                "theme": theme,
                "name": name,
                "n_members": len(members),
                "price": {
                    "shape": price.get("shape"),
                    "price_leader": price.get("price_leader"),
                    "group_residual_leader_candidate": (
                        price.get("group_residual_leader_candidate")
                    ),
                    "leadership": price.get("leadership"),
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
                "events": {
                    "state": event_state,
                    "season": event.get("season"),
                    "results": event.get("results"),
                    "guidance": event.get("guidance"),
                    "limits": event.get("limits"),
                },
                "fragility": fragility or None,
                "joint_state": state,
                "joint_scope": "price_plus_revisions_only",
                "decision_authority": {
                    "can_support_buy_decision": False,
                    "can_support_exit_decision": False,
                },
                "missing_named_legs": (
                    ["catalyst_structure", "macro_regime"]
                    + ([] if fragility else ["valuation", "crowding_fragility"])
                ),
            })

    return {
        "schema": SCHEMA,
        "authority": dict(AUTHORITY),
        "method": {
            "composition":
                "named_price_revision_event_fragility_legs_no_fused_score",
            "revision_owner": "engine.theme_revisions.theme_revisions_for",
            "price_owner": "engine.theme_repricing_context",
            "event_owner": "engine.group_earnings.member_event_context",
            "crowding_owner": "engine.theme_crowding.basket_crowding",
            "valuation_owner": "engine.valuation.read",
            "revision_role": "confirmation_and_runway_not_entry",
            "event_role": "earnings_and_guidance_confirmation_not_entry",
            "fragility_role":
                "late_cycle_context_and_deescalation_watch_not_exit_order",
        },
        "joint_state_counts": dict(sorted(Counter(
            row["joint_state"] for row in rows
        ).items())),
        "revision_state_counts": dict(sorted(Counter(
            row["revisions"]["state"] for row in rows
        ).items())),
        "event_state_counts": dict(sorted(Counter(
            row["events"]["state"] for row in rows
        ).items())),
        "crowding_state_counts": dict(sorted(Counter(
            (((row.get("fragility") or {}).get("crowding") or {}).get("state")
             or "unavailable")
            for row in rows
        ).items())),
        "extension_state_counts": dict(sorted(Counter(
            (((row.get("fragility") or {}).get("extension") or {}).get("state")
             or "unavailable")
            for row in rows
        ).items())),
        "subthemes": rows,
        "n_subthemes": len(rows),
    }
