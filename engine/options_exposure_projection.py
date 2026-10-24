"""Qualification and joint cells for the existing Options Hub producer.

This is a projection, not another Greek engine or store. Only owner-supplied
per-series terms/provenance qualify a contract. Bare EOD rows intentionally
remain unavailable: a ticker and the house multiplier are not series evidence.
All arithmetic delegates to exposure_math; no fallback IV or tenor floor.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
import math

import pandas as pd

from engine.exposure_math import MIN_QUOTED_IV, dealer_exposures
from engine.intraday_greeks import kernel_applicability

DATED_KIND = "dated_provider_approximation"
DATED_TENOR = "provider_eod_whole_days_0dte_0.15"
THETA_METHODOLOGY = "https://www.thetadata.net/docs/Articles/Data-And-Requests/Option-Greeks.html"
DATED_CAPABILITIES = dict(dated_cells=True, instantaneous=False, next_live=False,
    joint_scenario=False, repricing=False, historical_pit=False)

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

# The incumbent SSE consumer caps the complete event at 8 MiB. A projection
# cannot exceed that by itself; the publisher separately budgets ALL fields.
MAX_GEX_SSE_BYTES = 8 * 1024 * 1024
SSE_CONTROL_RESERVE_BYTES = 1024
MAX_CELL_BYTES = MAX_GEX_SSE_BYTES - SSE_CONTROL_RESERVE_BYTES
CELL_ENCODING = "tuple-v1"
CELL_FIELDS = ("expiry_index", "strike", "population_index", "metrics", "joint")
METRIC_FIELDS = ("expected", "received", "qualified", "missing", "status_index",
                 "net", "gross", "known_net", "known_gross", "qualified_population_index",
                 "call", "put", "exclusions")
JOINT_FIELDS = ("expected", "received", "qualified", "missing", "population_index",
                "model_index", "complete")
METRIC_STATUSES = ("unavailable", "partial", "complete_observed", "complete_expected")


def encode_projection_cells(cells):
    """Lossless v2 wire encoding; repeated units, keys and identities are shared.

    The five cell fields and nested tuple columns are explicit on the wire.
    Values, nulls, counts and all original identity digests retain their precision.
    There is no row sampling, rounded numeric encoding or inferred denominator.
    """
    populations, models, expiries = {}, {}, {}

    def intern(table, value):
        if value not in table:
            table[value] = len(table)
        return table[value]

    encoded = []
    for cell in cells:
        metrics = []
        for metric in METRIC_UNITS:
            m = cell[metric]
            metrics.append([m["expected"], m["received"], m["qualified"], m["missing"],
                METRIC_STATUSES.index(m["status"]), m["net"], m["gross"], m["known_net"],
                m["known_gross"], intern(populations, m["qualified_population_id"]),
                m["call"], m["put"], m["exclusions"]])
        j = cell["joint"]
        encoded.append([
            intern(expiries, (cell["expiry"], cell["economic_expiry_at"])), cell["strike"],
            intern(populations, cell["population_id"]), metrics,
            [j["expected"], j["received"], j["qualified"], j["missing"],
             intern(populations, j["population_id"]),
             None if j["model_ref"] is None else intern(models, j["model_ref"]), j["complete"]],
        ])
    return {"cell_encoding": CELL_ENCODING, "cell_fields": list(CELL_FIELDS),
        "metric_order": list(METRIC_UNITS), "metric_fields": list(METRIC_FIELDS),
        "joint_fields": list(JOINT_FIELDS), "metric_statuses": list(METRIC_STATUSES),
        "metric_units": dict(METRIC_UNITS), "population_ids": list(populations),
        "model_refs": list(models), "expiry_terms": [list(pair) for pair in expiries],
        "cells": encoded}


def expand_projection_cells(projection):
    """Reference expansion of producer v2 bytes for Python integration/tests.

    The Terminal independently validates untrusted wire bytes before expansion.
    This helper accepts the producer's own v2 shape, not an admission receipt.
    """
    if (projection.get("schema") != "options_hub.exposure_projection/v2"
            or projection.get("cell_encoding") != CELL_ENCODING
            or projection.get("cell_fields") != list(CELL_FIELDS)
            or projection.get("metric_fields") != list(METRIC_FIELDS)
            or projection.get("joint_fields") != list(JOINT_FIELDS)
            or projection.get("metric_order") != list(METRIC_UNITS)
            or projection.get("metric_statuses") != list(METRIC_STATUSES)
            or projection.get("metric_units") != METRIC_UNITS):
        raise ValueError("Unsupported exposure cell encoding")
    out = []
    for exp, strike, pop, metric_rows, joint in projection["cells"]:
        expiry, economic = projection["expiry_terms"][exp]
        cell = {"expiry": expiry, "economic_expiry_at": economic, "strike": strike,
                "population_id": projection["population_ids"][pop]}
        for metric, values in zip(METRIC_UNITS, metric_rows, strict=True):
            m = dict(zip(METRIC_FIELDS, values, strict=True))
            m["unit"] = METRIC_UNITS[metric]
            m["status"] = METRIC_STATUSES[m.pop("status_index")]
            m["qualified_population_id"] = projection["population_ids"][m.pop("qualified_population_index")]
            cell[metric] = m
        j = dict(zip(JOINT_FIELDS, joint, strict=True))
        j["population_id"] = projection["population_ids"][j.pop("population_index")]
        idx = j.pop("model_index")
        j["model_ref"] = None if idx is None else projection["model_refs"][idx]
        cell["joint"] = j
        out.append(cell)
    return out


def gex_sse_bytes(payload):
    """Conservative UTF-8 budget for the broadcaster's `data: JSON` frame.

    JavaScript writes 1e-6 through 1e20 in decimal form where Python may choose
    scientific notation. Budget that expansion rather than relying on the small
    control reserve to absorb a large array of tiny/large finite values.
    """
    def number_expansion(value):
        if isinstance(value, dict):
            return sum(number_expansion(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return sum(number_expansion(v) for v in value)
        if isinstance(value, float) and 1e-6 <= abs(value) < 1e21:
            text = repr(value)
            if "e" in text.lower():
                return max(0, len(format(Decimal(text), "f")) - len(text))
        return 0

    return (len(json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
                           allow_nan=False).encode()) + len(b"data: \n\n")
            + number_expansion(payload))


def fit_gex_transport(payload):
    """Bound the whole incumbent GEX event, including legacy fields and history.

    Never truncate cells or legacy fields. If necessary, withhold the entire
    optional projection and retain its population/counts. A legacy envelope
    that still exceeds the actual feed ceiling is not publishable.
    """
    budget = MAX_GEX_SSE_BYTES - SSE_CONTROL_RESERVE_BYTES
    if gex_sse_bytes(payload) <= budget:
        return True, payload
    candidate = payload
    projection = payload.get("exposure_projection")
    if isinstance(projection, dict) and projection.get("schema") == "options_hub.exposure_projection/v2":
        candidate = {**payload, "exposure_projection": {
            **projection, **encode_projection_cells([]), "cells_status": "payload_limit"}}
    return gex_sse_bytes(candidate) <= budget, candidate


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
            # Preserve raw observation identity when the native collector carries
            # it. Naive vendor text is not turned into a timezone/availability.
            for field in (("timestamp", "underlying_timestamp", "snapshot_ts", "_theta_acquisition",
                           "second_order_timestamp", "second_order_underlying_timestamp", "_theta_second_acquisition")
                          if greek else ("timestamp", "snapshot_ts", "_theta_acquisition")):
                if field in r:
                    value = r[field]
                    row[field] = None if pd.isna(value) else str(value)
            if greek:
                for field in ("second_order_underlying_price", "second_order_implied_vol", "second_order_iv_error",
                              "second_order_bid", "second_order_ask"):
                    if field in r:
                        row[field] = _number(r[field])
            out.append(row)
        return sorted(out, key=lambda row: json.dumps(row, sort_keys=True))
    return _digest([root, asof, records(greeks_df, True), records(oi_df, False)])


def compose_native_exposure_context(greeks_df, oi_df, asof, root, *, context):
    """Compose explicit source evidence; never grants rights or fills model/terms defaults.

    Existing owner input binding remains mandatory. Native receipt times are
    conservative known-by times for new acquisitions, not original publication.
    No context means no automatic opt-in or change to the dated reference path.
    """
    if context is None:
        return None
    from copy import deepcopy
    from lib.options_source_receipts import native_acquisitions, massive_reference_terms, ordinary_etf_terms
    out = deepcopy(context)
    if out.get("root", root) != root:
        raise ValueError("Exposure context root mismatch")
    if out.get("input_sha256") != exposure_input_digest(greeks_df, oi_df, asof, root):
        return out  # The incumbent qualifier rejects the unchanged mismatched receipt.
    identity_inputs = out.pop("dated_identity_inputs", None)
    observed_identity_inputs = out.pop("dated_population_identity_inputs", None)
    if identity_inputs is not None and observed_identity_inputs is not None:
        raise ValueError("Conflicting selected and observed identity inputs")
    if identity_inputs is not None:
        if out.get("kind") != DATED_KIND:
            raise ValueError("Selected dated identity cannot authorize instantaneous exposure")
        from engine.intelligence_workspace.options_contract_identity import resolve_dated_spy_contract_identity
        bound = resolve_dated_spy_contract_identity(greeks_df, oi_df, source_session=asof,
            input_sha256=out["input_sha256"], **identity_inputs).receipt
        if out.get("security_id") not in (None, bound["security_id"]):
            raise ValueError("Conflicting owner canonical identity")
        out["security_id"] = bound["security_id"]
        out["contract_identity"] = bound
    if observed_identity_inputs is not None:
        if out.get("kind") != DATED_KIND or root not in {"SPY", "QQQ"}:
            raise ValueError("Observed dated identity cannot authorize this exposure")
        from engine.intelligence_workspace.options_contract_identity import resolve_observed_etf_contract_identity
        bound = resolve_observed_etf_contract_identity(greeks_df, oi_df, root=root, source_session=asof,
            input_sha256=out["input_sha256"], **observed_identity_inputs).receipt
        if out.get("security_id") not in (None, bound["security_id"]):
            raise ValueError("Conflicting owner canonical identity")
        out["security_id"], out["contract_identity"] = bound["security_id"], bound
    terms = list(out.get("contract_terms") or [])
    term_indices = defaultdict(list)
    for index, term in enumerate(terms):
        term_indices[_key(term, root)].append(index)
    references = []
    for population in out.pop("contract_reference_populations", []):
        from lib.options_source_receipts import reference_population_terms
        population_terms, _ = reference_population_terms(population, root, out.get("security_id"))
        # Feed the same merge path without reinterpreting cursor queries as
        # per-expiry requests. These terms were mapped from the actual page.
        for term in population_terms:
            if out.get("term_policy") == {"SPY":"occ_standard_spy_etf/v1", "QQQ":"occ_standard_qqq_etf/v1"}.get(root):
                term = ordinary_etf_terms(term, root=root)
            key = _key(term, root)
            matches = term_indices.get(key, [])
            if len(matches)>1:
                raise ValueError("Ambiguous owner terms")
            if matches:
                old=terms[matches[0]]
                for field in ("series_id","exercise_style","shares_per_contract","additional_underlyings","correction"):
                    if field in old and field in term and old[field]!=term[field]:
                        raise ValueError("Conflicting reference terms")
                merged={**term,**old}
                previous,current=_time(old.get("available_at")),_time(term["available_at"])
                merged["available_at"]=max(previous,current).isoformat() if previous is not None else current.isoformat()
                merged["reference_observation_ref"]=term["terms_ref"]
                terms[matches[0]]=merged
            else:
                term_indices[key].append(len(terms));terms.append(term)
    for observation in out.pop("contract_reference_observations", []):
        if "contracts" in observation:
            references.extend((observation, c) for c in observation["contracts"])
        else:
            references.append((observation, None))
    for observation, contract in references:
        term = massive_reference_terms(observation, root, out.get("security_id"), contract=contract)
        if out.get("term_policy") == {"SPY":"occ_standard_spy_etf/v1", "QQQ":"occ_standard_qqq_etf/v1"}.get(root):
            term = ordinary_etf_terms(term, root=root)
        term_key = _key(term, root)
        matches = term_indices.get(term_key, [])
        if len(matches) > 1:
            raise ValueError("Ambiguous owner terms")
        if matches:
            old = terms[matches[0]]
            for key in ("series_id", "exercise_style", "shares_per_contract", "additional_underlyings", "correction"):
                if key in old and key in term and old[key] != term[key]:
                    raise ValueError("Conflicting reference terms")
            merged = {**term, **old}
            # The combined evidence was not known before both observations.
            previous = _time(old.get("available_at"))
            current = _time(term["available_at"])
            merged["available_at"] = max(previous, current).isoformat() if previous is not None else current.isoformat()
            merged["reference_observation_ref"] = term["terms_ref"]
            terms[matches[0]] = merged
        else:
            term_indices[term_key].append(len(terms))
            terms.append(term)
    if terms:
        out["contract_terms"] = terms
    acquisitions = {kind: native_acquisitions(frame, root, asof, kind)
                    for kind, frame in (("greeks", greeks_df), ("oi", oi_df))}
    clocks = dict(out.get("clocks") or {})
    for kind, field, session_field in (("greeks", "greeks_available_at", "source_session"),
                                       ("oi", "oi_available_at", "oi_report_date")):
        if not acquisitions[kind]:
            continue
        clocks.setdefault(session_field, asof)
        received = max(_time(rec["received_at"]) for rec in acquisitions[kind])
        old = _time(clocks.get(field))
        clocks[field] = max(old, received).isoformat() if old is not None else received.isoformat()
    if clocks:
        out["clocks"] = clocks
    if all(acquisitions.values()):
        # Never move an explicit selection cutoff forward to admit later evidence.
        evidence_times = [_time(clocks[k]) for k in ("greeks_available_at", "oi_available_at")]
        evidence_times += [_time(term.get("available_at")) for term in terms]
        evidence_times += [_time((out.get("contract_identity") or {}).get("known_at"))]
        clocks.setdefault("available_at", max(t for t in evidence_times if t is not None).isoformat())
        out.setdefault("source_snapshot_ref", "capture:sha256:" + _digest([out["input_sha256"], acquisitions]))
    return out


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
    kind = context.get("kind", "modeled_exposure")
    dated = kind == DATED_KIND
    valuation = context.get("valuation") or {}
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
    if dated:
        required_clocks = [_time(clocks.get(k)) for k in ("greeks_available_at", "oi_available_at")]
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
    elif not dated and _time(clocks.get("greeks_available_at")) < option_clock:
        source_reason = "source_availability_before_observation"
    elif not dated and any(t.tz_convert("America/New_York").date().isoformat() != asof
             for t in (option_clock, underlying_clock)):
        source_reason = "source_session_mismatch"
    if kind not in ("modeled_exposure", DATED_KIND):
        source_reason = "unsupported_projection_kind"
    if dated:
        from lib.options_source_receipts import native_acquisitions
        native = native_acquisitions(greeks_df, root, asof, "greeks")
        oi_native = native_acquisitions(oi_df, root, asof, "oi")
        if (valuation.get("basis") != "provider_eod_approximation"
                or valuation.get("source_session") != asof
                or valuation.get("observation_clock") != "session_only"
                or valuation.get("methodology_ref") != THETA_METHODOLOGY
                or valuation.get("endpoint") != "/v3/option/history/greeks/eod"
                or valuation.get("requested_version") != "1"
                or valuation.get("serving_build") is not None
                or valuation.get("tenor_policy") != DATED_TENOR
                or not native or not oi_native
                or any(str(r["parameters"].get("version")) != "1" for r in native)):
            source_reason = "dated_valuation_unqualified"
        elif asof > pd.Timestamp.now(tz="America/New_York").date().isoformat():
            source_reason = "source_session_in_future"
    identity_scope = None
    if context.get("contract_identity") is not None:
        try:
            from engine.intelligence_workspace.options_contract_identity import validate_dated_contract_identity
            if not dated:
                raise ValueError("Dated scoped identity cannot qualify instantaneous exposure")
            identity_scope = validate_dated_contract_identity(context["contract_identity"], root=root,
                source_session=asof, input_sha256=input_digest, cutoff=clocks.get("available_at"))
            if context["contract_identity"].get("schema") == "options.dated_contract_identity/v2":
                observed = {(k[0],format(Decimal(str(k[1])).normalize(),"f"),k[2]) for k in set(greek)|set(oi)}
                if observed != {tuple(k) for k in context["contract_identity"]["observed_contract_keys"]}:
                    raise ValueError("Observed identity denominator mismatch")
            if context.get("security_id") != context["contract_identity"]["security_id"]:
                raise ValueError("Canonical identity mismatch")
        except (ValueError, TypeError, KeyError):
            source_reason = "contract_identity_unqualified"
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
        if identity_scope is not None and (key[0], format(Decimal(str(key[1])).normalize(), "f"), key[2]) not in identity_scope:
            reason = "contract_identity_scope_unknown"
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
        if not dated and reason is None and (expiry is None or not term.get("exercise_style")
                or expiry.tz_convert("America/New_York").date().isoformat() != key[0]):
            reason = "economic_expiry_unknown"
        if not dated and reason is None and expiry <= option_clock:
            reason = "at_or_after_economic_expiry"
        if dated and reason is None and (key[0] < asof or not term.get("exercise_style")):
            reason = "dated_contract_expired_or_style_unknown"
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
            if dated and metric != "gamma":
                why = "dated_metric_unavailable"
            if why is None and oi_value != 0:
                if (not provenance.get("source_ref") or not provenance.get("model_ref")
                        or provenance.get("source_ref") != context.get("source_snapshot_ref")
                        or provenance.get("tenor_policy") != (DATED_TENOR if dated else "economic_expiry_no_floor")
                        or provenance.get("unit") != RAW_UNITS[metric]
                        or method not in (("provider_observed",) if dated else ("provider_observed", "engine.intraday_greeks"))):
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
    wire = encode_projection_cells(cells)
    if not context:
        wire, cells_status = encode_projection_cells([]), "source_unqualified"
    elif len(json.dumps(wire, separators=(",", ":"), allow_nan=False).encode()) > MAX_CELL_BYTES:
        wire, cells_status = encode_projection_cells([]), "payload_limit"
    underlying_reference = None
    if dated:
        spots = [_number(row.get("underlying_price")) for row in greek_rows]
        uniform = bool(spots) and all(v is not None and v > 0 for v in spots) and len(set(spots)) == 1
        underlying_reference = {"value": spots[0] if uniform else None, "currency": "USD",
            "basis": "uniform_selected_contract_underlying_price" if uniform else "nonuniform_or_missing_selected_underlying_prices",
            "source_session": asof, "instantaneous": False}
    return {
        "schema": "options_hub.exposure_projection/v2", "kind": kind,
        **({"valuation": valuation, "capabilities": dict(DATED_CAPABILITIES),
            "underlying_reference": underlying_reference} if dated else {}),
        "root": root, "source_snapshot_ref": context.get("source_snapshot_ref"),
        "input_sha256": input_digest,
        "security_id": context.get("security_id"),
        **({"contract_identity": context["contract_identity"]} if context.get("contract_identity") is not None else {}),
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
        "cell_count": cell_count, "cells_status": cells_status, **wire,
    }
