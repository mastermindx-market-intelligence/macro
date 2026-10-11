"""IM02 gap-aware chart release consumer over existing qualified return owners.

This is not an admission authority. The owner has already qualified each
endpoint, and the persisted source owner has witnessed every series used.
The raw chart adapter provides interior observed levels only; no interpolation,
benchmark permission, calendar completion or prior leadership is invented.

Pure projection: no I/O, credentials, provider calls, publication or UI writes.
"""
from __future__ import annotations

from copy import deepcopy
import math
import re

from engine.intl_inputs import countries
from lib.intl_compare_view import build_compare_catalogue

_REF_PREFIX = "intl-supplied-close:sha256:"
_HEX = re.compile(r"^[a-f0-9]{64}$")
_GAP_REASONS = frozenset({"missing_price", "missing_fx", "missing_price_and_fx", "invalid_calculation"})
_WINDOW_FIELDS = ("start", "end", "calendar_policy")
_BENCHMARK = {"status": "unavailable", "reason": "benchmark_source_not_qualified"}


def _finite_positive(value: object) -> float | None:
    if type(value) not in (float, int):
        return None
    v = float(value)
    return v if math.isfinite(v) and v > 0 else None


def _saved_series(source_evidence: object, series_id: str, ref: str, digest: str) -> bool:
    """Require one unambiguous exact-source witness, never a global source OK."""
    if type(source_evidence) is not list:
        return False
    candidates = [item for item in source_evidence
                  if type(item) is dict and item.get("series_id") == series_id]
    if len(candidates) != 1:
        return False
    item = candidates[0]
    return bool(
        item.get("source_reference") == ref
        and item.get("content_sha256") == digest
        and item.get("basis_state") == "accepted"
        and type(item.get("decision_ref")) is str
        and item["decision_ref"].strip()
        and type(item.get("latest_completed_observation")) is str
        and item["latest_completed_observation"].strip()
        and item.get("calendar_ref") == "intl-conservative-observed-eod-tplus2-v1"
    )


def _rebase(row: dict, raw: dict) -> dict | None:
    """Prove numerical endpoints equal the *qualified* owner return metric."""
    metric = row.get("metric")
    if type(metric) is not dict or metric.get("quality") != "qualified":
        return None
    window = metric.get("window")
    raw_window = raw.get("window")
    if type(window) is not dict or type(raw_window) is not dict:
        return None
    if any(window.get(k) != raw_window.get(k) for k in _WINDOW_FIELDS):
        return None
    if raw.get("numerical_status") not in ("available", "partial"):
        return None
    points = raw.get("points")
    if type(points) is not list or len(points) < 2:
        return None
    if (type(points[0]) is not dict or type(points[-1]) is not dict
            or points[0].get("timestamp") != window["start"]
            or points[-1].get("timestamp") != window["end"]):
        return None
    initial = _finite_positive(points[0].get("value"))
    final = _finite_positive(points[-1].get("value"))
    value = metric.get("value")
    if initial is None or final is None or type(value) not in (int, float):
        return None
    if not math.isfinite(float(value)):
        return None
    authorized_return = float(value)
    if abs(100.0 * (final / initial - 1.0) - authorized_return) > 1e-7:
        return None

    chart_points: list[dict] = []
    seen: set[str] = set()
    previous: str | None = None
    for p in points:
        if type(p) is not dict or type(p.get("timestamp")) is not str:
            return None
        timestamp = p["timestamp"]
        if timestamp in seen or (previous is not None and timestamp <= previous):
            return None
        if not (window["start"] <= timestamp <= window["end"]):
            return None
        seen.add(timestamp)
        previous = timestamp
        level = p.get("value")
        rebased = _finite_positive(level)
        if level is not None and rebased is None:
            return None
        if rebased is None:
            reason = p.get("reason")
            reason = reason if reason in _GAP_REASONS else "invalid_calculation"
            chart_points.append({"timestamp": timestamp, "rebased": None, "reason": reason})
        else:
            chart_points.append({"timestamp": timestamp,
                                 "rebased": round(100.0 * rebased / initial, 8),
                                 "reason": None})
    gaps = sum(item["rebased"] is None for item in chart_points)
    return {"slot": row["slot"], "market_id": row["market_id"],
            "status": "source_bound_partial" if gaps else "source_bound_observed",
            "window": {k: window[k] for k in _WINDOW_FIELDS},
            "gaps": gaps, "points": chart_points}


