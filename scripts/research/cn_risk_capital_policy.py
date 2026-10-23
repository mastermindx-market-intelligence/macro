"""Frozen China Risk Radar capital-policy replay and adjudication harness.

Research-only. It reads the exact live Radar state construction but never writes to
live data, engine, templates, allocation, execution, or authority paths. Historical
results are explicitly reconstructed rather than issued-forward policy performance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PREREG_PATH = ROOT / "research/cn_risk_capital_policy/preregistration.json"
RESULTS_DIR = ROOT / "research/cn_risk_capital_policy/results"
FORWARD_LOG = ROOT / "data/risk_radar_intl/cn_forward_log.jsonl"
ALLOWED_VERDICTS = (
    "CURRENT_LADDER_VALIDATED_FOR_ADVISORY_REFERENCE",
    "HAZARD_VALID_BUT_EXACT_GROSS_UNVALIDATED",
    "SIMPLER_POLICY_SUPPORTED",
    "NO_SIZING_EDGE / DISPLAY_CONTEXT_ONLY",
    "INSUFFICIENT_INDEPENDENT_EPISODES",
)


def load_preregistration(path: Path | str = PREREG_PATH) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema") != "cn_risk_capital_policy_prereg.v1":
        raise ValueError("unexpected or missing capital-policy preregistration schema")
    return payload


def sha256_file(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def assert_live_mapping_matches_prereg(prereg: dict[str, Any]) -> dict[str, float]:
    from engine import risk_radar_intl as radar

    actual = {str(key): float(value) for key, value in radar._GROSS.items()}
    expected = {str(key): float(value) for key, value in prereg["current_mapping"].items()}
    if actual != expected:
        raise RuntimeError(f"live gross mapping differs from frozen preregistration: {actual!r}")
    return actual


def _validate_series(series: pd.Series, name: str) -> pd.Series:
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError(f"{name} requires a DatetimeIndex")
    if not series.index.is_monotonic_increasing or not series.index.is_unique:
        raise ValueError(f"{name} index must be unique and increasing")
    return series.copy()


def target_gross(
    policy: str,
    states: pd.Series,
    benchmark_returns: pd.Series,
    prereg: dict[str, Any],
) -> pd.Series:
    """Return close-t target gross before execution lag is applied."""
    states = _validate_series(states, "states")
    benchmark_returns = _validate_series(benchmark_returns, "benchmark_returns")
    idx = states.index.intersection(benchmark_returns.index)
    states = states.reindex(idx)
    returns = pd.to_numeric(benchmark_returns.reindex(idx), errors="coerce")
    fixed = prereg["fixed_policies"]

    if policy == "matched_constant":
        raise KeyError(
            "matched_constant is constructed from executed current-ladder gross "
            "after applying the frozen scenario lag"
        )
    if policy == "vol_target_15":
        spec = fixed[policy]
        lookback = int(spec["lookback"])
        realized = returns.rolling(lookback, min_periods=lookback).std(ddof=1) * math.sqrt(252.0)
        target = float(spec["annual_target"]) / realized.replace(0.0, np.nan)
        target = target.clip(lower=float(spec["floor"]), upper=float(spec["cap"]))
        return target.fillna(1.0).rename(policy)
    if policy not in fixed:
        raise KeyError(f"unknown preregistered policy: {policy}")

    mapping = fixed[policy]
    if "all" in mapping:
        return pd.Series(float(mapping["all"]), index=idx, name=policy)
    missing = sorted(set(states.dropna().unique()) - set(mapping))
    if missing:
        raise ValueError(f"policy {policy} has no mapping for states: {missing}")
    return states.map({key: float(value) for key, value in mapping.items()}).astype(float).rename(policy)


def execute_policy(
    benchmark_returns: pd.Series,
    target: pd.Series,
    *,
    lag: int,
    cost_bps: float,
) -> pd.DataFrame:
    """Apply a frozen target gross with explicit lag and one-way turnover costs."""
    if lag < 0:
        raise ValueError("lag must be non-negative")
    if cost_bps < 0:
        raise ValueError("cost_bps must be non-negative")
    returns = _validate_series(benchmark_returns, "benchmark_returns")
    target = _validate_series(target, "target_gross")
    idx = returns.index.intersection(target.index)
    returns = pd.to_numeric(returns.reindex(idx), errors="coerce")
    target = pd.to_numeric(target.reindex(idx), errors="coerce").clip(lower=0.0, upper=1.0)
    executed = target.shift(lag)
    frame = pd.DataFrame({
        "benchmark_return": returns,
        "target_gross": target,
        "executed_gross": executed,
    }).dropna(subset=["benchmark_return", "executed_gross"])
    if frame.empty:
        raise ValueError("no executable observations after alignment and lag")
    frame["turnover"] = frame["executed_gross"].diff().abs().fillna(0.0)
    frame["transaction_cost"] = frame["turnover"] * (float(cost_bps) / 10000.0)
    frame["full_gross_return"] = frame["benchmark_return"]
    frame["policy_return"] = (
        frame["executed_gross"] * frame["benchmark_return"] - frame["transaction_cost"]
    )
    frame["missed_upside"] = (
        (1.0 - frame["executed_gross"]) * frame["benchmark_return"].clip(lower=0.0)
    )
    frame["avoided_downside"] = (
        (1.0 - frame["executed_gross"]) * (-frame["benchmark_return"].clip(upper=0.0))
    )
    frame["excess_vs_full"] = frame["policy_return"] - frame["full_gross_return"]
    return frame


def matched_constant_target(
    current_frame: pd.DataFrame,
    target_index: pd.DatetimeIndex,
) -> pd.Series:
    """Construct the sole exposure-matched baseline from executed current gross."""
    if "executed_gross" not in current_frame.columns:
        raise ValueError("current policy frame has no executed_gross column")
    mean_gross = float(pd.to_numeric(current_frame["executed_gross"], errors="coerce").mean())
    if not np.isfinite(mean_gross):
        raise ValueError("current policy frame has no finite executed gross")
    return pd.Series(mean_gross, index=target_index, name="matched_constant")


def _return_metrics(values: np.ndarray) -> dict[str, float | None]:
    returns = np.asarray(values, dtype=float)
    returns = returns[np.isfinite(returns)]
    n = len(returns)
    if n == 0:
        raise ValueError("return metrics require at least one finite observation")
    wealth = np.cumprod(1.0 + returns)
    final_wealth = float(wealth[-1])
    total_return = final_wealth - 1.0
    cagr = final_wealth ** (252.0 / n) - 1.0 if final_wealth > 0 else -1.0
    annual_mean = float(np.mean(returns) * 252.0)
    daily_std = float(np.std(returns, ddof=1)) if n > 1 else 0.0
    annual_vol = daily_std * math.sqrt(252.0)
    sharpe = annual_mean / annual_vol if annual_vol > 0 else None
    downside = np.minimum(returns, 0.0)
    downside_dev = float(np.sqrt(np.mean(np.square(downside))) * math.sqrt(252.0))
    sortino = annual_mean / downside_dev if downside_dev > 0 else None
    running_peak = np.maximum.accumulate(np.concatenate(([1.0], wealth)))[1:]
    drawdowns = wealth / running_peak - 1.0
    max_drawdown = float(np.min(drawdowns))
    tail_n = max(1, int(math.ceil(n * 0.05)))
    cvar_95 = float(np.mean(np.sort(returns)[:tail_n]))
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else None
    variance = float(np.var(returns, ddof=1)) if n > 1 else 0.0
    certainty_equivalent = annual_mean - 0.5 * 3.0 * variance * 252.0
    return {
        "n_sessions": int(n),
        "total_return": total_return,
        "cagr": cagr,
        "annualized_mean_return": annual_mean,
        "annualized_volatility": annual_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "cvar_95": cvar_95,
        "calmar": calmar,
        "certainty_equivalent": certainty_equivalent,
    }


def performance_metrics(frame: pd.DataFrame) -> dict[str, float | int | None]:
    required = {
        "benchmark_return", "policy_return", "executed_gross", "turnover",
        "transaction_cost", "missed_upside", "avoided_downside", "excess_vs_full",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"policy frame missing columns: {missing}")
    metrics: dict[str, float | int | None] = dict(
        _return_metrics(frame["policy_return"].to_numpy(dtype=float))
    )
    full = _return_metrics(frame["benchmark_return"].to_numpy(dtype=float))
    n = int(metrics["n_sessions"] or 0)
    metrics.update({
        "full_gross_total_return": full["total_return"],
        "total_return_delta_vs_full": (
            float(metrics["total_return"]) - float(full["total_return"])
        ),
        "average_gross": float(frame["executed_gross"].mean()),
        "time_reduced": float((frame["executed_gross"] < 1.0 - 1e-12).mean()),
        "turnover": float(frame["turnover"].sum()),
        "annualized_turnover": float(frame["turnover"].sum() * 252.0 / n),
        "exposure_change_count": int((frame["turnover"] > 1e-12).sum()),
        "transaction_cost": float(frame["transaction_cost"].sum()),
        "missed_upside": float(frame["missed_upside"].sum()),
        "avoided_downside": float(frame["avoided_downside"].sum()),
        "policy_excess_vs_full": float(frame["excess_vs_full"].sum()),
    })
    return metrics


def _compound(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    return float(np.prod(1.0 + values) - 1.0) if len(values) else 0.0


def _path_drawdown_from_start(returns: pd.Series) -> float:
    values = pd.to_numeric(returns, errors="coerce").dropna().to_numpy(dtype=float)
    if not len(values):
        return 0.0
    wealth = np.cumprod(1.0 + values)
    return float(np.min(wealth - 1.0))


def find_loud_episodes(
    states: pd.Series,
    *,
    max_non_loud_gap: int,
    min_loud_observations: int,
    post_window_sessions: int,
) -> list[dict[str, Any]]:
    """Group loud observations without treating overlapping days as independent N."""
    states = _validate_series(states, "states")
    loud_mask = states.isin(["elevated", "risk-off"]).to_numpy()
    loud_positions = np.flatnonzero(loud_mask)
    if not len(loud_positions):
        return []
    groups: list[list[int]] = [[int(loud_positions[0])]]
    for position in loud_positions[1:]:
        position = int(position)
        non_loud_gap = position - groups[-1][-1] - 1
        if non_loud_gap <= max_non_loud_gap:
            groups[-1].append(position)
        else:
            groups.append([position])
    episodes: list[dict[str, Any]] = []
    for group in groups:
        if len(group) < min_loud_observations:
            continue
        first, last = group[0], group[-1]
        requested_outcome_pos = last + int(post_window_sessions)
        outcome_complete = requested_outcome_pos < len(states)
        outcome_pos = min(len(states) - 1, requested_outcome_pos)
        episode_states = states.iloc[group]
        episodes.append({
            "episode_id": len(episodes) + 1,
            "start": states.index[first],
            "end": states.index[last],
            "outcome_end": states.index[outcome_pos],
            "start_pos": first,
            "end_pos": last,
            "outcome_end_pos": outcome_pos,
            "outcome_complete": outcome_complete,
            "loud_observations": len(group),
            "contains_risk_off": bool(episode_states.eq("risk-off").any()),
            "elevated_observations": int(episode_states.eq("elevated").sum()),
            "risk_off_observations": int(episode_states.eq("risk-off").sum()),
        })
    for index, episode in enumerate(episodes):
        next_start_pos = (
            int(episodes[index + 1]["start_pos"])
            if index + 1 < len(episodes)
            else None
        )
        overlaps_next = bool(
            episode["outcome_complete"]
            and next_start_pos is not None
            and int(episode["outcome_end_pos"]) >= next_start_pos
        )
        episode["next_episode_start_pos"] = next_start_pos
        episode["overlaps_next_episode"] = overlaps_next
        episode["authority_independent"] = bool(
            episode["outcome_complete"] and not overlaps_next
        )
    return episodes


def authority_independent_episodes(
    episodes: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return complete episode windows that do not bleed into the next alert."""
    return [episode for episode in episodes if bool(episode.get("authority_independent"))]


