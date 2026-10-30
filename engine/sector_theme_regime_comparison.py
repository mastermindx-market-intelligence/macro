"""Read-only cross-sector/theme evidence matrix; no ranking, score, or feed.

Takes P2 research-preview outputs from incumbent-qualified SHAPES. Refuses to
compare returns whose benchmark, session basis, price adjustment basis, period
start/end or decision cutoff differ. Mixed membership/rights source modes are
disclosed explicitly, not normalized into a claim of PIT comparability.

No market data, I/O, consumer publication, alerts, futures, trades or model fit.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
import math

SCHEMA = "sector_theme_regime_comparison/v1"
INPUT = "sector_theme_owner_preview/v1"
FP = "sector_theme_regime_fingerprint/v1"
COMP_FIELDS = (
    "market", "benchmark_id", "price_basis", "session_basis",
    "period_start", "period_end", "horizon", "decision_at",
)
GROUP_KINDS = frozenset(("sector", "industry", "theme"))


def _hold(reason: str) -> dict:
    return {
        "schema": SCHEMA, "status": "HELD", "reason": reason,
        "comparison_basis": None, "groups": [], "security_overlap": [],
        "issuer_overlap": [],
        "comparison_authority": False, "ranking_authority": False,
        "customer_publication": False, "forecast_or_trading_authority": False,
    }


def _numeric(raw: object) -> dict:
    if not isinstance(raw, Mapping):
        return {"status": "unmeasured", "reason": "missing_input"}
    if raw.get("status") != "measured":
        return {"status": "unmeasured", "reason": str(
            raw.get("reason") or "not_measured")}
    v = raw.get("value")
    if type(v) not in (int, float) or raw.get("unit") != "fraction":
        return {"status": "unmeasured", "reason": "invalid_unit_or_value"}
    try:
        n = float(v)
    except (TypeError, ValueError, OverflowError):
        return {"status": "unmeasured", "reason": "invalid_unit_or_value"}
    return ({"status": "measured", "value": n, "unit": "fraction"}
            if math.isfinite(n) else
            {"status": "unmeasured", "reason": "non_finite_input"})


def _breadth(raw: object) -> dict:
    if not isinstance(raw, Mapping) or (
        raw.get("bounds_kind") != "identification_bounds_not_confidence_interval"
    ):
        return {"status": "unmeasured", "reason": "missing_breadth_bounds"}
    vals = raw.get("identification_bounds")
    c = raw.get("coverage")
    if not isinstance(vals, (list, tuple)) or len(vals) != 2:
        return {"status": "unmeasured", "reason": "bad_breadth_bounds"}
    if (any(type(x) not in (float, int) for x in vals)
            or type(c) not in (float, int)):
        return {"status": "unmeasured", "reason": "bad_breadth_bounds"}
    try:
        lo, hi, coverage = float(vals[0]), float(vals[1]), float(c)
    except (ValueError, OverflowError):
        return {"status": "unmeasured", "reason": "bad_breadth_bounds"}
    if (not all(math.isfinite(x) for x in (lo, hi, coverage))
            or not 0 <= lo <= hi <= 1 or not 0 <= coverage <= 1):
        return {"status": "unmeasured", "reason": "bad_breadth_bounds"}
    value = raw.get("value")
    if raw.get("status") == "measured":
        if type(value) not in (float, int):
            return {"status": "unmeasured", "reason": "invalid_breadth_fraction"}
        try:
            n = float(value)
        except (TypeError, ValueError, OverflowError):
            return {"status": "unmeasured", "reason": "invalid_breadth_fraction"}
        if (not math.isfinite(n) or not 0 <= n <= 1
                or abs(coverage * n - lo) > 1e-9
                or abs(lo + (1 - coverage) - hi) > 1e-9):
            return {"status": "unmeasured", "reason": "inconsistent_breadth_algebra"}
    elif raw.get("status") == "unmeasured":
        n = None
        if (abs(coverage) > 1e-9 or abs(lo) > 1e-9
                or abs(hi - 1) > 1e-9):
            return {"status": "unmeasured", "reason": "inconsistent_zero_coverage_bounds"}
    else:
        return {"status": "unmeasured", "reason": "unknown_breadth_status"}
    return {
        "status": raw["status"], "value": n, "unit": "fraction",
        "coverage": coverage, "identification_bounds": [lo, hi],
        "bounds_kind": "identification_bounds_not_confidence_interval",
    }


def _name(value: object) -> str | None:
    return (value if type(value) is str and value
            and value == value.strip() else None)


def compose_regime_comparison(previews: Mapping[str, Mapping]) -> dict:
    """One source-aligned comparative scanner for research, NOT a ranked list.

    Caller provides distinct group IDs -> owner-bridge result. Any malformed
    group or clock holds the WHOLE comparison rather than silently dropping a
    weak sector and making the remaining groups appear stronger.
    """
    if not isinstance(previews, Mapping) or not previews:
        return _hold("no_preview_inputs")
    if any(_name(gid) is None for gid in previews):
        return _hold("invalid_group_key")
    baseline: dict | None = None
    result_rows = []
    member_to_groups: dict[str, set[str]] = defaultdict(set)
    issuer_to_groups: dict[str, set[str]] = defaultdict(set)
    for gid, p in sorted(previews.items()):
        if _name(gid) is None or not isinstance(p, Mapping) or (
            p.get("schema") != INPUT or p.get("status") != "RESEARCH_PREVIEW_ONLY"
        ):
            return _hold("held_or_noncanonical_input")
        if (p.get("eligible_for_customer_publication") is not False
                or p.get("eligible_for_historical_prediction") is not False
                or p.get("trading_or_alert_authority") is not False):
            return _hold("input_authority_not_source_qualified")
        if p.get("group_kind") not in GROUP_KINDS:
            return _hold("unqualified_group_kind")
        if p.get("basis") not in ("CURRENT_ROSTER", "PIT_AS_KNOWN"):
            return _hold("unrecognized_membership_basis")
        basis = p.get("comparison_basis")
        frame = p.get("frame")
        fp = p.get("fingerprint")
        if (not isinstance(basis, Mapping) or not isinstance(frame, Mapping)
                or not isinstance(fp, Mapping) or fp.get("schema") != FP):
            return _hold("missing_comparison_basis_or_fingerprint")
        if (not all(_name(basis.get(k)) for k in COMP_FIELDS)
                or frame.get("schema") != "sector_theme_factor_frame/v1"
                or not isinstance(frame.get("group"), Mapping)
                or not isinstance(fp.get("group"), Mapping)):
            return _hold("malformed_source_comparison_basis")
        cur = {k: basis[k] for k in COMP_FIELDS}
        if baseline is None:
            baseline = cur
        elif cur != baseline:
            return _hold("cross_group_time_benchmark_or_price_basis_mismatch")
        if (frame["group"].get("group_id") != gid
                or fp["group"].get("group_id") != gid
                or frame["group"].get("membership_mode") != p["basis"]
                or fp["group"].get("membership_mode") != p["basis"]):
            return _hold("group_id_or_membership_basis_mismatch")
        if (not isinstance(frame.get("clock"), Mapping)
                or frame["clock"].get("horizon") != basis["horizon"]
                or frame["clock"].get("period_end") != basis["period_end"]
                or frame["clock"].get("decision_at") != basis["decision_at"]):
            return _hold("source_frame_clock_mismatch")
        if (not isinstance(fp.get("horizons"), Mapping)
                or set(fp["horizons"]) != {basis["horizon"]}
                or not isinstance(fp["horizons"][basis["horizon"]], Mapping)):
            return _hold("fingerprint_horizon_mismatch")
        at = fp["horizons"][basis["horizon"]]
        if at.get("period_end") != basis["period_end"]:
            return _hold("fingerprint_period_end_mismatch")
        auth = fp.get("authority")
        if not isinstance(auth, Mapping) or any(
            auth.get(k) is not False for k in (
                "eligible_for_customer_publication", "predictive_promoted",
                "ranking_authority", "alert_authority", "entry_or_sizing_authority"
            )
        ):
            return _hold("fingerprint_claims_decision_authority")
        members = fp["group"].get("member_ids")
        if (not isinstance(members, list)
                or len(members) != len(set(members))
                or any(_name(x) is None for x in members)
                or len(members) != frame.get("universe", {}).get("expected_n")
                or set(members) != set(frame.get("universe", {}).get("member_ids", []))):
            return _hold("invalid_or_mismatched_group_population")
        issuer_map = p.get("issuer_by_security_id")
        if (not isinstance(issuer_map, Mapping)
                or set(issuer_map) != set(members)
                or any(_name(v) is None for v in issuer_map.values())):
            return _hold("missing_or_invalid_security_issuer_mapping")
        if (type(p.get("unique_issuer_n")) is not int
                or p["unique_issuer_n"] != len(set(issuer_map.values()))):
            return _hold("invalid_unique_issuer_population")
        for member in members:
            member_to_groups[member].add(gid)
            issuer_to_groups[issuer_map[member]].add(gid)
        measures = at.get("participation")
        if not isinstance(measures, Mapping) or not isinstance(at.get("absolute_trend"), Mapping):
            return _hold("missing_group_factor_measures")
        parent_rs = _numeric(at.get("rs_parent"))
        market_rs = _numeric(at.get("rs_market"))
        ret = _numeric(at["absolute_trend"].get("group_return"))
        breadth = _breadth(measures.get("positive_return_breadth"))
        above50 = _breadth(measures.get("above_ma50_breadth"))
        kind = p["group_kind"]
        n = len(members)
        descriptions = p.get("explanation")
        if not isinstance(descriptions, Mapping) or descriptions.get("status") != "RESEARCH_PREVIEW_ONLY":
            return _hold("missing_numerically_grounded_explanation")
        if (descriptions.get("eligible_for_customer_publication") is not False
                or descriptions.get("predictive_or_trading_authority") is not False):
            return _hold("explanation_claims_publication_authority")
        cards = descriptions.get("group_cards")
        if not isinstance(cards, list):
            return _hold("bad_explanation_cards")
        # No arbitrary text from a model or raw feed. The text cards remain
        # explicitly unqualified and source-scoped until the owner certifies them.
        if any(not isinstance(c, Mapping) or (
            c.get("source_status") != "unqualified_descriptive_preview"
            or c.get("forecast_probability") is not None
            or c.get("trade_recommendation") is not None
        ) for c in cards):
            return _hold("unsupported_narrative_claim")
        result_rows.append({
            "group_id": gid, "kind": kind,
            "parent_id": basis.get("parent_id"),
            "cohort_id": fp["group"].get("cohort_id"),
            "membership_revision": fp["group"].get("membership_revision"),
            "membership_basis": p["basis"],
            "population_n": n,
            "unique_issuer_n": p["unique_issuer_n"],
            "security_breadth_not_independent_issuer_breadth": True,
            "measured_return_n": frame.get("universe", {}).get("measured_return_n"),
            "equal_weight_full_cohort_return": ret,
            "rs_market": market_rs, "rs_parent": parent_rs,
            "positive_return_breadth": breadth,
            "above_ma50_breadth": above50,
            "group_facets": sorted({c.get("tag") for c in cards if type(c.get("tag")) is str}),
            "missing_by_reason": frame.get("universe", {}).get("missing_by_reason", {}),
            "source_evidence_status": "unqualified_preview_not_customer_publishable",
        })
    overlap = [
        {"member_id": member, "group_ids": sorted(gs)}
        for member, gs in sorted(member_to_groups.items()) if len(gs) > 1
    ]
    issuer_overlap = [
        {"issuer_id": issuer, "group_ids": sorted(gs)}
        for issuer, gs in sorted(issuer_to_groups.items()) if len(gs) > 1
    ]
    return {
        "schema": SCHEMA, "status": "RESEARCH_PREVIEW_ONLY",
        "comparison_basis": dict(baseline or {}),
        "groups": result_rows, "security_overlap": overlap,
        "issuer_overlap": issuer_overlap,
        "sort_basis": "canonical_group_id_not_performance_rank",
        "no_independent_votes_from_duplicate_securities": True,
        "no_independent_votes_from_duplicate_issuers": True,
        "input_rights_and_original_receipts_authenticated": False,
        "comparison_authority": False, "ranking_authority": False,
        "customer_publication": False, "forecast_or_trading_authority": False,
    }
