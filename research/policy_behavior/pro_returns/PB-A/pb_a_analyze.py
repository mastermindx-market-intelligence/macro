#!/usr/bin/env python3
"""PB-A retrospective research pilot. Stdlib only; never a production consumer.

forecast reads only the three frozen decision/design inputs and this script.
score verifies that freeze BEFORE loading any outcome source. Market results
are daily descriptive drifts; all market predictions abstain.
"""
import argparse
import calendar
import csv
import hashlib
import itertools
import json
import math
from bisect import bisect_right
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
CLASSES = ("DOWN", "HOLD", "UP")
MODELS = ("M0", "M1", "M2", "C0", "C1")
POLICY_TARGETS = ("fed_target_midpoint_net_direction", "first_subsequent_rate_change_within_horizon")
MARKET_SERIES = {"ust_2y": "DGS2", "ust_10y": "DGS10", "real_10y": "DFII10", "breakeven_10y": "T10YIE"}
GAP_TARGETS = ("policy_surprise_vs_pre_cut_pricing", "DXY", "growth_expectations", "inflation_expectations", "strategic_sector_relative")
FEATURE_KEYS = {"rhetoric_forward_direction", "has_new_rate_decision", "rate_decision_direction", "decided_target_upper_pct"}
ROW_KEYS = {"episode_id", "event_date", "decision_cut_utc", "cohort", "regime", "split", "features", "feature_source_ids", "source_time_bounds", "known_rate_decision"}
EPS = 1e-9


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def read_json(path):
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_suffix(p.suffix + ".tmp")
    temp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(p)


def utc(s):
    x = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("Naive timestamp is forbidden: " + s)
    return x.astimezone(timezone.utc)


def finite_number(x, label):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError("Expected finite numeric " + label)
    return float(x)


def direction(delta):
    return "UP" if delta > EPS else "DOWN" if delta < -EPS else "HOLD"


def add_months(d, months):
    n = d.year * 12 + d.month - 1 + months
    y, m = divmod(n, 12)
    m += 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def horizon_date(cut, months):
    return add_months(utc(cut).astimezone(NY).date(), months)


def probabilities(signal, modal=0.6):
    if signal == "ABSTAIN":
        return None
    if signal not in CLASSES or not 1 / 3 < modal < 1:
        raise ValueError("Invalid direction/probability convention")
    return [modal if c == signal else (1 - modal) / 2 for c in CLASSES]


def predict(features):
    """Pure predictor: only four allowed decision-time scalar features enter."""
    if set(features) != FEATURE_KEYS:
        raise ValueError("Predictor feature whitelist violation: " + repr(sorted(set(features) ^ FEATURE_KEYS)))
    r = features["rhetoric_forward_direction"]
    a = features["rate_decision_direction"]
    new = features["has_new_rate_decision"]
    upper = features["decided_target_upper_pct"]
    if r not in (*CLASSES, "ABSTAIN") or a not in (*CLASSES, "NOT_RATE") or type(new) is not bool:
        raise ValueError("Invalid feature codes/types")
    if new and a == "NOT_RATE" or not new and a != "NOT_RATE":
        raise ValueError("New-rate-decision flag and direction disagree")
    if upper is not None:
        upper = finite_number(upper, "decided_target_upper_pct")
    if new and upper is None:
        raise ValueError("New rate decision needs decided upper bound")
    inverse = {"UP": "DOWN", "DOWN": "UP"}.get(r, "ABSTAIN")
    persistence = a if new else "ABSTAIN"
    constrained = "HOLD" if new and a == "DOWN" and abs(upper - 0.25) <= EPS else persistence
    return {"M0": r, "M1": inverse, "M2": constrained, "C0": "HOLD", "C1": persistence}


