"""Outcome-free W3AR method projection; this is NOT an eligibility evaluator.

Derived from DEC:SI-REPLAY-ELIGIBILITY-SEPARATE-FROM-LIVE-AVAILABILITY §3
and W2_EXPERT_REPLAY_REGISTRATION §3, landed in Macro 8f1ed858. Callers
supply existing registry family metadata. No store, producer, partition,
outcome, or filesystem is accessed, and no method is executed here.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from engine.stock_identity.authority import authority_block


_R_METHODS = {
    "grey_dot_macro": ("PIT_RECOMPUTE",),
    "confirmed_buy": ("LEDGER_COVERAGE", "PIT_RECOMPUTE"),
    "rebuy": ("LEDGER_COVERAGE",),
    "reclaim_waiver": ("STORE_VINTAGE",),
    "weekly_washout_turn": ("LEDGER_COVERAGE", "PIT_RECOMPUTE"),
    "sea_event_classes": ("STORE_VINTAGE",),
    "starter_signature": ("PIT_RECOMPUTE",),
    "rsi30_cross": ("PRICE_REFERENCE",),
    "low20d_bounce": ("PRICE_REFERENCE",),
    "stoch2w_cross": ("PRICE_REFERENCE",),
}
_B_FAMILIES = frozenset((
    "grey_dot_terminal", "bottom_watch_terminal", "tier_cascade_t1",
    "tier_cascade_t2", "tier_cascade_t3", "tier_cascade_t4",
))
_P_FAMILIES = frozenset((
    "starter_pending", "starter_failed", "starter_converted", "amber_early",
    "door_r_rearm", "turn_watch_deck", "gc_v2_scores", "radar_c1_c2",
))
_FAMILIES = frozenset(_R_METHODS) | _B_FAMILIES | _P_FAMILIES
_ARM_NOTES = {
    ("confirmed_buy", "LEDGER_COVERAGE"): "committed buy-filter verdict only",
    ("confirmed_buy", "PIT_RECOMPUTE"): (
        "separate pre-filter cb_3d_confluence, not extended ledger verdicts; "
        "retain spec_postdates_history on pre-ledger recompute"
    ),
    ("weekly_washout_turn", "LEDGER_COVERAGE"): "ledger pure filter, keep-FIRST",
    ("weekly_washout_turn", "PIT_RECOMPUTE"): (
        "registered pure function on frames truncated at each completed weekly bar"
    ),
    ("reclaim_waiver", "STORE_VINTAGE"): (
        "persisted nightly-state artifact actual vintage only; no synthetic history"
    ),
    ("starter_signature", "PIT_RECOMPUTE"): (
        "union_admission signature only; no STARTER licensing-state history"
    ),
    ("sea_event_classes", "STORE_VINTAGE"): (
        "actual store/backfill coverage, never event min/max"
    ),
}


def project_registered_methods(families: list[dict[str, Any]]) -> dict[str, Any]:
    """Enumerate methods from all 24 registry families, without inferring support.

    Family membership/class drift is an error requiring source-law reconciliation.
    Producer identity is carried verbatim for later qualification, NOT authenticated
    or admitted by this function. Dates, spec hashes, and event counts never become
    coverage or live availability. Outputs cannot authorize research or live use.
    """
    if not isinstance(families, list) or len(families) != len(_FAMILIES):
        raise ValueError("complete 24-family registry metadata required")
    seen: set[str] = set()
    rows = []
    for family in families:
        if not isinstance(family, dict):
            raise ValueError("family metadata must be an object")
        key = family.get("family_key")
        if not isinstance(key, str) or key not in _FAMILIES or key in seen:
            raise ValueError("unknown or duplicate family identity")
        seen.add(key)
        expected_class = "P" if key in _P_FAMILIES else "B" if key in _B_FAMILIES else "R"
        if family.get("provenance_class") != expected_class:
            raise ValueError(f"registered provenance class changed: {key}")
        producer, eras, spec_hash = (family.get(k) for k in ("producer", "era_pins", "spec_hash"))
        if not isinstance(producer, str) or not producer.strip():
            raise ValueError(f"missing producer identity: {key}")
        if (not isinstance(eras, list) or not eras
                or any(not isinstance(e, str) or not e.strip() for e in eras)
                or len(set(eras)) != len(eras)):
            raise ValueError(f"missing or ambiguous era pins: {key}")
        # Prospective-only entries intentionally have no historical spec hash.
        # Carry that absence; do not manufacture a spec to complete the row.
        valid_hash = (isinstance(spec_hash, str) and len(spec_hash) == 64
                      and all(c in "0123456789abcdef" for c in spec_hash))
        if not valid_hash and not (expected_class == "P" and spec_hash is None):
            raise ValueError(f"invalid spec identity: {key}")
        methods = (("PROSPECTIVE_ONLY",) if expected_class == "P" else
                   ("LOCKED_SPEC_BACKCAST",) if expected_class == "B" else _R_METHODS[key])
        rows.append({
            "family_key": key,
            "provenance_class": expected_class,
            "registry_identity": {"producer": producer, "era_pins": deepcopy(eras), "spec_hash": spec_hash},
            "identity_qualified": False,
            "historical_coverage_status": False if expected_class == "P" else None,
            "historical_eligibility": False if expected_class == "P" else None,
            "live_availability_status": None,
            "methods": [{
                "basis": basis,
                "coverage_status": False if expected_class == "P" else None,
                "required_evidence_status": "PROSPECTIVE_ONLY" if expected_class == "P" else "UNMEASURED",
                "constraint": _ARM_NOTES.get((key, basis)),
                "spec_postdates_history_requirement": (
                    "ALWAYS" if expected_class == "B" else
                    "PRE_LEDGER_RECOMPUTE" if (key, basis) == ("confirmed_buy", "PIT_RECOMPUTE") else
                    "NOT_APPLICABLE"
                ),
                "preserve_registered_era_and_deviations": expected_class == "B",
            } for basis in methods],
        })
    return {
        "schema": "stock_identity.w3ar_method_projection.v1",
        "programme": "SI-FABLE-COO-PROGRAM-20260828",
        "successor": "SI-W3AR-CENSUS-P2-PREREG-V1",
        "scope": "registered methods only; identity and inputs require qualification",
        "rows": sorted(rows, key=lambda row: row["family_key"]),
        "clean_pool_count": None,
        "clean_pool_hash": None,
        "scientific_acceptance": False,
        "P2_executed": False,
        "authority": authority_block(),
    }
