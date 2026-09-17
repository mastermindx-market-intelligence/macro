#!/usr/bin/env python3
"""Pure pre-outcome A0/A1 policy mechanics for the SPY 0DTE prereg.

No network, future path, outcome, gamma, sizing, signal, order, or production
trade authority. This module only freezes candidate/direction selection metadata.
"""
from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence

CLOCKS = ("09:35:00.000", "09:45:00.000", "10:00:00.000")
FAMILIES = ("bull_put", "bear_call")
A1_DIRECTION_MODES = ("contrarian_gap", "price_confirmed")
HELD_DIRECTION_MODES = ("dual_candidate",)
RISK_RULES = ("R0", "R1", "R2", "R3", "R4")
CREDIT_LOW = 0.08
CREDIT_HIGH = 0.15
PRIMARY_TP_DEBIT = 0.02
PRIMARY_SYNCHRONY_SECONDS = 1.0
TIME_CLOSE_MAX_AGE_SECONDS = 5.0
PRIMARY_FEE_PER_CONTRACT_SIDE = 0.65
BOOTSTRAP_BLOCK_SESSIONS = 5
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260917
MIN_DEVELOPMENT_TRADES = 100
MIN_VALIDATION_TRADES = 50
ES95_FLOOR_R = -0.50
WORST_SESSION_FLOOR_R = -1.05


class PolicyError(ValueError):
    pass


def _positive(value: Any, name: str) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"{name} is malformed") from exc
    if not math.isfinite(out) or out <= 0:
        raise PolicyError(f"{name} must be finite/positive")
    return out


def _family(candidate: Mapping[str, Any]) -> str:
    family = str(candidate.get("family", ""))
    if family not in FAMILIES:
        raise PolicyError("candidate family is not frozen")
    return family


def otm_distance(candidate: Mapping[str, Any], decision_price: Any) -> float:
    price = _positive(decision_price, "decision_price")
    strike = _positive(candidate.get("short_strike"), "short_strike")
    family = _family(candidate)
    return price - strike if family == "bull_put" else strike - price


def _credit_in_band(candidate: Mapping[str, Any]) -> bool:
    credit = _positive(candidate.get("entry_credit"), "entry_credit")
    return CREDIT_LOW - 1e-12 <= credit <= CREDIT_HIGH + 1e-12


def _rank_key(candidate: Mapping[str, Any], decision_price: float) -> tuple[float, float, float]:
    distance = otm_distance(candidate, decision_price)
    credit = _positive(candidate.get("entry_credit"), "entry_credit")
    strike = _positive(candidate.get("short_strike"), "short_strike")
    # Higher distance/credit wins. Final strike term makes exact ties deterministic.
    strike_tie = -strike if _family(candidate) == "bull_put" else strike
    return distance, credit, strike_tie


def select_a0_candidate(
    candidates: Sequence[Mapping[str, Any]], family: str, decision_price: Any
) -> Mapping[str, Any] | None:
    if family not in FAMILIES:
        raise PolicyError("A0 family is not frozen")
    price = _positive(decision_price, "decision_price")
    eligible = [
        c for c in candidates
        if _family(c) == family
        and _credit_in_band(c)
        and otm_distance(c, price) > 0
    ]
    return max(eligible, key=lambda c: _rank_key(c, price)) if eligible else None


def permitted_a1_family(features: Mapping[str, Any], direction_mode: str) -> str | None:
    if direction_mode not in A1_DIRECTION_MODES:
        raise PolicyError("A1 direction mode is not executable in the first wave")
    event_fomc = features.get("event_fomc")
    if event_fomc not in {0, 1}:
        return None
    if event_fomc == 1:
        return None
    gap = features.get("gap_direction")
    if gap not in {-1, 1}:
        return None
    if direction_mode == "price_confirmed":
        reversal = features.get("reversal_from_gap_extreme_flag")
        if reversal not in {0, 1} or reversal != 1:
            return None
    return "bull_put" if gap < 0 else "bear_call"


def containment_margin_sigma(
    candidate: Mapping[str, Any], features: Mapping[str, Any]
) -> float | None:
    move = features.get("expected_move_1sigma_abs")
    try:
        move_f = float(move)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(move_f) or move_f <= 0:
        return None
    strike = _positive(candidate.get("short_strike"), "short_strike")
    family = _family(candidate)
    boundary_key = "expected_move_lower" if family == "bull_put" else "expected_move_upper"
    try:
        boundary = float(features.get(boundary_key))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(boundary):
        return None
    margin = boundary - strike if family == "bull_put" else strike - boundary
    return margin / move_f


def select_a1_candidate(
    candidates: Sequence[Mapping[str, Any]],
    features: Mapping[str, Any],
    direction_mode: str,
) -> Mapping[str, Any] | None:
    family = permitted_a1_family(features, direction_mode)
    if family is None:
        return None
    decision_price = _positive(features.get("decision_price"), "decision_price")
    ranked: list[tuple[tuple[float, float, float, float], Mapping[str, Any]]] = []
    for candidate in candidates:
        if _family(candidate) != family or not _credit_in_band(candidate):
            continue
        margin = containment_margin_sigma(candidate, features)
        if margin is None or margin < 0 or otm_distance(candidate, decision_price) <= 0:
            continue
        distance, credit, strike_tie = _rank_key(candidate, decision_price)
        ranked.append(((margin, distance, credit, strike_tie), candidate))
    return max(ranked, key=lambda item: item[0])[1] if ranked else None


