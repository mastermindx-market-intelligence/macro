#!/usr/bin/env python3
"""Synthetic research reference: positive one-feature QLIKE augmentation.

No production imports, market observations, network calls, or automatic writes.
The chronology checker checks supplied ordering, not evidence authenticity.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import sys


SPEC_VERSION = "options.p3.positive_offset.reference.v1"
BETA_LOWER, BETA_UPPER = -1.0, 1.0
BRACKET_TOLERANCE, MAX_ITERATIONS = 1e-10, 100


class Refusal(ValueError):
    def __init__(self, code, detail):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}")


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Refusal("INVALID_NUMBER", name)
    try:
        answer = float(value)
    except (ValueError, OverflowError) as exc:
        raise Refusal("NONFINITE_INPUT", name) from exc
    if not math.isfinite(answer):
        raise Refusal("NONFINITE_INPUT", name)
    return answer


def finite(value, name):
    if not math.isfinite(value):
        raise Refusal("NONFINITE_CALCULATION", name)
    return value


def checked_sum(values, name):
    try:
        return finite(math.fsum(values), name)
    except OverflowError as exc:
        raise Refusal("NONFINITE_CALCULATION", name) from exc


def positive_product(a, b, name):
    result = finite(a * b, name)
    if a > 0 and b > 0 and result == 0:
        raise Refusal("POSITIVE_UNDERFLOW", name)
    return result


def positive_exp(value, name):
    try:
        result = finite(math.exp(value), name)
    except OverflowError as exc:
        raise Refusal("EXP_OVERFLOW", name) from exc
    if result == 0:
        raise Refusal("POSITIVE_UNDERFLOW", name)
    return result


def prepare(rows):
    """Validate all rows, normalize positive weights, preserve every row."""
    if not isinstance(rows, (list, tuple)) or not rows:
        raise Refusal("NO_TRAINING_ROWS", "a nonempty explicit row sequence is required")
    out, identities = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise Refusal("INVALID_ROW", "training row must be a mapping")
        identity = row.get("id")
        if not isinstance(identity, str) or not identity or identity in identities:
            raise Refusal("INVALID_ROW_ID", "missing or duplicate training identity")
        identities.add(identity)
        y, v1, z, weight = (number(row.get(k), k) for k in ("y", "v1", "z", "weight"))
        if y < 0 or v1 <= 0 or weight <= 0:
            raise Refusal("INVALID_DOMAIN", "require y >= 0, v1 > 0, weight > 0")
        ratio = finite(y / v1, "y/v1")
        if y > 0 and ratio == 0:
            raise Refusal("POSITIVE_UNDERFLOW", "y/v1")
        log_ratio = (math.log1p((y - v1) / v1) if 0.5 < ratio < 2.0 else math.log(ratio)) if y > 0 else None
        out.append({"id": identity, "y": y, "v1": v1, "z": z,
                    "original_weight": weight, "ratio": ratio, "log_ratio": log_ratio})
    maximum = max(r["original_weight"] for r in out)
    scaled = [r["original_weight"] / maximum for r in out]
    if any(w == 0 for w in scaled):
        raise Refusal("POSITIVE_UNDERFLOW", "relative training weight")
    total = checked_sum(scaled, "scaled weight sum")
    for row, weight in zip(out, scaled):
        row["weight"] = weight / total
        if row["weight"] == 0:
            raise Refusal("POSITIVE_UNDERFLOW", "normalized training weight")
    return out


def evaluate_prepared(rows, beta):
    beta = number(beta, "beta")
    if not BETA_LOWER <= beta <= BETA_UPPER:
        raise Refusal("BETA_OUTSIDE_FIXED_DOMAIN", str(beta))
    losses, derivatives, forecasts = [], [], []
    for row in rows:
        arg = finite(beta * row["z"], "beta*z")
        multiplier = positive_exp(arg, "exp(beta*z)")
        inverse = positive_exp(-arg, "exp(-beta*z)")
        forecast = positive_product(row["v1"], multiplier, "variance forecast")
        relative_error = positive_product(row["ratio"], inverse, "y/v2")
        if row["y"] == 0:
            loss = checked_sum((math.log(row["v1"]), arg), "QLIKE")
            derivative = row["z"]
        else:
            # Cancellation-safe around y/v2=1, including tiny nonzero z.
            d = finite(row["log_ratio"] - arg, "log(y/v2)")
            try:
                expm1 = finite(math.expm1(d), "expm1(log(y/v2))")
            except OverflowError as exc:
                raise Refusal("EXP_OVERFLOW", "expm1(log(y/v2))") from exc
            derivative = finite(-row["z"] * expm1, "QLIKE derivative")
            if row["z"] != 0 and d != 0 and derivative == 0:
                raise Refusal("NUMERICALLY_UNIDENTIFIED", "nonzero row derivative underflow")
            if abs(d) < 1e-3:
                # expm1(d)-d=sum(d**k/k!, k>=2); eight terms exceed
                # float64 precision in this declared small-d interval.
                term = d * d / 2.0
                terms = [term]
                for k in range(3, 10):
                    term *= d / k
                    terms.append(term)
                curvature_loss = checked_sum(terms, "QLIKE curvature")
            else:
                curvature_loss = finite(expm1 - d, "QLIKE curvature")
            loss = checked_sum((math.log(row["y"]), 1.0, curvature_loss), "QLIKE")
        if 0 < abs(derivative) < sys.float_info.min:
            raise Refusal("NUMERICALLY_UNIDENTIFIED", "subnormal row derivative cannot certify bracket")
        losses.append(finite(row["weight"] * loss, "weighted loss"))
        # Sum weight products exactly after each row derivative is computed.
        # This avoids reversing a tiny affine slope through normalization
        # and multiplication rounding before the summation begins.
        derivatives.append(Fraction.from_float(row["original_weight"]) * Fraction.from_float(derivative))
        forecasts.append({"id": row["id"], "v2": forecast})
    weight_total = sum((Fraction.from_float(r["original_weight"]) for r in rows), Fraction(0))
    exact_weighted_derivative = sum(derivatives, Fraction(0)) / weight_total
    final_derivative = finite(float(exact_weighted_derivative), "mean QLIKE derivative")
    if exact_weighted_derivative != 0 and (final_derivative == 0 or abs(final_derivative) < sys.float_info.min):
        raise Refusal("NUMERICALLY_UNIDENTIFIED", "unresolved weighted derivative scale")
    return {"beta": beta, "loss": checked_sum(losses, "mean QLIKE"),
            "derivative": final_derivative,
            "forecasts": forecasts}


def evaluate(rows, beta):
    return evaluate_prepared(prepare(rows), beta)


def fit(rows):
    """Constrained convex fit; no intercept, second smearing, or fallback."""
    prepared = prepare(rows)
    # Strict convexity holds if any positive-target row has nonzero feature.
    # Otherwise the objective is affine; exact binary-rational arithmetic
    # distinguishes truly flat data from a small but nonzero affine slope.
    curved = any(row["y"] > 0 and row["z"] != 0 for row in prepared)
    if not curved:
        slope = sum((Fraction.from_float(r["original_weight"]) * Fraction.from_float(r["z"])
                     for r in prepared), Fraction(0))
        if slope == 0:
            raise Refusal("FIT_UNIDENTIFIED", "objective is analytically flat")
    lower, upper = BETA_LOWER, BETA_UPPER
    lo, hi = evaluate_prepared(prepared, lower), evaluate_prepared(prepared, upper)
    if lo["derivative"] > hi["derivative"]:
        raise Refusal("DERIVATIVE_NOT_MONOTONE", "finite arithmetic contradicts convexity")
    if curved and lo["derivative"] == 0 and hi["derivative"] == 0:
        raise Refusal("NUMERICALLY_UNIDENTIFIED", "curved objective has unresolved endpoint derivatives")
    if not curved:
        # Do not classify a rounded-to-zero affine derivative as identified.
        if lo["derivative"] == 0 or hi["derivative"] == 0:
            raise Refusal("NUMERICALLY_UNIDENTIFIED", "nonzero affine slope rounded to zero")
    iterations = 0
    if lo["derivative"] >= 0:
        answer, boundary = lo, True
    elif hi["derivative"] <= 0:
        answer, boundary = hi, True
    else:
        boundary = False
        while upper - lower > BRACKET_TOLERANCE and iterations < MAX_ITERATIONS:
            midpoint = (lower + upper) / 2.0
            trial = evaluate_prepared(prepared, midpoint)
            iterations += 1
            if trial["derivative"] == 0:
                lower = upper = midpoint
                break
            if trial["derivative"] < 0:
                lower = midpoint
            else:
                upper = midpoint
        if upper - lower > BRACKET_TOLERANCE:
            raise Refusal("SOLVER_NONCONVERGENCE", "fixed iteration budget exhausted")
        answer = evaluate_prepared(prepared, (lower + upper) / 2.0)
    return {"status": "FIT", "rows": len(prepared), "beta": answer["beta"],
            "mean_qlike": answer["loss"], "derivative": answer["derivative"],
            "constrained_optimum": boundary, "bracket_width": 0.0 if boundary else upper - lower,
            "iterations": iterations, "domain": [BETA_LOWER, BETA_UPPER],
            "forecasts": answer["forecasts"], "empirical_evidence": False}


def epoch_ns(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise Refusal("INVALID_CLOCK", name + " must be nonnegative integer epoch nanoseconds")
    return value


def validate_training_chronology(records, augmentation_fit_at_ns, first_test_decision_ns):
    """Checks a minimal supplied chronology, never authenticates PIT capture.

    Raw feature/nuisance and target-adapted baseline predictions for training
    rows must be honest as-of. The final RZ transform is fitted on the training
    fold separately; it is not falsely required to predate every training row.
    """
    cutoff = epoch_ns(augmentation_fit_at_ns, "augmentation fit")
    first_test = epoch_ns(first_test_decision_ns, "first test decision")
    if cutoff >= first_test:
        raise Refusal("FIT_NOT_BEFORE_TEST", "fit must precede first test decision")
    if not isinstance(records, list) or not records:
        raise Refusal("NO_CHRONOLOGY_ROWS", "nonempty explicit chronology required")
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            raise Refusal("INVALID_ROW", "chronology row must be a mapping")
        identity = row.get("id")
        if not isinstance(identity, str) or not identity or identity in seen:
            raise Refusal("INVALID_ROW_ID", "missing or duplicate chronology identity")
        seen.add(identity)
        for key in ("source_revision_id", "feature_revision_id", "baseline_revision_id", "label_revision_id"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise Refusal("MISSING_REVISION", key)
        keys = ("formation_at_ns", "label_mature_at_ns", "label_revision_available_at_ns", "feature_input_available_at_ns",
                "feature_published_at_ns", "feature_received_at_ns", "nuisance_fit_at_ns",
                "nuisance_latest_training_label_mature_at_ns", "baseline_input_available_at_ns",
                "baseline_fit_at_ns", "baseline_latest_training_label_mature_at_ns",
                "baseline_published_at_ns", "baseline_received_at_ns")
        clocks = {k: epoch_ns(row.get(k), k) for k in keys}
        formed = clocks["formation_at_ns"]
        if not formed < clocks["label_mature_at_ns"] <= cutoff:
            raise Refusal("TRAINING_LABEL_NOT_MATURE", identity)
        if clocks["label_revision_available_at_ns"] > cutoff:
            raise Refusal("TRAINING_LABEL_REVISION_UNAVAILABLE", identity)
        if clocks["label_revision_available_at_ns"] < clocks["label_mature_at_ns"]:
            raise Refusal("LABEL_REVISION_BEFORE_MATURITY", "final immutable label revision is not provisional: " + identity)
        for prefix in ("feature", "baseline"):
            if not clocks[f"{prefix}_input_available_at_ns"] <= clocks[f"{prefix}_published_at_ns"] <= clocks[f"{prefix}_received_at_ns"] <= formed:
                raise Refusal("PREDICTION_NOT_ASOF", prefix + ":" + identity)
        if not clocks["nuisance_latest_training_label_mature_at_ns"] <= clocks["nuisance_fit_at_ns"] <= clocks["feature_published_at_ns"]:
            raise Refusal("NUISANCE_LABEL_LEAKAGE", identity)
        if not clocks["baseline_latest_training_label_mature_at_ns"] <= clocks["baseline_fit_at_ns"] <= clocks["baseline_published_at_ns"]:
            raise Refusal("BASELINE_LABEL_LEAKAGE", identity)
    return {"status": "ORDERING_VALID", "rows": len(records), "availability_attested": False,
            "consumer_capture_attested": False, "scope": "supplied_clock_order_only"}


def robust_scaler(history, fit_at_ns, root, clock_bin):
    """Last 60 eligible sessions; min40 and positive MAD, no clip or floor.

    The caller supplies an already qualified history census. Ineligible rows
    remain counted; eligibility and provenance are not established here.
    """
    cutoff = epoch_ns(fit_at_ns, "scaler fit")
    if any(not isinstance(value, str) or not value.strip() for value in (root, clock_bin)):
        raise Refusal("INVALID_SCALER_SCOPE", "nonblank root and formation bin required")
    if not isinstance(history, list):
        raise Refusal("INVALID_SCALER_HISTORY", "explicit history required")
    admitted, seen = [], set()
    for row in history:
        if not isinstance(row, dict):
            raise Refusal("INVALID_ROW", "scaler row must be a mapping")
        if row.get("root") != root or row.get("clock_bin") != clock_bin:
            raise Refusal("SCALER_SCOPE_MISMATCH", "root or formation bin")
        session = row.get("session")
        if not isinstance(session, str) or not session or session in seen:
            raise Refusal("DUPLICATE_SCALER_SESSION", "one observation per root/bin/session")
        seen.add(session)
        observed = epoch_ns(row.get("formation_at_ns"), "scaler observation")
        available = epoch_ns(row.get("available_at_ns"), "scaler availability")
        if observed >= cutoff or available > cutoff or available < observed:
            raise Refusal("SCALER_FUTURE_INFORMATION", session)
        if not isinstance(row.get("eligible"), bool):
            raise Refusal("UNKNOWN_SCALER_ELIGIBILITY", session)
        if row["eligible"]:
            admitted.append((observed, session, number(row.get("value"), "scaler value")))
    selected = sorted(admitted)[-60:]
    if len(selected) < 40:
        raise Refusal("INSUFFICIENT_SCALER_HISTORY", "require at least 40 eligible sessions")
    median = statistics.median(row[2] for row in selected)
    deviations = [finite(abs(row[2] - median), "absolute median deviation") for row in selected]
    mad = statistics.median(deviations)
    if mad <= 0:
        raise Refusal("ZERO_MAD", "no epsilon scale or pooling fallback")
    scale = positive_product(1.4826, mad, "robust scale")
    return {"status": "SCALER_FIT", "root": root, "clock_bin": clock_bin,
            "census_rows": len(history), "selected_sessions": [r[1] for r in selected],
            "observations": len(selected), "median": median, "mad": mad, "scale": scale,
            "fit_at_ns": cutoff, "eligibility_attested": False}


def transform(value, scaler):
    x = number(value, "raw feature")
    scale = number(scaler.get("scale"), "scale")
    if scale <= 0:
        raise Refusal("INVALID_SCALE", "strictly positive scale required")
    difference = finite(x - number(scaler.get("median"), "median"), "feature minus median")
    result = finite(difference / scale, "RZ transform")
    if difference != 0 and result == 0:
        raise Refusal("NONZERO_UNDERFLOW", "RZ transform")
    return result


def run_fixtures():
    results = []

    def accepted(name, call, expected):
        result = call()
        if not expected(result):
            raise AssertionError(name + ": unexpected result " + repr(result))
        results.append({"case": name, "result": "PASS", "observed": result})
        return result

    def refused(name, call, code):
        try:
            call()
        except Refusal as error:
            if error.code != code:
                raise AssertionError(f"{name}: {error.code} != {code}") from error
            results.append({"case": name, "result": "PASS", "refusal": error.code, "detail": error.detail})
            return
        raise AssertionError(name + ": expected refusal")

    rows = [{"id": "a", "y": 0.04 * math.exp(0.35 * -0.8), "v1": 0.04, "z": -0.8, "weight": 1},
            {"id": "b", "y": 0.09 * math.exp(0.35 * 1.4), "v1": 0.09, "z": 1.4, "weight": 2},
            {"id": "c", "y": 0.06 * math.exp(0.35 * 0.2), "v1": 0.06, "z": 0.2, "weight": 1}]
    accepted("beta_zero_exactly_recovers_incumbent", lambda: evaluate(rows, 0),
             lambda r: [x["v2"] for x in r["forecasts"]] == [x["v1"] for x in rows])
    recovered = accepted("known_interior_convex_optimum", lambda: fit(rows),
                         lambda r: abs(r["beta"] - 0.35) < 1e-9 and not r["constrained_optimum"])
    accepted("negative_feature_keeps_variance_positive", lambda: evaluate(rows, recovered["beta"]),
             lambda r: 0 < r["forecasts"][0]["v2"] < rows[0]["v1"])
    accepted("permutation_does_not_change_fit", lambda: fit(list(reversed(rows))),
             lambda r: r["beta"] == recovered["beta"])
    huge_weights = [{**r, "weight": r["weight"] * 1e307} for r in rows]
    accepted("common_weight_scale_preserves_fit", lambda: fit(huge_weights),
             lambda r: r["beta"] == recovered["beta"])
    scaled = [{**r, "y": r["y"] * 10000, "v1": r["v1"] * 10000} for r in rows]
    scaled_fit = accepted("variance_unit_scale_preserves_beta", lambda: fit(scaled),
                          lambda r: abs(r["beta"] - recovered["beta"]) < 1e-9)
    accepted("paired_qlike_is_invariant_to_common_variance_units",
             lambda: {"unscaled": evaluate(rows, 0)["loss"] - recovered["mean_qlike"],
                      "scaled": evaluate(scaled, 0)["loss"] - scaled_fit["mean_qlike"]},
             lambda r: math.isclose(r["unscaled"], r["scaled"], abs_tol=1e-12))
    def single(y, z=1, v1=1):
        return [{"id": "one", "y": y, "v1": v1, "z": z, "weight": 1}]
    accepted("upper_boundary_optimum_is_declared", lambda: fit(single(math.exp(2))),
             lambda r: r["beta"] == 1 and r["constrained_optimum"])
    accepted("lower_boundary_optimum_is_declared", lambda: fit(single(math.exp(-2))),
             lambda r: r["beta"] == -1 and r["constrained_optimum"])
    accepted("zero_target_valid_affine_boundary", lambda: fit(single(0)),
             lambda r: r["beta"] == -1 and r["forecasts"][0]["v2"] > 0)
    accepted("tiny_affine_slope_sign_survives_weight_cancellation",
             lambda: fit([{"id": "positive", "y": 0, "v1": 1, "z": 5, "weight": 1},
                          {"id": "negative", "y": 0, "v1": 1, "z": -1, "weight": 5},
                          {"id": "tiny", "y": 0, "v1": 1, "z": -1e-18, "weight": 1}]),
             lambda r: r["beta"] == 1 and r["constrained_optimum"] and r["derivative"] < 0)
    accepted("constant_nonzero_feature_can_identify_offset", lambda: fit(single(math.exp(0.2))),
             lambda r: abs(r["beta"] - 0.2) < 1e-9)
    accepted("tiny_feature_preserves_unique_zero_optimum", lambda: fit(single(1, 1e-20)),
             lambda r: r["beta"] == 0 and not r["constrained_optimum"] and r["mean_qlike"] == 1)
    refused("curved_derivative_underflow_does_not_choose_boundary", lambda: fit(single(1, 1e-200)), "NUMERICALLY_UNIDENTIFIED")
    refused("subnormal_derivative_cannot_report_false_exact_root",
            lambda: fit([{"id": "curved", "y": 1, "v1": 1, "z": 1e-160, "weight": 1},
                         {"id": "affine", "y": 0, "v1": 1, "z": -1e-321, "weight": 1}]),
            "NUMERICALLY_UNIDENTIFIED")
    accepted("zero_target_and_positive_target_can_coexist", lambda: fit(single(0) + [{**single(1, -1)[0], "id": "two"}]),
             lambda r: math.isfinite(r["mean_qlike"]))
    refused("all_zero_feature_is_unidentified", lambda: fit(single(1, 0)), "FIT_UNIDENTIFIED")
    refused("balanced_zero_targets_are_unidentified", lambda: fit(single(0) + [{**single(0, -1)[0], "id": "two"}]), "FIT_UNIDENTIFIED")
    refused("negative_target_is_not_dropped", lambda: fit(rows + [{**single(-1)[0], "id": "bad"}]), "INVALID_DOMAIN")
    refused("zero_baseline_is_not_floored", lambda: fit(single(1, v1=0)), "INVALID_DOMAIN")
    refused("missing_feature_is_not_zero", lambda: fit(single(1, None)), "INVALID_NUMBER")
    refused("nonfinite_feature_is_not_clipped", lambda: fit(single(1, float("inf"))), "NONFINITE_INPUT")
    refused("boolean_feature_is_not_numeric", lambda: fit(single(1, True)), "INVALID_NUMBER")
    refused("duplicate_training_identity_is_not_double_weighted", lambda: fit(rows + [rows[0]]), "INVALID_ROW_ID")
    refused("exponential_range_violation_refuses_entire_fit", lambda: fit(single(1, 1000)), "POSITIVE_UNDERFLOW")
    refused("positive_exponential_overflow_refuses", lambda: evaluate(single(1, 1000), 1), "EXP_OVERFLOW")
    refused("positive_variance_underflow_is_not_zero", lambda: evaluate(single(0, -700, 1e-300), 1), "POSITIVE_UNDERFLOW")
    refused("ratio_overflow_is_not_clipped", lambda: fit(single(1e308, v1=1e-308)), "NONFINITE_CALCULATION")
    refused("zero_weight_does_not_drop_failed_row", lambda: fit([{**single(1)[0], "weight": 0}]), "INVALID_DOMAIN")
    refused("empty_fit_does_not_fallback", lambda: fit([]), "NO_TRAINING_ROWS")

    record = {"id": "historical-a", "source_revision_id": "synthetic-source-a", "feature_revision_id": "synthetic-feature-a",
              "baseline_revision_id": "synthetic-baseline-a", "label_revision_id": "synthetic-label-a", "formation_at_ns": 1000,
              "label_mature_at_ns": 2000, "label_revision_available_at_ns": 2000,
              "feature_input_available_at_ns": 900, "feature_published_at_ns": 950,
              "feature_received_at_ns": 980, "nuisance_fit_at_ns": 800, "nuisance_latest_training_label_mature_at_ns": 790,
              "baseline_input_available_at_ns": 900, "baseline_fit_at_ns": 850, "baseline_latest_training_label_mature_at_ns": 840,
              "baseline_published_at_ns": 960, "baseline_received_at_ns": 990}
    accepted("chronology_valid_does_not_attest_capture", lambda: validate_training_chronology([record], 3000, 4000),
             lambda r: r["status"] == "ORDERING_VALID" and not r["consumer_capture_attested"])
    for name, key, value, code in [
        ("immature_training_label", "label_mature_at_ns", 3001, "TRAINING_LABEL_NOT_MATURE"),
        ("unavailable_training_label_revision", "label_revision_available_at_ns", 3001, "TRAINING_LABEL_REVISION_UNAVAILABLE"),
        ("final_label_revision_cannot_precede_maturity", "label_revision_available_at_ns", 1999, "LABEL_REVISION_BEFORE_MATURITY"),
        ("feature_published_after_decision", "feature_published_at_ns", 1001, "PREDICTION_NOT_ASOF"),
        ("feature_received_after_decision", "feature_received_at_ns", 1001, "PREDICTION_NOT_ASOF"),
        ("upstream_nuisance_label_leakage", "nuisance_latest_training_label_mature_at_ns", 801, "NUISANCE_LABEL_LEAKAGE"),
        ("upstream_baseline_label_leakage", "baseline_latest_training_label_mature_at_ns", 851, "BASELINE_LABEL_LEAKAGE"),
        ("missing_feature_revision", "feature_revision_id", "", "MISSING_REVISION"),
        ("fractional_clock_is_not_truncated", "feature_received_at_ns", 980.9, "INVALID_CLOCK")]:
        refused(name, lambda k=key, v=value: validate_training_chronology([{**record, k: v}], 3000, 4000), code)
    refused("fit_cannot_occur_at_first_test", lambda: validate_training_chronology([record], 3000, 3000), "FIT_NOT_BEFORE_TEST")

    history = [{"root": "SYNTHETIC", "clock_bin": "09:35", "session": f"session-{i:03d}",
                "formation_at_ns": 100 + i, "available_at_ns": 101 + i, "eligible": True, "value": float(i)} for i in range(65)]
    scaler = accepted("last_60_eligible_sessions_only", lambda: robust_scaler(history, 1000, "SYNTHETIC", "09:35"),
                      lambda r: r["observations"] == 60 and r["selected_sessions"][0] == "session-005" and r["median"] == 34.5)
    accepted("RZ_is_unclipped", lambda: {"z": transform(1e6, scaler)}, lambda r: r["z"] > 1000)
    refused("scaler_requires_40_sessions", lambda: robust_scaler(history[:39], 1000, "SYNTHETIC", "09:35"), "INSUFFICIENT_SCALER_HISTORY")
    refused("scaler_zero_MAD_refuses", lambda: robust_scaler([{**r, "value": 7} for r in history], 1000, "SYNTHETIC", "09:35"), "ZERO_MAD")
    refused("scaler_future_availability_refuses", lambda: robust_scaler(history[:-1] + [{**history[-1], "available_at_ns": 1001}], 1000, "SYNTHETIC", "09:35"), "SCALER_FUTURE_INFORMATION")
    refused("scaler_scope_cannot_pool_roots", lambda: robust_scaler(history[:-1] + [{**history[-1], "root": "OTHER"}], 1000, "SYNTHETIC", "09:35"), "SCALER_SCOPE_MISMATCH")
    refused("scaler_duplicate_session_refuses", lambda: robust_scaler(history + [history[0]], 1000, "SYNTHETIC", "09:35"), "DUPLICATE_SCALER_SESSION")
    refused("invalid_scale_cannot_epsilon_rescue", lambda: transform(-0.2, {"median": 0, "scale": 0}), "INVALID_SCALE")
    refused("positive_RZ_underflow_is_not_zero", lambda: transform(1e-300, {"median": 0, "scale": 1e100}), "NONZERO_UNDERFLOW")
    refused("negative_RZ_underflow_is_not_zero", lambda: transform(-1e-300, {"median": 0, "scale": 1e100}), "NONZERO_UNDERFLOW")
    refused("null_scaler_scope_is_not_identity", lambda: robust_scaler([{**r, "root": None} for r in history], 1000, None, "09:35"), "INVALID_SCALER_SCOPE")
    return {"schema": SPEC_VERSION, "evidence_class": "SYNTHETIC_REFERENCE_ONLY", "empirical_fit_performed": False,
            "production_compatible_schema": False, "availability_attested": False, "python": platform.python_version(),
            "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "case_count": len(results), "passed": len(results), "cases": results,
            "solver_policy": {"beta_domain": [-1, 1], "bracket_tolerance": BRACKET_TOLERANCE, "max_iterations": MAX_ITERATIONS,
                              "intercept": False, "epsilon_floor": False, "failed_row_fallback": False}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_fixtures()
    encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        # Research artifacts are created explicitly; existing evidence is not overwritten.
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    print(json.dumps({"case_count": result["case_count"], "passed": result["passed"],
                      "source_sha256": result["source_sha256"], "result_sha256": hashlib.sha256(encoded.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