def validate_episode(row, protocol):
    if set(row) != ROW_KEYS:
        raise ValueError("Decision row key whitelist violation for " + str(row.get("episode_id")) + ": " + repr(sorted(set(row) ^ ROW_KEYS)))
    cut = utc(row["decision_cut_utc"])
    event = date.fromisoformat(row["event_date"])
    if event > cut.astimezone(NY).date():
        raise ValueError("Event date after cut")
    if row["cohort"] not in ("PRIMARY", "ADVERSARIAL_CHALLENGE"):
        raise ValueError("Unknown cohort")
    expected_split = "DEVELOPMENT" if event < date(2023, 1, 1) else "CHRONOLOGICAL_REPORT"
    if row["split"] != expected_split:
        raise ValueError("Incorrect chronological split")
    matching = [r["id"] for r in protocol["regimes"] if date.fromisoformat(r["start"]) <= event <= date.fromisoformat(r["end"])]
    if matching != [row["regime"]]:
        raise ValueError("Incorrect historical regime")
    if row["cohort"] == "PRIMARY":
        admitted = [s.split(":")[0] for s in protocol["selected_event_dates"]]
        if row["event_date"] not in admitted:
            raise ValueError("Primary episode outside fixed selection")
    bounds = row["source_time_bounds"]
    by_id = {}
    for bound in bounds:
        if set(bound) != {"source_id", "public_time_upper_bound_utc", "role"}:
            raise ValueError("Source bound shape violation")
        if utc(bound["public_time_upper_bound_utc"]) > cut:
            raise ValueError("Source after decision cut: " + bound["source_id"])
        by_id[bound["source_id"]] = bound
    if not row["feature_source_ids"] or not set(row["feature_source_ids"]) <= set(by_id):
        raise ValueError("Missing feature source bounds")
    known = row["known_rate_decision"]
    if row["features"]["has_new_rate_decision"] and known is None:
        raise ValueError("Focal rate decision needs known decided anchor")
    if known is not None:
        if set(known) != {"lower_pct", "upper_pct", "decision_utc", "effective_date", "status"}:
            raise ValueError("Known decision shape violation")
        lo = finite_number(known["lower_pct"], "lower_pct")
        hi = finite_number(known["upper_pct"], "upper_pct")
        if lo > hi or utc(known["decision_utc"]) > cut or known["status"] != "KNOWN_DECIDED":
            raise ValueError("Invalid known decided anchor")
        if known["effective_date"] is not None:
            date.fromisoformat(known["effective_date"])
        if row["features"]["has_new_rate_decision"] and abs(hi - row["features"]["decided_target_upper_pct"]) > EPS:
            raise ValueError("Known decision and feature upper bound disagree")
    return predict(row["features"])


def make_forecasts(decisions, protocol, clarifications):
    """No paths, callbacks, outcome histories or full casebook are accepted."""
    if set(decisions) != {"meta", "episodes"}:
        raise ValueError("Decision input top-level whitelist violation")
    if protocol["primary_target"]["classes"] != list(CLASSES):
        raise ValueError("Frozen class order differs")
    if protocol["primary_target"]["horizons_calendar_months"] != [1, 3, 6]:
        raise ValueError("Frozen horizons differ")
    if abs(protocol["probability_convention"]["modal_probability"] - 0.6) > EPS:
        raise ValueError("Frozen modal probability differs")
    if clarifications.get("protocol_changed") is not False:
        raise ValueError("Clarifications change frozen protocol")
    rows, seen = [], set()
    for row in decisions["episodes"]:
        eid = row["episode_id"]
        if eid in seen:
            raise ValueError("Duplicate episode ID: " + eid)
        seen.add(eid)
        signs = validate_episode(row, protocol)
        item = {k: row[k] for k in ROW_KEYS if k != "features"}
        item["decision_features"] = dict(row["features"])
        item["forecasts"] = {}
        for months in (1, 3, 6):
            item["forecasts"][str(months)] = {
                "horizon_date_ny": horizon_date(row["decision_cut_utc"], months).isoformat(),
                "horizon_extrapolation_assumption": "Identical coded direction extrapolated to all horizons; not an official promise for these calendar endpoints.",
                "policy_targets": {target: {m: {"direction": signs[m], "probabilities_down_hold_up": probabilities(signs[m]), "abstain": signs[m] == "ABSTAIN"} for m in MODELS} for target in POLICY_TARGETS},
                "market_targets": {t: {m: {"direction": "ABSTAIN", "probabilities": None, "abstain": True} for m in ("M0", "M1", "M2")} for t in (*MARKET_SERIES, *GAP_TARGETS)},
            }
        item["C0_condition"] = "HOLD comparator only scoreable if public known rate anchor is available; anchor reconstructed only in outcome join for non-rate episodes."
        rows.append(item)
    return {"schema": "mastermind.pb_a_forecasts.v1", "class_order": list(CLASSES), "meta": decisions["meta"], "episodes": rows, "outcome_access": "NONE", "authority": "RESEARCH_ONLY", "model_scope": "Minimal persistence plus conventional operating floor; no private-motive features."}


def design_paths(args):
    return {"decisions": Path(args.decisions), "protocol": Path(args.protocol), "clarifications": Path(args.clarifications), "code": Path(__file__).resolve()}


def prepare_payload(args):
    paths = design_paths(args)
    hashes = {key: digest(path) for key, path in paths.items()}
    result = make_forecasts(read_json(paths["decisions"]), read_json(paths["protocol"]), read_json(paths["clarifications"]))
    return {"input_sha256": hashes, "forecast_payload": result}


def forecast_command(args):
    frozen = prepare_payload(args)
    frozen["freeze_content_sha256"] = object_digest(frozen)
    write_json(args.forecasts, frozen)
    print(json.dumps({"status": "FORECAST_FROZEN_NO_OUTCOMES_READ", "path": str(Path(args.forecasts).resolve()), "sha256": digest(args.forecasts), "episodes": len(frozen["forecast_payload"]["episodes"])}))