def structural_breach(family: str, short_strike: Any, completed_bar_close: Any) -> bool:
    if family not in FAMILIES:
        raise PolicyError("structural-breach family is not frozen")
    strike = _positive(short_strike, "short_strike")
    close = _positive(completed_bar_close, "completed_bar_close")
    return close < strike if family == "bull_put" else close > strike


def validation_grid() -> tuple[tuple[str, str, str, str], ...]:
    rows: list[tuple[str, str, str, str]] = []
    for clock in CLOCKS:
        for family in FAMILIES:
            for risk in RISK_RULES:
                rows.append(("A0", clock, family, risk))
        for direction in A1_DIRECTION_MODES:
            for risk in RISK_RULES:
                rows.append(("A1", clock, direction, risk))
    return tuple(rows)


def circular_block_bootstrap_means(
    values: Sequence[float], *,
    block_sessions: int = BOOTSTRAP_BLOCK_SESSIONS,
    replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
) -> tuple[float, ...]:
    """Deterministic circular moving-block bootstrap of a calendar-session series."""
    series = tuple(float(v) for v in values)
    if not series or not all(math.isfinite(v) for v in series):
        raise PolicyError("bootstrap series must be non-empty and finite")
    if block_sessions <= 0 or replicates <= 0:
        raise PolicyError("bootstrap dimensions must be positive")
    n = len(series)
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(replicates):
        total = 0.0
        count = 0
        while count < n:
            start = int(rng.random() * n)
            for offset in range(block_sessions):
                if count >= n:
                    break
                total += series[(start + offset) % n]
                count += 1
        means.append(total / n)
    return tuple(means)


def empirical_lower_bound(samples: Sequence[float], tail_probability: float = 0.05) -> float:
    """Non-interpolated empirical lower-tail order statistic."""
    ordered = sorted(float(v) for v in samples)
    if not ordered or not all(math.isfinite(v) for v in ordered):
        raise PolicyError("lower-bound samples must be non-empty and finite")
    if not 0 < tail_probability < 1:
        raise PolicyError("tail probability must be inside (0,1)")
    rank = max(1, math.ceil(tail_probability * len(ordered)))
    return ordered[rank - 1]


def expected_shortfall_95(values: Sequence[float]) -> float:
    """Mean of the worst ceil(5%) calendar-session net_R observations."""
    ordered = sorted(float(v) for v in values)
    if not ordered or not all(math.isfinite(v) for v in ordered):
        raise PolicyError("expected-shortfall series must be non-empty and finite")
    count = max(1, math.ceil(0.05 * len(ordered)))
    return sum(ordered[:count]) / count


def configuration_id(config: tuple[str, str, str, str]) -> str:
    if config not in set(validation_grid()):
        raise PolicyError("configuration is outside the frozen validation grid")
    return "|".join(config)


def select_highest_lower_bound(
    lower_bounds: Mapping[tuple[str, str, str, str], float]
) -> tuple[str, str, str, str]:
    if not lower_bounds:
        raise PolicyError("no eligible validation configurations")
    frozen = set(validation_grid())
    normalized: list[tuple[float, str, tuple[str, str, str, str]]] = []
    for config, value in lower_bounds.items():
        if config not in frozen:
            raise PolicyError("validation score contains an unfrozen configuration")
        score = float(value)
        if not math.isfinite(score):
            raise PolicyError("validation lower bound is not finite")
        normalized.append((score, configuration_id(config), config))
    best_score = max(row[0] for row in normalized)
    tied = [row for row in normalized if row[0] == best_score]
    return min(tied, key=lambda row: row[1])[2]


def holm_bonferroni_rejections(
    p_values: Mapping[str, float], *, alpha: float = 0.05
) -> dict[str, bool]:
    """Deterministic Holm step-down decisions for a frozen confirmatory family."""
    if not p_values:
        raise PolicyError("Holm family must be non-empty")
    if not 0 < alpha < 1:
        raise PolicyError("Holm alpha must be inside (0,1)")
    ordered: list[tuple[float, str]] = []
    for name, value in p_values.items():
        p_value = float(value)
        if not math.isfinite(p_value) or not 0 <= p_value <= 1:
            raise PolicyError("Holm p-value must be finite inside [0,1]")
        ordered.append((p_value, str(name)))
    ordered.sort(key=lambda row: (row[0], row[1]))
    m = len(ordered)
    rejected = {name: False for _, name in ordered}
    still_rejecting = True
    for index, (p_value, name) in enumerate(ordered):
        threshold = alpha / (m - index)
        if still_rejecting and p_value <= threshold:
            rejected[name] = True
        else:
            still_rejecting = False
    return rejected