def analyze_episodes(
    frame: pd.DataFrame,
    states: pd.Series,
    episodes: Iterable[dict[str, Any]],
    *,
    downside_threshold: float = -0.05,
) -> list[dict[str, Any]]:
    """Measure protection, false positives, and recovery participation by episode."""
    rows: list[dict[str, Any]] = []
    for episode in episodes:
        start = pd.Timestamp(episode["start"])
        end = pd.Timestamp(episode["end"])
        outcome_end = pd.Timestamp(episode["outcome_end"])
        window = frame.loc[(frame.index >= start) & (frame.index <= outcome_end)]
        alert = frame.loc[(frame.index >= start) & (frame.index <= end)]
        recovery = frame.loc[(frame.index > end) & (frame.index <= outcome_end)]
        if window.empty:
            continue
        benchmark_path_loss = _path_drawdown_from_start(window["benchmark_return"])
        recovery_full = _compound(recovery["benchmark_return"]) if not recovery.empty else 0.0
        recovery_policy = _compound(recovery["policy_return"]) if not recovery.empty else 0.0
        recovery_capture = (
            recovery_policy / recovery_full if recovery_full > 0 else None
        )
        row = {
            **episode,
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            "outcome_end": outcome_end.date().isoformat(),
            "downside_event": bool(benchmark_path_loss <= downside_threshold),
            "benchmark_path_loss": benchmark_path_loss,
            "alert_policy_return": _compound(alert["policy_return"]),
            "alert_full_return": _compound(alert["benchmark_return"]),
            "window_policy_return": _compound(window["policy_return"]),
            "window_full_return": _compound(window["benchmark_return"]),
            "policy_excess": float(window["excess_vs_full"].sum()),
            "positive_timing_benefit": bool(window["excess_vs_full"].sum() > 0),
            "recovery_policy_return": recovery_policy,
            "recovery_full_return": recovery_full,
            "recovery_capture": recovery_capture,
            "recovery_average_gross": (
                float(recovery["executed_gross"].mean()) if not recovery.empty else None
            ),
            "recovery_missed_upside": (
                float(recovery["missed_upside"].sum()) if not recovery.empty else 0.0
            ),
        }
        rows.append(_jsonable(row))
    return rows


def _moving_block_indices(
    n: int, block_sessions: int, rng: np.random.Generator
) -> np.ndarray:
    if n <= 0 or block_sessions <= 0:
        raise ValueError("n and block_sessions must be positive")
    blocks = int(math.ceil(n / block_sessions))
    starts = rng.integers(0, n, size=blocks)
    pieces = [
        (int(start) + np.arange(block_sessions, dtype=int)) % n
        for start in starts
    ]
    return np.concatenate(pieces)[:n]


def bootstrap_pair(
    frame_a: pd.DataFrame,
    frame_b: pd.DataFrame,
    *,
    draws: int,
    block_sessions: int,
    seed: int,
    ci: float,
) -> dict[str, list[float]]:
    """Paired circular moving-block intervals for risk/return metric differences."""
    if not 0 < ci < 1:
        raise ValueError("ci must be between zero and one")
    idx = frame_a.index.intersection(frame_b.index)
    a = frame_a.reindex(idx)["policy_return"].to_numpy(dtype=float)
    b = frame_b.reindex(idx)["policy_return"].to_numpy(dtype=float)
    good = np.isfinite(a) & np.isfinite(b)
    a, b = a[good], b[good]
    if not len(a):
        raise ValueError("bootstrap pair has no aligned finite returns")
    metric_map = {
        "cagr_diff": "cagr",
        "max_drawdown_diff": "max_drawdown",
        "cvar_95_diff": "cvar_95",
        "calmar_diff": "calmar",
        "certainty_equivalent_diff": "certainty_equivalent",
    }
    samples = {name: [] for name in metric_map}
    rng = np.random.default_rng(seed)
    for _ in range(int(draws)):
        take = _moving_block_indices(len(a), int(block_sessions), rng)
        ma = _return_metrics(a[take])
        mb = _return_metrics(b[take])
        for output_name, metric_name in metric_map.items():
            av, bv = ma[metric_name], mb[metric_name]
            if av is None or bv is None:
                samples[output_name].append(np.nan)
            else:
                samples[output_name].append(float(av) - float(bv))
    alpha = (1.0 - float(ci)) / 2.0
    out: dict[str, list[float]] = {}
    for name, values in samples.items():
        clean = np.asarray(values, dtype=float)
        clean = clean[np.isfinite(clean)]
        if not len(clean):
            out[name] = [math.nan, math.nan, math.nan]
        else:
            out[name] = [
                float(np.quantile(clean, alpha)),
                float(np.quantile(clean, 0.5)),
                float(np.quantile(clean, 1.0 - alpha)),
            ]
    return out


def _relative_protection(candidate: float, baseline: float) -> float:
    denominator = abs(float(baseline))
    if denominator <= 0:
        return 0.0
    return (denominator - abs(float(candidate))) / denominator


def _metric(summary: dict[str, Any], policy: str, metric: str) -> float:
    value = summary["primary"][policy][metric]
    if value is None:
        return math.nan
    return float(value)