def verify_freeze(args):
    frozen = read_json(args.forecasts)
    if set(frozen) != {"input_sha256", "forecast_payload", "freeze_content_sha256"}:
        raise ValueError("Forecast artifact shape violation")
    unsigned = {k: frozen[k] for k in ("input_sha256", "forecast_payload")}
    if object_digest(unsigned) != frozen["freeze_content_sha256"]:
        raise ValueError("Frozen forecast content digest mismatch")
    rebuilt = prepare_payload(args)
    if canonical(unsigned) != canonical(rebuilt):
        raise ValueError("Frozen inputs, code hashes or predictions changed; scoring refused")
    return frozen


def read_series(path, series_id):
    result = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or series_id not in reader.fieldnames:
            raise ValueError("Series column missing: " + series_id)
        date_key = "observation_date" if "observation_date" in reader.fieldnames else "DATE" if "DATE" in reader.fieldnames else None
        if date_key is None:
            raise ValueError("Observation date column missing")
        for row in reader:
            d = date.fromisoformat(row[date_key])
            raw = row[series_id].strip()
            if raw in ("", ".", "NA", "NaN"):
                continue
            val = float(raw)
            if not math.isfinite(val) or d in result:
                raise ValueError("Invalid/duplicate series observation")
            result[d] = val
    return result


def validate_changes(data, lower, upper):
    if data.get("unverified_changes", 0):
        raise ValueError("Unverified policy changes: secondary target quarantined")
    changes = sorted(data["changes"], key=lambda c: utc(c["decision_utc"]))
    seen = set()
    for c in changes:
        clock, effective = utc(c["decision_utc"]), date.fromisoformat(c["effective_date"])
        if clock in seen or effective < clock.astimezone(NY).date():
            raise ValueError("Invalid decision/effective chronology")
        seen.add(clock)
        if effective not in lower or effective not in upper:
            raise ValueError("Missing exact effective-date policy observation")
        if abs(lower[effective] - c["lower"]) > EPS or abs(upper[effective] - c["upper"]) > EPS:
            raise ValueError("Decision/effective range disagreement")
        delta = ((c["lower"] + c["upper"]) - (c["previous_lower"] + c["previous_upper"])) / 2
        if direction(delta) == "HOLD" or abs(delta * 100 - c["change_bps"]) > EPS:
            raise ValueError("Change row is not reconciled nonzero change")
    if set(lower) != set(upper):
        raise ValueError("Policy lower/upper valid-observation dates differ")
    window = data.get("window")
    if window is not None:
        start, finish = map(date.fromisoformat, window)
        actual_change_dates = set()
        days = sorted(d for d in lower if start <= d <= finish)
        for previous, current in zip(days, days[1:]):
            if current != previous + timedelta(days=1):
                raise ValueError("Policy reconciliation window lacks seven-day daily observations")
            old = (lower[previous] + upper[previous]) / 2
            new = (lower[current] + upper[current]) / 2
            if direction(new - old) != "HOLD":
                actual_change_dates.add(current)
        declared_change_dates = {date.fromisoformat(c["effective_date"]) for c in changes if start <= date.fromisoformat(c["effective_date"]) <= finish}
        if actual_change_dates != declared_change_dates:
            raise ValueError("Effective CSV changes and public decision-change ledger do not reconcile")
    return changes


def known_anchor(row, changes_data):
    cut = utc(row["decision_cut_utc"])
    initial = changes_data.get("initial_observation")
    candidate = None
    if initial and date.fromisoformat(initial["date"]) <= cut.astimezone(NY).date():
        candidate = {"lower_pct": initial["lower"], "upper_pct": initial["upper"], "decision_utc": None, "effective_date": initial["date"], "provenance": "LEFT_CENSORED_INITIAL_PUBLIC_POLICY_LEVEL"}
    prior = [c for c in changes_data["changes"] if utc(c["decision_utc"]) <= cut]
    if prior:
        latest = max(prior, key=lambda c: utc(c["decision_utc"]))
        candidate = {"lower_pct": latest["lower"], "upper_pct": latest["upper"], "decision_utc": latest["decision_utc"], "effective_date": latest["effective_date"], "provenance": "LATEST_PUBLICLY_DECIDED_CHANGE"}
    declared = row["known_rate_decision"]
    if declared is not None:
        if candidate is not None and (abs(candidate["lower_pct"] - declared["lower_pct"]) > EPS or abs(candidate["upper_pct"] - declared["upper_pct"]) > EPS):
            raise ValueError("Known declared anchor disagrees with latest public decision: " + row["episode_id"])
        candidate = dict(declared, provenance="FROZEN_KNOWN_DECIDED_FOCAL_TARGET")
    if candidate is None:
        return None
    candidate["midpoint_pct"] = (candidate["lower_pct"] + candidate["upper_pct"]) / 2
    return candidate


