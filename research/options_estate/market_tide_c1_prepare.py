"""Fail-closed supplied-source preparation bridge for Market Tide C1-M1.

This module transforms already supplied price/calendar/event evidence into the
prepared-row shape consumed by :mod:`market_tide_c1`.  It does NOT fetch data,
authenticate an owner, certify historical completeness, admit a cohort, publish
a forecast, or grant trading authority.

Feature measurements use only price observations/vintages available by the
post-close decision.  The five-session outcome may use a separately supplied
later total-return vintage; this prevents an outcome-vintage rescaling from
leaking into pre-decision volatility or trend features.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Mapping

import numpy as np

from lib.dataos.price import Session, VenueScope, is_ambiguous
from lib.dataos.temporal import utc
from research.options_estate import market_tide_c1 as core


def _text(value, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def _price_keys_clean(row: Mapping) -> None:
    if any(is_ambiguous(key) for key in row):
        raise ValueError("ambiguous_price_column")


def _price_identity(value):
    if not isinstance(value, Mapping):
        raise ValueError("price_identity_unavailable")
    try:
        session = Session(value.get("session"))
    except (TypeError, ValueError):
        raise ValueError("price_identity_unavailable")
    if session is not Session.REGULAR:
        raise ValueError("unsupported_price_session_scope")
    try:
        venue = VenueScope(value.get("venue_scope"))
    except (TypeError, ValueError):
        raise ValueError("price_venue_scope_unavailable")
    return {"session": session.value, "venue_scope": venue.value}


def _window_rows(rows, expected_sessions, *, label: str):
    if not isinstance(rows, list) or len(rows) != len(expected_sessions):
        raise ValueError(f"{label}_window_session_mismatch")
    out = []
    for row, expected in zip(rows, expected_sessions):
        if not isinstance(row, Mapping):
            raise ValueError(f"{label}_window_session_mismatch")
        _price_keys_clean(row)
        if row.get("session") != expected.isoformat():
            raise ValueError(f"{label}_window_session_mismatch")
        out.append(row)
    return out


def _feature_measurements(rows, expected_sessions, calendar, decision, adjustment_asof):
    rows = _window_rows(rows, expected_sessions, label="feature")
    if adjustment_asof < calendar[expected_sessions[-1]] or adjustment_asof > decision:
        raise ValueError("feature_adjustment_not_known_at_decision")
    sadj, tradj, availability = [], [], []
    for row, session in zip(rows, expected_sessions):
        try:
            available = utc(row["available_at"])
            s = core._number(row["close_sadj"])
            t = core._number(row["close_tradj"])
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError("feature_price_field_unavailable") from exc
        if available < calendar[session]:
            raise ValueError("price_available_before_close")
        if available > decision:
            raise ValueError("feature_price_not_known_at_decision")
        if s <= 0 or t <= 0:
            raise ValueError("prices_must_be_positive")
        sadj.append(s)
        tradj.append(t)
        availability.append(available)
    sl = np.log(np.asarray(sadj, dtype=float))
    tl = np.log(np.asarray(tradj, dtype=float))
    v20 = float(np.sqrt(np.mean(np.diff(tl[-21:]) ** 2)))
    if not math.isfinite(v20) or v20 <= 0:
        raise ValueError("volatility_unavailable")
    return {
        "v20": v20,
        "trend63": float(sl[-1] - sl[0]),
        "momentum5": float(sl[-1] - sl[-6]),
        "source_available_at": max([adjustment_asof, *availability]),
    }


def _label_measurement(rows, expected_sessions, calendar, adjustment_asof, v20):
    rows = _window_rows(rows, expected_sessions, label="label")
    end_close = calendar[expected_sessions[-1]]
    if adjustment_asof < end_close:
        raise ValueError("label_adjustment_precedes_outcome")
    values, availability = [], []
    for row, session in zip(rows, expected_sessions):
        try:
            available = utc(row["available_at"])
            price = core._number(row["close_tradj"])
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, ValueError):
                raise
            raise ValueError("label_price_field_unavailable") from exc
        if available < calendar[session]:
            raise ValueError("price_available_before_close")
        if price <= 0:
            raise ValueError("prices_must_be_positive")
        values.append(price)
        availability.append(available)
    logs = np.log(np.asarray(values, dtype=float))
    path = logs[1:] - logs[0]
    y5 = float(-min(0.0, float(np.min(path))) / (v20 * math.sqrt(5.0)))
    return y5, max([adjustment_asof, *availability])


def _event_fields(evidence, *, decision, next_close):
    if not isinstance(evidence, Mapping):
        raise ValueError("event_coverage_unavailable")
    if evidence.get("coverage_status") != "complete_for_window":
        raise ValueError("event_coverage_unavailable")
    known = utc(evidence.get("known_at"))
    if known > decision:
        raise ValueError("event_evidence_not_known_at_decision")
    ref = _text(evidence.get("coverage_ref"), "event_coverage_unavailable")
    rights_ref = _text(evidence.get("rights_ref"), "event_rights_unavailable")
    features = evidence.get("features")
    event_times = evidence.get("event_times")
    negatives = evidence.get("negative_coverage_refs")
    if not isinstance(features, Mapping) or not isinstance(event_times, Mapping):
        raise ValueError("event_coverage_unavailable")
    if negatives is None:
        negatives = {}
    if not isinstance(negatives, Mapping):
        raise ValueError("negative_event_coverage_unavailable")
    flags, times = {}, {}
    for key in core.EVENTS:
        value = features.get(key)
        if type(value) is not int or value not in (0, 1):
            raise ValueError("event_coverage_unavailable")
        raw_times = event_times.get(key)
        if not isinstance(raw_times, list) or len(raw_times) != value:
            raise ValueError("event_time_mismatch")
        if value == 0:
            _text(negatives.get(key), "negative_event_coverage_unavailable")
        parsed = []
        for item in raw_times:
            stamp = utc(item)
            if not decision < stamp <= next_close:
                raise ValueError("event_time_mismatch")
            parsed.append(stamp.isoformat())
        flags[key] = value
        times[key] = parsed
    return ref, rights_ref, known, flags, times


def _prepare_origin(origin, days, calendar, positions):
    if not isinstance(origin, Mapping):
        raise ValueError("invalid_origin")
    session = core._date(origin.get("session"))
    if session not in positions:
        raise ValueError("origin_not_in_calendar")
    pos = positions[session]
    if pos < 63 or pos + 5 >= len(days) or pos + 1 >= len(days):
        raise ValueError("insufficient_calendar_window")
    decision = utc(origin.get("decision_at"))
    if not calendar[session] < decision < calendar[days[pos + 1]]:
        raise ValueError("invalid_decision_window")

    price_ref = _text(origin.get("price_bundle_ref"), "source_reference_unavailable")
    price_rights_ref = _text(origin.get("price_rights_ref"), "price_rights_unavailable")
    feature_identity = _price_identity(origin.get("feature_price_identity"))
    label_identity = _price_identity(origin.get("label_price_identity"))
    feature_sadj_ref = _text(origin.get("feature_sadj_ref"), "source_reference_unavailable")
    feature_tradj_ref = _text(origin.get("feature_tradj_ref"), "source_reference_unavailable")
    label_tradj_ref = _text(origin.get("label_tradj_ref"), "source_reference_unavailable")

    feature_adjustment = utc(origin.get("feature_adjustment_asof"))
    label_adjustment = utc(origin.get("label_adjustment_asof"))
    feature_sessions = days[pos - 63: pos + 1]
    label_sessions = days[pos: pos + 6]

    measured = _feature_measurements(
        origin.get("feature_prices"), feature_sessions, calendar, decision, feature_adjustment
    )
    y5, label_available = _label_measurement(
        origin.get("label_prices"), label_sessions, calendar, label_adjustment, measured["v20"]
    )
    event_ref, event_rights_ref, known, flags, event_times = _event_fields(
        origin.get("event_evidence"), decision=decision, next_close=calendar[days[pos + 1]]
    )

    return {
        "session": session.isoformat(),
        "decision_at": decision.isoformat(),
        "source_available_at": measured["source_available_at"].isoformat(),
        "event_schedule_known_at": known.isoformat(),
        "price_ref": price_ref,
        "event_ref": event_ref,
        "v20": measured["v20"],
        "trend63": measured["trend63"],
        "momentum5": measured["momentum5"],
        "event_flags": flags,
        "event_times": event_times,
        "y5": y5,
        "label_end_session": label_sessions[-1].isoformat(),
        "label_available_at": label_available.isoformat(),
        "source_evidence": {
            "price_rights_ref": price_rights_ref,
            "feature_price_identity": feature_identity,
            "label_price_identity": label_identity,
            "feature_sadj_ref": feature_sadj_ref,
            "feature_tradj_ref": feature_tradj_ref,
            "feature_adjustment_asof": feature_adjustment.isoformat(),
            "label_tradj_ref": label_tradj_ref,
            "label_adjustment_asof": label_adjustment.isoformat(),
            "event_coverage_ref": event_ref,
            "event_rights_ref": event_rights_ref,
        },
    }


def prepare_packet(bundle):
    """Transform supplied evidence without authenticating or admitting it."""
    if not isinstance(bundle, Mapping):
        raise ValueError("invalid_bundle")
    if bundle.get("study") != "C1-M1" or bundle.get("instrument") not in ("SPY", "QQQ", "IWM"):
        raise ValueError("unsupported_study_or_instrument")
    if bundle.get("evidence_kind") not in ("synthetic", "retrospective_supplied"):
        raise ValueError("unsupported_evidence_kind")
    lo, hi, days, calendar = core._calendar(bundle)
    positions = {d: i for i, d in enumerate(days)}
    origins = bundle.get("origins")
    if not isinstance(origins, list):
        raise ValueError("origins_must_be_list")
    prepared = []
    seen = set()
    for origin in origins:
        row = _prepare_origin(origin, days, calendar, positions)
        if row["session"] in seen:
            raise ValueError("duplicate_prepared_origin")
        seen.add(row["session"])
        prepared.append(row)
    prepared.sort(key=lambda row: row["session"])

    return {
        "study": "C1-M1",
        "evidence_kind": bundle["evidence_kind"],
        "instrument": bundle["instrument"],
        "calendar_ref": copy.deepcopy(bundle["calendar_ref"]),
        "coverage_start": lo.isoformat(),
        "coverage_end": hi.isoformat(),
        "calendar": copy.deepcopy(bundle["calendar"]),
        "rows": prepared,
        "source_qualification": "not_assessed_by_preparation_bridge",
        "primary_cohort_admitted": False,
        "can_publish_forecast": False,
        "may_trade": False,
        "limitations": [
            "source owners must independently qualify basis rights versions and historical availability",
            "event completeness and known-negative coverage are supplied claims not authenticated here",
            "prepared rows require separate empirical review before any forecast or policy use",
        ],
    }
