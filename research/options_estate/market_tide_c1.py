"""C1-M1 numerical research runner; no acquisition, admission, publication or trades.

Method: MARKET_TIDE_R1_SOURCE_AND_EVENT_SEQUENCE_2026-09-24.md, amended only
by MARKET_TIDE_C1_M1_PUBLICATION_AND_MEASUREMENT_2026-09-24.md. Prepared rows
and an explicit session roster are SUPPLIED evidence, not authenticated here.
The existing Data OS owns timestamp semantics; source owners must separately
qualify basis, versions, rights and complete schedule/negative coverage.

python -m research.options_estate.market_tide_c1 --input prepared.json \
  --evaluation-at 2026-09-24T20:30:00Z

Input rows carry measured v20/trend63/momentum5/Y5, source references, source
availability, resolved event flags/times, and label endpoint/availability.
measure_closes provides the exact arithmetic for a separately qualified
64-session structural / 69-session total-return window (origin index 63).
No latest-data lookup, source-qualification switch, new event resolver or clock.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from lib.dataos.temporal import utc

MODELS = ("N", "P", "PE", "PEI")
EVENTS = ("CPI", "NFP", "FOMC")
PENALTY = .01
SEED = 20260924
DRAWS = 10000
FLOORS = {"CPI": 40, "NFP": 40, "FOMC": 30}
START = date(2017, 1, 1)
END = date(2026, 8, 31)
_ET = ZoneInfo("America/New_York")


def _number(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.number)):
        raise ValueError("invalid_numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("invalid_numeric")
    return value


def _date(value):
    if not isinstance(value, str):
        raise ValueError("invalid_session")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("noncanonical_session")
    return parsed


def measure_closes(structure, total_return):
    """Pure fixed-window arithmetic, not source/time/basis qualification."""
    if len(structure) != 64 or len(total_return) != 69:
        raise ValueError("requires_64_structural_and_69_total_return_closes")
    s = np.asarray([_number(x) for x in structure], dtype=float)
    t = np.asarray([_number(x) for x in total_return], dtype=float)
    if np.any(s <= 0) or np.any(t <= 0):
        raise ValueError("prices_must_be_positive")
    sl, tl = np.log(s), np.log(t)
    v20 = float(np.sqrt(np.mean(np.diff(tl[43:64]) ** 2)))
    if not math.isfinite(v20) or v20 <= 0:
        raise ValueError("volatility_unavailable")
    return {"v20": v20, "trend63": float(sl[63] - sl[0]),
            "momentum5": float(sl[63] - sl[58]),
            "y5": float(-min(0., float(np.min(tl[64:69] - tl[63]))) / (v20 * math.sqrt(5)))}


def design(row, model):
    if model not in MODELS[1:]:
        raise ValueError("unsupported_model")
    v, trend, momentum = (_number(row[k]) for k in ("v20", "trend63", "momentum5"))
    if v <= 0:
        raise ValueError("volatility_unavailable")
    d = int(trend > 0 and momentum < 0)
    x = [math.log(v), trend, momentum, d]
    if model != "P":
        flags = row["event_flags"]
        e = []
        for key in EVENTS:
            if type(flags.get(key)) is not int or flags[key] not in (0, 1):
                raise ValueError("event_coverage_unavailable")
            e.append(flags[key])
        x.extend(e)
        if model == "PEI":
            x.extend([d * (e[0] + e[1]), d * e[2]])
    return x


def fit_ridge(train_x, train_y, test_x):
    """Fixed mean-loss ridge; only the first three continuous inputs standardized."""
    x, y, z = (np.asarray(a, dtype=float) for a in (train_x, train_y, test_x))
    if x.ndim != 2 or z.ndim != 2 or y.ndim != 1 or len(x) != len(y) or len(y) == 0:
        raise ValueError("invalid_fit_shape")
    if x.shape[1] not in (4, 7, 9) or z.shape[1] != x.shape[1]:
        raise ValueError("invalid_feature_count")
    if not all(np.all(np.isfinite(a)) for a in (x, y, z)) or np.any(y < 0):
        raise ValueError("invalid_fit_values")
    mean = np.mean(x[:, :3], axis=0)
    scale = np.std(x[:, :3], axis=0, ddof=0)
    # An exactly constant floating column can have nonzero computed std from
    # summation roundoff. Compare its observed values, without a tuned floor.
    constant = np.all(x[:, :3] == x[0, :3], axis=0)
    if np.any((scale == 0) & ~constant):
        raise ValueError("nonconstant_scale_underflow")
    scale = np.where(constant, 0., scale)
    safe_scale = np.where(constant, 1., scale)
    a, b = x.copy(), z.copy()
    a[:, :3] = np.where(constant, 0., (x[:, :3] - mean) / safe_scale)
    b[:, :3] = np.where(constant, 0., (z[:, :3] - mean) / safe_scale)
    a = np.column_stack([np.ones(len(a)), a])
    b = np.column_stack([np.ones(len(b)), b])
    penalty = np.eye(a.shape[1]) * math.sqrt(PENALTY)
    penalty[0, 0] = 0.  # Unpenalized intercept.
    beta = np.linalg.lstsq(np.vstack([a / math.sqrt(len(a)), penalty]),
                          np.concatenate([y / math.sqrt(len(y)), np.zeros(a.shape[1])]), rcond=None)[0]
    prediction = np.maximum(0., b @ beta)
    if not np.all(np.isfinite(prediction)):
        raise ValueError("nonfinite_prediction")
    return prediction.tolist(), {"continuous_mean": mean.tolist(), "continuous_scale": scale.tolist(),
        "constant_continuous": np.flatnonzero(constant).tolist(), "coefficients": beta.tolist(),
        "penalty": PENALTY, "loss": "mean_squared_error", "n_train": len(y)}


def _calendar(packet):
    lo, hi = _date(packet["coverage_start"]), _date(packet["coverage_end"])
    if lo > hi or not isinstance(packet.get("calendar_ref"), str) or not packet["calendar_ref"].strip():
        raise ValueError("calendar_coverage_unavailable")
    calendar = {}
    for entry in packet["calendar"]:
        d, close = _date(entry["session"]), utc(entry["close_at"])
        if d in calendar or not lo <= d <= hi or close.astimezone(_ET).date() != d:
            raise ValueError("invalid_calendar_identity")
        calendar[d] = close
    days = sorted(calendar)
    if not days or any(calendar[b] <= calendar[a] for a, b in zip(days, days[1:])):
        raise ValueError("invalid_calendar_order")
    return lo, hi, days, calendar


def walk_forward(packet, evaluation_at):
    """Fit monthly on supplied prepared rows. Output never grants source admission.

    Fit cutoff is 00:00 UTC on the first of each test month: a computational
    boundary, NOT an inferred publication clock. Full years require supplied
    calendar coverage, eligible inputs and mature labels at every historical
    session except the ordinary five-session boundary purge. No shorter-training
    fallback; missing historical outcomes are not a complete training year.
    """
    if packet.get("study") != "C1-M1" or packet.get("instrument") not in ("SPY", "QQQ", "IWM"):
        raise ValueError("unsupported_study_or_instrument")
    if packet.get("evidence_kind") not in ("synthetic", "retrospective_supplied"):
        raise ValueError("unsupported_evidence_kind")
    evaluation = utc(evaluation_at)
    lo, hi, days, calendar = _calendar(packet)
    positions = {d: i for i, d in enumerate(days)}
    rows = {}
    for r in packet["rows"]:
        d = _date(r["session"])
        if d in rows or d not in positions:
            raise ValueError("duplicate_or_unmapped_session")
        rows[d] = r
    valid, excluded = {}, []
    for d in days:
        i = positions[d]
        if d < START or d > END or calendar[d] >= evaluation:
            continue
        r = rows.get(d)
        if r is None:
            excluded.append({"session": d.isoformat(), "reason": "missing_observation"}); continue
        try:
            if i + 1 >= len(days):
                raise ValueError("next_session_unavailable")
            decision = utc(r["decision_at"])
            if not calendar[d] < decision < calendar[days[i + 1]] or decision > evaluation:
                raise ValueError("invalid_decision_window")
            source_available = utc(r["source_available_at"])
            if source_available < calendar[d]:
                raise ValueError("completed_inputs_precede_session_close")
            if source_available > decision or utc(r["event_schedule_known_at"]) > decision:
                raise ValueError("inputs_not_available_at_decision")
            for key in ("price_ref", "event_ref"):
                if not isinstance(r.get(key), str) or not r[key].strip():
                    raise ValueError("source_reference_unavailable")
            features = {name: design(r, name) for name in MODELS[1:]}
            event_dates = {}
            for key in EVENTS:
                times = r["event_times"].get(key)
                if not isinstance(times, list) or len(times) > 1 or len(times) != r["event_flags"][key]:
                    raise ValueError("event_time_mismatch")
                event_dates[key] = []
                for t in times:
                    stamp = utc(t)
                    if not decision < stamp <= calendar[days[i + 1]]:
                        raise ValueError("event_time_mismatch")
                    event_dates[key].append(stamp.astimezone(_ET).date().isoformat())
        except (ValueError, TypeError, KeyError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) else "input_field_unavailable"
            excluded.append({"session": d.isoformat(), "reason": reason}); continue
        y, ready, endpoint = None, None, None
        try:
            if i + 5 >= len(days) or r.get("label_end_session") != days[i + 5].isoformat():
                raise ValueError("incorrect_or_missing_fifth_endpoint")
            endpoint = calendar[days[i + 5]]
            ready = utc(r["label_available_at"])
            y = _number(r["y5"])
            if ready < endpoint or y < 0:
                raise ValueError("invalid_label_clock_or_value")
        except (ValueError, TypeError, KeyError) as exc:
            y, ready, endpoint = None, None, None
            excluded.append({"session": d.isoformat(), "reason": "label_unavailable:" + str(exc)})
        valid[d] = {"features": features, "y": y, "ready": ready, "endpoint": endpoint,
                    "events": event_dates, "decision": decision}
    by_year = defaultdict(set)
    for d in days:
        if START <= d <= END:
            by_year[d.year].add(d)
    covered_years = [year for year, expected in sorted(by_year.items())
                     if lo <= date(year, 1, 1) and hi >= date(year, 12, 31) and expected <= valid.keys()]
    months = sorted({(d.year, d.month) for d in valid})
    fits, predictions, skipped_months = [], [], []
    for year, month in months:
        cutoff = datetime(year, month, 1, tzinfo=timezone.utc)
        prior = [d for d in valid if d < cutoff.date()]
        train = [d for d in prior if valid[d]["ready"] is not None and valid[d]["ready"] < cutoff
                 and valid[d]["endpoint"] < cutoff]
        # Calendar/feature coverage alone must not count as usable training
        # history. Only ordinary boundary-crossing labels may be unavailable.
        # Determine that boundary from the supplied roster, never from an
        # untrusted or missing label endpoint. Re-evaluate at each fit cutoff.
        boundary_purged = {d for d in prior if valid[d]["decision"] < cutoff
                           and positions[d] + 5 < len(days)
                           and calendar[days[positions[d] + 5]] >= cutoff}
        eligible_coverage = set(train) | boundary_purged
        years = [y for y in covered_years if y < year and by_year[y] <= eligible_coverage]
        if len(years) < 3:
            skipped_months.append({"month": f"{year:04}-{month:02}", "reason": "three_complete_training_years_unavailable"}); continue
        test = [d for d in valid if (d.year, d.month) == (year, month)]
        if not train:
            skipped_months.append({"month": f"{year:04}-{month:02}", "reason": "no_mature_training_labels"}); continue
        y = [valid[d]["y"] for d in train]
        reference = float(np.mean(y))
        outputs = {"N": [reference] * len(test)}
        fit = {"month": f"{year:04}-{month:02}", "cutoff_at": cutoff.isoformat(),
               "complete_training_years": years, "n_train": len(train),
               "purged_or_immature": len(prior) - len(train), "reference_mean": reference,
               "last_training_label_at": max(valid[d]["ready"] for d in train).isoformat(), "models": {}}
        for name in MODELS[1:]:
            outputs[name], fit["models"][name] = fit_ridge(
                [valid[d]["features"][name] for d in train], y,
                [valid[d]["features"][name] for d in test])
        fits.append(fit)
        for i, d in enumerate(test):
            item = valid[d]
            actual = item["y"] if item["ready"] is not None and item["ready"] <= evaluation else None
            predictions.append({"session": d.isoformat(), "decision_at": item["decision"].isoformat(),
                "predictions": {name: outputs[name][i] for name in MODELS}, "actual": actual,
                "event_dates": item["events"], "event_cohort": any(item["events"].values())})
    predictions.sort(key=lambda r: r["session"])
    start = predictions[0]["session"] if predictions else None
    test_calendar = [d.isoformat() for d in days if start and start <= d.isoformat() and d <= END and calendar[d] < evaluation]
    return {"study": "C1-M1", "evidence_kind": packet["evidence_kind"], "instrument": packet["instrument"],
            "evaluation_at": evaluation.isoformat(), "fits": fits, "predictions": predictions,
            "test_calendar": test_calendar, "excluded": excluded, "skipped_months": skipped_months,
            "exclusion_counts": dict(sorted(Counter(e["reason"] for e in excluded).items())),
            "source_qualification": "not_assessed_by_numerical_runner", "primary_cohort_admitted": False,
            "can_publish_forecast": False, "may_trade": False,
            "limitations": ["prepared_values_require_independent_source_and_measurement_qualification",
                "supplied_calendar_is_not_authenticated_here", "no_execution_or_policy_value_estimate"]}


def score_predictions(actual, predictions):
    y = np.asarray(actual, dtype=float)
    if y.ndim != 1 or set(predictions) != set(MODELS) or not np.all(np.isfinite(y)):
        raise ValueError("invalid_score_input")
    models = {}
    for name in MODELS:
        p = np.asarray(predictions[name], dtype=float)
        if p.shape != y.shape or not np.all(np.isfinite(p)):
            raise ValueError("unpaired_score_input")
        error = p - y
        models[name] = {"n": len(y), "mse": float(np.mean(error ** 2)) if len(y) else None,
                        "mae_secondary": float(np.mean(np.abs(error))) if len(y) else None}
    comparisons = {}
    for base in ("P", "PE"):
        b, m = models[base]["mse"], models["PEI"]["mse"]
        comparisons["PEI_vs_" + base] = {"absolute_mse_reduction": b - m if b is not None else None,
            "relative_mse_reduction": (b - m) / b if b is not None and b > 0 else None}
    return {"models": models, "comparisons": comparisons}


def block_intervals(squared_errors, eligible, *, block=63):
    """Paired circular calendar-position blocks. Missing rows keep their positions.

    Each replicate has the original chronological-panel length, truncating its
    final sampled block. All models and event masks share the exact same draws.
    Undefined replicates are disclosed, never turned into zero improvement.
    """
    e, mask = np.asarray(squared_errors, dtype=float), np.asarray(eligible, dtype=bool)
    if e.ndim != 2 or e.shape[1] != 4 or mask.shape != (len(e),) or block not in (21, 63, 126):
        raise ValueError("invalid_bootstrap_shape_or_block")
    if not np.all(np.isfinite(e)) or np.any(e < 0):
        raise ValueError("invalid_squared_errors")
    n = len(e)
    out = {"block": block, "draws": DRAWS, "seed": SEED, "rng": "PCG64",
           "calendar_positions": n, "eligible_positions": int(mask.sum()), "interval_level": .975}
    comparisons = {base: {"absolute": [], "relative": []} for base in (1, 2)}
    if n and mask.any():
        length = min(block, n)
        segments = math.ceil(n / length)
        lengths = np.full(segments, length, dtype=int)
        lengths[-1] = n - length * (segments - 1)
        values = np.column_stack([mask.astype(float), e * mask[:, None]])
        prefix = np.vstack([np.zeros((1, 5)), np.cumsum(np.tile(values, (2, 1)), axis=0)])
        rng = np.random.Generator(np.random.PCG64(SEED))
        for offset in range(0, DRAWS, 256):
            starts = rng.integers(0, n, size=(min(256, DRAWS - offset), segments))
            totals = (prefix[starts + lengths] - prefix[starts]).sum(axis=1)
            counts, errors = totals[:, 0], totals[:, 1:]
            for base in comparisons:
                delta = errors[:, base] - errors[:, 3]
                has_event = counts > 0
                comparisons[base]["absolute"].extend((delta[has_event] / counts[has_event]).tolist())
                positive_base = has_event & (errors[:, base] > 0)
                comparisons[base]["relative"].extend((delta[positive_base] / errors[positive_base, base]).tolist())
    for base, key in ((1, "PEI_vs_P"), (2, "PEI_vs_PE")):
        out[key] = {}
        for metric in ("absolute", "relative"):
            values = comparisons[base][metric]
            out[key][metric + "_valid_draws"] = len(values)
            out[key][metric + "_interval"] = np.quantile(values, [.0125, .9875]).tolist() if values else None
    return out


def summarize(report):
    """Descriptive candidate scores and locked uncertainty checks; never promotion."""
    rows = [r for r in report["predictions"] if r["actual"] is not None]
    def score(group):
        return score_predictions([r["actual"] for r in group], {k: [r["predictions"][k] for r in group] for k in MODELS})
    event_rows = [r for r in rows if r["event_cohort"]]
    counts = {key: len({d for r in event_rows for d in r["event_dates"][key]}) for key in EVENTS}
    positions = {d: i for i, d in enumerate(report["test_calendar"])}
    errors = np.zeros((len(positions), 4)); mask = np.zeros(len(positions), dtype=bool)
    for r in event_rows:
        i = positions[r["session"]]; mask[i] = True
        errors[i] = [(r["predictions"][k] - r["actual"]) ** 2 for k in MODELS]
    intervals = {str(block): block_intervals(errors, mask, block=block) for block in (63, 21, 126)}
    event_score = score(event_rows)
    improvement = event_score["comparisons"]["PEI_vs_P"]["relative_mse_reduction"]
    floors = all(counts[k] >= FLOORS[k] for k in EVENTS)
    intervals_positive = all(intervals["63"][k][m + "_valid_draws"] == DRAWS
        and intervals["63"][k][m + "_interval"][0] > 0
        for k in ("PEI_vs_P", "PEI_vs_PE") for m in ("absolute", "relative"))
    years = sorted({r["session"][:4] for r in event_rows})
    return {"full": score(rows), "events": event_score, "non_events": score([r for r in rows if not r["event_cohort"]]),
            "distinct_event_dates": counts, "event_count_floors": FLOORS,
            "event_floors_met": floors, "paired_block_intervals": intervals,
            "event_scores_by_year": {year: score([r for r in event_rows if r["session"].startswith(year)]) for year in years},
            "leave_one_year_out_score_influence": {year: score([r for r in event_rows if not r["session"].startswith(year)]) for year in years},
            "numerical_hurdle_conditions_met": bool(floors and improvement is not None and improvement >= .05 and intervals_positive),
            "promotion_permitted": False, "reason": "source_admission_independent_review_and_prospective_evidence_not_granted",
            "not_implemented": ["risk_strata_diagnostics", "secondary_1_3_10_session_views", "cross_instrument_report_composition"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--evaluation-at", required=True)
    args = parser.parse_args()
    path = Path(args.input)
    if path.stat().st_size > 32 * 1024 * 1024:
        parser.error("prepared research input exceeds 32 MiB")
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
        result = walk_forward(packet, args.evaluation_at)
        result["summary"] = summarize(result)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
    except (ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