def policy_outcome(row, months, changes_data, lower, upper):
    end = horizon_date(row["decision_cut_utc"], months)
    anchor = known_anchor(row, changes_data)
    result = {"horizon_date_ny": end.isoformat(), "endpoint_semantics": "End of civil date America/New_York; effective daily target range", "anchor": anchor}
    if anchor is None or end not in lower or end not in upper:
        reason = "KNOWN_DECIDED_ANCHOR_UNAVAILABLE" if anchor is None else "EXACT_HORIZON_POLICY_DATE_UNAVAILABLE_NO_CARRY_FORWARD"
        result["targets"] = {t: {"status": "NOT_SCORED", "reason": reason} for t in POLICY_TARGETS}
        return result
    if lower[end] > upper[end]:
        raise ValueError("Invalid horizon range")
    endpoint = (lower[end] + upper[end]) / 2
    result["endpoint_range_pct"] = [lower[end], upper[end]]
    result["endpoint_midpoint_pct"] = endpoint
    result["targets"] = {POLICY_TARGETS[0]: {"status": "OBSERVED", "direction": direction(endpoint - anchor["midpoint_pct"]), "net_change_bps": (endpoint - anchor["midpoint_pct"]) * 100}}
    cut = utc(row["decision_cut_utc"])
    eligible = sorted([c for c in changes_data["changes"] if utc(c["decision_utc"]) > cut and date.fromisoformat(c["effective_date"]) <= end], key=lambda c: utc(c["decision_utc"]))
    first = eligible[0] if eligible else None
    ledger_window = changes_data.get("window")
    if ledger_window and not (date.fromisoformat(ledger_window[0]) <= cut.astimezone(NY).date() <= end <= date.fromisoformat(ledger_window[1])):
        result["targets"][POLICY_TARGETS[1]] = {"status": "NOT_SCORED", "reason": "DECISION_LEDGER_WINDOW_DOES_NOT_COVER_CUT_AND_HORIZON"}
    else:
        result["targets"][POLICY_TARGETS[1]] = {"status": "OBSERVED", "direction": direction(first["change_bps"]) if first else "HOLD", "first_change": first, "definition": "First publicly decided CHANGE strictly after cut and effective by horizon; known next-day change excluded."}
    return result


def latest_observation(series, boundary, strictly_before=False):
    keys = sorted(series)
    cutoff = boundary - timedelta(days=1) if strictly_before else boundary
    i = bisect_right(keys, cutoff) - 1
    if i < 0:
        return {"status": "NOT_OBSERVED", "reason": "NO_VALID_OBSERVATION"}
    d = keys[i]
    age = (boundary - d).days
    if age > 7:
        return {"status": "NOT_OBSERVED", "reason": "STALE_OVER_7_CALENDAR_DAYS", "observation_date": d.isoformat(), "staleness_calendar_days": age}
    return {"status": "OBSERVED", "observation_date": d.isoformat(), "value_percent": series[d], "staleness_calendar_days": age}


def market_outcomes(row, months, series):
    cut_day = utc(row["decision_cut_utc"]).astimezone(NY).date()
    end = horizon_date(row["decision_cut_utc"], months)
    result = {}
    for target, sid in MARKET_SERIES.items():
        data = series.get(sid)
        if data is None:
            result[target] = {"status": "NOT_OBSERVED", "reason": "SOURCE_SERIES_UNAVAILABLE", "series": sid}
            continue
        start = latest_observation(data, cut_day, strictly_before=True)
        finish = latest_observation(data, end)
        item = {"series": sid, "start": start, "endpoint": finish, "forecast_status_all_models": "ABSTAIN", "interpretation": "Descriptive daily drift, not intraday surprise, causal effect or abnormal return."}
        if start["status"] == finish["status"] == "OBSERVED":
            item.update(status="OBSERVED", drift_bps=(finish["value_percent"] - start["value_percent"]) * 100)
        else:
            item.update(status="NOT_OBSERVED", reason="MISSING_OR_STALE_ENDPOINT")
        result[target] = item
    parts = [result[t] for t in ("ust_10y", "real_10y", "breakeven_10y")]
    if all(x["status"] == "OBSERVED" for x in parts) and len({(x["start"]["observation_date"], x["endpoint"]["observation_date"]) for x in parts}) == 1:
        result["nominal_real_breakeven_decomposition"] = {"status": "OBSERVED", "rounding_residual_bps": parts[0]["drift_bps"] - parts[1]["drift_bps"] - parts[2]["drift_bps"], "note": "Breakeven is inflation compensation, not pure expected inflation; source rounding residual retained."}
    else:
        result["nominal_real_breakeven_decomposition"] = {"status": "NOT_OBSERVED", "reason": "MISSING_OR_UNSYNCHRONIZED_DATES"}
    for t in GAP_TARGETS:
        result[t] = {"status": "NOT_OBSERVED", "reason": "No frozen admissible target dataset/mapping; no DXY proxy, no pricing surprise or expectations substitution.", "forecast_status_all_models": "ABSTAIN"}
    return result