def build_source_bound_charts(overview: dict, raw_charts: dict, *, source_evidence: list) -> dict:
    """Project gap-aware lines only after existing endpoint/source evidence gates.

    Caller must provide an Overview qualified by the accepted source evaluator,
    raw numerical levels from its existing chart adapter, and producer-bound
    saved-series witness receipts for the same content digest. Only a matching
    same-window cohort can be overlaid; a benchmark remains unqualified.
    """
    catalogue = build_compare_catalogue(overview)  # Existing strict owner validator.
    ref = catalogue["context"].get("source_reference")
    result = {"schema": "intl-source-bound-chart.v1",
              "context": deepcopy(catalogue["context"]),
              "status": "unavailable", "reason": "series_qualification_not_supplied",
              "series": [], "cohorts": [], "benchmark": deepcopy(_BENCHMARK)}
    if (type(ref) is not str or not ref.startswith(_REF_PREFIX)
            or not _HEX.fullmatch(ref[len(_REF_PREFIX):])):
        return result
    digest = ref[len(_REF_PREFIX):]
    if type(raw_charts) is not dict or raw_charts.get("source_reference") != ref:
        return result
    raw_records = raw_charts.get("records")
    if type(raw_records) is not list or type(source_evidence) is not list:
        return result
    mapped_basis = {"local": "local", "usd_unhedged": "usd"}.get(
        catalogue["context"]["currency_basis"])
    if mapped_basis is None or catalogue["context"]["return_basis"] != "price":
        return result

    # A repeated or ambiguous market record cannot win by iteration order.
    by_market = {}
    for record in raw_records:
        if type(record) is not dict or type(record.get("market_id")) is not str:
            continue
        key = record["market_id"]
        if key in by_market:
            by_market[key] = None
        else:
            by_market[key] = record

    configured = countries()
    for row in catalogue["rows"]:
        market_id = row.get("market_id")
        if type(market_id) is not str or market_id not in configured:
            continue  # A denied redacted slot never becomes a named market.
        # The qualified metric already includes the actual owner disclosure
        # decision, so do not invent a second per-point permission regime.
        overview_row = next(
            (item for item in overview["rows"] if item.get("slot") == row["slot"]), None)
        if overview_row is None or overview_row.get("metric", {}).get("quality") != "qualified":
            continue
        raw = by_market.get(market_id)
        if type(raw) is not dict:
            continue
        ids = configured[market_id]
        if (raw.get("market_id") != market_id
                or raw.get("index_id") != ids["index"]
                or raw.get("fx_id") != ids["fx"]
                or raw.get("horizon") != catalogue["context"]["horizon"]
                or raw.get("basis") != mapped_basis):
            continue
        required = [ids["index"]] + ([ids["fx"]] if mapped_basis == "usd" else [])
        if not all(_saved_series(source_evidence, s, ref, digest) for s in required):
            continue
        line = _rebase(overview_row, raw)
        if line is not None:
            result["series"].append(line)

    valid_slots = {line["slot"] for line in result["series"]}
    lookup = {line["slot"]: line["market_id"] for line in result["series"]}
    for cohort in catalogue["cohorts"]:
        slots = [s for s in cohort["order_slots"] if s in valid_slots]
        if len(slots) >= 2:
            result["cohorts"].append({
                "id": cohort["id"], "slots": slots,
                "market_ids": [lookup[s] for s in slots],
                "window": deepcopy(cohort["window"]),
            })
    if not result["series"]:
        return result
    all_admitted = len(result["series"]) == sum(
        row.get("usd" if mapped_basis == "usd" else "local", {}).get("quality") == "qualified"
        for row in catalogue["rows"])
    has_gaps = any(line["gaps"] for line in result["series"])
    result["status"] = ("available" if result["cohorts"] and all_admitted and not has_gaps
                        else "partial")
    result["reason"] = (None if result["status"] == "available"
                        else "observation_gaps" if has_gaps
                        else "insufficient_comparable_markets" if not result["cohorts"]
                        else "source_witness_unavailable")
    return result
