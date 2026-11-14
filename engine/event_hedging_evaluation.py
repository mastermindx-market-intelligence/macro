"""Paired event-turn research scorecard using the incumbent K3E scoring math.

This is an I/O-free consumer of already-issued forecast and outcome receipts.
It creates no forecasts, labels, ledger, registration, model fit or promotion.
Only generic multiclass loss functions are reused; K3E's 21-session protocol,
trial identity and acceptance thresholds do not apply to these intraday targets.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math

from engine.k3e_eval1_forward import brier_score, mean_log_loss

_LABELS = {"UPPER_FIRST": "UP", "LOWER_FIRST": "DOWN", "NEITHER": "FLAT"}
_PROTOCOL_FIELDS = {
    "registration_ref", "registered_at", "target_ref", "horizon_minutes", "security_id",
    "baseline_model_ref", "challenger_model_ref", "training_episode_ids",
    "evaluation_start", "evaluation_end", "expected_origins", "cohort_source_ref",
}
_ROW_FIELDS = {"origin_id", "episode_id", "target_ref", "horizon_minutes", "security_id",
               "decision_at", "target_end_at", "target_window_ref", "baseline", "challenger", "outcome"}
_FORECAST_FIELDS = {"model_ref", "receipt_ref", "issued_at", "features_known_at", "training_labels_known_at", "probabilities"}
_OUTCOME_FIELDS = {"status", "label", "known_at", "receipt_ref", "reason"}
_AUTHORITY = {key: False for key in (
    "calibrated_probability", "trading", "ranking", "sizing", "portfolio", "auto_exit", "can_publish",
)}


def _text(value, name):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError(f"invalid {name}")
    return value


def _time(value, name):
    _text(value, name)
    try:
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid {name}") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} requires timezone")
    return value.astimezone(timezone.utc)


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _closed(value, fields, name):
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{name} must use the exact contract")


def _forecast(value, model, decision, name):
    if value is None:
        return "missing_" + name
    _closed(value, _FORECAST_FIELDS, name)
    _text(value["receipt_ref"], name + ".receipt_ref")
    if value["model_ref"] != model:
        raise ValueError(f"{name} model identity mismatch")
    issued = _time(value["issued_at"], name + ".issued_at")
    features = _time(value["features_known_at"], name + ".features_known_at")
    training = _time(value["training_labels_known_at"], name + ".training_labels_known_at")
    if not max(features, training) <= issued <= decision:
        raise ValueError(f"{name} uses information or issuance after its decision")
    probs = value["probabilities"]
    if not isinstance(probs, list) or len(probs) != 3:
        raise ValueError("probability vector must have UPPER_FIRST, LOWER_FIRST, NEITHER entries")
    for x in probs:
        if isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) or not 0 <= x <= 1:
            raise ValueError("probabilities must be finite numbers in [0,1]")
    if abs(math.fsum(probs) - 1.) > 1e-9:
        raise ValueError("probabilities must sum to one; no implicit renormalization")
    return None


def _loss(probs, labels):
    value = mean_log_loss(probs, labels)
    return {"multiclass_brier": brier_score(probs, labels),
            "mean_log_loss": value if math.isfinite(value) else None,
            "log_loss_state": "finite" if math.isfinite(value) else "infinite"}


def _mean_scores(scores):
    n = len(scores)
    infinite = any(s["log_loss_state"] == "infinite" for s in scores)
    return {"multiclass_brier": math.fsum(s["multiclass_brier"] for s in scores) / n,
            "mean_log_loss": None if infinite else math.fsum(s["mean_log_loss"] for s in scores) / n,
            "log_loss_state": "infinite" if infinite else "finite"}


def score_event_hedging_forecasts(*, protocol: dict, records: list[dict], evaluated_at: str) -> dict:
    """Score a fixed supplied cohort without hiding abstentions or event clustering.

    Every eligible origin is declared before scoring. Missing forecasts, censored
    outcomes and pending labels remain in the denominator. Same-event observations
    are not independent replications: both row- and equal-episode-weighted scores
    are shown, with no p-value, calibration certificate or automatic promotion.
    """
    _closed(protocol, _PROTOCOL_FIELDS, "protocol")
    _wire({"protocol": protocol, "records": records, "evaluated_at": evaluated_at})
    for key in ("registration_ref", "target_ref", "security_id", "baseline_model_ref", "challenger_model_ref", "cohort_source_ref"):
        _text(protocol[key], key)
    if protocol["baseline_model_ref"] == protocol["challenger_model_ref"]:
        raise ValueError("baseline and challenger require distinct model identities")
    horizon = protocol["horizon_minutes"]
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon not in {30, 60, 120}:
        raise ValueError("only explicit 30/60/120 minute research strata are supported")
    registered = _time(protocol["registered_at"], "registered_at")
    start = _time(protocol["evaluation_start"], "evaluation_start")
    end = _time(protocol["evaluation_end"], "evaluation_end")
    now = _time(evaluated_at, "evaluated_at")
    if not registered <= start < end <= now:
        raise ValueError("registration, evaluation window or evaluation clock is invalid")
    training = protocol["training_episode_ids"]
    if not isinstance(training, list):
        raise ValueError("training episodes must be a unique list")
    for value in training:
        _text(value, "training episode")
    if len(training) != len(set(training)):
        raise ValueError("duplicate training episode")
    origins = protocol["expected_origins"]
    if not isinstance(origins, list) or not 1 <= len(origins) <= 100_000:
        raise ValueError("expected cohort must contain 1..100000 origins")
    population = {}
    for item in origins:
        _closed(item, {"origin_id", "episode_id"}, "expected origin")
        origin, episode = _text(item["origin_id"], "origin_id"), _text(item["episode_id"], "episode_id")
        if origin in population:
            raise ValueError("duplicate expected origin")
        if episode in training:
            raise ValueError("evaluation episode overlaps model-development episodes")
        population[origin] = episode
    if not isinstance(records, list) or len(records) > len(population):
        raise ValueError("records must fit the declared cohort")
    seen, eligible, exclusions = set(), [], []
    for row in records:
        _closed(row, _ROW_FIELDS, "forecast/outcome pair")
        origin = _text(row["origin_id"], "origin_id")
        if origin not in population or origin in seen:
            raise ValueError("foreign or duplicate origin")
        seen.add(origin)
        if row["episode_id"] != population[origin]:
            raise ValueError("episode identity mismatch")
        for key in ("target_ref", "horizon_minutes", "security_id"):
            if row[key] != protocol[key] or isinstance(row[key], bool):
                raise ValueError("incomparable target, horizon or security")
        decision = _time(row["decision_at"], "decision_at")
        target_end = _time(row["target_end_at"], "target_end_at")
        _text(row["target_window_ref"], "target_window_ref")
        if not start <= decision < target_end <= end:
            raise ValueError("target window falls outside the frozen evaluation interval")
        if (target_end - decision).total_seconds() != horizon * 60:
            raise ValueError("continuous intraday target duration disagrees with its horizon")
        # The owner supplies exchange-session and path-coverage qualification.
        # This adapter does not invent a trading calendar or infer complete bars.
        reasons = []
        for name in ("baseline", "challenger"):
            reason = _forecast(row[name], protocol[name + "_model_ref"], decision, name)
            if reason:
                reasons.append(reason)
        outcome = row["outcome"]
        if outcome is None:
            reasons.append("missing_outcome")
        else:
            _closed(outcome, _OUTCOME_FIELDS, "outcome")
            status = outcome["status"]
            if status not in {"available", "pending", "unavailable"}:
                raise ValueError("unknown outcome state")
            if status != "available":
                if outcome["label"] is not None:
                    raise ValueError("pending or censored outcomes must not carry a label")
                reasons.append(status + "_outcome")
            else:
                _text(outcome["receipt_ref"], "outcome receipt")
                if outcome["reason"] is not None or outcome["label"] not in _LABELS:
                    raise ValueError("available outcome has invalid label or censoring reason")
                known = _time(outcome["known_at"], "outcome.known_at")
                if known < target_end:
                    raise ValueError("full-horizon outcome not mature at its reported availability")
                if known > now:
                    reasons.append("outcome_not_yet_available")
        if reasons:
            exclusions.append({"origin_id": origin, "episode_id": row["episode_id"], "reasons": reasons})
        else:
            eligible.append(row)
    for origin in sorted(set(population) - seen):
        exclusions.append({"origin_id": origin, "episode_id": population[origin], "reasons": ["missing_record"]})
    scores, by_episode = None, []
    if eligible:
        labels = [_LABELS[row["outcome"]["label"]] for row in eligible]
        scores = {name: _loss([row[name]["probabilities"] for row in eligible], labels)
                  for name in ("baseline", "challenger")}
        groups = defaultdict(list)
        for row in eligible:
            groups[row["episode_id"]].append(row)
        for episode, group in sorted(groups.items()):
            labels = [_LABELS[row["outcome"]["label"]] for row in group]
            by_episode.append({"episode_id": episode, "scored_origins": len(group),
                **{name: _loss([r[name]["probabilities"] for r in group], labels) for name in ("baseline", "challenger")}})
    balanced = None if not by_episode else {
        name: _mean_scores([x[name] for x in by_episode]) for name in ("baseline", "challenger")
    }
    # Positive difference means smaller challenger loss, not a promotion pass.
    delta = None if scores is None else scores["baseline"]["multiclass_brier"] - scores["challenger"]["multiclass_brier"]
    expected_episodes = set(population.values())
    receipt = {
        "schema": "options.event_hedging_scorecard/v1", "evidence_class": "RESEARCH_EVALUATION",
        "protocol": deepcopy(protocol), "evaluated_at": evaluated_at,
        "input_digest": sha256(_wire({"protocol": protocol, "records": records}).encode()).hexdigest(),
        "status": "scored" if eligible else "non_evaluable", "class_order": list(_LABELS),
        "coverage": {"expected_origins": len(population), "received_origins": len(records),
                     "scored_origins": len(eligible), "excluded_origins": len(exclusions),
                     "expected_episodes": len(expected_episodes), "scored_episodes": len(by_episode),
                     "scored_fraction": len(eligible) / len(population)},
        "exclusions": sorted(exclusions, key=lambda x: x["origin_id"]),
        "exclusion_counts": dict(sorted(Counter(r for x in exclusions for r in x["reasons"]).items())),
        "row_weighted_scores": scores, "equal_episode_weighted_scores": balanced,
        "baseline_minus_challenger_brier": delta, "by_episode": by_episode,
        "promotion_eligible": False, "authority": dict(_AUTHORITY),
        "limitations": [
            "Receipt references and stated registration chronology require separate owner verification.",
            "The declared cohort supplies the denominator; this function cannot authenticate completeness.",
            "Scores assess paired supplied forecasts, not calibration, causal hedging impact or trade utility.",
            "Minute rows sharing an event are not independent episodes; no significance claim is computed.",
            "Generic K3E loss math is reused without its target protocol or promotion thresholds.",
            "No forecasts or labels are created, fitted, stored, promoted or published by this function.",
        ],
    }
    receipt["content_id"] = "event-scorecard:" + sha256(_wire(receipt).encode()).hexdigest()
    return receipt