def scores(signal, truth, modal=0.6):
    vector = probabilities(signal, modal)
    if vector is None:
        return None
    label = CLASSES.index(truth)
    return {"accuracy": int(signal == truth), "brier": sum((p - int(i == label)) ** 2 for i, p in enumerate(vector)), "nll": -math.log(vector[label])}


def mean(values):
    return sum(values) / len(values) if values else None


def stats(rows, model, modal=0.6):
    vals = [scores(r["predictions"][model], r["truth"], modal) for r in rows]
    if any(v is None for v in vals):
        raise ValueError("ABSTAIN slipped into scoring intersection")
    return {"count": len(rows), "episode_ids": [r["episode_id"] for r in rows], "true_class_counts": {c: sum(r["truth"] == c for r in rows) for c in CLASSES}, "regime_counts": dict(sorted(Counter(r["regime"] for r in rows).items())), "direction_accuracy": mean([v["accuracy"] for v in vals]), "multiclass_brier_sum_squared_range_0_to_2": mean([v["brier"] for v in vals]), "negative_log_likelihood_natural_log": mean([v["nll"] for v in vals]), "reliability_modal_bucket": {"modal_probability": modal, "count": len(rows), "observed_modal_class_frequency": mean([v["accuracy"] for v in vals]), "calibration_slope": None, "slope_reason": "Fixed confidence has no fitted calibration slope."}}


def percentile(values, quantile):
    if not values:
        return None
    a = sorted(values)
    pos = (len(a) - 1) * quantile
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return a[lo] + (a[hi] - a[lo]) * (pos - lo)


def paired_delta(rows, left, right):
    a = [scores(r["predictions"][left], r["truth"]) for r in rows]
    b = [scores(r["predictions"][right], r["truth"]) for r in rows]
    return {k: mean([x[k] - y[k] for x, y in zip(a, b)]) for k in ("accuracy", "brier", "nll")}


def regime_uncertainty(rows, left, right):
    clusters = {k: [r for r in rows if r["regime"] == k] for k in sorted({r["regime"] for r in rows})}
    keys = list(clusters)
    draws = []
    if keys:
        for draw in itertools.product(keys, repeat=len(keys)):
            block = [r for k in draw for r in clusters[k]]
            draws.append(paired_delta(block, left, right))
    return {"paired_left_minus_right": paired_delta(rows, left, right), "interpretation": "Positive accuracy favors left; negative Brier/NLL favors left. Descriptive sensitivity only, no significance/generalization inference.", "regimes": keys, "K": len(keys), "exact_K_to_K_draw_count": len(draws), "central_95_percent_descriptive_intervals": {m: [percentile([d[m] for d in draws], 0.025), percentile([d[m] for d in draws], 0.975)] for m in ("accuracy", "brier", "nll")}, "leave_one_regime_out": {k: {"remaining_episode_ids": [r["episode_id"] for r in rows if r["regime"] != k], "delta": paired_delta([r for r in rows if r["regime"] != k], left, right)} for k in keys}, "limit": "Only up to four purposive historical clusters; overlapping horizons and dependence remain."}


def metric_group(candidates):
    valid = [r for r in candidates if r["status"] == "OBSERVED"]
    result = {"eligible_episode_ids": [r["episode_id"] for r in candidates], "observed_outcome_ids": [r["episode_id"] for r in valid], "not_scored_outcome_ids": [r["episode_id"] for r in candidates if r["status"] != "OBSERVED"], "own_coverage": {}, "pairwise_common_coverage": {}, "all_three_common_coverage": {}}
    for m in MODELS:
        common = [r for r in valid if r["predictions"][m] != "ABSTAIN"]
        item = stats(common, m)
        item.update(coverage=len(common) / len(valid) if valid else None, denominator="Episodes in this cohort/slice with observed target outcome", denominator_count=len(valid), input_episode_count=len(candidates), scored_input_coverage=len(common) / len(candidates) if candidates else None, abstentions=len(valid) - len(common), abstention_episode_ids=[r["episode_id"] for r in valid if r["predictions"][m] == "ABSTAIN"], all_input_abstention_ids=[r["episode_id"] for r in candidates if r["predictions"][m] == "ABSTAIN"])
        item["probability_sensitivity"] = {str(p): stats(common, m, p) for p in (0.4, 0.6, 0.8)}
        result["own_coverage"][m] = item
    intersections = [(a + "__" + b, (a, b), "pairwise_common_coverage") for a, b in itertools.combinations(MODELS, 2)] + [("M0__M1__M2", ("M0", "M1", "M2"), "all_three_common_coverage")]
    for label, models, key in intersections:
        common = [r for r in valid if all(r["predictions"][m] != "ABSTAIN" for m in models)]
        result[key][label] = {"intersection_episode_ids": [r["episode_id"] for r in common], "true_class_counts": {c: sum(r["truth"] == c for r in common) for c in CLASSES}, "regime_counts": dict(sorted(Counter(r["regime"] for r in common).items())), "coverage": len(common) / len(valid) if valid else None, "denominator_count": len(valid), "models": {m: stats(common, m) for m in models}, "probability_sensitivity": {str(p): {m: stats(common, m, p) for m in models} for p in (0.4, 0.6, 0.8)}, "paired_contrasts": {a + "__" + b: regime_uncertainty(common, a, b) for a, b in itertools.combinations(models, 2)}}
    return result