def adjudicate(
    summary: dict[str, Any], prereg: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    """Apply the frozen decision tree without optimizing thresholds after results."""
    p = prereg["promotion"]
    historical_authority_eligible = bool(summary["historical_authority_eligible"])
    n = int(summary["authority_effective_episode_n"])
    n_riskoff = int(summary["authority_riskoff_episode_n"])
    n_elevated = int(summary["authority_elevated_only_episode_n"])
    crisis_count = len(prereg["crises"])

    cur_mdd = _metric(summary, "current_ladder", "max_drawdown")
    cur_cvar = _metric(summary, "current_ladder", "cvar_95")
    cur_calmar = _metric(summary, "current_ladder", "calmar")
    cur_cagr = _metric(summary, "current_ladder", "cagr")
    full_mdd = _metric(summary, "constant_100", "max_drawdown")
    full_cvar = _metric(summary, "constant_100", "cvar_95")
    full_calmar = _metric(summary, "constant_100", "calmar")
    full_cagr = _metric(summary, "constant_100", "cagr")
    matched_calmar = _metric(summary, "matched_constant", "calmar")
    matched_cvar = _metric(summary, "matched_constant", "cvar_95")
    floor_mdd = _metric(summary, "current_riskoff_075", "max_drawdown")
    floor_calmar = _metric(summary, "current_riskoff_075", "calmar")
    floor_cagr = _metric(summary, "current_riskoff_075", "cagr")

    exact_checks = {
        "historical_authority_eligible": historical_authority_eligible,
        "episode_floor": n >= int(p["exact_min_episodes"]),
        "riskoff_episode_floor": n_riskoff >= int(p["exact_min_riskoff_episodes"]),
        "elevated_only_episode_floor": n_elevated >= int(p["exact_min_elevated_only_episodes"]),
        "mdd_protection": _relative_protection(cur_mdd, full_mdd) >= float(p["mdd_relative_improvement"]),
        "cvar_protection": _relative_protection(cur_cvar, full_cvar) >= float(p["cvar_relative_improvement"]),
        "calmar_vs_full_and_matched": cur_calmar > full_calmar and cur_calmar > matched_calmar,
        "cagr_cost": (full_cagr - cur_cagr) * 100.0 <= float(p["max_cagr_penalty_pp"]),
        "certainty_equivalent_ci": (
            float(summary["bootstrap"]["current_vs_matched"]["certainty_equivalent_diff"][0]) > 0.0
        ),
        "riskoff_062_mdd_increment": (
            (abs(floor_mdd) - abs(cur_mdd)) * 100.0 + 1e-12
            >= float(p["exact_vs_075_mdd_pp"])
        ),
        "riskoff_062_calmar": cur_calmar >= floor_calmar,
        "riskoff_062_cagr_cost": (
            (floor_cagr - cur_cagr) * 100.0 <= float(p["exact_vs_075_max_cagr_penalty_pp"])
        ),
        "sensitivity": bool(summary["sensitivity_pass"]["current_ladder"]),
        "era_stability": bool(summary["era_pass"]["current_ladder"]),
        "all_loco": int(summary["loco_positive_count"]["current_ladder"]) >= crisis_count,
        "crisis_concentration": (
            float(summary["crisis_concentration"]["current_ladder"])
            < float(p["exact_max_crisis_concentration"])
        ),
    }
    exact_pass = all(exact_checks.values())

    binary_mdd = _metric(summary, "binary_loud_075", "max_drawdown")
    binary_cvar = _metric(summary, "binary_loud_075", "cvar_95")
    binary_calmar = _metric(summary, "binary_loud_075", "calmar")
    binary_cagr = _metric(summary, "binary_loud_075", "cagr")
    simple_checks = {
        "historical_authority_eligible": historical_authority_eligible,
        "episode_floor": n >= int(p["simple_min_episodes"]),
        "riskoff_episode_floor": n_riskoff >= int(p["simple_min_riskoff_episodes"]),
        "mdd_protection": _relative_protection(binary_mdd, full_mdd) >= float(p["mdd_relative_improvement"]),
        "cvar_protection": _relative_protection(binary_cvar, full_cvar) >= float(p["cvar_relative_improvement"]),
        "calmar_vs_full_and_matched": binary_calmar > full_calmar and binary_calmar > matched_calmar,
        "cagr_cost": (full_cagr - binary_cagr) * 100.0 <= float(p["max_cagr_penalty_pp"]),
        "certainty_equivalent_ci": (
            float(summary["bootstrap"]["binary_vs_matched"]["certainty_equivalent_diff"][0]) > 0.0
        ),
        "positive_episode_fraction": (
            float(summary["positive_episode_fraction"]["binary_loud_075"])
            >= float(p["simple_positive_episode_fraction"])
        ),
        "sensitivity": bool(summary["sensitivity_pass"]["binary_loud_075"]),
        "era_stability": bool(summary["era_pass"]["binary_loud_075"]),
        "loco": int(summary["loco_positive_count"]["binary_loud_075"]) >= 8,
        "crisis_concentration": (
            float(summary["crisis_concentration"]["binary_loud_075"])
            < float(p["simple_max_crisis_concentration"])
        ),
    }
    simple_pass = all(simple_checks.values())

    if exact_pass:
        verdict = ALLOWED_VERDICTS[0]
    elif simple_pass:
        verdict = ALLOWED_VERDICTS[2]
    elif n < int(p["simple_min_episodes"]) or n_riskoff < int(p["simple_min_riskoff_episodes"]):
        verdict = ALLOWED_VERDICTS[4]
    else:
        current_edge = cur_calmar > matched_calmar and cur_cvar > matched_cvar
        binary_edge = binary_calmar > matched_calmar and binary_cvar > matched_cvar
        verdict = ALLOWED_VERDICTS[1] if (current_edge or binary_edge) else ALLOWED_VERDICTS[3]
    return verdict, {
        "exact_current_pass": exact_pass,
        "simple_binary_pass": simple_pass,
        "exact_checks": exact_checks,
        "simple_checks": simple_checks,
    }


def ui_language_verdict(verdict: str) -> dict[str, Any]:
    if verdict not in ALLOWED_VERDICTS:
        raise ValueError(f"unknown product verdict: {verdict}")
    exact = verdict == "CURRENT_LADDER_VALIDATED_FOR_ADVISORY_REFERENCE"
    return {
        "may_say_suggested_size": False,
        "may_say_risk_budget_reference": exact,
        "may_show_x062_as_advice": exact,
        "may_show_x062_in_research_disclosure": True,
        "should_round_plain_english_fraction": False,
        "authority_level": (
            "ADVISORY_REFERENCE_NON_AUTOMATIC" if exact else "DISPLAY_CONTEXT_ONLY"
        ),
        "live_policy_promotion_authorized": False,
        "can_force_change_authorized": False,
        "trade_or_exit_authority": False,
    }


def analyze_crises(
    frame: pd.DataFrame,
    crises: dict[str, list[str]],
    *,
    recovery_sessions: int = 63,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, bounds in crises.items():
        start, end = pd.Timestamp(bounds[0]), pd.Timestamp(bounds[1])
        if start < frame.index.min() or end > frame.index.max():
            continue
        crisis = frame.loc[(frame.index >= start) & (frame.index <= end)]
        if crisis.empty:
            continue
        crisis_policy = _return_metrics(crisis["policy_return"].to_numpy(dtype=float))
        crisis_full = _return_metrics(crisis["benchmark_return"].to_numpy(dtype=float))
        end_pos = int(frame.index.searchsorted(end, side="right"))
        recovery = frame.iloc[end_pos:end_pos + int(recovery_sessions)]
        recovery_policy = _compound(recovery["policy_return"]) if not recovery.empty else 0.0
        recovery_full = _compound(recovery["benchmark_return"]) if not recovery.empty else 0.0
        rows.append(_jsonable({
            "crisis": name,
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            "n_sessions": len(crisis),
            "policy_return": crisis_policy["total_return"],
            "full_return": crisis_full["total_return"],
            "protection_vs_full": (
                float(crisis_policy["total_return"]) - float(crisis_full["total_return"])
            ),
            "policy_max_drawdown": crisis_policy["max_drawdown"],
            "full_max_drawdown": crisis_full["max_drawdown"],
            "max_drawdown_improvement": (
                float(crisis_policy["max_drawdown"]) - float(crisis_full["max_drawdown"])
            ),
            "policy_cvar_95": crisis_policy["cvar_95"],
            "full_cvar_95": crisis_full["cvar_95"],
            "recovery_sessions": len(recovery),
            "recovery_policy_return": recovery_policy,
            "recovery_full_return": recovery_full,
            "recovery_capture": (
                recovery_policy / recovery_full if recovery_full > 0 else None
            ),
            "recovery_average_gross": (
                float(recovery["executed_gross"].mean()) if not recovery.empty else None
            ),
            "recovery_missed_upside": (
                float(recovery["missed_upside"].sum()) if not recovery.empty else 0.0
            ),
        }))
    return rows


def leave_one_crisis_out(
    frame: pd.DataFrame, crises: dict[str, list[str]]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, bounds in crises.items():
        start, end = pd.Timestamp(bounds[0]), pd.Timestamp(bounds[1])
        kept = frame.loc[~((frame.index >= start) & (frame.index <= end))]
        metrics = performance_metrics(kept)
        rows.append(_jsonable({"excluded_crisis": name, **metrics}))
    return rows


def crisis_concentration(crisis_rows: Iterable[dict[str, Any]]) -> float:
    positive = [
        float(row["protection_vs_full"])
        for row in crisis_rows
        if row.get("protection_vs_full") is not None
        and float(row["protection_vs_full"]) > 0.0
    ]
    if not positive:
        return 1.0
    return float(max(positive) / sum(positive))


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _population_fingerprint(frame: pd.DataFrame) -> str:
    rows = [
        [
            timestamp.isoformat(),
            str(row.state),
            float(row.benchmark_close).hex(),
            float(row.radar_score).hex(),
            bool(row.gate_open),
        ]
        for timestamp, row in frame.iterrows()
    ]
    encoded = json.dumps(rows, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def reconstruct_cn_state_frame(prereg: dict[str, Any]) -> pd.DataFrame:
    """Reconstruct the exact pinned-base CN Radar state, causally and read-only."""
    from engine import risk_radar_intl as radar

    assert_live_mapping_matches_prereg(prereg)
    benchmark, _, composite, gate = radar.composite_series(radar.CN_PROFILE)
    if benchmark is None or composite is None or gate is None:
        raise RuntimeError("CN Radar reconstruction returned no usable series")
    idx = benchmark.index.intersection(composite.dropna().index)
    frame = pd.DataFrame({
        "benchmark_close": benchmark.reindex(idx),
        "radar_score": composite.reindex(idx) * 100.0,
        "gate_open": gate.reindex(idx).fillna(False).astype(bool),
    }).dropna(subset=["benchmark_close", "radar_score"])
    ungated = frame["radar_score"].map(
        lambda value: radar._band(float(value), radar.CN_PROFILE.bands)
    )
    state = ungated.copy()
    loud_without_gate = (~frame["gate_open"]) & state.isin(["elevated", "risk-off"])
    state.loc[loud_without_gate] = "caution"
    frame["ungated_state"] = ungated.astype("object")
    frame["state"] = state.astype("object")
    if frame.empty:
        raise RuntimeError("CN state reconstruction is empty")
    return frame


def load_vehicle_frame(
    state_frame: pd.DataFrame,
    vehicle: tuple[str, str],
) -> pd.DataFrame:
    from lib import store

    group, name = vehicle
    if (group, name) == ("china", "000001.SS"):
        close = state_frame["benchmark_close"].copy()
    else:
        raw = store.read(group, name)
        if raw is None or getattr(raw, "empty", True):
            raise RuntimeError(f"missing vehicle series: {group}/{name}")
        column = "close" if "close" in raw.columns else raw.columns[0]
        close = pd.to_numeric(raw[column], errors="coerce").dropna()
        close.index = pd.to_datetime(close.index)
        close = close.sort_index()
    returns = close.pct_change(fill_method=None)
    idx = state_frame.index.intersection(returns.dropna().index)
    frame = state_frame.reindex(idx).copy()
    frame["vehicle_close"] = close.reindex(idx)
    frame["benchmark_return"] = returns.reindex(idx)
    return frame.dropna(subset=["state", "benchmark_return", "vehicle_close"])


def historical_source_qualification() -> dict[str, Any]:
    """Qualify whether reconstructed history may carry policy authority.

    The replay can be causal in calculation while still failing point-in-time source
    law. In particular, a breadth history rebuilt from today's membership universe
    is definition-current rather than membership-PIT.
    """
    from engine import risk_radar_intl as radar

    collector_path = ROOT / "collectors/china_breadth.py"
    constituents_path = ROOT / "data/china_breadth/constituents.parquet"
    engine_path = ROOT / "engine/risk_radar_intl.py"
    collector_text = collector_path.read_text() if collector_path.exists() else ""
    engine_text = engine_path.read_text() if engine_path.exists() else ""

    exact_state_uses_cn_breadth = any(
        "cn_breadth" in variable
        for _, variables, _ in radar.CN_PROFILE.comp_legs
        for variable in variables
    )
    breadth_current_membership_backfill = (
        'config.load()["china"]["constituents"]' in collector_text
        and '_download_closes(tickers, "max")' in collector_text
    )

    membership_columns: list[str] = []
    if constituents_path.exists():
        membership_columns = [
            str(column) for column in pd.read_parquet(constituents_path).columns
        ]
    normalized_membership_columns = {column.lower() for column in membership_columns}
    effective_date_fields = {
        "effective_from", "effective_to", "valid_from", "valid_to",
        "start_date", "end_date", "asof", "as_of",
    }
    date_effective_membership_present = bool(
        normalized_membership_columns.intersection(effective_date_fields)
    )

    vintage_fields = {
        "vintage", "vintage_date", "realtime_start", "realtime_end",
        "first_observed", "published_at", "release_date", "asof", "as_of",
    }
    source_paths = [
        "data/fred/DGS2.parquet",
        "data/fred/DFII10.parquet",
        "data/fred/DGS10.parquet",
        "data/yahoo/CNH_F.parquet",
        "data/yahoo/DX-Y.NYB.parquet",
        "data/china_property/cgb.parquet",
        "data/china_breadth/breadth.parquet",
    ]
    source_vintage_evidence: dict[str, dict[str, Any]] = {}
    for relative in source_paths:
        path = ROOT / relative
        columns: list[str] = []
        attrs: list[str] = []
        if path.exists():
            data = pd.read_parquet(path)
            columns = [str(column) for column in data.columns]
            attrs = [str(key) for key in getattr(data, "attrs", {}).keys()]
        normalized = {value.lower() for value in columns + attrs}
        source_vintage_evidence[relative] = {
            "exists": path.exists(),
            "columns": columns,
            "attribute_keys": attrs,
            "has_vintage_metadata": bool(normalized.intersection(vintage_fields)),
        }
    source_vintage_metadata_present = all(
        evidence["has_vintage_metadata"]
        for evidence in source_vintage_evidence.values()
    )

    construction_is_causal = (
        "def composite_series" in engine_text
        and ".rolling(" in engine_text
        and ".shift(-" not in engine_text
    )
    historical_authority_eligible = bool(
        construction_is_causal
        and exact_state_uses_cn_breadth
        and not breadth_current_membership_backfill
        and date_effective_membership_present
        and source_vintage_metadata_present
    )
    return {
        "classification": (
            "AUTHORITY_GRADE_PIT"
            if historical_authority_eligible
            else "CAUSAL_DEFINITION_CURRENT_NOT_AUTHORITY_GRADE_PIT"
        ),
        "construction_is_causal": construction_is_causal,
        "exact_state_uses_cn_breadth": exact_state_uses_cn_breadth,
        "breadth_current_membership_backfill": breadth_current_membership_backfill,
        "date_effective_membership_present": date_effective_membership_present,
        "membership_columns": membership_columns,
        "source_vintage_metadata_present": source_vintage_metadata_present,
        "source_vintage_evidence": source_vintage_evidence,
        "historical_authority_eligible": historical_authority_eligible,
        "authority_effect": (
            "diagnostic_reconstruction_only"
            if not historical_authority_eligible
            else "eligible_for_frozen_policy_gates"
        ),
        "evidence_paths": {
            "breadth_collector": str(collector_path.relative_to(ROOT)),
            "breadth_membership": str(constituents_path.relative_to(ROOT)),
            "radar_engine": str(engine_path.relative_to(ROOT)),
        },
    }


def _has_h21_grade(row: dict[str, Any]) -> bool:
    """Return whether an issued row has a complete 21-session outcome grade."""
    graded = row.get("graded")
    if not isinstance(graded, dict):
        return False
    fwd_dd = graded.get("fwd_dd")
    if isinstance(fwd_dd, dict) and fwd_dd.get("h21") is not None:
        return True
    hit = graded.get("hit")
    return isinstance(hit, dict) and isinstance(hit.get("h21"), dict)


def _forward_loud_episodes(
    rows: list[dict[str, Any]],
    *,
    session_index: pd.DatetimeIndex | None = None,
    max_non_loud_gap: int = 10,
    min_loud_observations: int = 3,
) -> list[dict[str, Any]]:
    """Group issued loud rows by elapsed market sessions, not graded-row adjacency."""
    loud_rows = [
        row
        for row in sorted(rows, key=lambda item: str(item.get("asof") or ""))
        if row.get("state") in {"elevated", "risk-off"} and row.get("asof")
    ]
    if not loud_rows:
        return []

    if session_index is not None:
        sessions = pd.DatetimeIndex(pd.to_datetime(session_index)).normalize().unique().sort_values()
        positions = [
            int(sessions.searchsorted(pd.Timestamp(row["asof"]).normalize(), side="left"))
            for row in loud_rows
        ]
        gap_basis = "benchmark_trading_sessions"
    else:
        epoch = np.datetime64("1970-01-01", "D")
        positions = [
            int(np.busday_count(epoch, np.datetime64(str(row["asof"]), "D")))
            for row in loud_rows
        ]
        gap_basis = "weekday_fallback"

    groups: list[list[tuple[dict[str, Any], int]]] = [[(loud_rows[0], positions[0])]]
    for row, position in zip(loud_rows[1:], positions[1:]):
        non_loud_gap = position - groups[-1][-1][1] - 1
        if non_loud_gap <= max_non_loud_gap:
            groups[-1].append((row, position))
        else:
            groups.append([(row, position)])

    episodes: list[dict[str, Any]] = []
    for group in groups:
        if len(group) < min_loud_observations:
            continue
        episode_rows = [row for row, _ in group]
        episodes.append({
            "episode_id": len(episodes) + 1,
            "start": episode_rows[0].get("asof"),
            "end": episode_rows[-1].get("asof"),
            "loud_observations": len(group),
            "contains_risk_off": any(
                row.get("state") == "risk-off" for row in episode_rows
            ),
            "elevated_observations": sum(
                row.get("state") == "elevated" for row in episode_rows
            ),
            "risk_off_observations": sum(
                row.get("state") == "risk-off" for row in episode_rows
            ),
            "outcome_complete": all(_has_h21_grade(row) for row in episode_rows),
            "session_gap_basis": gap_basis,
        })
    return episodes


def forward_ledger_inventory(
    path: Path | str = FORWARD_LOG,
    *,
    session_index: pd.DatetimeIndex | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    file_path = Path(path)
    if file_path.exists():
        for line in file_path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    rows = sorted(rows, key=lambda row: str(row.get("asof") or ""))

    session_calendar = "weekday_fallback"
    if session_index is None:
        try:
            from lib import store

            benchmark = store.read("china", "000001.SS")
            if benchmark is not None and not getattr(benchmark, "empty", True):
                session_index = pd.DatetimeIndex(pd.to_datetime(benchmark.index))
                session_calendar = "china/000001.SS"
        except Exception:  # pragma: no cover - fail-closed fallback is deterministic
            session_index = None
    else:
        session_calendar = "provided_session_index"

    matured = [row for row in rows if _has_h21_grade(row)]
    matured_loud = [
        row for row in matured
        if row.get("state") in {"elevated", "risk-off"}
    ]
    all_episodes = _forward_loud_episodes(rows, session_index=session_index)
    episodes = [
        episode for episode in all_episodes if bool(episode["outcome_complete"])
    ]
    open_episodes = [
        episode for episode in all_episodes if not bool(episode["outcome_complete"])
    ]
    riskoff_episode_n = sum(
        bool(episode["contains_risk_off"]) for episode in episodes
    )
    return {
        "label": "issued_forward_monitoring_only_not_policy_optimization",
        "rows": len(rows),
        "matured_rows": len(matured),
        "unmatured_rows": len(rows) - len(matured),
        "matured_loud_rows": len(matured_loud),
        "asof_from": rows[0].get("asof") if rows else None,
        "asof_through": rows[-1].get("asof") if rows else None,
        "state_counts": dict(Counter(row.get("state") for row in rows)),
        "matured_state_counts": dict(Counter(row.get("state") for row in matured)),
        "session_calendar": session_calendar,
        "independent_loud_episode_n": len(episodes),
        "riskoff_containing_episode_n": riskoff_episode_n,
        "elevated_only_episode_n": len(episodes) - riskoff_episode_n,
        "open_loud_episode_n": len(open_episodes),
        "episodes": episodes,
        "open_episodes": open_episodes,
        "all_episodes": all_episodes,
        "policy_coefficients_estimable": False,
        "historical_coefficients_estimable": False,
    }


def build_input_manifest(prereg: dict[str, Any], state_frame: pd.DataFrame) -> dict[str, Any]:
    relative_inputs = [
        "engine/risk_radar_intl.py",
        "collectors/china_breadth.py",
        "data/china_breadth/constituents.parquet",
        "data/china/000001.SS.parquet",
        "data/china/510300.SS.parquet",
        "data/fred/DGS2.parquet",
        "data/fred/DFII10.parquet",
        "data/fred/DGS10.parquet",
        "data/yahoo/CNH_F.parquet",
        "data/yahoo/DX-Y.NYB.parquet",
        "data/china_property/cgb.parquet",
        "data/china_breadth/breadth.parquet",
        "data/risk_radar_intl/cn_forward_log.jsonl",
        "research/cn_risk_capital_policy/preregistration.json",
        "scripts/research/cn_risk_capital_policy.py",
    ]
    hashes = {
        rel: sha256_file(ROOT / rel)
        for rel in relative_inputs
        if (ROOT / rel).exists()
    }
    prereg_rel = str(PREREG_PATH.relative_to(ROOT))
    return {
        "schema": "cn_risk_capital_policy_inputs.v1",
        "source_base": prereg["source_base"],
        "skillpack_sha": prereg["skillpack_sha"],
        "prereg_commit": _git_output("log", "-1", "--format=%H", "--", prereg_rel),
        "file_sha256": hashes,
        "state_population_sha256": _population_fingerprint(state_frame),
        "state_coverage": {
            "from": state_frame.index.min().date().isoformat(),
            "through": state_frame.index.max().date().isoformat(),
            "rows": len(state_frame),
            "counts": dict(Counter(state_frame["state"])),
        },
    }


def scenario_key(lag: int, cost_bps: float) -> str:
    cost = int(cost_bps) if float(cost_bps).is_integer() else float(cost_bps)
    return f"lag{int(lag)}_cost{cost}"


def build_policy_frames(
    vehicle_frame: pd.DataFrame,
    prereg: dict[str, Any],
    *,
    lag: int,
    cost_bps: float,
) -> dict[str, pd.DataFrame]:
    states = vehicle_frame["state"].astype("object")
    returns = vehicle_frame["benchmark_return"].astype(float)
    order = list(prereg["policy_order"])
    if not order or order[0] != "current_ladder":
        raise RuntimeError("current ladder must be evaluated first")
    frames: dict[str, pd.DataFrame] = {}
    current_target = target_gross("current_ladder", states, returns, prereg)
    frames["current_ladder"] = execute_policy(
        returns, current_target, lag=lag, cost_bps=cost_bps
    )
    for policy in order[1:]:
        if policy == "matched_constant":
            target = matched_constant_target(frames["current_ladder"], states.index)
        else:
            target = target_gross(policy, states, returns, prereg)
        frames[policy] = execute_policy(
            returns, target, lag=lag, cost_bps=cost_bps
        )
    return frames


def _label_rows(
    rows: Iterable[dict[str, Any]], **labels: Any
) -> list[dict[str, Any]]:
    return [{**labels, **row} for row in rows]


def era_results(
    frame: pd.DataFrame,
    eras: dict[str, list[str | None]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, bounds in eras.items():
        start = pd.Timestamp(bounds[0]) if bounds[0] else frame.index.min()
        end = pd.Timestamp(bounds[1]) if bounds[1] else frame.index.max()
        scoped = frame.loc[(frame.index >= start) & (frame.index <= end)]
        if scoped.empty:
            continue
        rows.append(_jsonable({"era": name, **performance_metrics(scoped)}))
    return rows


def _passes_direction(
    candidate: dict[str, Any],
    full: dict[str, Any],
    matched: dict[str, Any],
) -> bool:
    values = [
        candidate.get("max_drawdown"), full.get("max_drawdown"),
        candidate.get("cvar_95"), full.get("cvar_95"),
        candidate.get("calmar"), matched.get("calmar"),
    ]
    if any(value is None or not np.isfinite(float(value)) for value in values):
        return False
    return (
        float(candidate["max_drawdown"]) > float(full["max_drawdown"])
        and float(candidate["cvar_95"]) > float(full["cvar_95"])
        and float(candidate["calmar"]) > float(matched["calmar"])
    )


def _episode_severity(episode_rows: list[dict[str, Any]]) -> dict[str, Any]:
    riskoff = [row for row in episode_rows if row["contains_risk_off"]]
    elevated = [row for row in episode_rows if not row["contains_risk_off"]]

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {"n": 0, "downside_rate": None, "median_path_loss": None}
        return {
            "n": len(rows),
            "downside_rate": float(np.mean([bool(row["downside_event"]) for row in rows])),
            "median_path_loss": float(np.median([float(row["benchmark_path_loss"]) for row in rows])),
        }

    return {"risk_off_containing": summarize(riskoff), "elevated_only": summarize(elevated)}


def run_study(
    *,
    output_dir: Path | str = RESULTS_DIR,
    emit_artifacts: bool = True,
) -> dict[str, Any]:
    prereg = load_preregistration()
    source_qualification = historical_source_qualification()
    forward_ledger = forward_ledger_inventory()
    state_frame = reconstruct_cn_state_frame(prereg)
    manifest = build_input_manifest(prereg, state_frame)
    vehicles = {
        "shanghai_composite": tuple(prereg["benchmarks"]["primary"]),
        "csi300_etf_proxy": tuple(prereg["benchmarks"]["investable_proxy"]),
    }
    vehicle_frames = {
        name: load_vehicle_frame(state_frame, vehicle)
        for name, vehicle in vehicles.items()
    }
    policy_frames: dict[str, dict[str, dict[str, pd.DataFrame]]] = {}
    metrics_lookup: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    metrics_rows: list[dict[str, Any]] = []

    for vehicle_name, vehicle_frame in vehicle_frames.items():
        policy_frames[vehicle_name] = {}
        metrics_lookup[vehicle_name] = {}
        for scenario in prereg["scenarios"]:
            lag, cost_bps = int(scenario["lag"]), float(scenario["cost_bps"])
            key = scenario_key(lag, cost_bps)
            frames = build_policy_frames(
                vehicle_frame, prereg, lag=lag, cost_bps=cost_bps
            )
            policy_frames[vehicle_name][key] = frames
            metrics_lookup[vehicle_name][key] = {}
            for policy in prereg["policy_order"]:
                metrics = _jsonable(performance_metrics(frames[policy]))
                metrics_lookup[vehicle_name][key][policy] = metrics
                metrics_rows.append({
                    "vehicle": vehicle_name,
                    "scenario": key,
                    "lag": lag,
                    "cost_bps": cost_bps,
                    "policy": policy,
                    **metrics,
                })

    primary_vehicle = "shanghai_composite"
    primary_scenario = scenario_key(1, 10)
    primary_frames = policy_frames[primary_vehicle][primary_scenario]
    primary_metrics = metrics_lookup[primary_vehicle][primary_scenario]
    episode_spec = prereg["episodes"]
    all_episodes = find_loud_episodes(
        vehicle_frames[primary_vehicle]["state"],
        max_non_loud_gap=int(episode_spec["max_non_loud_gap"]),
        min_loud_observations=int(episode_spec["min_loud_observations"]),
        post_window_sessions=int(episode_spec["post_window_sessions"]),
    )
    complete_episodes = [
        episode for episode in all_episodes if episode["outcome_complete"]
    ]
    diagnostic_independent_episodes = authority_independent_episodes(all_episodes)
    overlap_excluded_episodes = [
        episode
        for episode in complete_episodes
        if not episode["authority_independent"]
    ]
    censored_episodes = [
        episode for episode in all_episodes if not episode["outcome_complete"]
    ]

    episode_rows: list[dict[str, Any]] = []
    crisis_rows: list[dict[str, Any]] = []
    loco_rows: list[dict[str, Any]] = []
    era_rows: list[dict[str, Any]] = []
    for policy in prereg["policy_order"]:
        episode_rows.extend(_label_rows(
            analyze_episodes(
                primary_frames[policy],
                vehicle_frames[primary_vehicle]["state"],
                complete_episodes,
                downside_threshold=float(episode_spec["downside_threshold"]),
            ),
            vehicle=primary_vehicle,
            scenario=primary_scenario,
            policy=policy,
        ))
        crisis_rows.extend(_label_rows(
            analyze_crises(primary_frames[policy], prereg["crises"]),
            vehicle=primary_vehicle,
            scenario=primary_scenario,
            policy=policy,
        ))
        loco_rows.extend(_label_rows(
            leave_one_crisis_out(primary_frames[policy], prereg["crises"]),
            vehicle=primary_vehicle,
            scenario=primary_scenario,
            policy=policy,
        ))
        era_rows.extend(_label_rows(
            era_results(primary_frames[policy], prereg["eras"]),
            vehicle=primary_vehicle,
            scenario=primary_scenario,
            policy=policy,
        ))

    for policy in prereg["policy_order"]:
        crisis_rows.extend(_label_rows(
            analyze_crises(
                policy_frames["csi300_etf_proxy"][primary_scenario][policy],
                prereg["crises"],
            ),
            vehicle="csi300_etf_proxy",
            scenario=primary_scenario,
            policy=policy,
        ))

    bootstrap_spec = prereg["bootstrap"]
    pair_specs = {
        "current_vs_matched": ("current_ladder", "matched_constant"),
        "binary_vs_matched": ("binary_loud_075", "matched_constant"),
        "current_vs_riskoff_075": ("current_ladder", "current_riskoff_075"),
    }
    bootstrap = {
        name: bootstrap_pair(
            primary_frames[left],
            primary_frames[right],
            draws=int(bootstrap_spec["draws"]),
            block_sessions=int(bootstrap_spec["block_sessions"]),
            seed=int(bootstrap_spec["seed"]),
            ci=float(bootstrap_spec["ci"]),
        )
        for name, (left, right) in pair_specs.items()
    }

    episode_by_policy = {
        policy: [row for row in episode_rows if row["policy"] == policy]
        for policy in prereg["policy_order"]
    }
    diagnostic_episode_by_policy = {
        policy: [
            row for row in rows if bool(row.get("authority_independent"))
        ]
        for policy, rows in episode_by_policy.items()
    }
    positive_episode_fraction = {
        policy: (
            float(np.mean([bool(row["positive_timing_benefit"]) for row in rows]))
            if rows else 0.0
        )
        for policy, rows in diagnostic_episode_by_policy.items()
    }
    crisis_by_policy = {
        policy: [
            row for row in crisis_rows
            if row["vehicle"] == primary_vehicle and row["policy"] == policy
        ]
        for policy in prereg["policy_order"]
    }
    crisis_concentrations = {
        policy: crisis_concentration(rows)
        for policy, rows in crisis_by_policy.items()
    }

    sensitivity_pass: dict[str, bool] = {}
    for candidate in ("current_ladder", "binary_loud_075"):
        checks = []
        for scenario in prereg["scenarios"]:
            key = scenario_key(int(scenario["lag"]), float(scenario["cost_bps"]))
            scoped = metrics_lookup[primary_vehicle][key]
            checks.append(_passes_direction(
                scoped[candidate], scoped["constant_100"], scoped["matched_constant"]
            ))
        sensitivity_pass[candidate] = all(checks)

    era_lookup: dict[str, dict[str, dict[str, Any]]] = {}
    for row in era_rows:
        era_lookup.setdefault(row["era"], {})[row["policy"]] = row
    era_pass: dict[str, bool] = {}
    for candidate in ("current_ladder", "binary_loud_075"):
        checks = []
        for era in prereg["eras"]:
            scoped = era_lookup.get(era, {})
            if not all(key in scoped for key in (candidate, "constant_100", "matched_constant")):
                checks.append(False)
            else:
                checks.append(_passes_direction(
                    scoped[candidate], scoped["constant_100"], scoped["matched_constant"]
                ))
        era_pass[candidate] = all(checks)

    loco_lookup: dict[str, dict[str, dict[str, Any]]] = {}
    for row in loco_rows:
        loco_lookup.setdefault(row["excluded_crisis"], {})[row["policy"]] = row
    loco_positive_count: dict[str, int] = {}
    for candidate in ("current_ladder", "binary_loud_075"):
        count = 0
        for crisis in prereg["crises"]:
            scoped = loco_lookup.get(crisis, {})
            if not all(key in scoped for key in (candidate, "matched_constant")):
                continue
            candidate_row = scoped[candidate]
            matched_row = scoped["matched_constant"]
            if (
                candidate_row.get("calmar") is not None
                and matched_row.get("calmar") is not None
                and float(candidate_row["calmar"]) > float(matched_row["calmar"])
                and float(candidate_row["cvar_95"]) > float(matched_row["cvar_95"])
            ):
                count += 1
        loco_positive_count[candidate] = count

    diagnostic_effective_episode_n = len(diagnostic_independent_episodes)
    diagnostic_riskoff_episode_n = sum(
        bool(episode["contains_risk_off"])
        for episode in diagnostic_independent_episodes
    )
    diagnostic_elevated_only_episode_n = (
        diagnostic_effective_episode_n - diagnostic_riskoff_episode_n
    )
    authority_effective_episode_n = int(
        forward_ledger["independent_loud_episode_n"]
    )
    authority_riskoff_episode_n = int(
        forward_ledger["riskoff_containing_episode_n"]
    )
    authority_elevated_only_episode_n = int(
        forward_ledger["elevated_only_episode_n"]
    )
    adjudication_input = {
        "historical_authority_eligible": bool(
            source_qualification["historical_authority_eligible"]
        ),
        "authority_effective_episode_n": authority_effective_episode_n,
        "authority_riskoff_episode_n": authority_riskoff_episode_n,
        "authority_elevated_only_episode_n": authority_elevated_only_episode_n,
        "primary": primary_metrics,
        "bootstrap": bootstrap,
        "positive_episode_fraction": positive_episode_fraction,
        "crisis_concentration": crisis_concentrations,
        "sensitivity_pass": sensitivity_pass,
        "era_pass": era_pass,
        "loco_positive_count": loco_positive_count,
    }
    verdict, gate_results = adjudicate(adjudication_input, prereg)
    ui_verdict = ui_language_verdict(verdict)


    full = primary_metrics["constant_100"]
    current = primary_metrics["current_ladder"]
    matched = primary_metrics["matched_constant"]
    binary = primary_metrics["binary_loud_075"]
    floor_075 = primary_metrics["current_riskoff_075"]
    proxy_primary = metrics_lookup["csi300_etf_proxy"][primary_scenario]
    proxy_current = proxy_primary["current_ladder"]
    proxy_floor_075 = proxy_primary["current_riskoff_075"]

    def deltas(candidate: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
        keys = (
            "cagr", "max_drawdown", "cvar_95", "annualized_volatility",
            "calmar", "certainty_equivalent", "total_return",
        )
        return {
            key: (
                None if candidate.get(key) is None or baseline.get(key) is None
                else float(candidate[key]) - float(baseline[key])
            )
            for key in keys
        }

    full_episode_rows = diagnostic_episode_by_policy["constant_100"]
    false_positive_rows = [row for row in full_episode_rows if not row["downside_event"]]
    current_episode_rows = diagnostic_episode_by_policy["current_ladder"]
    current_false_positive_rows = [
        row for row in current_episode_rows if not row["downside_event"]
    ]
    current_downside_rows = [
        row for row in current_episode_rows if row["downside_event"]
    ]
    episode_severity = _episode_severity(full_episode_rows)
    current_crisis_rows = crisis_by_policy["current_ladder"]
    positive_crisis_protection = sorted(
        [
            float(row["protection_vs_full"])
            for row in current_crisis_rows
            if float(row["protection_vs_full"]) > 0.0
        ],
        reverse=True,
    )
    positive_total = sum(positive_crisis_protection)
    top_two_crisis_concentration = (
        sum(positive_crisis_protection[:2]) / positive_total
        if positive_total > 0 else 1.0
    )
    contribution_annualization = 252.0 / float(current["n_sessions"])
    shadow_candidate = None
    if verdict == "SIMPLER_POLICY_SUPPORTED":
        shadow_candidate = {
            "schema": "cn_risk_capital_policy_shadow.v1",
            "policy_id": "binary_loud_075",
            "mapping": prereg["fixed_policies"]["binary_loud_075"],
            "status": "SHADOW_ONLY_NO_LIVE_CONSUMER",
            "authority": "research_candidate_only",
            "live_allocation_plane_created": False,
            "promotion_requires": "separate Astra integrator decision and source wave",
        }

    summary = _jsonable({
        "schema": "cn_risk_capital_policy_result.v1",
        "operation_key": prereg["operation_key"],
        "status": "DRAFT_HOLD_RESEARCH_ONLY",
        "branch": _git_output("branch", "--show-current"),
        "source_base": prereg["source_base"],
        "skillpack_sha": prereg["skillpack_sha"],
        "prereg_sha": manifest["prereg_commit"],
        "historical_evidence_label": (
            "causal/date-aligned definition-current reconstruction; not "
            "membership-PIT or source-vintage verified; diagnostic only"
        ),
        "source_qualification": source_qualification,
        "historical_authority_eligible": bool(
            source_qualification["historical_authority_eligible"]
        ),
        "benchmark_and_timing": {
            "primary": {
                "store": list(prereg["benchmarks"]["primary"]),
                "label": "Shanghai Composite",
                "state_history_from": manifest["state_coverage"]["from"],
                "return_exposure_from": (
                    vehicle_frames[primary_vehicle].index.min().date().isoformat()
                ),
                "from": vehicle_frames[primary_vehicle].index.min().date().isoformat(),
                "through": vehicle_frames[primary_vehicle].index.max().date().isoformat(),
                "state_history_sessions": manifest["state_coverage"]["rows"],
                "aligned_return_sessions": len(vehicle_frames[primary_vehicle]),
                "policy_sessions": int(current["n_sessions"]),
                "sessions": len(vehicle_frames[primary_vehicle]),
            },
            "investable_proxy": {
                "store": list(prereg["benchmarks"]["investable_proxy"]),
                "label": "CSI 300 ETF 510300.SS robustness lane",
                "from": vehicle_frames["csi300_etf_proxy"].index.min().date().isoformat(),
                "through": vehicle_frames["csi300_etf_proxy"].index.max().date().isoformat(),
                "sessions": len(vehicle_frames["csi300_etf_proxy"]),
            },
            "primary_scenario": {
                "state_observation": "close_t",
                "return_exposure": "next_close_to_close",
                "lag_sessions": 1,
                "transaction_cost_bps_per_unit_gross_change": 10,
                "cash_return": 0.0,
                "first_allocation_costed": False,
            },
            "sensitivities": prereg["scenarios"],
        },
        "state_reconstruction": manifest["state_coverage"],
        "forward_ledger": forward_ledger,
        "current_ladder_results": current,
        "baseline_results": {
            policy: primary_metrics[policy]
            for policy in prereg["policy_order"]
            if policy != "current_ladder"
        },
        "investable_proxy_primary_results": metrics_lookup["csi300_etf_proxy"][primary_scenario],
        "economic_comparisons": {
            "current_vs_full_gross": deltas(current, full),
            "current_vs_exposure_matched_constant": deltas(current, matched),
            "current_062_vs_same_ladder_riskoff_075": deltas(current, floor_075),
            "investable_proxy_current_062_vs_same_ladder_riskoff_075": deltas(
                proxy_current, proxy_floor_075
            ),
            "binary_loud_075_vs_exposure_matched_constant": deltas(binary, matched),
            "current_average_gross": current["average_gross"],
            "matched_constant_gross": matched["average_gross"],
        },
        "opportunity_cost": {
            "current_missed_upside_sum": current["missed_upside"],
            "current_avoided_downside_sum": current["avoided_downside"],
            "current_transaction_cost_sum": current["transaction_cost"],
            "current_policy_excess_vs_full_sum": current["policy_excess_vs_full"],
            "current_missed_upside_annualized_contribution": (
                current["missed_upside"] * contribution_annualization
            ),
            "current_avoided_downside_annualized_contribution": (
                current["avoided_downside"] * contribution_annualization
            ),
            "current_transaction_cost_annualized_contribution": (
                current["transaction_cost"] * contribution_annualization
            ),
            "current_policy_excess_vs_full_annualized_contribution": (
                current["policy_excess_vs_full"] * contribution_annualization
            ),
            "current_total_return_delta_vs_full": current["total_return_delta_vs_full"],
            "binary_missed_upside_sum": binary["missed_upside"],
            "binary_avoided_downside_sum": binary["avoided_downside"],
        },
        "turnover": {
            policy: {
                "total": primary_metrics[policy]["turnover"],
                "annualized": primary_metrics[policy]["annualized_turnover"],
                "exposure_change_count": primary_metrics[policy]["exposure_change_count"],
                "transaction_cost": primary_metrics[policy]["transaction_cost"],
            }
            for policy in prereg["policy_order"]
        },
        "episodes": {
            "authority_source": "issued_forward_ledger",
            "authority_effective_n": authority_effective_episode_n,
            "authority_risk_off_containing_n": authority_riskoff_episode_n,
            "authority_elevated_only_n": authority_elevated_only_episode_n,
            "reconstructed_complete_n": len(complete_episodes),
            "reconstructed_independent_nonoverlap_n": diagnostic_effective_episode_n,
            "reconstructed_risk_off_containing_n": diagnostic_riskoff_episode_n,
            "reconstructed_elevated_only_n": diagnostic_elevated_only_episode_n,
            "overlap_excluded_n": len(overlap_excluded_episodes),
            "overlap_excluded": overlap_excluded_episodes,
            "censored_open_n": len(censored_episodes),
            "censored_open": censored_episodes,
            "diagnostic_false_positive_n": len(false_positive_rows),
            "diagnostic_downside_event_n": (
                diagnostic_effective_episode_n - len(false_positive_rows)
            ),
            "false_positive_policy_excess_sum_current": sum(
                float(row["policy_excess"]) for row in current_false_positive_rows
            ),
            "false_positive_recovery_missed_upside_sum_current": sum(
                float(row["recovery_missed_upside"])
                for row in current_false_positive_rows
            ),
            "false_positive_positive_timing_n_current": sum(
                bool(row["positive_timing_benefit"])
                for row in current_false_positive_rows
            ),
            "downside_policy_excess_sum_current": sum(
                float(row["policy_excess"]) for row in current_downside_rows
            ),
            "downside_positive_timing_n_current": sum(
                bool(row["positive_timing_benefit"])
                for row in current_downside_rows
            ),
            "diagnostic_severity": episode_severity,
            "diagnostic_positive_timing_fraction": positive_episode_fraction,
        },
        "crisis_and_loco": {
            "current_crisis_concentration_top_one": crisis_concentrations["current_ladder"],
            "current_crisis_concentration_top_two": top_two_crisis_concentration,
            "loco_positive_count": loco_positive_count,
            "number_of_frozen_crises": len(prereg["crises"]),
        },
        "stability": {
            "sensitivity_pass": sensitivity_pass,
            "era_pass": era_pass,
            "bootstrap": bootstrap,
        },
        "policy_verdict": verdict,
        "adjudication": gate_results,
        "ui_language_verdict": ui_verdict,
        "shadow_candidate_if_earned": shadow_candidate,
        "discoveries": {
            "historical_reconstruction_authority_eligible": bool(
                source_qualification["historical_authority_eligible"]
            ),
            "historical_reconstruction_is_definition_current": True,
            "issued_forward_independent_loud_episode_n": (
                authority_effective_episode_n
            ),
            "reconstructed_overlapping_episode_windows_excluded": (
                len(overlap_excluded_episodes)
            ),
            "forward_sample_can_optimize_five_coefficients": False,
            "detector_validity_implies_sizing_validity": False,
            "primary_timing_edge_survives_exposure_matched_constant": (
                current["cagr"] > matched["cagr"]
                and current["calmar"] > matched["calmar"]
                and current["cvar_95"] > matched["cvar_95"]
            ),
            "current_vs_matched_mdd_bootstrap_lower_bound_positive": (
                bootstrap["current_vs_matched"]["max_drawdown_diff"][0] > 0.0
            ),
            "exact_062_precision_requires_incremental_evidence_over_075": True,
            "exact_062_cagr_mdd_calmar_bootstrap_all_exclude_zero": all(
                bootstrap["current_vs_riskoff_075"][metric][0] > 0.0
                for metric in ("cagr_diff", "max_drawdown_diff", "calmar_diff")
            ),
            "investable_proxy_062_beats_075_on_cagr_mdd_and_calmar": (
                proxy_current["cagr"] > proxy_floor_075["cagr"]
                and proxy_current["max_drawdown"] > proxy_floor_075["max_drawdown"]
                and proxy_current["calmar"] > proxy_floor_075["calmar"]
            ),
            "all_false_positive_episodes_added_timing_value": (
                len(current_false_positive_rows) > 0
                and all(row["positive_timing_benefit"] for row in current_false_positive_rows)
            ),
            "plain_english_half_normal_is_semantically_faithful_to_062": False,
            "benefit_must_survive_exposure_matched_constant": True,
        },
        "authority": {
            "live_gross_mapping_changed": False,
            "live_consumer_added": False,
            "can_force_changed": False,
            "trade_or_exit_authority_added": False,
            "merge_authorized": False,
        },
    })

    result = {
        "summary": summary,
        "input_manifest": manifest,
        "source_qualification": source_qualification,
        "metrics_rows": metrics_rows,
        "crisis_rows": crisis_rows,
        "episode_rows": episode_rows,
        "loco_rows": loco_rows,
        "era_rows": era_rows,
        "bootstrap": bootstrap,
        "shadow_candidate": shadow_candidate,
    }
    if emit_artifacts:
        write_artifacts(Path(output_dir), result)
    return result


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(_jsonable(payload), indent=2, sort_keys=True, allow_nan=False) + "\n"
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], sort_by: list[str]) -> None:
    frame = pd.DataFrame([_jsonable(row) for row in rows])
    if frame.empty:
        path.write_text("")
        return
    valid_sort = [column for column in sort_by if column in frame.columns]
    if valid_sort:
        frame = frame.sort_values(valid_sort, kind="mergesort", na_position="last")
    preferred = [
        "vehicle", "scenario", "lag", "cost_bps", "policy", "episode_id",
        "crisis", "excluded_crisis", "era", "start", "end", "outcome_end",
    ]
    columns = [column for column in preferred if column in frame.columns]
    columns += sorted(column for column in frame.columns if column not in columns)
    frame.to_csv(
        path,
        index=False,
        columns=columns,
        float_format="%.10g",
        na_rep="",
        lineterminator="\n",
    )


def _fmt_pct(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    return f"{100.0 * float(value):.{digits}f}%"


def _fmt_num(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    return f"{float(value):.{digits}f}"


def _fmt_ci(interval: list[float | None] | None, *, percent: bool = True) -> str:
    if not interval or any(value is None for value in interval):
        return "—"
    if percent:
        return "[" + ", ".join(_fmt_pct(value) for value in interval) + "]"
    return "[" + ", ".join(_fmt_num(value) for value in interval) + "]"


def _forward_evidence_sentence(forward: dict[str, Any]) -> str:
    completed = int(forward["independent_loud_episode_n"])
    open_count = int(forward.get("open_loud_episode_n", 0))
    completed_noun = "episode" if completed == 1 else "episodes"
    open_noun = "episode" if open_count == 1 else "episodes"
    open_verb = "remains" if open_count == 1 else "remain"
    return (
        f"The issued ledger has {forward['rows']} rows, {forward['matured_rows']} matured rows, "
        f"and {forward['matured_loud_rows']} matured loud rows. Its matured state counts are "
        f"`{forward['matured_state_counts']}`. Those matured loud rows form only "
        f"**{completed}** completed independent {completed_noun}; {open_count} open loud "
        f"{open_noun} {open_verb} ungraded. Therefore neither five coefficients nor a "
        "simpler promoted policy can be estimated honestly."
    )


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    policies = {
        "current_ladder": summary["current_ladder_results"],
        **summary["baseline_results"],
    }
    display_order = [
        "current_ladder", "constant_100", "constant_075", "matched_constant",
        "binary_loud_075", "current_riskoff_075", "vol_target_15",
    ]
    exact_failures = [
        name for name, passed in summary["adjudication"]["exact_checks"].items()
        if not passed
    ]
    simple_failures = [
        name for name, passed in summary["adjudication"]["simple_checks"].items()
        if not passed
    ]
    source = summary["source_qualification"]
    forward = summary["forward_ledger"]
    episodes = summary["episodes"]
    comparison = summary["economic_comparisons"]
    opportunity = summary["opportunity_cost"]
    turnover = summary["turnover"]
    severity = episodes["diagnostic_severity"]

    lines = [
        "# China Risk Radar Capital-Policy Validation",
        "",
        f"**Operation:** `{summary['operation_key']}`<br>",
        f"**Status:** `{summary['status']}`<br>",
        f"**Policy verdict:** **{summary['policy_verdict']}**<br>",
        f"**Source base:** `{summary['source_base']}`<br>",
        f"**Preregistration commit:** `{summary['prereg_sha']}`",
        "",
        "> Historical policy results are a causal/date-aligned, definition-current reconstruction. They are not membership-PIT, are not source-vintage verified, and are diagnostic only. Authority is adjudicated from the issued-forward ledger.",
        "",
        "## Executive ruling",
        "",
        f"Authority-bearing effective episode N is **{episodes['authority_effective_n']}**: "
        f"{episodes['authority_risk_off_containing_n']} risk-off-containing and "
        f"{episodes['authority_elevated_only_n']} elevated-only. This is insufficient to estimate either a five-step ladder or the exact ×0.62 risk-off coefficient.",
        "",
        f"The exact current ladder passed the frozen exact-policy gate: **{summary['adjudication']['exact_current_pass']}**. "
        f"The preregistered binary loud-state policy passed its separate gate: **{summary['adjudication']['simple_binary_pass']}**.",
        "",
        f"Exact-gate failures: `{', '.join(exact_failures) if exact_failures else 'none'}`.<br>",
        f"Simple-policy gate failures: `{', '.join(simple_failures) if simple_failures else 'none'}`.",
        "",
        "No source mapping, UI, `can_force`, Market State, ranking, execution, Prophet, or live allocation consumer changed in this wave.",
        "",
        "## Historical source qualification",
        "",
        f"Classification: **{source['classification']}**. Construction is causal: **{source['construction_is_causal']}**. Historical authority eligible: **{source['historical_authority_eligible']}**.",
        "",
        f"The exact CN state uses the breadth leg: **{source['exact_state_uses_cn_breadth']}**. The breadth history is rebuilt from the current hand-curated membership over maximum available history: **{source['breadth_current_membership_backfill']}**. Date-effective membership fields are present: **{source['date_effective_membership_present']}**; observed membership columns are `{source['membership_columns']}`.",
        "",
        f"Source-vintage metadata is present across the reconstructed macro inputs: **{source['source_vintage_metadata_present']}**. Therefore the long history is retained for diagnostic counterfactuals but is barred from promotion gates.",
        "",
        "## Frozen benchmark and execution contract",
        "",
        f"The state reconstruction begins {summary['benchmark_and_timing']['primary']['state_history_from']}; the first aligned benchmark return is {summary['benchmark_and_timing']['primary']['return_exposure_from']} because close-to-close returns consume one prior close. The lane runs through {summary['benchmark_and_timing']['primary']['through']} with {summary['benchmark_and_timing']['primary']['aligned_return_sessions']} aligned returns and {summary['benchmark_and_timing']['primary']['policy_sessions']} executed primary-policy observations after the one-session lag.",
        "",
        "State is observed at close *t* and gross is applied to the next close-to-close return. The primary scenario charges 10 bps per unit of gross change, earns zero on unused gross, and does not charge the initial allocation. Lag-two and 25-bps variants are frozen sensitivities.",
        "",
        f"The investable robustness lane uses CSI 300 ETF `510300.SS` from {summary['benchmark_and_timing']['investable_proxy']['from']} through {summary['benchmark_and_timing']['investable_proxy']['through']}.",
        "",
        "## Diagnostic reconstructed results — not authority-bearing",
        "",
        "| Policy | CAGR | Max DD | CVaR 95 | Vol | Sharpe | Sortino | Calmar | Avg gross | Reduced time | Turnover |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for policy in display_order:
        metric = policies[policy]
        lines.append(
            f"| `{policy}` | {_fmt_pct(metric['cagr'])} | {_fmt_pct(metric['max_drawdown'])} | "
            f"{_fmt_pct(metric['cvar_95'])} | {_fmt_pct(metric['annualized_volatility'])} | "
            f"{_fmt_num(metric['sharpe'])} | {_fmt_num(metric['sortino'])} | {_fmt_num(metric['calmar'])} | "
            f"{_fmt_num(metric['average_gross'])} | {_fmt_pct(metric['time_reduced'])} | "
            f"{_fmt_num(metric['turnover'])} |"
        )

    lines += [
        "",
        "## Diagnostic protection versus merely holding less",
        "",
        f"The current ladder's mean executed gross is **{_fmt_num(comparison['current_average_gross'])}**; the one canonical exposure-matched constant holds exactly **{_fmt_num(comparison['matched_constant_gross'])}**, derived from executed post-lag current-ladder gross without return optimization.",
        "",
        f"Current minus matched constant: CAGR {_fmt_pct(comparison['current_vs_exposure_matched_constant']['cagr'])}, max-drawdown difference {_fmt_pct(comparison['current_vs_exposure_matched_constant']['max_drawdown'])}, CVaR difference {_fmt_pct(comparison['current_vs_exposure_matched_constant']['cvar_95'])}, Calmar difference {_fmt_num(comparison['current_vs_exposure_matched_constant']['calmar'])}, and certainty-equivalent difference {_fmt_pct(comparison['current_vs_exposure_matched_constant']['certainty_equivalent'])}.",
        "",
        f"Exact risk-off ×0.62 minus the same ladder with ×0.75: CAGR {_fmt_pct(comparison['current_062_vs_same_ladder_riskoff_075']['cagr'])}, max drawdown {_fmt_pct(comparison['current_062_vs_same_ladder_riskoff_075']['max_drawdown'])}, CVaR {_fmt_pct(comparison['current_062_vs_same_ladder_riskoff_075']['cvar_95'])}, and Calmar {_fmt_num(comparison['current_062_vs_same_ladder_riskoff_075']['calmar'])}.",
        "",
        f"On the investable CSI-300 proxy, ×0.62 minus ×0.75 is: CAGR {_fmt_pct(comparison['investable_proxy_current_062_vs_same_ladder_riskoff_075']['cagr'])}, max drawdown {_fmt_pct(comparison['investable_proxy_current_062_vs_same_ladder_riskoff_075']['max_drawdown'])}, CVaR {_fmt_pct(comparison['investable_proxy_current_062_vs_same_ladder_riskoff_075']['cvar_95'])}, and Calmar {_fmt_num(comparison['investable_proxy_current_062_vs_same_ladder_riskoff_075']['calmar'])}; negative values favor ×0.75.",
        "",
        "Diagnostic bootstrap 90% intervals (current minus matched):",
        "",
        f"- CAGR: {_fmt_ci(summary['stability']['bootstrap']['current_vs_matched']['cagr_diff'])}",
        f"- Max drawdown: {_fmt_ci(summary['stability']['bootstrap']['current_vs_matched']['max_drawdown_diff'])}",
        f"- CVaR 95: {_fmt_ci(summary['stability']['bootstrap']['current_vs_matched']['cvar_95_diff'])}",
        f"- Calmar: {_fmt_ci(summary['stability']['bootstrap']['current_vs_matched']['calmar_diff'], percent=False)}",
        f"- Certainty equivalent: {_fmt_ci(summary['stability']['bootstrap']['current_vs_matched']['certainty_equivalent_diff'])}",
        "",
        "Diagnostic bootstrap 90% intervals (×0.62 minus ×0.75):",
        "",
        f"- CAGR: {_fmt_ci(summary['stability']['bootstrap']['current_vs_riskoff_075']['cagr_diff'])}",
        f"- Max drawdown: {_fmt_ci(summary['stability']['bootstrap']['current_vs_riskoff_075']['max_drawdown_diff'])}",
        f"- CVaR 95: {_fmt_ci(summary['stability']['bootstrap']['current_vs_riskoff_075']['cvar_95_diff'])}",
        f"- Calmar: {_fmt_ci(summary['stability']['bootstrap']['current_vs_riskoff_075']['calmar_diff'], percent=False)}",
        f"- Certainty equivalent: {_fmt_ci(summary['stability']['bootstrap']['current_vs_riskoff_075']['certainty_equivalent_diff'])}",
        "",
        "## Diagnostic opportunity cost and churn",
        "",
        f"Annualized arithmetic contribution equivalents are: missed upside **{_fmt_pct(opportunity['current_missed_upside_annualized_contribution'])}**, avoided downside **{_fmt_pct(opportunity['current_avoided_downside_annualized_contribution'])}**, cost drag **{_fmt_pct(opportunity['current_transaction_cost_annualized_contribution'])}**, and net timing contribution **{_fmt_pct(opportunity['current_policy_excess_vs_full_annualized_contribution'])}**.",
        "",
        f"The current ladder makes **{turnover['current_ladder']['exposure_change_count']}** executed gross changes, with total turnover **{_fmt_num(turnover['current_ladder']['total'])}** and annualized turnover **{_fmt_num(turnover['current_ladder']['annualized'])}**.",
        "",
        "## Episode accounting",
        "",
        f"Issued-forward authority N is **{episodes['authority_effective_n']}**. The diagnostic reconstruction contains {episodes['reconstructed_complete_n']} complete clusters, of which {episodes['overlap_excluded_n']} have 21-session outcome windows that reach the next alert and are excluded from independent N. That leaves **{episodes['reconstructed_independent_nonoverlap_n']}** non-overlapping diagnostic episodes; {episodes['censored_open_n']} open cluster is censored.",
        "",
        f"Within the non-overlapping diagnostic set, downside episodes are **{episodes['diagnostic_downside_event_n']}** and non-5%-drawdown/false-positive episodes are **{episodes['diagnostic_false_positive_n']}**.",
        "",
        f"False-positive aggregate arithmetic policy excess is **{_fmt_pct(episodes['false_positive_policy_excess_sum_current'])}**, positive in **{episodes['false_positive_positive_timing_n_current']} / {episodes['diagnostic_false_positive_n']}** cases, with **{_fmt_pct(episodes['false_positive_recovery_missed_upside_sum_current'])}** of recovery upside missed.",
        "",
        f"True-downside aggregate arithmetic policy excess is **{_fmt_pct(episodes['downside_policy_excess_sum_current'])}**, positive in **{episodes['downside_positive_timing_n_current']} / {episodes['diagnostic_downside_event_n']}** cases.",
        "",
        f"Diagnostic risk-off-containing downside rate: **{_fmt_pct(severity['risk_off_containing']['downside_rate'])}**, median path loss **{_fmt_pct(severity['risk_off_containing']['median_path_loss'])}**. Elevated-only downside rate: **{_fmt_pct(severity['elevated_only']['downside_rate'])}**, median path loss **{_fmt_pct(severity['elevated_only']['median_path_loss'])}**.",
        "",
        f"Diagnostic positive-timing fraction: current **{_fmt_pct(episodes['diagnostic_positive_timing_fraction']['current_ladder'])}**; binary **{_fmt_pct(episodes['diagnostic_positive_timing_fraction']['binary_loud_075'])}**.",
        "",
        "## Diagnostic crisis, recovery, and leave-one-crisis-out",
        "",
        f"Current-ladder protection concentration: top crisis **{_fmt_pct(summary['crisis_and_loco']['current_crisis_concentration_top_one'])}**; top two **{_fmt_pct(summary['crisis_and_loco']['current_crisis_concentration_top_two'])}** of all positive crisis protection.",
        "",
        f"LOCO runs beating the matched constant on both Calmar and CVaR: current **{summary['crisis_and_loco']['loco_positive_count']['current_ladder']} / {summary['crisis_and_loco']['number_of_frozen_crises']}**; binary **{summary['crisis_and_loco']['loco_positive_count']['binary_loud_075']} / {summary['crisis_and_loco']['number_of_frozen_crises']}**.",
        "",
        "Recovery capture is undefined when benchmark recovery is non-positive.",
        "",
        "| Crisis | Policy return | Full return | Protection | Policy max DD | Full max DD | Recovery capture | Recovery avg gross |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    current_crises = sorted(
        [
            row for row in result["crisis_rows"]
            if row["vehicle"] == "shanghai_composite"
            and row["policy"] == "current_ladder"
        ],
        key=lambda row: row["start"],
    )
    for row in current_crises:
        lines.append(
            f"| `{row['crisis']}` | {_fmt_pct(row['policy_return'])} | {_fmt_pct(row['full_return'])} | "
            f"{_fmt_pct(row['protection_vs_full'])} | {_fmt_pct(row['policy_max_drawdown'])} | "
            f"{_fmt_pct(row['full_max_drawdown'])} | {_fmt_pct(row['recovery_capture'])} | "
            f"{_fmt_num(row['recovery_average_gross'])} |"
        )

    ui = summary["ui_language_verdict"]
    lines += [
        "",
        "## Diagnostic stability",
        "",
        f"Lag/cost direction — current: **{summary['stability']['sensitivity_pass']['current_ladder']}**; binary: **{summary['stability']['sensitivity_pass']['binary_loud_075']}**.<br>",
        f"Split-era direction — current: **{summary['stability']['era_pass']['current_ladder']}**; binary: **{summary['stability']['era_pass']['binary_loud_075']}**.",
        "",
        "These diagnostic checks cannot override the non-PIT source qualification or the issued-forward episode floor.",
        "",
        "## Product-language adjudication",
        "",
        f"- May say **suggested size**: **{ui['may_say_suggested_size']}**.",
        f"- May say **risk-budget reference**: **{ui['may_say_risk_budget_reference']}**.",
        f"- May show **×0.62 as advice**: **{ui['may_show_x062_as_advice']}**.",
        f"- May show **×0.62 in research/debug disclosure**: **{ui['may_show_x062_in_research_disclosure']}**.",
        f"- Should round to “half of normal”: **{ui['should_round_plain_english_fraction']}**.",
        f"- Supported authority today: **{ui['authority_level']}**.",
        "",
        "No ruling in this wave authorizes automatic sizing, trade origination, exits, name vetoes, `can_force`, or a live control-plane consumer.",
        "",
        "## Forward evidence limit",
        "",
        _forward_evidence_sentence(forward),
        "",
        "## Shadow candidate",
        "",
        (
            f"An inert shadow candidate was earned: `{summary['shadow_candidate_if_earned']['policy_id']}`. It has no live consumer."
            if summary["shadow_candidate_if_earned"]
            else "No shadow policy candidate was earned under the frozen gates."
        ),
        "",
        "## Hold boundary",
        "",
        "This evidence carrier is intentionally Draft/HOLD. The Astra integrator may consume the fail-closed ruling, but any PIT-data repair or later source/UI policy change requires a separately authorized wave. Do not merge this PR and do not search alternative ladders around these outcomes.",
        "",
    ]
    return "\n".join(lines)

def write_artifacts(output_dir: Path, result: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "summary.json", result["summary"])
    _write_json(output_dir / "input_manifest.json", result["input_manifest"])
    _write_json(
        output_dir / "source_qualification.json",
        result["source_qualification"],
    )
    _write_json(output_dir / "bootstrap.json", result["bootstrap"])
    _write_csv(
        output_dir / "metrics.csv",
        result["metrics_rows"],
        ["vehicle", "lag", "cost_bps", "policy"],
    )
    _write_csv(
        output_dir / "crisis_results.csv",
        result["crisis_rows"],
        ["vehicle", "policy", "start"],
    )
    _write_csv(
        output_dir / "episode_results.csv",
        result["episode_rows"],
        ["policy", "episode_id"],
    )
    _write_csv(
        output_dir / "loco_results.csv",
        result["loco_rows"],
        ["policy", "excluded_crisis"],
    )
    _write_csv(
        output_dir / "era_results.csv",
        result["era_rows"],
        ["policy", "era"],
    )
    (output_dir / "REPORT.md").write_text(render_report(result))
    shadow_path = output_dir / "shadow_candidate.json"
    if result["shadow_candidate"] is not None:
        _write_json(shadow_path, result["shadow_candidate"])
    elif shadow_path.exists():
        shadow_path.unlink()

    artifact_paths = sorted(
        path for path in output_dir.iterdir()
        if path.is_file() and path.name != "artifact_manifest.json"
    )
    artifact_manifest = {
        "schema": "cn_risk_capital_policy_artifacts.v1",
        "operation_key": result["summary"]["operation_key"],
        "prereg_sha": result["summary"]["prereg_sha"],
        "files": {
            path.name: {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in artifact_paths
        },
    }
    _write_json(output_dir / "artifact_manifest.json", artifact_manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the frozen China Risk Radar capital-policy validation."
    )
    parser.add_argument("--output-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument(
        "--no-write", action="store_true",
        help="Compute and print the adjudication without writing artifacts.",
    )
    args = parser.parse_args(argv)
    result = run_study(output_dir=args.output_dir, emit_artifacts=not args.no_write)
    summary = result["summary"]
    print(json.dumps({
        "operation_key": summary["operation_key"],
        "policy_verdict": summary["policy_verdict"],
        "effective_episode_n": summary["episodes"]["authority_effective_n"],
        "riskoff_episode_n": summary["episodes"]["authority_risk_off_containing_n"],
        "elevated_only_episode_n": summary["episodes"]["authority_elevated_only_n"],
        "current_ladder_results": summary["current_ladder_results"],
        "ui_language_verdict": summary["ui_language_verdict"],
        "output_dir": str(args.output_dir) if not args.no_write else None,
    }, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
