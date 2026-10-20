"""Qualification and joint cells for the existing Options Hub producer.

This is a projection, not another Greek engine or store. Only owner-supplied
per-series terms/provenance qualify a contract. Bare EOD rows intentionally
remain unavailable: a ticker and the house multiplier are not series evidence.
All arithmetic delegates to exposure_math; no fallback IV or tenor floor.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import math

import pandas as pd

from engine.exposure_math import MIN_QUOTED_IV, dealer_exposures
from engine.intraday_greeks import kernel_applicability

METRIC_UNITS = {
    "gamma": "usd_delta_per_1pct_spot",
    "vanna": "usd_delta_per_1vol_point",
    "charm": "usd_delta_per_calendar_day",
}
RAW_UNITS = {
    "gamma": "delta_per_underlying_price_unit",
    "vanna": "delta_per_1.00_vol",
    "charm": "delta_per_elapsed_calendar_year",
}

# The incumbent SSE consumer caps the complete event at 8 MiB. Reserve space
# for the legacy payload; withhold an oversized joint projection as a whole,
# never rank a silently truncated population.
MAX_CELL_BYTES = 2 * 1024 * 1024


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _time(value):
    try:
        t = pd.Timestamp(value)
        return t.tz_convert("UTC") if not pd.isna(t) and t.tzinfo else None
    except (TypeError, ValueError):
        return None


def _session_date(value):
    try:
        t = pd.Timestamp(value)
        return None if pd.isna(t) else t.date().isoformat()
    except (TypeError, ValueError):
        return None


def _key(row, root):
    """Provider row key only; full economic identity lives in qualified terms."""
    if row.get("root", root) != root:
        return None
    strike = _number(row.get("strike"))
    right = str(row.get("right", "")).upper()
    expiry = _session_date(row.get("expiration"))
    if expiry is None or strike is None or strike <= 0 or right not in ("C", "P"):
        return None
    return (expiry, strike, right)


def _index(records, root):
    indexed = {}
    invalid = 0
    for row in records:
        key = _key(row, root)
        if key is None:
            invalid += 1
        else:
            indexed.setdefault(key, []).append(row)
    return indexed, invalid


def _digest(values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _sum(values):
    try:
        total = math.fsum(values)
        return total if math.isfinite(total) else None
    except OverflowError:
        return None


def exposure_input_digest(greeks_df, oi_df, asof, root):
    """Stable identity of the exact fields this projection consumes, before exclusions.

    The owner records this when admitting the snapshot. Comparing it later does
    not grant rights or manufacture terms; it prevents applying a receipt to
    changed source rows. Nonfinite/missing numbers normalize to JSON null.
    """
    def records(frame, greek):
        out = []
        for r in ([] if frame is None else frame.to_dict("records")):
            if (greek or "date" in r) and _session_date(r.get("date")) != asof:
                continue
            row = {"root": str(r.get("root", root)), "expiration": str(r.get("expiration")),
                   "strike": _number(r.get("strike")), "right": str(r.get("right", "")).upper()}
            for field in (("underlying_price", "implied_vol", "gamma", "vanna", "charm") if greek else ("open_interest",)):
                row[field] = _number(r.get(field))
            out.append(row)
        return sorted(out, key=lambda row: json.dumps(row, sort_keys=True))
    return _digest([root, asof, records(greeks_df, True), records(oi_df, False)])


def _summary(rows, metric, expected_known, *, both_sides=False):
    known = [r["values"][metric] for r in rows if r["values"][metric] is not None]
    complete = bool(rows) and len(known) == len(rows)
    sides = {}
    for right, name in (("C", "call"), ("P", "put")):
        members = [r for r in rows if r["right"] == right]
        values = [r["values"][metric] for r in members if r["values"][metric] is not None]
        # An absent side is unknown under observed-only membership. An explicit
        # expected population may positively establish an empty side.
        side_complete = (bool(members) or expected_known) and len(values) == len(members)
        sides[name] = _sum(values) if side_complete else None
    net, gross = _sum(known), _sum(abs(v) for v in known)
    complete &= net is not None and gross is not None
    if both_sides:
        complete &= all(v is not None for v in sides.values())
    missing = len(rows) - len(known)
    return {
        "unit": METRIC_UNITS[metric],
        "expected": len(rows) if expected_known else None,
        "received": sum(r["greek_received"] for r in rows),
        "qualified": len(known), "missing": missing,
        "status": ("complete_expected" if expected_known else "complete_observed")
        if complete else ("partial" if known else "unavailable"),
        "net": net if complete else None,
        "gross": gross if complete else None,
        "known_net": net if known else None,
        "known_gross": gross if known else None,
        "qualified_population_id": _digest([r["identity"] for r in rows
                                               if r["values"][metric] is not None]),
        **sides,
        "exclusions": dict(sorted(Counter(r["reasons"][metric] for r in rows
                                           if r["values"][metric] is None).items())),
    }


def build_exposure_projection(greeks_df, oi_df, asof, root, *, context=None):
    """Return JSON-safe, dollar-valued joint cells before legacy exclusions.

    ``context`` is an optional *existing owner* receipt, not enrollment or a
    rights decision minted here. Its contract is documented in
    docs/OPTIONS_EXPOSURE_PROJECTION.md. Expected membership is optional; absent
    membership is unknown, never inferred from the received chain. Duplicate
    keys are refused rather than creating a Cartesian OI/Greek join.
    """
    context = context or {}
    clocks = dict(context.get("clocks") or {})
    greek_rows = [] if greeks_df is None else greeks_df.to_dict("records")
    oi_rows = [] if oi_df is None else oi_df.to_dict("records")
    # Keep only this source session. OI date is its report date, not a second
    # shift of the positions that the existing producer already loads.
    greek_rows = [r for r in greek_rows if _session_date(r.get("date")) == asof]
    oi_rows = [r for r in oi_rows if "date" not in r or _session_date(r["date"]) == asof]
    greek, invalid_greek = _index(greek_rows, root)
    oi, invalid_oi = _index(oi_rows, root)
    expected_rows = context.get("expected_contracts")
    expected_known = isinstance(expected_rows, list)
    expected, invalid_expected = _index(expected_rows or [], root)
    terms, invalid_terms = _index(context.get("contract_terms") or [], root)
    series_keys = defaultdict(set)
    for key, records in terms.items():
        for record in records:
            if record.get("series_id"):
                series_keys[record["series_id"]].add(key)
    # Include unexpected observed contracts instead of hiding them before counts.
    keys = sorted(set(greek) | set(oi) | set(expected))
    unexpected = set(keys) - set(expected) if expected_known else set()
    if unexpected or invalid_expected or any(len(v) != 1 for v in expected.values()):
        expected_known = False

    cutoff = _time(clocks.get("available_at"))
    option_clock = _time(clocks.get("option_observed_at"))
    underlying_clock = _time(clocks.get("underlying_observed_at"))
    required_clocks = [option_clock, underlying_clock,
                       _time(clocks.get("greeks_available_at")),
                       _time(clocks.get("oi_available_at"))]
    source_reason = None
    input_digest = exposure_input_digest(greeks_df, oi_df, asof, root)
    if (not context.get("source_snapshot_ref") or not context.get("security_id")
            or clocks.get("source_session") != asof or clocks.get("oi_report_date") != asof):
        source_reason = "source_identity_unknown"
    elif context.get("input_sha256") != input_digest:
        source_reason = "source_inputs_do_not_match_receipt"
    elif cutoff is None or any(t is None for t in required_clocks):
        source_reason = "source_availability_unknown"
    elif any(t > cutoff for t in required_clocks):
        source_reason = "source_after_availability_cutoff"
    elif _time(clocks.get("greeks_available_at")) < option_clock:
        source_reason = "source_availability_before_observation"
    elif any(t.tz_convert("America/New_York").date().isoformat() != asof
             for t in (option_clock, underlying_clock)):
        source_reason = "source_session_mismatch"
    if invalid_greek or invalid_oi or invalid_expected:
        source_reason = "invalid_contract_identity"

    rows = []
    for key in keys:
        gs, os, ts = greek.get(key, []), oi.get(key, []), terms.get(key, [])
        g, o, term = (gs[0] if len(gs) == 1 else {}), (os[0] if len(os) == 1 else {}), (ts[0] if len(ts) == 1 else {})
        reason = source_reason
        if len(gs) > 1 or len(os) > 1 or len(ts) > 1:
            reason = "duplicate_contract_key"
        if len(series_keys.get(term.get("series_id"), set())) > 1:
            reason = "ambiguous_series_binding"
        # Explicit source terms only. The shared arithmetic is currently defined
        # for 100 underlying shares, so adjusted/non-share deliverables refuse.
        if reason is None and (not term.get("series_id") or not term.get("terms_ref")
                or not term.get("deliverable_ref") or term.get("security_id") != context["security_id"]
                or term.get("currency") != "USD" or term.get("deliverable") != "100_underlying_shares"
                or _number(term.get("multiplier")) != 100):
            reason = "exact_series_terms_unqualified"
        terms_clock = _time(term.get("available_at"))
        if reason is None and (terms_clock is None or terms_clock > cutoff):
            reason = "series_terms_availability_unqualified"
        expiry = _time(term.get("economic_expiry_at"))
        if reason is None and (expiry is None or not term.get("exercise_style")
                or expiry.tz_convert("America/New_York").date().isoformat() != key[0]):
            reason = "economic_expiry_unknown"
        if reason is None and expiry <= option_clock:
            reason = "at_or_after_economic_expiry"
        oi_value = _number(o.get("open_interest"))
        if reason is None and (oi_value is None or oi_value < 0 or not oi_value.is_integer()):
            reason = "oi_unknown_or_invalid"
        spot = _number(g.get("underlying_price"))
        if reason is None and oi_value != 0 and (spot is None or spot <= 0):
            reason = "spot_unknown_or_invalid"
        iv = _number(g.get("implied_vol"))
        if reason is None and iv is not None and iv < MIN_QUOTED_IV and oi_value != 0:
            reason = "degenerate_iv"
        values, reasons, methods = {}, {}, {}
        for metric in METRIC_UNITS:
            why = reason
            provenance = (context.get("greek_provenance") or {}).get(metric) or {}
            method = provenance.get("method")
            if why is None and oi_value != 0:
                if (not provenance.get("source_ref") or not provenance.get("model_ref")
                        or provenance.get("source_ref") != context.get("source_snapshot_ref")
                        or provenance.get("tenor_policy") != "economic_expiry_no_floor"
                        or provenance.get("unit") != RAW_UNITS[metric]
                        or method not in ("provider_observed", "engine.intraday_greeks")):
                    why = "greek_provenance_unqualified"
                elif method == "engine.intraday_greeks":
                    app = kernel_applicability(exercise_style=term["exercise_style"], right=key[2],
                        seconds_to_economic_expiry=(expiry - option_clock).total_seconds(),
                        discrete_dividend_before_expiry=term.get("discrete_dividend_before_expiry"))
                    if app["status"] != "supported":
                        why = app["reason"]
                if why is None and _number(g.get(metric)) is None:
                    why = "greek_missing"
                if why is None and metric == "gamma" and _number(g[metric]) < 0:
                    why = "negative_gamma"
            value = None
            if why is None:
                # Observed zero OI is zero even if the Greek is undefined.
                value = 0.0 if oi_value == 0 else float(dealer_exposures(
                    is_call=[key[2] == "C"], oi=[oi_value], spot=[spot],
                    **{metric: [_number(g[metric])]} )[metric][0])
                if not math.isfinite(value):
                    value, why = None, "nonfinite_exposure"
            values[metric], reasons[metric], methods[metric] = value, why, method
        rows.append({"expiration": key[0], "strike": key[1], "right": key[2],
            "economic_expiry_at": term.get("economic_expiry_at"),
            "series_id": term.get("series_id"), "terms_ref": term.get("terms_ref"),
            "identity": [root, *key, term.get("series_id"), term.get("terms_ref"),
                         context.get("source_snapshot_ref"), clocks.get("correction_ref")],
            "greek_received": len(gs) == 1, "oi_received": len(os) == 1,
            "values": values, "reasons": reasons, "methods": methods})

    cells, groups = [], defaultdict(list)
    for row in rows:
        groups[(row["expiration"], row["strike"])].append(row)
    for (expiry, strike), members in sorted(groups.items()):
        expiries = {r["economic_expiry_at"] for r in members}
        economic_expiry = next(iter(expiries)) if len(expiries) == 1 else None
        models = {(context.get("greek_provenance") or {}).get(m, {}).get("model_ref")
                  for m in METRIC_UNITS}
        same_model = len(models) == 1 and None not in models
        joint = [r for r in members if all(v is not None for v in r["values"].values())
                 and (same_model or all(v == 0 for v in r["values"].values()))]
        cells.append({"expiry": expiry, "strike": strike,
            "economic_expiry_at": economic_expiry if _time(economic_expiry) is not None else None,
            "population_id": _digest([context.get("source_snapshot_ref"), clocks,
                                        [r["identity"] for r in members]]),
            **{m: _summary(members, m, expected_known, both_sides=True) for m in METRIC_UNITS},
            "joint": {"expected": len(members) if expected_known else None,
                "received": sum(r["greek_received"] for r in members),
                "qualified": len(joint), "missing": len(members) - len(joint),
                "population_id": _digest([context.get("source_snapshot_ref"), clocks,
                    [[r["series_id"], r["terms_ref"]] for r in joint]]),
                "model_ref": next(iter(models)) if same_model else None,
                "complete": bool(members) and len(joint) == len(members)
                    and (expected_known or {r["right"] for r in members} == {"C", "P"})}})
    cells_status = "complete"
    cell_count = len(cells)
    if not context:
        cells, cells_status = [], "source_unqualified"
    elif len(json.dumps(cells, separators=(",", ":"), allow_nan=False).encode()) > MAX_CELL_BYTES:
        cells, cells_status = [], "payload_limit"
    return {
        "schema": "options_hub.exposure_projection/v1", "kind": "modeled_exposure",
        "root": root, "source_snapshot_ref": context.get("source_snapshot_ref"),
        "input_sha256": input_digest,
        "security_id": context.get("security_id"),
        "position_basis": "assumed_long_call_short_put", "scale": "dollars",
        "rights_decision_ref": context.get("rights_decision_ref"),
        "greek_provenance": context.get("greek_provenance"),
        "clocks": {k: clocks.get(k) for k in ("source_session", "oi_report_date", "oi_position_session",
            "oi_available_at", "option_observed_at", "underlying_observed_at", "greeks_available_at",
            "available_at", "published_at", "correction_ref")},
        "population": {"id": _digest([context.get("source_snapshot_ref"), clocks,
            [[root, *key] for key in keys],
            sorted(context.get("contract_terms") or [], key=lambda t: json.dumps(t, sort_keys=True))]),
            "scope": "supplied_expected_population" if expected_known else "observed_population",
            "full_universe_expected": None, "full_universe_complete": False,
            "expected_contracts": len(keys) if expected_known else None,
            "received_contracts": len(greek), "received_rows": len(greek_rows),
            "oi_received_contracts": len(oi),
            "observed_contracts": len(set(greek) | set(oi)),
            "unexpected_contracts": len(unexpected),
            "invalid_rows": {"greeks": invalid_greek, "oi": invalid_oi,
                             "expected": invalid_expected, "terms": invalid_terms}},
        "metrics": {m: _summary(rows, m, expected_known, both_sides=True) for m in METRIC_UNITS},
        "cell_count": cell_count, "cells_status": cells_status, "cells": cells,
    }