def build_metrics(forecast_rows, outcome_rows):
    outcomes = {r["episode_id"]: r for r in outcome_rows}
    cohorts = {}
    for cohort in ("PRIMARY", "ADVERSARIAL_CHALLENGE"):
        selected = [r for r in forecast_rows if r["cohort"] == cohort]
        cohort_result = {"episode_ids": [r["episode_id"] for r in selected], "pooled_with_other_cohort": False, "targets": {}}
        for target in POLICY_TARGETS:
            horizon_results = {}
            for months in (1, 3, 6):
                candidates = []
                for row in selected:
                    observed = outcomes[row["episode_id"]]["horizons"][str(months)]["policy"]["targets"][target]
                    candidates.append({"episode_id": row["episode_id"], "regime": row["regime"], "split": row["split"], "status": observed["status"], "truth": observed.get("direction"), "predictions": {m: row["forecasts"][str(months)]["policy_targets"][target][m]["direction"] for m in MODELS}})
                groups = {"ALL": metric_group(candidates)}
                for split in ("DEVELOPMENT", "CHRONOLOGICAL_REPORT"):
                    groups[split] = metric_group([r for r in candidates if r["split"] == split])
                for regime in sorted({r["regime"] for r in selected}):
                    groups["REGIME:" + regime] = metric_group([r for r in candidates if r["regime"] == regime])
                horizon_results[str(months)] = groups
            cohort_result["targets"][target] = horizon_results
        cohort_result["market_targets"] = {t: {str(h): {"observed_daily_drift_ids": [r["episode_id"] for r in selected if outcomes[r["episode_id"]]["horizons"][str(h)]["market"][t]["status"] == "OBSERVED"], "model_forecast_coverage": {m: 0 for m in ("M0", "M1", "M2")}, "scored_forecasts": 0, "interpretation": "Observed daily drifts only; no prediction mapping or proxy."} for h in (1, 3, 6)} for t in (*MARKET_SERIES, *GAP_TARGETS)}
        cohorts[cohort] = cohort_result
    return cohorts


def score_command(args):
    frozen = verify_freeze(args)  # Guard precedes every outcome read.
    root = Path(args.outcome_dir)
    paths = {sid: root / (sid + ".csv") for sid in ("DFEDTARU", "DFEDTARL", *MARKET_SERIES.values())}
    paths["policy_decision_changes"] = root / "policy_decision_changes.json"
    for sid in ("DFEDTARU", "DFEDTARL", "policy_decision_changes"):
        if not paths[sid].is_file():
            raise ValueError("Required policy source absent: " + str(paths[sid]))
    lower = read_series(paths["DFEDTARL"], "DFEDTARL")
    upper = read_series(paths["DFEDTARU"], "DFEDTARU")
    changes_data = read_json(paths["policy_decision_changes"])
    changes_data["changes"] = validate_changes(changes_data, lower, upper)
    source_hashes = {sid: digest(p) if p.is_file() else None for sid, p in paths.items()}
    # Reconcile advertised policy CSV identities without binding to original directories.
    for source in changes_data.get("source_csvs", []):
        sid = source.get("series_id")
        if sid in source_hashes and source.get("sha256") and source_hashes[sid] != source["sha256"]:
            raise ValueError("Decision-change source CSV hash disagreement: " + sid)
    series = {sid: read_series(paths[sid], sid) if paths[sid].is_file() else None for sid in MARKET_SERIES.values()}
    rows = frozen["forecast_payload"]["episodes"]
    results = []
    for row in rows:
        results.append({"episode_id": row["episode_id"], "cohort": row["cohort"], "regime": row["regime"], "split": row["split"], "horizons": {str(h): {"policy": policy_outcome(row, h, changes_data, lower, upper), "market": market_outcomes(row, h, series)} for h in (1, 3, 6)}})
    outcome_artifact = {"schema": "mastermind.pb_a_outcomes.v1", "authority": "RESEARCH_ONLY_OUTCOME_JOIN", "forecast_freeze_file_sha256": digest(args.forecasts), "forecast_freeze_content_sha256": frozen["freeze_content_sha256"], "input_sha256": frozen["input_sha256"], "outcome_source_sha256": source_hashes, "episodes": results, "no_outcome_to_predictor": True}
    pilot = {"schema": "mastermind.pb_a_baseline_pilot.v1", "authority": "RESEARCH_ONLY", "study_kind": "RETROSPECTIVE_FEASIBILITY_PILOT_NOT_PROSPECTIVE_VALIDATION", "forecast_freeze_file_sha256": digest(args.forecasts), "input_sha256": frozen["input_sha256"], "outcome_source_sha256": source_hashes, "outcomes_content_sha256": object_digest(outcome_artifact), "cohorts": build_metrics(rows, results), "metric_dependence": "With fixed modal p and equal other probabilities, accuracy, Brier and NLL are algebraically linked; sensitivity0.4/0.6/0.8 is design sensitivity, not independent skill validation.", "calibration_slope": None, "limitations": ["Purposive sample; chronology is reporting, not unseen validation.", "At most four regime clusters, exact K^K resampling is descriptive, with overlapping horizons.", "No horizon pooling or cross-intersection model league table.", "All market forecasts abstain; nominal/real/breakeven drifts are descriptive only.", "Policy anchors include known decided changes even before next-day implementation.", "C0 is eligible only where public anchor reconstructed; C1 isolates conventional-floor assumption."]}
    write_json(args.outcomes, outcome_artifact)
    write_json(args.pilot, pilot)
    print(json.dumps({"status": "SCORED_FROZEN_FORECAST", "outcomes": str(Path(args.outcomes).resolve()), "pilot": str(Path(args.pilot).resolve()), "outcome_sha256": digest(args.outcomes), "pilot_sha256": digest(args.pilot)}))


