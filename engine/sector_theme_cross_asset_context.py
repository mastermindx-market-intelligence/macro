"""P4a research-only cross-asset join over precomputed *incumbent* owner snapshots.

This module does not calculate correlation, credit spreads, regime scores,
directional odds or hedges. It NEVER opens a data store, connects to a feed,
authenticates source rights, creates alerts, trades, writes history, or
publishes anything. The existing owners keep their original math:
engine.cross_asset.snapshot, engine.credit_window.window_state,
engine.bond_cross_asset.snapshot.

A snapshot's as_of date is NOT its first-observed availability. Caller-supplied
available_at is checked for causal coherence, not authenticated as a receipt.
Outputs remain RESEARCH_PREVIEW_ONLY, source-unqualified, date-resolution
context only; they cannot confirm a ticker's intraday move or a future price.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
import math
from zoneinfo import ZoneInfo

SCHEMA = "sector_theme_cross_asset_context/v1"
SOURCE = "sector_theme_owner_preview/v1"
NY = ZoneInfo("America/New_York")
OWNERS = {
    "market_concentration": ("engine.cross_asset.snapshot", "asof"),
    "credit_window": ("engine.credit_window.window_state", "as_of"),
    "bond_transmission": ("engine.bond_cross_asset.snapshot", "as_of"),
}
VERDICTS = frozenset(("diversified", "converging", "concentrated"))
CREDIT_STATES = frozenset(("open", "neutral", "shut", "not_evaluable"))


def _text(value: object) -> str | None:
    return value if type(value) is str and value and value == value.strip() else None


def _instant(value: object) -> datetime | None:
    if type(value) is not str:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.utcoffset() is None:
            return None
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _day(value: object) -> date | None:
    if type(value) is not str:
        return None
    try:
        d = date.fromisoformat(value)
        return d if d.isoformat() == value else None
    except (TypeError, ValueError):
        return None


def _num(value: object) -> float | None:
    if type(value) not in (int, float):
        return None
    try:
        n = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return n if math.isfinite(n) else None


def _held(reason: str) -> dict:
    return {
        "schema": SCHEMA, "status": "HELD", "reason": reason,
        "contexts": {}, "customer_publication": False,
        "predictive_authority": False, "ranking_authority": False,
        "alert_or_trading_authority": False,
    }


def _unknown(reason: str) -> dict:
    return {"status": "UNMEASURED", "reason": reason,
            "intraday_confirmation": False, "source_authenticity_verified": False}


def _concentration(snapshot: Mapping) -> dict | None:
    if snapshot.get("verdict") == "unknown":
        return _unknown("market_concentration_owner_unavailable")
    markets = snapshot.get("markets")
    ratio = _num(snapshot.get("absorption_ratio"))
    window = snapshot.get("window_d")
    if (type(snapshot.get("verdict")) is not str
            or snapshot.get("verdict") not in VERDICTS
            or type(window) is not int or window < 2
            or not isinstance(markets, list) or len(markets) < 3
            or any(_text(m) is None for m in markets)
            or len(markets) != len(set(markets))
            or ratio is None or not 1 / len(markets) - 1e-6 <= ratio <= 1):
        return None
    return {
        "status": "OWNER_REPORTED_RESEARCH_CONTEXT",
        "market_count": len(markets),
        "owner_verdict": snapshot["verdict"],
        "absorption_ratio": ratio,
        "lookback_sessions": window,
        "interpretation": "coarse_cross_market_correlation_not_hedge_or_forecast",
    }


def _credit(snapshot: Mapping, source_day: date) -> dict | None:
    if snapshot.get("SCORED") is not False or snapshot.get("research_only") is not True:
        return None
    segments = snapshot.get("segments")
    if (not isinstance(segments, list) or len(segments) != 2
            or any(not isinstance(seg, Mapping) or
                   type(seg.get("key")) is not str for seg in segments)
            or {seg["key"] for seg in segments} != {"hy", "ig"}):
        return None
    summaries = []
    for seg in sorted(segments, key=lambda s: s["key"]):
        inputs = seg.get("inputs")
        if (not isinstance(inputs, list) or len(inputs) != 3
                or any(not isinstance(r, Mapping) or
                       type(r.get("key")) is not str for r in inputs)
                or {r["key"] for r in inputs}
                != {"spread_range", "spread_drift", "rates_vol"}
                or type(seg.get("state")) is not str
                or seg["state"] not in CREDIT_STATES):
            return None
        raw_count = seg.get("n_inputs")
        present = 0
        dated = {}
        for r in inputs:
            state = r.get("state")
            rd = _day(r.get("as_of"))
            if (state not in ("open", "neutral", "shut", "unknown")
                    or (r.get("as_of") is not None and rd is None)
                    or (rd is not None and rd > source_day)
                    or (state != "unknown" and rd is None)):
                return None
            if state != "unknown":
                present += 1
            dated[r["key"]] = {"as_of": rd.isoformat() if rd else None,
                               "owner_state": state}
        if (type(raw_count) is not int or raw_count != present
                or (present < 2) != (seg["state"] == "not_evaluable")
                or seg.get("low_confidence") is not (present < 3)):
            return None
        summaries.append({
            "segment": seg["key"],
            "owner_state": seg["state"], "observed_inputs_n": present,
            "expected_inputs_n": 3,
            "input_as_of": dated,
        })
    return {
        "status": "OWNER_REPORTED_RESEARCH_CONTEXT",
        "credit_segments": summaries,
        "interpretation": "coincident_daily_credit_window_not_intraday_signal",
    }


def _bond(snapshot: Mapping) -> dict | None:
    if snapshot.get("interpretation_scope") != (
        "contemporaneous_association_not_lead_or_causal_effect"
    ):
        return None
    raw = snapshot.get("assets")
    if not isinstance(raw, list):
        return None
    if not raw:
        return _unknown("bond_transmission_owner_unavailable")
    by_key = {}
    for row in raw:
        if not isinstance(row, Mapping):
            return None
        key, driver = _text(row.get("key")), _text(row.get("driver_key"))
        n, beta, corr = row.get("n"), _num(row.get("beta")), _num(row.get("corr"))
        if (key is None or driver is None or key in by_key
                or type(n) is not int or n < 104
                or beta is None or corr is None or not -1 <= corr <= 1):
            return None
        by_key[key] = {
            "driver": driver, "contemporaneous_beta": beta,
            "contemporaneous_corr": corr, "overlap_weekly_n": n,
            "relationship_stability": "unmeasured_not_a_conditional_hedge",
        }
    return {
        "status": "OWNER_REPORTED_RESEARCH_CONTEXT",
        "associations": {key: by_key[key] for key in sorted(by_key)},
        "interpretation": "contemporaneous_association_not_lead_or_causal_effect",
    }


def compose_sector_theme_cross_asset_context(preview: object,
                                             owner_reads: object) -> dict:
    """Join date-scoped descriptive context without inventing qualifying data."""
    if not isinstance(preview, Mapping) or preview.get("schema") != SOURCE or (
        preview.get("status") != "RESEARCH_PREVIEW_ONLY"
    ) or any(preview.get(key) is not False for key in (
        "eligible_for_customer_publication",
        "eligible_for_historical_prediction", "trading_or_alert_authority",
    )):
        return _held("unqualified_sector_theme_preview")
    basis = preview.get("comparison_basis")
    frame = preview.get("frame")
    group = frame.get("group") if isinstance(frame, Mapping) else None
    fingerprint = preview.get("fingerprint")
    evidence = frame.get("evidence") if isinstance(frame, Mapping) else None
    authority = frame.get("authority") if isinstance(frame, Mapping) else None
    if (not isinstance(basis, Mapping) or not isinstance(frame, Mapping)
            or not isinstance(frame.get("clock"), Mapping)
            or not isinstance(group, Mapping)
            or not isinstance(fingerprint, Mapping)
            or not isinstance(fingerprint.get("group"), Mapping)
            or not isinstance(evidence, Mapping)
            or not isinstance(authority, Mapping)
            or _text(group.get("group_id")) is None
            or group.get("group_id") != fingerprint["group"].get("group_id")
            or group.get("membership_mode") != preview.get("basis")
            or any(evidence.get(key) is not False for key in (
                "source_rights_verified", "original_known_at_receipts_verified",
            ))
            or any(authority.get(key) is not False for key in (
                "eligible_for_customer_publication", "predictive_promoted",
                "entry_or_sizing_authority", "alert_authority", "ranking_authority",
            ))):
        return _held("missing_sector_theme_basis")
    period_end, decision = _instant(basis.get("period_end")), _instant(basis.get("decision_at"))
    if (period_end is None or decision is None or period_end > decision
            or _instant(frame["clock"].get("period_end")) != period_end
            or _instant(frame["clock"].get("decision_at")) != decision
            or not _text(basis.get("horizon"))
            or frame["clock"].get("horizon") != basis.get("horizon")):
        return _held("incompatible_sector_theme_clock")
    if not isinstance(owner_reads, Mapping) or any(
        _text(k) is None or k not in OWNERS for k in owner_reads
    ):
        return _held("unknown_or_malformed_owner_context")

    end_day = period_end.astimezone(NY).date()
    contexts = {}
    for kind, (qualified_owner, day_field) in OWNERS.items():
        payload = owner_reads.get(kind)
        if payload is None:
            contexts[kind] = _unknown("owner_context_missing")
            continue
        if (not isinstance(payload, Mapping)
                or payload.get("owner") != qualified_owner
                or not isinstance(payload.get("snapshot"), Mapping)
                or _text(payload.get("source_revision")) is None):
            return _held("unbound_"+kind+"_owner")
        snap = payload["snapshot"]
        day = _day(snap.get(day_field))
        available = _instant(payload.get("available_at"))
        if (day is None or available is None or day > end_day
                or available > decision or available.astimezone(NY).date() < day):
            return _held("incompatible_"+kind+"_observation_clock")
        result = (
            _concentration(snap) if kind == "market_concentration"
            else _credit(snap, day) if kind == "credit_window"
            else _bond(snap)
        )
        if result is None:
            return _held("invalid_"+kind+"_owner_fields")
        # Independent owners retain their own day and revision. No attempt
        # to force daily credit into an RTH/overnight or 1-minute bar.
        contexts[kind] = {
            **result, "source_owner": qualified_owner,
            "source_revision": payload["source_revision"],
            "as_of_date": day.isoformat(),
            "asserted_available_at": available.isoformat(),
            "calendar_lag_days": (end_day - day).days,
            "original_availability_authenticated": False,
            "intraday_confirmation": False,
            "source_authenticity_verified": False,
        }
    return {
        "schema": SCHEMA, "status": "RESEARCH_PREVIEW_ONLY",
        "group_id": frame["group"]["group_id"],
        "horizon": basis["horizon"],
        "period_end": period_end.isoformat(),
        "decision_at": decision.isoformat(),
        "contexts": contexts,
        "same_clock_market_join_proven": False,
        "source_rights_and_vintage_qualification": "unverified",
        "independent_hedge_relationship_proven": False,
        "customer_publication": False,
        "predictive_authority": False,
        "ranking_authority": False,
        "alert_or_trading_authority": False,
    }
