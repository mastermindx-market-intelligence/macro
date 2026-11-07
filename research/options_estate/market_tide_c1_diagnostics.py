"""Descriptive views around the frozen C1-M1 numerical runner.

No fitting changes, new forecast, source admission, collection or trading rule.
Risk bands are fixed dimensionless Y5 ranges, not optimized decision thresholds.
Optional diagnostic_path inputs carry total-return closes with supplied source
refs and availability clocks. They are NOT authenticated by this reader. Each
horizon requires every intervening session and its own mature endpoint prices.
The five-session forecast is never scored as a one/three/ten-session forecast.

Run from repo root: python -m research.options_estate.market_tide_c1_diagnostics
  --input prepared.json --evaluation-at <timezone-aware ISO timestamp>
Repeat --input for separately qualified instruments; reports are never pooled.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from research.options_estate import market_tide_c1 as core
from lib.dataos.temporal import utc

BAND_LOWER = (0., .5, 1., 2.)
HORIZONS = (1, 3, 10)
INSTRUMENTS = ("SPY", "QQQ", "IWM")
MAX_INPUT_BYTES = 32 * 1024 * 1024


def _mean(values):
    return math.fsum(values) / len(values) if values else None


def _nonnegative(value):
    number = core._number(value)
    if number < 0:
        raise ValueError("negative_risk_measure")
    return number


def _groups(rows):
    return {"full": rows, "events": [r for r in rows if r["event_cohort"]],
            "non_events": [r for r in rows if not r["event_cohort"]]}


def risk_strata(report):
    """Fixed half-open prediction bins. Means/errors share mature observations."""
    rows = report["predictions"]
    for row in rows:
        if type(row["event_cohort"]) is not bool:
            raise ValueError("invalid_event_cohort")
        if row["actual"] is not None:
            _nonnegative(row["actual"])
        for model in core.MODELS:
            _nonnegative(row["predictions"][model])
    out = {"descriptive_only": True,
           "band_definition": "fixed_absolute_Y5_units_not_action_thresholds",
           "not_calibrated_probabilities": True}
    for key, group in _groups(rows).items():
        out[key] = {}
        for model in core.MODELS:
            bins = []
            for i, lower in enumerate(BAND_LOWER):
                upper = BAND_LOWER[i + 1] if i + 1 < len(BAND_LOWER) else None
                members = [r for r in group if r["predictions"][model] >= lower
                           and (upper is None or r["predictions"][model] < upper)]
                mature = [r for r in members if r["actual"] is not None]
                p = [_nonnegative(r["predictions"][model]) for r in mature]
                y = [_nonnegative(r["actual"]) for r in mature]
                bins.append({"lower_inclusive": lower, "upper_exclusive": upper,
                             "n_issued": len(members), "n_scored": len(mature),
                             "mean_prediction_scored": _mean(p), "mean_actual": _mean(y),
                             "mean_error_descriptive": _mean([a-b for a,b in zip(p,y)]),
                             "mse_descriptive": _mean([(a-b)**2 for a,b in zip(p,y)])})
            out[key][model] = bins
    return out


def _unavailable(reason):
    return {str(h): {"status": "unavailable", "reason": reason} for h in HORIZONS}


def _path_views(row, position, days, calendar, evaluation, decision_at):
    """Validate only supplied path semantics, never certify its source or roster."""
    path = row.get("diagnostic_path")
    if not isinstance(path, Mapping):
        return _unavailable("path_unavailable")
    try:
        if (path.get("basis") != "total_return" or path.get("price_ref") != row["price_ref"]
                or path.get("origin_session") != row["session"]):
            raise ValueError("path_basis_or_identity_mismatch")
        origin = core._number(path["origin_close"])
        v20 = core._number(row["v20"])
        if origin <= 0 or v20 <= 0:
            raise ValueError("nonpositive_origin_or_volatility")
        decision = utc(decision_at)
        available = utc(path["origin_available_at"])
        if not calendar[days[position]] <= available <= decision or utc(row["decision_at"]) != decision:
            raise ValueError("invalid_origin_clock")
        raw_points = path["points"]
        if not isinstance(raw_points, list):
            raise ValueError("invalid_path_points")
        points = {}
        for point in raw_points:
            if not isinstance(point, Mapping):
                raise ValueError("invalid_endpoint")
            d = core._date(point["session"])
            if d in points:
                raise ValueError("duplicate_endpoint")
            if d not in days[position + 1:position + 11]:
                raise ValueError("endpoint_outside_diagnostic_window")
            points[d] = point
    except (ValueError, KeyError, TypeError) as exc:
        return _unavailable(str(exc) if isinstance(exc, ValueError) else "path_field_unavailable")
    result = {}
    for horizon in HORIZONS:
        try:
            if position + horizon >= len(days):
                raise ValueError("calendar_horizon_unavailable")
            values = [math.log(origin)]
            ready = []
            for day in days[position + 1:position + horizon + 1]:
                if day not in points:
                    raise ValueError("missing_endpoint")
                point = points[day]
                stamp = utc(point["available_at"])
                if stamp < calendar[day]:
                    raise ValueError("endpoint_precedes_close")
                if stamp > evaluation:
                    raise ValueError("not_mature")
                price = core._number(point["close"])
                if price <= 0:
                    raise ValueError("nonpositive_endpoint")
                values.append(math.log(price)); ready.append(stamp)
            moves = [v - values[0] for v in values[1:]]
            increments = [b-a for a,b in zip(values, values[1:])]
            result[str(horizon)] = {
                "status": "available", "endpoint_session": days[position + horizon].isoformat(),
                "available_at": max(ready).isoformat(),
                "normalized_downside": -min(0., min(moves)) / (v20 * math.sqrt(horizon)),
                "signed_log_return": moves[-1],
                "rms_log_return": math.sqrt(math.fsum(v*v for v in increments)/horizon)}
        except (ValueError, KeyError, TypeError) as exc:
            result[str(horizon)] = {"status": "unavailable", "reason":
                                   str(exc) if isinstance(exc, ValueError) else "endpoint_field_unavailable"}
    return result


def horizon_views(packet, report):
    """Endpoint descriptions only; horizon populations and missingness are explicit."""
    if any(packet.get(k) != report.get(k) for k in ("study", "instrument", "evidence_kind")):
        raise ValueError("packet_report_identity_mismatch")
    _, _, days, calendar = core._calendar(packet)
    positions = {d.isoformat(): i for i, d in enumerate(days)}
    supplied = {}
    for row in packet["rows"]:
        if row["session"] in supplied:
            raise ValueError("duplicate_prepared_origin")
        supplied[row["session"]] = row
    evaluation = utc(report["evaluation_at"])
    rows = []
    for prediction in report["predictions"]:
        session = prediction["session"]
        if session not in supplied or session not in positions:
            raise ValueError("prediction_origin_unmapped")
        values = _path_views(supplied[session], positions[session], days, calendar,
                             evaluation, prediction["decision_at"])
        rows.append({"session": session, "event_cohort": prediction["event_cohort"], "horizons": values})
    out = {"descriptive_only": True, "rows": rows, "horizons": {},
           "does_not_score_y5_prediction_at_other_horizons": True,
           "overlapping_horizons_are_not_independent": True,
           "source_qualification": "not_assessed_by_diagnostics"}
    metrics = ("normalized_downside", "signed_log_return", "rms_log_return")
    for horizon in map(str, HORIZONS):
        out["horizons"][horizon] = {}
        for key, group in _groups(rows).items():
            available = [r["horizons"][horizon] for r in group
                         if r["horizons"][horizon]["status"] == "available"]
            out["horizons"][horizon][key] = {
                "n_origins": len(group), "n_available": len(available),
                "exclusion_counts": dict(sorted(Counter(r["horizons"][horizon]["reason"] for r in group
                      if r["horizons"][horizon]["status"] != "available").items())),
                **{"mean_" + m: _mean([r[m] for r in available]) for m in metrics}}
    out["all_horizons_common_origins"] = sum(all(v["status"] == "available" for v in r["horizons"].values()) for r in rows)
    return out


def analyze_packet(packet, evaluation_at):
    """Compose around, never retune or replace, the existing numerical core."""
    result = core.walk_forward(packet, evaluation_at)
    result["summary"] = core.summarize(result)
    result["diagnostics"] = {"risk_strata": risk_strata(result), "horizon_views": horizon_views(packet, result)}
    done = {"risk_strata_diagnostics", "secondary_1_3_10_session_views"}
    result["summary"]["not_implemented"] = [x for x in result["summary"]["not_implemented"] if x not in done]
    return result


def compose_reports(reports):
    """Keep SPY/QQQ/IWM separate; no pooled n, score, efficacy or authority."""
    if not reports or len(reports) > len(INSTRUMENTS):
        raise ValueError("invalid_report_count")
    result = {}; kinds = set(); evaluations = set()
    for report in reports:
        symbol = report.get("instrument")
        if report.get("study") != "C1-M1" or symbol not in INSTRUMENTS or symbol in result:
            raise ValueError("duplicate_or_unsupported_instrument")
        if report.get("evidence_kind") not in ("synthetic", "retrospective_supplied"):
            raise ValueError("unsupported_evidence_kind")
        if any(report.get(key) is not False for key in ("primary_cohort_admitted", "may_trade", "can_publish_forecast")):
            raise ValueError("unexpected_granted_or_missing_authority")
        kinds.add(report["evidence_kind"]); evaluations.add(utc(report["evaluation_at"]))
        result[symbol] = copy.deepcopy(report)
        if "summary" in result[symbol]:
            result[symbol]["summary"]["not_implemented"] = [x for x in result[symbol]["summary"]["not_implemented"]
                                                           if x != "cross_instrument_report_composition"]
    if len(kinds) != 1 or len(evaluations) != 1:
        raise ValueError("incomparable_evidence_or_evaluation_times")
    return {"study": "C1-M1", "evidence_kind": next(iter(kinds)),
            "evaluation_at": next(iter(evaluations)).isoformat(), "instruments": result,
            "missing_instruments": [s for s in INSTRUMENTS if s not in result],
            "pooled_score": None, "independent_replications": False,
            "primary_cohort_admitted": False, "promotion_permitted": False,
            "can_publish_forecast": False, "may_trade": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--evaluation-at", required=True)
    args = parser.parse_args()
    try:
        if len(args.input) > len(INSTRUMENTS):
            raise ValueError("at_most_three_instrument_inputs")
        reports = []
        for filename in args.input:
            with Path(filename).open("rb") as handle:
                content = handle.read(MAX_INPUT_BYTES + 1)
            if len(content) > MAX_INPUT_BYTES:
                raise ValueError("prepared_input_exceeds_32_MiB")
            reports.append(analyze_packet(json.loads(content), args.evaluation_at))
        print(json.dumps(compose_reports(reports), sort_keys=True, allow_nan=False))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