def self_test_command(_args):
    checks = []
    f = {"rhetoric_forward_direction": "HOLD", "has_new_rate_decision": False, "rate_decision_direction": "NOT_RATE", "decided_target_upper_pct": None}
    assert predict(f)["M1"] == "ABSTAIN"
    assert predict(f)["M2"] == predict(f)["C1"] == "ABSTAIN"
    checks += ["M1 HOLD abstains", "Non-rate M2/C1 abstain"]
    floor = dict(f, has_new_rate_decision=True, rate_decision_direction="DOWN", decided_target_upper_pct=0.25)
    assert predict(floor)["M2"] == "HOLD" and predict(floor)["C1"] == "DOWN"
    checks.append("Conventional-floor M2 differs from action-only C1")
    try:
        predict(dict(f, outcome_direction="UP"))
        raise AssertionError("Outcome key accepted")
    except ValueError:
        checks.append("Strict predictor whitelist rejects outcome injection")
    assert add_months(date(2020, 1, 31), 1) == date(2020, 2, 29)
    assert horizon_date("2024-02-01T00:30:00Z", 1) == date(2024, 2, 29)
    checks.append("NY civil-date month arithmetic/leap clamp")
    row = {"episode_id": "SYNTHETIC", "event_date": "2020-03-15", "decision_cut_utc": "2020-03-15T21:01:00Z", "cohort": "PRIMARY", "regime": "2020_PANDEMIC", "split": "DEVELOPMENT", "features": floor, "feature_source_ids": ["x"], "source_time_bounds": [{"source_id": "x", "public_time_upper_bound_utc": "2020-03-15T21:00:00Z", "role": "DECISION_TIME_FACT"}], "known_rate_decision": {"lower_pct": 0, "upper_pct": 0.25, "decision_utc": "2020-03-15T21:00:00Z", "effective_date": "2020-03-16", "status": "KNOWN_DECIDED"}}
    protocol = {"regimes": [{"id": "2020_PANDEMIC", "start": "2020-01-01", "end": "2020-12-31"}], "selected_event_dates": ["2020-03-15"], "primary_target": {"classes": list(CLASSES), "horizons_calendar_months": [1, 3, 6]}, "probability_convention": {"modal_probability": 0.6}}
    validate_episode(row, protocol)
    future = json.loads(json.dumps(row))
    future["source_time_bounds"][0]["public_time_upper_bound_utc"] = "2020-03-15T21:02:00Z"
    try:
        validate_episode(future, protocol)
        raise AssertionError("Post-cut source accepted")
    except ValueError:
        checks.append("Source after cut rejected")
    changes = {"changes": [{"decision_utc": "2020-03-15T21:00:00Z", "effective_date": "2020-03-16", "lower": 0, "upper": 0.25, "change_bps": -100}], "initial_observation": {"date": "2020-01-01", "lower": 1, "upper": 1.25}}
    rates_lo, rates_hi = {date(2020, 4, 15): 0}, {date(2020, 4, 15): 0.25}
    observed = policy_outcome(row, 1, changes, rates_lo, rates_hi)
    assert all(x["direction"] == "HOLD" for x in observed["targets"].values())
    checks.append("Known next-day cut not credited to net or first-change forecast")
    reversed_changes = json.loads(json.dumps(changes))
    reversed_changes["changes"] += [
        {"decision_utc": "2020-03-20T18:00:00Z", "effective_date": "2020-03-21", "lower": 0.25, "upper": 0.5, "change_bps": 25},
        {"decision_utc": "2020-04-01T18:00:00Z", "effective_date": "2020-04-02", "lower": 0, "upper": 0.25, "change_bps": -25},
    ]
    reversed_outcome = policy_outcome(row, 1, reversed_changes, rates_lo, rates_hi)
    assert reversed_outcome["targets"][POLICY_TARGETS[0]]["direction"] == "HOLD"
    assert reversed_outcome["targets"][POLICY_TARGETS[1]]["direction"] == "UP"
    checks.append("First subsequent change distinct from net movement after reversal")
    missing = policy_outcome(row, 3, changes, rates_lo, rates_hi)
    assert all(x["status"] == "NOT_SCORED" for x in missing["targets"].values())
    checks.append("Missing exact horizon quarantines instead of carry/zero")
    decisions = {"meta": {}, "episodes": [row]}
    before = make_forecasts(decisions, protocol, {"protocol_changed": False})
    changes["changes"][0]["change_bps"] = 999
    after = make_forecasts(decisions, protocol, {"protocol_changed": False})
    assert canonical(before) == canonical(after)
    assert make_forecasts.__code__.co_argcount == 3
    checks.append("Outcome mutation cannot affect forecast function; no outcome parameter/path")
    assert abs(scores("UP", "UP")["brier"] - 0.24) < EPS
    assert abs(scores("UP", "DOWN")["brier"] - 1.04) < EPS
    assert abs(sum(probabilities("UP")) - 1) < EPS
    checks.append("Unnormalized multiclass Brier and vector normalization")
    no_rate = dict(row, known_rate_decision=None, features=f)
    assert known_anchor(no_rate, changes)["upper_pct"] == 0.25
    checks.append("Non-rate anchor absorbs earlier publicly announced change")
    sample = [{"episode_id": str(i), "regime": "r" + str(i), "truth": "UP", "predictions": {"M0": "UP", "M2": "DOWN"}} for i in range(4)]
    assert regime_uncertainty(sample, "M0", "M2")["exact_K_to_K_draw_count"] == 256
    checks.append("Exact four-cluster4^4 enumeration")
    candidates = [
        {"episode_id": "A", "regime": "r1", "split": "DEVELOPMENT", "status": "OBSERVED", "truth": "UP", "predictions": {"M0": "UP", "M1": "DOWN", "M2": "UP", "C0": "HOLD", "C1": "UP"}},
        {"episode_id": "B", "regime": "r2", "split": "CHRONOLOGICAL_REPORT", "status": "OBSERVED", "truth": "HOLD", "predictions": {"M0": "ABSTAIN", "M1": "ABSTAIN", "M2": "HOLD", "C0": "HOLD", "C1": "HOLD"}},
    ]
    groups = metric_group(candidates)
    assert groups["own_coverage"]["M0"]["episode_ids"] == ["A"]
    assert groups["own_coverage"]["M2"]["episode_ids"] == ["A", "B"]
    assert groups["all_three_common_coverage"]["M0__M1__M2"]["intersection_episode_ids"] == ["A"]
    assert groups["pairwise_common_coverage"]["M0__M2"]["models"]["M2"]["count"] == 1
    assert groups["own_coverage"]["M0"]["abstentions"] == 1
    checks.append("Own, pairwise and all-three exact coverage intersections")
    s = {date(2020, 1, 1): 1.0, date(2020, 1, 2): 2.0}
    assert latest_observation(s, date(2020, 1, 2), True)["value_percent"] == 1.0
    assert latest_observation(s, date(2020, 1, 10))["status"] == "NOT_OBSERVED"
    checks.append("Market baseline strictly pre-cut civil date;7-day staleness")
    print(json.dumps({"status": "SYNTHETIC_SELF_CHECKS_PASS", "count": len(checks), "checks": checks, "real_cases_run": False}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("forecast", "score"):
        p = sub.add_parser(cmd)
        p.add_argument("--decisions", default=str(BASE / "PB_A_DECISION_INPUTS.json"))
        p.add_argument("--protocol", default=str(BASE / "PB_A_PROTOCOL_FREEZE.json"))
        p.add_argument("--clarifications", default=str(BASE / "PB_A_IMPLEMENTATION_CLARIFICATIONS.json"))
        p.add_argument("--forecasts", default=str(BASE / "PB_A_FORECAST_FREEZE.json"))
        if cmd == "score":
            p.add_argument("--outcome-dir", default=str(BASE / "outcome_inputs"))
            p.add_argument("--outcomes", default=str(BASE / "PB_A_OUTCOMES.json"))
            p.add_argument("--pilot", default=str(BASE / "PB_A_BASELINE_PILOT.json"))
        p.set_defaults(func=forecast_command if cmd == "forecast" else score_command)
    p = sub.add_parser("self-test")
    p.set_defaults(func=self_test_command)
    args = parser.parse_args()
    try:
        args.func(args)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(2, "PB-A validation failed: " + str(exc) + "\n")


if __name__ == "__main__":
    main()
