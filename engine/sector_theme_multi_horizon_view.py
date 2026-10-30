"""Source-held multi-horizon sector/theme preview; no new market, history or publication owner.

Combines original P2 owner-shaped research preview frames across horizons,
only when all share the EXACT cohort, identity population, membership revision,
decision cutoff, end instant, benchmark/parent, price and session basis.
Different start instants identify *distinct* horizons, not extra observations
or compounding windows. The P1a composer owns all numeric cross-horizon tags.

This never validates caller-claimed source rights or original historic vintages.
It does not rank, forecast, alert, execute, retain data, or publish to users.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from engine.sector_theme_regime_fingerprint import compose_regime_fingerprint
from engine.sector_theme_regime_explain import explain_regime_preview

SCHEMA = "sector_theme_multihorizon_preview/v1"
INPUT = "sector_theme_owner_preview/v1"
BASIS_FIELDS = (
    "market", "benchmark_id", "parent_id", "price_basis",
    "session_basis", "period_end", "decision_at",
)


def _held(reason: str) -> dict:
    return {
        "schema": SCHEMA, "status": "HELD", "reason": reason,
        "group": None, "fingerprint": None, "explanation": None,
        "horizons": [], "customer_publication": False,
        "forecast_or_trading_authority": False,
    }


def _clock(value: object) -> datetime | None:
    if type(value) is not str:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return None
    if d.tzinfo is None or d.utcoffset() is None:
        return None
    return d.astimezone(timezone.utc)


def compose_owner_multihorizon_preview(previews: object) -> dict:
    """Compare source-shaped observations, never claim source authentication.

    All-or-nothing: one refused/partially malformed input holds the composite.
    This is a deliberate product-null state, not an empty neutral reading.
    """
    if not isinstance(previews, Mapping) or len(previews) < 2:
        return _held("requires_two_distinct_horizons")
    frames = {}
    comparable = None
    group_id = None
    provenance = None
    issuer_map = None
    member_known_at = None
    for horizon, p in sorted(previews.items(), key=lambda item: str(item[0])):
        if type(horizon) is not str or not horizon or not isinstance(p, Mapping):
            return _held("malformed_horizon_or_source")
        if p.get("schema") != INPUT or p.get("status") != "RESEARCH_PREVIEW_ONLY":
            return _held("refused_or_unknown_owner_preview")
        if (p.get("eligible_for_customer_publication") is not False
                or p.get("eligible_for_historical_prediction") is not False
                or p.get("trading_or_alert_authority") is not False):
            return _held("source_preview_claims_decision_authority")
        frame, source_basis = p.get("frame"), p.get("comparison_basis")
        if not isinstance(frame, Mapping) or not isinstance(source_basis, Mapping):
            return _held("missing_factor_frame_or_source_basis")
        if (source_basis.get("horizon") != horizon
                or not all(
                    type(source_basis.get(k)) is str and bool(source_basis[k])
                    for k in BASIS_FIELDS if k != "parent_id"
                )):
            return _held("malformed_owner_source_basis")
        parent_id = source_basis.get("parent_id")
        if parent_id is not None and (
            type(parent_id) is not str or not parent_id
        ):
            return _held("malformed_parent_identity")
        end = _clock(source_basis.get("period_end"))
        decision = _clock(source_basis.get("decision_at"))
        start = _clock(source_basis.get("period_start"))
        if (start is None or end is None or decision is None
                or not start < end <= decision):
            return _held("missing_or_noncausal_owner_window")
        if (not isinstance(frame.get("clock"), Mapping)
                or frame["clock"].get("horizon") != horizon
                or frame["clock"].get("period_end") != source_basis["period_end"]
                or frame["clock"].get("decision_at") != source_basis["decision_at"]):
            return _held("frame_horizon_or_decision_mismatch")
        if not isinstance(frame.get("group"), Mapping):
            return _held("malformed_frame_population")
        known = _clock(frame["clock"].get("membership_known_at"))
        if known is None or known > decision or (
            frame.get("group", {}).get("membership_mode") == "PIT_AS_KNOWN"
            and known > end
        ):
            return _held("noncausal_membership_availability")
        if (not isinstance(frame.get("group"), Mapping)
                or not isinstance(frame.get("universe"), Mapping)
                or not isinstance(frame.get("constituents"), Mapping)):
            return _held("malformed_frame_population")
        group = frame["group"]
        if (type(group.get("group_id")) is not str or not group["group_id"]
                or p.get("group_kind") not in ("theme", "sector", "industry")):
            return _held("unknown_group_or_kind")
        if (group.get("membership_mode") != p.get("basis")
                or group.get("group_id") != p.get("group_id", group.get("group_id"))):
            return _held("source_population_identity_mismatch")
        ids = frame["universe"].get("member_ids")
        if (not isinstance(ids, list) or not ids or
                any(type(i) is not str or not i for i in ids)
                or len(ids) != len(set(ids))
                or frame["universe"].get("expected_n") != len(ids)):
            return _held("unqualified_security_population")
        mapped = p.get("issuer_by_security_id")
        if (not isinstance(mapped, Mapping) or set(mapped) != set(ids)
                or any(type(v) is not str or not v for v in mapped.values())
                or type(p.get("unique_issuer_n")) is not int
                or p["unique_issuer_n"] != len(set(mapped.values()))):
            return _held("unqualified_issuer_population")
        this_comparison = tuple(source_basis.get(k) for k in BASIS_FIELDS)
        this_group = (
            group.get("group_id"), group.get("cohort_id"),
            group.get("membership_revision"), group.get("membership_mode"),
            p.get("group_kind"), tuple(ids),
        )
        this_origin = p.get("source_origin")
        if type(this_origin) is not str or this_origin not in (
            "synthetic_fixture", "owner_reported"
        ):
            return _held("unknown_source_origin")
        canonical_issuer_map = tuple(sorted(mapped.items()))
        if comparable is None:
            comparable = this_comparison
            group_id = this_group
            provenance = this_origin
            issuer_map = canonical_issuer_map
            member_known_at = known
        elif (this_comparison != comparable or this_group != group_id
              or provenance != this_origin or issuer_map != canonical_issuer_map
              or member_known_at != known):
            return _held("cross_horizon_cohort_benchmark_or_clock_mismatch")
        frames[horizon] = frame
    try:
        fingerprint = compose_regime_fingerprint(frames)
        explanation = explain_regime_preview(fingerprint)
    except (ValueError, TypeError, OverflowError, KeyError, AttributeError):
        return _held("invalid_canonical_factor_fingerprint")
    if (explanation.get("status") != "RESEARCH_PREVIEW_ONLY"
            or explanation.get("eligible_for_customer_publication") is not False
            or explanation.get("predictive_or_trading_authority") is not False):
        return _held("invalid_explanation_authority")
    return {
        "schema": SCHEMA,
        "status": "RESEARCH_PREVIEW_ONLY",
        "group": {
            "group_id": group_id[0], "cohort_id": group_id[1],
            "membership_revision": group_id[2],
            "membership_basis": group_id[3], "group_kind": group_id[4],
            "member_ids": list(group_id[5]),
            "unique_issuer_n": len(set(dict(issuer_map).values())),
        },
        "comparison_basis": dict(zip(BASIS_FIELDS, comparable)),
        "horizons": sorted(frames),
        "per_horizon_period_start": {
            h: previews[h]["comparison_basis"]["period_start"]
            for h in sorted(frames)
        },
        "fingerprint": fingerprint,
        "explanation": explanation,
        "source_origin": provenance,
        "owner_source_and_historical_vintage_authenticated": False,
        "cross_horizon_returns_not_added_or_averaged": True,
        "customer_publication": False,
        "forecast_or_trading_authority": False,
    }
