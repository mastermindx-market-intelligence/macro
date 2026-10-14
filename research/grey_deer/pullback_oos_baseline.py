"""Research-only empirical future-low quantiles and held-out score algebra.

No I/O, no model registry, no publisher, no live risk score, no capital sizing.
Do not import into the site render path. This consumes *matured outcome labels*
from the causal labeler, never future path information as a contemporaneous
feature. Current-source-vintage and episode-proxy limitations still apply.
"""
from __future__ import annotations

from datetime import date
from math import isfinite
from numbers import Real
from statistics import fmean
from typing import Iterable, Mapping

SCHEMA = "pullback_empirical_baseline_research.v1"


def _date(label: object, field: str) -> date:
    if not isinstance(label, str) or len(label) != 10:
        raise ValueError(f"{field} must be YYYY-MM-DD")
    try:
        day = date.fromisoformat(label)
    except ValueError as exc:
        raise ValueError(f"invalid {field}") from exc
    if day.isoformat() != label:
        raise ValueError(f"{field} must be canonical YYYY-MM-DD")
    return day


def _loss(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field} must be a loss fraction")
    try:
        x = float(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError(f"{field} invalid") from exc
    if not isfinite(x) or not 0 <= x <= 1:
        raise ValueError(f"{field} outside [0,1]")
    return x


def _interpolated_quantile(sorted_losses: list[float], probability: float) -> float:
    loc = (len(sorted_losses) - 1) * probability
    i = int(loc)
    if i == len(sorted_losses) - 1:
        return sorted_losses[-1]
    portion = loc - i
    return sorted_losses[i] * (1.0 - portion) + sorted_losses[i + 1] * portion


def predict_research_quantiles(
    outcomes: Iterable[Mapping], *,
    forecast_origin: str,
    training_end_exclusive: str,
    market: str,
    price_basis: str,
    phase: str | None,
    horizon_sessions: int,
    min_origins: int = 30,
    min_episodes: int = 20,
) -> dict:
    """Fit a frozen pre-holdout empirical baseline; never return a live estimate.

    Scope keys, exact-phase membership, label maturation, and both time cutoffs
    are explicit. Neither test outcomes nor immature overlapping training labels
    may train this model. Distinct peak dates are *proxies*, not independent
    issued-episode IDs; a minimum count is a pilot gate, not final calibration.
    """
    when = _date(forecast_origin, "forecast_origin")
    freeze = _date(training_end_exclusive, "training_end_exclusive")
    if when < freeze:
        raise ValueError("forecast origin precedes held-out evaluation period")
    if not market or not price_basis:
        raise ValueError("market and price basis are required")
    if (isinstance(horizon_sessions, bool) or not isinstance(horizon_sessions, int)
            or horizon_sessions not in (5, 10, 21)):
        raise ValueError("only prespecified 5, 10 or 21 session horizons are admitted")
    if (isinstance(min_origins, bool) or isinstance(min_episodes, bool)
            or not isinstance(min_origins, int) or not isinstance(min_episodes, int)
            or min_origins < 1 or min_episodes < 1):
        raise ValueError("positive sample gates required")
    if phase is not None and phase not in (
        "monitoring", "developing", "underway", "stabilizing",
        "recovering", "repaired",
    ):
        raise ValueError("phase must be an observed price phase or None")

    chosen: list[float] = []
    proxies: set[str] = set()
    result = {
        "schema": SCHEMA,
        "state": "unavailable",
        "publication_authorized": False,
        "reason": None,
        "market": market,
        "price_basis": price_basis,
        "forecast_origin": forecast_origin,
        "training_end_exclusive": training_end_exclusive,
        "phase": phase,
        "horizon_sessions": horizon_sessions,
        "training_origins": 0,
        "distinct_episode_proxies": 0,
        "q25": None, "q75": None, "q90": None,
    }
    for row in outcomes:
        if not isinstance(row, Mapping):
            raise ValueError("training row must be a mapping")
        if row.get("market") != market or row.get("price_basis") != price_basis:
            continue
        if phase is not None and row.get("phase") != phase:
            continue
        label = row.get("label")
        if not isinstance(label, Mapping) or label.get("horizon_sessions") != horizon_sessions:
            continue
        if label.get("matured") is not True:
            continue
        training_origin = _date(label.get("origin"), "training origin")
        label_end = _date(label.get("target_end"), "mature label end")
        if (training_origin >= freeze or label_end >= freeze
                or label_end >= when):
            continue
        if label_end < training_origin:
            raise ValueError("label ends before its forecast origin")
        y = _loss(label.get("additional_loss_fraction"), "mature label")
        chosen.append(y)
        proxy = row.get("episode_proxy")
        if not isinstance(proxy, str) or not proxy.strip():
            # The owning observer must provide a real retained-peak proxy;
            # missing episode provenance is NOT independent evidence.
            raise ValueError("training episode proxy unavailable")
        proxies.add(proxy.strip())
    result["training_origins"] = len(chosen)
    result["distinct_episode_proxies"] = len(proxies)
    if len(chosen) < min_origins:
        return {**result, "reason": "insufficient_training_origins"}
    if len(proxies) < min_episodes:
        return {**result, "reason": "insufficient_episode_proxies"}
    values = sorted(chosen)
    return {
        **result,
        "state": "research_only",
        "reason": None,
        "q25": _interpolated_quantile(values, 0.25),
        "q75": _interpolated_quantile(values, 0.75),
        "q90": _interpolated_quantile(values, 0.90),
    }


def pinball(probability: float, *, y: float, qhat: float) -> float:
    """Nonnegative conditional-quantile score (smaller is better)."""
    if isinstance(probability, bool) or probability not in (0.25, 0.75, 0.9):
        raise ValueError("probability must be a prespecified quantile")
    outcome = _loss(y, "outcome")
    estimate = _loss(qhat, "quantile estimate")
    residual = outcome - estimate
    return (probability - (1.0 if residual < 0 else 0.0)) * residual


def evaluate_research_predictions(cases: Iterable[Mapping]) -> dict:
    """Describe held-out coverage and loss; absolutely no publication verdict."""
    ys: list[float] = []
    qs: dict[float, list[float]] = {0.25: [], 0.75: [], 0.9: []}
    unavailable = 0
    for row in cases:
        if not isinstance(row, Mapping):
            raise ValueError("evaluation row must be a mapping")
        candidate = row.get("estimate")
        if not isinstance(candidate, Mapping):
            raise ValueError("candidate must be a mapping")
        if candidate.get("publication_authorized") is True:
            raise ValueError("research evaluator cannot consume promoted predictions")
        if candidate.get("state") == "unavailable":
            unavailable += 1
            continue
        if candidate.get("state") != "research_only":
            raise ValueError("unrecognized candidate")
        y = _loss(row.get("observed_loss"), "held-out outcome")
        v = {q: _loss(candidate.get(k), f"{k} estimate")
             for q, k in [(0.25, "q25"), (0.75, "q75"), (0.9, "q90")]}
        if not (v[0.25] <= v[0.75] <= v[0.9]):
            raise ValueError("crossing predictive quantiles")
        ys.append(y)
        for q in qs:
            qs[q].append(v[q])
    result = {
        "schema": "pullback_quantile_evaluation_research.v1",
        "publication_authorized": False,
        "evaluated_origins": len(ys),
        "unavailable_origins": unavailable,
        "interval_coverage": None,
        "interval_width": None,
        "q90_exceedance": None,
        "pinball_q25": None,
        "pinball_q75": None,
        "pinball_q90": None,
    }
    if not ys:
        return result
    n = len(ys)
    return {
        **result,
        "interval_coverage": sum(qs[0.25][i] <= ys[i] <= qs[0.75][i]
                                 for i in range(n)) / n,
        "interval_width": fmean(qs[0.75][i] - qs[0.25][i] for i in range(n)),
        "q90_exceedance": sum(ys[i] > qs[0.9][i] for i in range(n)) / n,
        "pinball_q25": fmean(pinball(0.25, y=ys[i], qhat=qs[0.25][i]) for i in range(n)),
        "pinball_q75": fmean(pinball(0.75, y=ys[i], qhat=qs[0.75][i]) for i in range(n)),
        "pinball_q90": fmean(pinball(0.9, y=ys[i], qhat=qs[0.9][i]) for i in range(n)),
    }
