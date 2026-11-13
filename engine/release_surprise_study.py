"""MRI study adapter over canonical shared statistics, not a promotion owner.

Requires authoritative session-close instants and adjusted-close price receipts.
A vendor summary table is not an input. Outcomes and forecasts are separate:
chronological fits consume only matured labels known before the decision cut.
All return quantities are percentage points, not decimal returns.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from engine.challenger_spa_comparison import stationary_bootstrap_indices
from engine.desk_placebo import holm_adjust
from engine.grading_stats import wilson_ci
from engine.release_surprise_confirmation import (
    EvidenceError, PAIR_DEFINITIONS, authority, digest, finite, instant, iso, valid_authority,
)

SCHEMA = "release_surprise_study.v1"
QUADRANTS = ("cpi_cold_ppi_cold", "cpi_hot_ppi_hot", "cpi_hot_ppi_cold", "cpi_cold_ppi_hot")
CONDITIONS = (*QUADRANTS, "agreement", "disagreement", "agreement_vs_disagreement")
DEFAULT_HORIZONS = (1, 5, 10, 20)
DEFAULT_SYMBOLS = ("SPY", "QQQ", "IWM")
FEATURES = ("cpi_surprise", "ppi_surprise", "agreement")


def validate_sessions(session_closes: Sequence[str]) -> list:
    sessions = [instant(value) for value in session_closes]
    if len(sessions) < 2 or sessions != sorted(set(sessions)):
        raise EvidenceError("session_closes_must_be_strictly_increasing")
    return sessions


def _prices(bars: Iterable[Mapping[str, Any]], sessions: list) -> dict:
    allowed = set(sessions)
    result: dict[tuple, dict] = {}
    for bar in bars:
        if not isinstance(bar, Mapping):
            raise EvidenceError("price_bar_not_object")
        symbol = bar.get("symbol")
        if not isinstance(symbol, str) or not symbol or len(symbol) > 24:
            raise EvidenceError("invalid_symbol")
        close_at, known_at = instant(bar.get("close_at")), instant(bar.get("known_at"))
        if close_at not in allowed or known_at < close_at:
            raise EvidenceError("price_clock_or_calendar_mismatch")
        if bar.get("basis") != "total_return_adjusted_close":
            raise EvidenceError("unqualified_price_adjustment_basis")
        value = finite(bar.get("close"))
        if value <= 0:
            raise EvidenceError("nonpositive_price")
        if not isinstance(bar.get("source_ref"), str) or not bar["source_ref"]:
            raise EvidenceError("price_source_ref_missing")
        key = (symbol, close_at)
        if key in result:
            raise EvidenceError("duplicate_price_bar")
        result[key] = {**bar, "close": value, "close_instant": close_at, "known_instant": known_at}
    return result


def forward_outcomes(
    events: Iterable[dict], bars: Iterable[dict], session_closes: Sequence[str], *,
    symbols: Sequence[str] = DEFAULT_SYMBOLS, horizons: Sequence[int] = DEFAULT_HORIZONS,
    asof: str, round_trip_cost_bps: float = 0.0,
) -> dict:
    """First close strictly after known_at, then EXACT exchange-session horizon.

    The supplied calendar must cover the entry and exit and have a named source
    in the caller's dataset manifest. Missing bars never compress the horizon.
    Cost=0 is a declared gross scenario, not a claim that implementation is free.
    """
    cutoff = instant(asof)
    sessions = validate_sessions(session_closes)
    prices = _prices(bars, sessions)
    if len(set(symbols)) != len(symbols) or not symbols:
        raise EvidenceError("invalid_symbol_family")
    if not horizons or len(set(horizons)) != len(horizons) or any(type(h) is not int or not 1 <= h <= 252 for h in horizons):
        raise EvidenceError("invalid_horizon_family")
    cost = finite(round_trip_cost_bps)
    if not 0 <= cost <= 1000:
        raise EvidenceError("invalid_cost_scenario")
    records, exclusions = [], Counter()
    seen = set()
    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id or event_id in seen:
            raise EvidenceError("event_identity_missing_or_duplicate")
        seen.add(event_id)
        known = instant(event.get("known_at"))
        if known > cutoff:
            exclusions["signal_not_known_at_evaluation_cut"] += len(symbols) * len(horizons)
            continue
        # A calendar beginning after the signal cannot prove the FIRST session.
        if known < sessions[0]:
            exclusions["calendar_left_coverage_unknown"] += len(symbols) * len(horizons)
            continue
        entry = bisect_right(sessions, known)
        for symbol in symbols:
            for horizon in horizons:
                exit_index = entry + horizon
                if exit_index >= len(sessions):
                    exclusions["calendar_right_coverage_missing"] += 1
                    continue
                if sessions[exit_index] > cutoff:
                    exclusions["outcome_not_matured"] += 1
                    continue
                window = [prices.get((symbol, stamp)) for stamp in sessions[entry:exit_index + 1]]
                if any(bar is None for bar in window):
                    exclusions["missing_session_price"] += 1
                    continue
                outcome_known = max(bar["known_instant"] for bar in window)
                if outcome_known > cutoff:
                    exclusions["outcome_not_known_at_evaluation_cut"] += 1
                    continue
                values = np.array([bar["close"] for bar in window], dtype=float)
                gross = float((values[-1] / values[0] - 1) * 100)
                path = values / values[0]
                max_drawdown = float(np.min(values / np.maximum.accumulate(values) - 1) * 100)
                records.append({
                    "event_id": event_id, "pair_id": event.get("pair_id", event.get("release")),
                    "period": event["period"], "symbol": symbol, "horizon": horizon,
                    "signal_known_at": iso(known), "entry_at": iso(sessions[entry]),
                    "exit_at": iso(sessions[exit_index]), "outcome_known_at": iso(outcome_known),
                    "return_pct": gross, "net_return_pct": gross - cost / 100,
                    "round_trip_cost_bps": cost, "max_drawdown_pct": max_drawdown,
                    "entry_adverse_close_pct": float(min(0.0, (np.min(path) - 1) * 100)),
                    "risk_basis": "session_closes_only_not_intraday",
                    "quadrant": event.get("quadrant", "not_a_pair"), "agreement": event.get("agreement"),
                    "cpi_surprise": event.get("cpi_surprise"), "ppi_surprise": event.get("ppi_surprise"),
                    "price_source_refs": sorted({bar["source_ref"] for bar in window}),
                    "regime_features": dict(event.get("regime_features", {})),
                    "regime_source_refs": dict(event.get("regime_source_refs", {})),
                })
    return {"rows": records, "exclusions": dict(sorted(exclusions.items())),
            "entry_rule": "first_session_close_strictly_after_signal_known_at",
            "asof": iso(cutoff), "price_basis": "total_return_adjusted_close"}


def _mask(rows: list[dict], condition: str) -> np.ndarray:
    if condition == "agreement":
        return np.array([r.get("agreement") is True for r in rows], dtype=bool)
    if condition == "disagreement":
        return np.array([r.get("agreement") is False for r in rows], dtype=bool)
    return np.array([r.get("quadrant") == condition for r in rows], dtype=bool)


def _describe(values: np.ndarray, rows: list[dict]) -> dict:
    n = len(values)
    if not n:
        return {"n": 0, "mean_pct": None, "median_pct": None, "win_rate": None,
                "win_rate_interval_descriptive": None, "expected_shortfall_10_pct": None,
                "worst_pct": None, "mean_close_max_drawdown_pct": None}
    tail_n = max(1, int(np.ceil(n * 0.1)))
    wins = int(np.sum(values > 0))
    return {"n": n, "mean_pct": float(np.mean(values)), "median_pct": float(np.median(values)),
            "win_rate": wins / n, "win_rate_interval_descriptive": wilson_ci(wins, n),
            "win_rate_interval_basis": "Wilson_not_adjusted_for_time_dependence",
            "expected_shortfall_10_pct": float(np.mean(np.sort(values)[:tail_n])),
            "worst_pct": float(np.min(values)),
            "mean_close_max_drawdown_pct": float(np.mean([r["max_drawdown_pct"] for r in rows]))}


def evaluate_matrix(
    rows: Iterable[dict], *, symbols: Sequence[str] = DEFAULT_SYMBOLS,
    horizons: Sequence[int] = DEFAULT_HORIZONS, draws: int = 800, seed: int = 7,
    min_cell_n: int = 30, mean_block: float = 3.0,
) -> dict:
    """Predeclared complete family, shared time-block resampling and Holm control.

    Intervals are uncertainty about the estimated MEAN GAP, not prediction
    intervals. Bootstrap p-values are approximate centered-null diagnostics.
    Positive raw means and Wilson intervals are descriptive, never alpha tests.
    """
    if type(min_cell_n) is not int or min_cell_n < 2:
        raise EvidenceError("invalid_min_cell_n")
    if type(draws) is not int or not 50 <= draws <= 10_000 or not 1 <= finite(mean_block) <= 24:
        raise EvidenceError("invalid_bootstrap_configuration")
    grouped: dict[tuple, list] = defaultdict(list)
    for row in rows:
        finite(row.get("net_return_pct"))
        grouped[(row["pair_id"], row["symbol"], row["horizon"])].append(row)
    months = []
    for group in grouped.values():
        for row in group:
            try:
                year, month = map(int, row["period"].split("-"))
                if not 1 <= month <= 12 or row["period"] != f"{year:04d}-{month:02d}":
                    raise ValueError
                months.append(year * 12 + month - 1)
            except (TypeError, ValueError, KeyError) as exc:
                raise EvidenceError("invalid_macro_calendar_period") from exc
    if months and max(months) - min(months) > 1200:
        raise EvidenceError("macro_calendar_coverage_out_of_bounds")
    # One complete monthly clock is shared across assets and variants. Missing
    # months remain gaps rather than compressing a different time axis per ETF.
    timeline = [f"{m // 12:04d}-{m % 12 + 1:02d}" for m in range(min(months), max(months) + 1)] if months else []
    shared_indices = stationary_bootstrap_indices(len(timeline), draws, min(mean_block, max(1, len(timeline) / 2)), np.random.default_rng(seed)) if len(timeline) >= 2 else None
    reports, pvalues = [], {}
    for pair_id, _, _ in PAIR_DEFINITIONS:
        for symbol in symbols:
            for horizon in horizons:
                group = sorted(grouped.get((pair_id, symbol, horizon), []), key=lambda r: (instant(r["signal_known_at"]), r["period"]))
                if len({r["period"] for r in group}) != len(group):
                    raise EvidenceError("duplicate_macro_period_in_cell")
                observed_n = len(group)
                by_period = {r["period"]: r for r in group}
                group = [by_period.get(period, {}) for period in timeline]
                values = np.array([r.get("net_return_pct", np.nan) for r in group], dtype=float)
                present = np.isfinite(values)
                idx = shared_indices if observed_n >= 2 * min_cell_n else None
                for condition in CONDITIONS:
                    key = f"{pair_id}:{symbol}:{horizon}:{condition}"
                    selected = _mask(group, "agreement" if condition == "agreement_vs_disagreement" else condition) & present
                    reference = (_mask(group, "disagreement") & present) if condition == "agreement_vs_disagreement" else present
                    selected_rows = [r for r, keep in zip(group, selected) if keep]
                    report = {"hypothesis_id": key, "pair_id": pair_id, "symbol": symbol, "horizon": horizon,
                              "condition": condition, "conditional": _describe(values[selected], selected_rows),
                              "baseline": _describe(values[reference], [r for r, keep in zip(group, reference) if keep]),
                              "baseline_kind": "disagreement_same_event_sample" if condition == "agreement_vs_disagreement" else "all_paired_event_months_same_clock",
                              "distinct_macro_periods": observed_n, "gap_pct": None, "gap_ci95": None,
                              "p_bootstrap_approx": None, "status": "insufficient_evidence"}
                    pvalues[key] = 1.0  # missing cells retain their slot in the declared family
                    if selected.any() and reference.any():
                        gap = float(np.mean(values[selected]) - np.mean(values[reference]))
                        report["gap_pct"] = gap
                        complement_n = int(((~selected) & present).sum()) if condition != "agreement_vs_disagreement" else int(reference.sum())
                        if idx is not None and selected.sum() >= min_cell_n and complement_n >= min_cell_n:
                            simulated = []
                            for indices in idx:
                                sm, rm = selected[indices], reference[indices]
                                if sm.any() and rm.any():
                                    simulated.append(float(np.mean(values[indices][sm]) - np.mean(values[indices][rm])))
                            if len(simulated) >= draws // 2 and np.ptp(simulated) > 1e-12:
                                boot = np.array(simulated)
                                p = float((np.sum(np.abs(boot - gap) >= abs(gap)) + 1) / (len(boot) + 1))
                                report.update({"gap_ci95": [float(x) for x in np.quantile(boot, [0.025, 0.975])],
                                               "p_bootstrap_approx": p, "status": "exploratory_estimate"})
                                pvalues[key] = p
                    reports.append(report)
    adjusted = holm_adjust(pvalues)
    for report in reports:
        report["p_holm"] = adjusted[report["hypothesis_id"]] if report["p_bootstrap_approx"] is not None else None
    return {"cells": reports, "declared_hypotheses": len(pvalues), "bootstrap_draws": draws,
            "bootstrap_mean_block_periods": mean_block, "seed": seed, "min_cell_n": min_cell_n,
            "resampling_clock": "shared_complete_reference_month_calendar", "calendar_months": len(timeline),
            "multiplicity": "Holm_all_declared_pair_asset_horizon_conditions_including_unavailable",
            "inference": "exploratory_time_block_bootstrap_not_prospective_validation",
            "authority": authority()}


def join_regime_features(events: Iterable[dict], observations: Iterable[dict], *, names: Sequence[str], max_age_hours: float = 72) -> list[dict]:
    """As-of join existing-owner numerical context, without invented defaults."""
    if not 0 < finite(max_age_hours) <= 720 or len(set(names)) != len(names):
        raise EvidenceError("invalid_regime_join_configuration")
    by_name: dict[str, list] = defaultdict(list)
    for observation in observations:
        if observation.get("name") not in names:
            continue
        known = instant(observation.get("known_at"))
        observed = instant(observation.get("observed_at"))
        if observed > known or not observation.get("source_ref"):
            raise EvidenceError("regime_source_clock_invalid")
        finite(observation.get("value"))
        by_name[observation["name"]].append({**observation, "known": known, "observed": observed})
    output = []
    for event in events:
        cutoff = instant(event["known_at"])
        features, missing, refs = {}, [], {}
        for name in names:
            candidates = [o for o in by_name[name] if o["known"] <= cutoff and cutoff - o["observed"] <= timedelta(hours=max_age_hours)]
            if not candidates:
                missing.append(name)
                continue
            latest = max(candidates, key=lambda o: (o["observed"], o["known"]))
            ties = [o for o in candidates if (o["observed"], o["known"]) == (latest["observed"], latest["known"])]
            if len({(o["value"], o["source_ref"]) for o in ties}) != 1:
                missing.append(name + ":conflicting")
                continue
            features[name], refs[name] = latest["value"], latest["source_ref"]
        output.append({**event, "regime_features": features, "regime_missing": missing, "regime_source_refs": refs})
    return output


def forecast_at(rows: Iterable[dict], target: dict, *, features: Sequence[str] = FEATURES,
                min_train: int = 60, ridge_alpha: float = 10.0, embargo_hours: float = 24.0) -> dict:
    """One as-of fit; no target outcome is read or required. Pure, no capture claim."""
    if type(min_train) is not int or min_train < max(8, len(features) + 2):
        raise EvidenceError("invalid_min_train")
    if not features or len(set(features)) != len(features) or not 0 < finite(ridge_alpha) <= 1e6 or not 0 <= finite(embargo_hours) <= 720:
        raise EvidenceError("invalid_forecast_configuration")
    cutoff = instant(target["signal_known_at"])
    key = (target["pair_id"], target["symbol"], target["horizon"])
    def vector(row):
        result = []
        for name in features:
            value = row.get("regime_features", {}).get(name[7:]) if name.startswith("regime:") else row.get(name)
            if name == "agreement" and type(value) is bool:
                value = float(value)
            result.append(finite(value))
        return result
    try:
        x_target = np.array(vector(target))
    except EvidenceError:
        return {"status": "abstain", "reason": "missing_feature"}
    train, vectors, seen, periods = [], [], set(), set()
    for prior in sorted(rows, key=lambda r: (instant(r["signal_known_at"]), r["event_id"])):
        if (prior["pair_id"], prior["symbol"], prior["horizon"]) != key:
            continue
        if prior["event_id"] in seen:
            raise EvidenceError("duplicate_forecast_training_event")
        seen.add(prior["event_id"])
        if prior["period"] in periods:
            raise EvidenceError("duplicate_forecast_training_period")
        periods.add(prior["period"])
        if instant(prior["signal_known_at"]) >= cutoff:
            continue
        if instant(prior["outcome_known_at"]) + timedelta(hours=embargo_hours) >= cutoff or instant(prior["exit_at"]) >= cutoff:
            continue
        try:
            values = vector(prior)
            finite(prior["net_return_pct"])
        except EvidenceError:
            continue
        train.append(prior)
        vectors.append(values)
    if len(train) < min_train:
        return {"status": "abstain", "reason": "insufficient_mature_training_history", "n_train": len(train)}
    costs = {finite(r.get("round_trip_cost_bps")) for r in train}
    if len(costs) != 1:
        raise EvidenceError("mixed_training_cost_scenarios")
    matrix, y = np.array(vectors), np.array([r["net_return_pct"] for r in train])
    center, scale = matrix.mean(axis=0), matrix.std(axis=0)
    scale = np.where(scale > 1e-12, scale, 1.0)
    z = (matrix - center) / scale
    beta = np.linalg.solve(z.T @ z + ridge_alpha * np.eye(len(features)), z.T @ (y - y.mean()))
    forecast = float(y.mean() + ((x_target - center) / scale) @ beta)
    subgroup = [r["net_return_pct"] for r in train if r["quadrant"] == target["quadrant"]]
    cell_forecast = float((sum(subgroup) + 10 * y.mean()) / (len(subgroup) + 10))
    prediction = {"event_id": target["event_id"], "pair_id": target["pair_id"],
                  "symbol": target["symbol"], "horizon": target["horizon"],
                  "decision_at": iso(cutoff), "n_train": len(train),
                  "latest_training_outcome_known_at": iso(max(instant(r["outcome_known_at"]) for r in train)),
                  "forecast_pct": forecast, "unconditional_forecast_pct": float(y.mean()),
                  "round_trip_cost_bps": next(iter(costs)),
                  "shrunk_quadrant_forecast_pct": cell_forecast,
                  "fit_basis": "train_only_standardization_fixed_ridge",
                  "training_receipt": digest(train), "target_features_receipt": digest(vector(target))}
    return {"status": "computed", "prediction": prediction}


def prepare_shadow_proposals(rows: Iterable[dict], events: Iterable[dict], session_closes: Sequence[str], *,
                             symbols: Sequence[str] = DEFAULT_SYMBOLS, horizons: Sequence[int] = DEFAULT_HORIZONS,
                             asof: str, features: Sequence[str] = FEATURES, min_train: int = 60,
                             protocol_receipt: str, evidence_class: str = "synthetic") -> dict:
    """Prepare current forecasts with no outcome labels; persistence is MRI's job.

    A supplied asof is a research cutoff, NOT a trusted capture clock. The original
    MRI writer separately observes its real clock and refuses late capture.
    """
    cutoff, sessions, history = instant(asof), validate_sessions(session_closes), list(rows)
    if not isinstance(protocol_receipt, str) or not protocol_receipt:
        raise EvidenceError("protocol_receipt_required")
    if evidence_class not in {"synthetic", "retrospective_pit", "prospective_capture"}:
        raise EvidenceError("invalid_shadow_evidence_class")
    proposals, reasons = [], Counter()
    for event in events:
        known = instant(event["known_at"])
        if known > cutoff or known < sessions[0]:
            reasons["event_clock_outside_known_calendar"] += 1
            continue
        entry_index = bisect_right(sessions, known)
        if entry_index >= len(sessions) or sessions[entry_index] <= cutoff:
            reasons["entry_already_passed_or_calendar_unavailable"] += 1
            continue
        for symbol in symbols:
            for horizon in horizons:
                target = {**event, "signal_known_at": event["known_at"], "symbol": symbol, "horizon": horizon}
                fitted = forecast_at(history, target, features=features, min_train=min_train)
                if fitted["status"] != "computed":
                    reasons[fitted["reason"]] += 1
                    continue
                prediction = fitted["prediction"]
                forecast_id = "msc_forecast:" + digest([protocol_receipt, event["event_id"], symbol, horizon])[:24]
                proposal = {"schema": "macro_return_shadow_forecast.v1", "row_type": "macro_return_forecast",
                            "forecast_id": forecast_id, "protocol_receipt": protocol_receipt,
                            "data_evidence_class": evidence_class,
                            "prepared_asof": iso(cutoff), "entry_at": iso(sessions[entry_index]),
                            "prediction": prediction, "authority": authority(),
                            "release": event["pair_id"], "period": event["period"],
                            "model": "msc_fixed_ridge_v1", "asof_night": iso(known)[:10]}
                proposal["proposal_digest"] = digest(proposal)
                proposals.append(proposal)
    return {"proposals": proposals, "exclusions": dict(reasons),
            "status": "prepared_not_captured" if proposals else "no_eligible_proposal", "authority": authority()}


def walk_forward(rows: Iterable[dict], *, features: Sequence[str] = FEATURES, min_train: int = 60,
                 ridge_alpha: float = 10.0, embargo_hours: float = 24.0) -> dict:
    """Fixed ridge challenger; purged label availability, train-only scaling.

    Calendar embargo is explicit hours after an outcome becomes known. It is not
    falsely labeled trading sessions. No tuning or automatic promotion occurs.
    Missing features abstain. All models see identical chronological rows.
    """
    if type(min_train) is not int or min_train < max(8, len(features) + 2):
        raise EvidenceError("invalid_min_train")
    if not features or len(set(features)) != len(features) or not 0 < finite(ridge_alpha) <= 1e6 or not 0 <= finite(embargo_hours) <= 720:
        raise EvidenceError("invalid_walk_forward_configuration")
    groups: dict[tuple, list] = defaultdict(list)
    for row in rows:
        groups[(row["pair_id"], row["symbol"], row["horizon"])].append(row)
    predictions, excluded = [], Counter()
    for group in groups.values():
        ordered = sorted(group, key=lambda row: (instant(row["signal_known_at"]), row["event_id"]))
        seen_ids = set()
        for target in ordered:
            if target["event_id"] in seen_ids:
                raise EvidenceError("duplicate_walk_forward_event")
            seen_ids.add(target["event_id"])
            fitted = forecast_at(ordered, target, features=features, min_train=min_train,
                                 ridge_alpha=ridge_alpha, embargo_hours=embargo_hours)
            if fitted["status"] != "computed":
                excluded[fitted["reason"]] += 1
                continue
            predictions.append({**fitted["prediction"], "realized_pct": finite(target["net_return_pct"])})
    scores = {}
    for key in sorted({(p["pair_id"], p["symbol"], p["horizon"]) for p in predictions}):
        subset = [p for p in predictions if (p["pair_id"], p["symbol"], p["horizon"]) == key]
        truth = np.array([p["realized_pct"] for p in subset])
        scores[":".join(map(str, key))] = {"n": len(subset), "models": {}}
        for name in ("forecast_pct", "unconditional_forecast_pct", "shrunk_quadrant_forecast_pct"):
            errors = np.array([p[name] for p in subset]) - truth
            scores[":".join(map(str, key))]["models"][name] = {"mae_pct": float(np.mean(np.abs(errors))), "mse_pct_squared": float(np.mean(errors ** 2))}
    return {"predictions": predictions, "scores_by_pair_asset_horizon": scores, "exclusions": dict(excluded),
            "min_train": min_train, "ridge_alpha": ridge_alpha, "embargo_hours": embargo_hours,
            "features": list(features), "validation_class": "retrospective_walk_forward_not_prospective",
            "authority": authority()}


def evaluate_shadow_captures(ledger_rows: Iterable[dict], outcomes: Iterable[dict], *, asof: str) -> dict:
    """Grade only original, linked, locally observed pre-entry captures.

    Read-only evaluation over the incumbent MRI ledger. This is not independent
    clock attestation, a new acceptance state machine, or promotion authority.
    """
    cutoff = instant(asof)
    forecasts, captures, labels, reasons = {}, {}, {}, Counter()
    for row in ledger_rows:
        target = forecasts if row.get("row_type") == "macro_return_forecast" else captures if row.get("row_type") == "macro_return_capture" else None
        if target is not None:
            key = row.get("forecast_id")
            if key in target and target[key] != row:
                raise EvidenceError("conflicting_shadow_capture_rows")
            target[key] = row
    for row in outcomes:
        key = (row["event_id"], row["symbol"], row["horizon"])
        if key in labels:
            raise EvidenceError("duplicate_shadow_outcome")
        labels[key] = row
    graded = []
    for identity, forecast in forecasts.items():
        capture = captures.get(identity)
        try:
            proposal = {k: v for k, v in forecast.items() if k not in {"proposal_digest", "captured_at"}}
            if not capture or capture.get("capture_eligible") is not True or not valid_authority(forecast.get("authority")) or not valid_authority(capture.get("authority")):
                raise EvidenceError("capture_not_qualified")
            if forecast.get("data_evidence_class") not in {"retrospective_pit", "prospective_capture"}:
                raise EvidenceError("synthetic_capture_not_prospective_evidence")
            if forecast["proposal_digest"] != digest(proposal) or capture.get("proposal_digest") != forecast["proposal_digest"]:
                raise EvidenceError("shadow_capture_binding_mismatch")
            if capture.get("receipt_digest") != digest({k: v for k, v in capture.items() if k != "receipt_digest"}):
                raise EvidenceError("shadow_capture_receipt_corrupt")
            prediction = forecast["prediction"]
            clocks = [instant(prediction["decision_at"]), instant(forecast["prepared_asof"]), instant(forecast["captured_at"]), instant(capture["capture_observed_at"])]
            if clocks != sorted(clocks) or not clocks[-1] < instant(forecast["entry_at"]) or clocks[-1] > cutoff:
                raise EvidenceError("shadow_capture_not_before_entry")
            if capture["entry_at"] != forecast["entry_at"]:
                raise EvidenceError("shadow_entry_binding_mismatch")
            key = (prediction["event_id"], prediction["symbol"], prediction["horizon"])
            outcome = labels.get(key)
            if not outcome or instant(outcome["outcome_known_at"]) > cutoff:
                reasons["label_not_yet_available"] += 1
                continue
            if instant(outcome["entry_at"]) != instant(forecast["entry_at"]):
                raise EvidenceError("shadow_outcome_entry_mismatch")
            if finite(outcome.get("round_trip_cost_bps")) != finite(prediction.get("round_trip_cost_bps")):
                raise EvidenceError("shadow_outcome_cost_basis_mismatch")
            realized = finite(outcome["net_return_pct"])
            graded.append({"forecast_id": identity, "event_id": prediction["event_id"],
                           "symbol": prediction["symbol"], "horizon": prediction["horizon"],
                           "pair_id": prediction["pair_id"], "realized_pct": realized,
                           "forecast_pct": prediction["forecast_pct"],
                           "absolute_error_pct": abs(realized - finite(prediction["forecast_pct"])),
                           "baseline_absolute_error_pct": abs(realized - finite(prediction["unconditional_forecast_pct"])),
                           "capture_receipt_digest": capture["receipt_digest"], "outcome_receipt": digest(outcome)})
        except (EvidenceError, ValueError, TypeError, KeyError) as exc:
            reasons[str(exc) if isinstance(exc, EvidenceError) else "invalid_shadow_capture_contract"] += 1
    return {"graded": graded, "exclusions": dict(reasons), "evidence_basis": "local_publisher_capture_and_source_bound_outcomes",
            "independent_timestamp_attestation": False, "live_promotion": False, "authority": authority()}
