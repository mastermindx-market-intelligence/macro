"""Closed-session parent/subtheme leadership observations for the rotation desk.

This is a descriptive, scoreless extension of the existing Group Reads plane.  It
separates strength level, acceleration and persistence over fixed completed-session
windows; preserves exact coverage and source receipts; deduplicates parent membership;
and carries no ranking, gating, sizing, Prophet or trading authority.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from lib.closes_panel import align_latest_common_observation, population_observation

SCHEMA = "subsector_rotation.early_leadership.v1"
WINDOWS = (1, 3, 5, 10, 20, 60)
COVERAGE_TARGET_IDS = (
    "cpu_server_compute",
    "gpu_accelerators",
    "hbm",
    "dram",
    "nand_ssd",
    "disk_storage",
    "equipment",
    "optics",
)

# Existing taxonomy nodes only.  ``proxy`` means the local node does not isolate the
# requested economic subtheme; no canonical identity is fabricated here.
_COVERAGE_TARGETS: tuple[dict, ...] = (
    {"target_id": "cpu_server_compute", "label": "CPU / server compute",
     "nodes": (("semiscompute", "direct"), ("hardwareservers", "direct")),
     "gap": "CPU silicon and server systems remain separate mixed local nodes."},
    {"target_id": "gpu_accelerators", "label": "GPU / accelerators",
     "nodes": (("semiscompute", "direct"),),
     "gap": "The node also contains CPUs, wireless and custom silicon; GPU is not isolated."},
    {"target_id": "hbm", "label": "HBM",
     "nodes": (("semismemory", "proxy"),),
     "gap": "HBM is not a distinct canonical local node; Memory is an exploratory proxy."},
    {"target_id": "dram", "label": "DRAM",
     "nodes": (("semismemory", "proxy"),),
     "gap": "DRAM is not separated from HBM, NAND and storage in the existing node."},
    {"target_id": "nand_ssd", "label": "NAND / SSD",
     "nodes": (("semismemory", "proxy"), ("hardwarestorage", "proxy")),
     "gap": "NAND and SSD are not isolated from memory suppliers and storage systems."},
    {"target_id": "disk_storage", "label": "Disk storage",
     "nodes": (("hardwarestorage", "direct"),),
     "gap": "The node mixes drives, arrays and server/storage vendors."},
    {"target_id": "equipment", "label": "Semiconductor equipment",
     "nodes": (("semislithography", "direct"),),
     "gap": None},
    {"target_id": "optics", "label": "Optics",
     "nodes": (("hardwaretelecom", "proxy"),),
     "gap": "Optics is not isolated from broader communications and telecom equipment."},
)

_PERMISSIONS = {
    "is_context_only": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_trade": False,
    "may_escalate": False,
    "may_modify_prophet": False,
    "may_modify_oracle": False,
}


def _date_text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _normalise_panel(panel: pd.DataFrame | None) -> pd.DataFrame:
    if panel is None:
        return pd.DataFrame()
    out = panel.copy()
    out.index = pd.to_datetime(out.index)
    out = out.loc[~out.index.duplicated(keep="last")]
    out.columns = [str(c).strip().upper() for c in out.columns]
    return out.sort_index()


def _normalise_series(series: pd.Series) -> pd.Series:
    out = series.copy()
    out.index = pd.to_datetime(out.index)
    out = out.loc[~out.index.duplicated(keep="last")]
    return out.sort_index()


def _members(values: Sequence | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values or ():
        ticker = str(value).strip().upper()
        if ticker and ticker not in seen:
            seen.add(ticker)
            out.append(ticker)
    return out


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None or not np.isfinite(value):
        return None
    return round(float(value), digits)


def _fully_adjusted_basis(price_basis) -> bool:
    if isinstance(price_basis, Mapping):
        values = list(price_basis.values())
        return bool(values) and all(_fully_adjusted_basis(value) for value in values)
    text = str(price_basis or "").lower()
    if "unadjusted" in text or "raw" in text:
        return False
    return any(token in text for token in ("adjusted", "tradj", "total_return"))


def _corporate_action_candidates(panel: pd.DataFrame, lookback: int = 70) -> list[str]:
    if panel.empty:
        return []
    tail = panel.tail(lookback + 1)
    candidates: list[str] = []
    for ticker in tail.columns:
        s = pd.to_numeric(tail[ticker], errors="coerce")
        jump = s.pct_change(fill_method=None).abs()
        if bool((jump >= 0.40).any()) or bool((s.dropna() <= 0).any()):
            candidates.append(str(ticker))
    return sorted(candidates)


def _population(panel: pd.DataFrame, members: list[str], asof, *, min_members: int,
                min_coverage: float) -> dict:
    return population_observation(
        panel,
        [{"ticker": ticker} for ticker in members],
        asof,
        min_members=min_members,
        min_coverage=min_coverage,
    )


def _market_return(benchmark: pd.Series, window: int) -> float | None:
    if len(benchmark) <= window:
        return None
    first, last = benchmark.iloc[-(window + 1)], benchmark.iloc[-1]
    if pd.isna(first) or pd.isna(last) or float(first) <= 0:
        return None
    return (float(last) / float(first) - 1.0) * 100.0


def _horizon(
    panel: pd.DataFrame,
    members: list[str],
    window: int,
    benchmark: pd.Series,
    *,
    parent_return: float | None,
    excluded: set[str],
    min_members: int,
    min_coverage: float,
) -> dict:
    configured_n = len(members)
    reasons: list[str] = []
    if len(panel) <= window:
        return {
            "return_pct": None, "market_pct": None, "parent_pct": parent_return,
            "rel_market_pct": None, "rel_parent_pct": None,
            "coverage": {"configured_n": configured_n, "eligible_n": 0, "coverage": 0.0,
                         "status": "insufficient"},
            "participation": None, "dispersion_pct": None,
            "concentration": None, "reason_codes": ["INSUFFICIENT_SESSION_HISTORY"],
        }
    start = panel.iloc[-(window + 1)]
    end = panel.iloc[-1]
    returns: dict[str, float] = {}
    for ticker in members:
        if ticker in excluded or ticker not in panel.columns:
            continue
        a, b = start.get(ticker), end.get(ticker)
        if pd.isna(a) or pd.isna(b) or float(a) <= 0:
            continue
        value = (float(b) / float(a) - 1.0) * 100.0
        if np.isfinite(value):
            returns[ticker] = value
    eligible_n = len(returns)
    coverage = eligible_n / configured_n if configured_n else 0.0
    aggregate_eligible = bool(
        configured_n and eligible_n >= min_members and coverage >= min_coverage
    )
    status = "complete" if configured_n and eligible_n == configured_n else (
        "partial" if aggregate_eligible else "insufficient"
    )
    market = _market_return(benchmark, window)
    if market is None:
        reasons.append("MARKET_WINDOW_UNAVAILABLE")
    if not aggregate_eligible:
        reasons.append("INSUFFICIENT_HORIZON_COVERAGE")
    if excluded.intersection(members):
        reasons.append("CORPORATE_ACTION_CANDIDATE_EXCLUDED")
    result = {
        "return_pct": None, "market_pct": _round(market), "parent_pct": _round(parent_return),
        "rel_market_pct": None, "rel_parent_pct": None,
        "coverage": {"configured_n": configured_n, "eligible_n": eligible_n,
                     "coverage": _round(coverage), "status": status,
                     "eligible_members": list(returns)},
        "participation": None, "dispersion_pct": None,
        "concentration": None, "reason_codes": reasons,
    }
    if not aggregate_eligible:
        return result
    values = np.array(list(returns.values()), dtype=float)
    group_return = float(values.mean())
    result["return_pct"] = _round(group_return)
    result["rel_market_pct"] = _round(group_return - market) if market is not None else None
    result["rel_parent_pct"] = _round(group_return - parent_return) if parent_return is not None else None
    beat_parent = None if parent_return is None else float((values > parent_return).mean())
    beat_market = None if market is None else float((values > market).mean())
    result["participation"] = {
        "n": eligible_n,
        "up_fraction": _round(float((values > 0).mean())),
        "beat_market_fraction": _round(beat_market),
        "beat_parent_fraction": _round(beat_parent),
    }
    result["dispersion_pct"] = _round(float(values.std(ddof=0)))
    magnitudes = np.abs(values)
    total = float(magnitudes.sum())
    top_i = int(np.argmax(magnitudes)) if eligible_n else 0
    top_share = float(magnitudes[top_i] / total) if total > 1e-12 else 0.0
    result["concentration"] = {
        "top_ticker": list(returns)[top_i] if eligible_n else None,
        "top_share": _round(top_share),
        "concentrated": bool(top_share >= 0.50 and eligible_n >= min_members),
        "basis": "absolute_member_return_share",
    }
    return result


def _daily_group_return(panel: pd.DataFrame, members: list[str], excluded: set[str], *,
                        min_members: int, min_coverage: float) -> pd.Series:
    keep = [ticker for ticker in members if ticker in panel.columns and ticker not in excluded]
    if not keep:
        return pd.Series(np.nan, index=panel.index, dtype="float64")
    returns = panel[keep].pct_change(fill_method=None)
    required = max(min_members, int(math.ceil(len(members) * min_coverage)))
    counts = returns.notna().sum(axis=1)
    return returns.mean(axis=1, skipna=True).where(counts >= required)


def _rs_slopes(group_daily: pd.Series, benchmark: pd.Series) -> tuple[dict, dict]:
    bench_daily = benchmark.pct_change(fill_method=None)
    slopes: dict[str, float | None] = {}
    changes: dict[str, float | None] = {}
    for window in WINDOWS:
        g = group_daily.tail(window)
        b = bench_daily.tail(window)
        joined = pd.concat([g.rename("g"), b.rename("b")], axis=1)
        values = joined.to_numpy(dtype=float)
        if (len(joined) != window or joined.isna().any().any()
                or not np.isfinite(values).all() or bool((values <= -1.0).any())):
            slopes[str(window)] = None
            changes[str(window)] = None
            continue
        rel = np.log1p(joined["g"].to_numpy()) - np.log1p(joined["b"].to_numpy())
        slopes[str(window)] = _round(float(rel.mean() * 100.0), 6)
        split = window // 2
        if split < 2 or window - split < 2:
            changes[str(window)] = None
        else:
            prior = float(rel[:split].mean())
            recent = float(rel[split:].mean())
            changes[str(window)] = _round((recent - prior) * 100.0, 6)
    return slopes, changes


def _breakout_reclaim(panel: pd.DataFrame, members: list[str], excluded: set[str]) -> tuple[dict, dict]:
    attempted = held = failed = reclaim = 0
    measured = 0
    for ticker in members:
        if ticker in excluded or ticker not in panel.columns:
            continue
        w = pd.to_numeric(panel[ticker].tail(26), errors="coerce")
        if len(w) < 26 or w.isna().any():
            continue
        prior_high = float(w.iloc[:-5].max())
        recent = w.iloc[-5:]
        last = float(recent.iloc[-1])
        prev = float(recent.iloc[-2])
        measured += 1
        tried = bool(float(recent.max()) > prior_high)
        is_held = bool(last > prior_high)
        is_failed = bool(tried and not is_held)
        attempted += int(tried)
        held += int(tried and is_held)
        failed += int(is_failed)
        reclaim += int(prev <= prior_high and last > prior_high)
    return (
        {"measured_n": measured, "attempted_n": attempted, "held_n": held,
         "failed_n": failed, "definition": "prior_20_session_high_vs_last_5_sessions"},
        {"measured_n": measured, "reclaimed_20d_high_n": reclaim,
         "definition": "prior_close_at_or_below_prior_20d_high_then_close_above"},
    )


def _volume(volume: pd.DataFrame | None, members: list[str], excluded: set[str]) -> dict:
    configured_n = len(members)
    if volume is None or volume.empty:
        return {"status": "unavailable", "reason": "VOLUME_PANEL_UNAVAILABLE",
                "configured_n": configured_n, "measured_n": 0, "coverage": 0.0,
                "median_5v20_ratio": None, "above_prior_average_fraction": None}
    ratios: list[float] = []
    for ticker in members:
        if ticker in excluded or ticker not in volume.columns:
            continue
        s = pd.to_numeric(volume[ticker].tail(25), errors="coerce")
        if len(s) < 25 or s.isna().any():
            continue
        prior = float(s.iloc[:-5].mean())
        recent = float(s.iloc[-5:].mean())
        if prior > 0 and np.isfinite(prior) and np.isfinite(recent):
            ratios.append(recent / prior)
    if not ratios:
        return {"status": "unavailable", "reason": "INSUFFICIENT_VOLUME_HISTORY",
                "configured_n": configured_n, "measured_n": 0, "coverage": 0.0,
                "median_5v20_ratio": None, "above_prior_average_fraction": None}
    arr = np.array(ratios, dtype=float)
    return {"status": "available", "reason": None, "configured_n": configured_n,
            "measured_n": len(ratios),
            "coverage": _round(len(ratios) / configured_n) if configured_n else None,
            "median_5v20_ratio": _round(float(np.median(arr))),
            "above_prior_average_fraction": _round(float((arr > 1.0).mean())),
            "definition": "member_mean_volume_last_5_over_prior_20"}


def _mean_available(values: Sequence[float | None]) -> float | None:
    kept = [float(value) for value in values if value is not None and np.isfinite(value)]
    return float(np.mean(kept)) if kept else None


def _descriptions(horizons: dict, slope_changes: dict, breakout: dict) -> tuple[dict, dict, dict]:
    short = _mean_available([horizons[str(w)]["rel_market_pct"] for w in (1, 3, 5)])
    long = _mean_available([horizons[str(w)]["rel_market_pct"] for w in (20, 60)])
    strength_reasons: list[str] = []
    if short is None:
        strength_state = "insufficient"
        strength_reasons.append("SHORT_WINDOWS_UNAVAILABLE")
    elif long is None:
        strength_state = "short_only_observed" if short > 0 else "short_lagging_long_unavailable"
        strength_reasons.append("LONG_WINDOWS_UNAVAILABLE")
    elif short > 0 and long <= 0:
        strength_state = "short_leading_long_lagging"
    elif short > 0 and long > 0:
        strength_state = "leading"
    elif short <= 0 and long > 0:
        strength_state = "short_pullback_inside_long_lead"
    else:
        strength_state = "lagging"
    strength = {"state": strength_state, "short_rel_market_pct": _round(short),
                "long_rel_market_pct": _round(long), "reason_codes": strength_reasons,
                "definition": "short=mean(1,3,5); long=mean(20,60); zero boundary only"}

    change = next((slope_changes[str(w)] for w in (5, 10, 20, 60)
                   if slope_changes.get(str(w)) is not None), None)
    accel_reasons: list[str] = []
    if breakout.get("failed_n", 0) > 0:
        acceleration_state = "cooling_after_failed_breakout"
        accel_reasons.append("FAILED_BREAKOUT")
    elif change is None:
        acceleration_state = "insufficient"
        accel_reasons.append("RS_SLOPE_CHANGE_UNAVAILABLE")
    elif change > 0 and short is not None and short > 0:
        acceleration_state = "reaccelerating"
    elif change > 0:
        acceleration_state = "improving"
    elif change < 0 and short is not None and short <= 0:
        acceleration_state = "cooling"
    else:
        acceleration_state = "steady"
    acceleration = {"state": acceleration_state, "selected_slope_change": change,
                    "reason_codes": accel_reasons,
                    "definition": "recent-minus-prior relative log-return pace; failed breakout overrides"}

    measured = [(w, horizons[str(w)]["rel_market_pct"]) for w in WINDOWS
                if horizons[str(w)]["rel_market_pct"] is not None]
    positive = [w for w, value in measured if value > 0]
    short_vals = [horizons[str(w)]["rel_market_pct"] for w in (1, 3, 5)]
    long_vals = [horizons[str(w)]["rel_market_pct"] for w in (20, 60)]
    if not measured:
        persistence_state = "insufficient"
    elif all(value is not None and value > 0 for value in short_vals) and any(
        value is not None and value <= 0 for value in long_vals
    ):
        persistence_state = "short_only"
    elif len(positive) == len(measured):
        persistence_state = "broad_across_windows"
    elif not positive:
        persistence_state = "absent"
    else:
        persistence_state = "mixed"
    persistence = {"state": persistence_state, "positive_rel_windows": positive,
                   "measured_windows": [w for w, _ in measured],
                   "definition": "sign agreement across fixed windows; no forecast weight"}
    return strength, acceleration, persistence


def _row(
    *,
    key: str,
    name: str,
    theme: str,
    members: list[str],
    panel: pd.DataFrame,
    benchmark: pd.Series,
    volume: pd.DataFrame | None,
    parent_horizons: dict[str, dict] | None,
    excluded: set[str],
    asof: str,
    min_members: int,
    min_coverage: float,
) -> dict:
    pop = _population(panel, members, asof, min_members=min_members, min_coverage=min_coverage)
    horizons: dict[str, dict] = {}
    for window in WINDOWS:
        parent_return = None
        if parent_horizons is not None:
            parent_return = (parent_horizons.get(str(window)) or {}).get("return_pct")
        horizons[str(window)] = _horizon(
            panel, members, window, benchmark,
            parent_return=parent_return, excluded=excluded,
            min_members=min_members, min_coverage=min_coverage,
        )
    daily = _daily_group_return(
        panel, members, excluded, min_members=min_members, min_coverage=min_coverage,
    )
    slopes, slope_changes = _rs_slopes(daily, benchmark)
    breakout, reclaim = _breakout_reclaim(panel, members, excluded)
    strength, acceleration, persistence = _descriptions(horizons, slope_changes, breakout)
    return {
        "key": key,
        "name": name,
        "theme": theme,
        "population": pop,
        "measurement_excluded_members": sorted(excluded.intersection(members)),
        "horizons": horizons,
        "rs_slope_pct_per_session": slopes,
        "rs_slope_change_pct_per_session": slope_changes,
        "strength": strength,
        "acceleration": acceleration,
        "persistence": persistence,
        "breakout": breakout,
        "reclaim": reclaim,
        "volume": _volume(volume, members, excluded),
    }


def _coverage(rows: list[dict]) -> list[dict]:
    by_key = {row["key"]: row for row in rows}
    out: list[dict] = []
    for spec in _COVERAGE_TARGETS:
        source_nodes: list[dict] = []
        for key, relationship in spec["nodes"]:
            row = by_key.get(key)
            if row is None:
                source_nodes.append({"key": key, "relationship": relationship,
                                     "mapped": False, "priced_n": 0, "configured_n": 0,
                                     "eligible": False})
                continue
            pop = row["population"]
            source_nodes.append({
                "key": key,
                "theme": row["theme"],
                "name": row["name"],
                "relationship": relationship,
                "mapped": True,
                "priced_n": pop["observed_n"],
                "configured_n": pop["configured_n"],
                "eligible": bool(pop["aggregate_eligible"]),
            })
        mapped_nodes = [node for node in source_nodes if node["mapped"]]
        out.append({
            "target_id": spec["target_id"],
            "label": spec["label"],
            "mapped": bool(mapped_nodes),
            "eligible": any(node["eligible"] for node in mapped_nodes),
            "mapping_status": "existing_local_node" if any(
                node["relationship"] == "direct" for node in mapped_nodes
            ) else ("exploratory_proxy" if mapped_nodes else "unmapped"),
            "source_nodes": source_nodes,
            "granularity_gap": spec["gap"],
        })
    return out


def unavailable_early_leadership(reason: str, *, source_receipts: Mapping | None = None,
                                 clocks: Mapping | None = None) -> dict:
    """JSON-ready degrade receipt with the same zero-authority contract."""
    return {
        "schema": SCHEMA,
        "status": "unavailable",
        "asof": None,
        "windows": list(WINDOWS),
        "permissions": dict(_PERMISSIONS),
        "reason_codes": [str(reason)],
        "source_receipts": dict(source_receipts or {}),
        "clocks": dict(clocks or {}),
        "parents": [],
        "subthemes": [],
        "coverage": [],
    }


def compute_early_leadership(
    tree: Sequence[Mapping],
    close_panel: pd.DataFrame,
    benchmark_close: pd.Series,
    *,
    volume_panel: pd.DataFrame | None = None,
    asof: str | None = None,
    provisional_dates: Sequence | None = None,
    membership_revision: Mapping | None = None,
    price_basis="caller_supplied_adjusted_close",
    source_receipts: Mapping | None = None,
    min_members: int = 3,
    min_coverage: float = 0.60,
) -> dict:
    """Build a deterministic closed-session parent/subtheme observation.

    Current tree membership is used only for the current observation.  It is never
    replayed as historical point-in-time membership.  The caller owns input loading and
    source rights; this function owns pure measurement and explicit receipts.
    """
    panel = _normalise_panel(close_panel)
    benchmark = _normalise_series(benchmark_close)
    volume = _normalise_panel(volume_panel) if volume_panel is not None else None
    provisional = sorted({_date_text(value) for value in (provisional_dates or ()) if _date_text(value)})
    provisional_ts = {pd.Timestamp(value) for value in provisional}
    if provisional_ts:
        panel = panel.loc[~panel.index.isin(provisional_ts)]
        benchmark = benchmark.loc[~benchmark.index.isin(provisional_ts)]
        if volume is not None:
            volume = volume.loc[~volume.index.isin(provisional_ts)]
    if asof:
        cutoff = pd.Timestamp(asof)
        panel = panel.loc[panel.index <= cutoff]
        benchmark = benchmark.loc[benchmark.index <= cutoff]
        if volume is not None:
            volume = volume.loc[volume.index <= cutoff]
    panel, benchmark, observation = align_latest_common_observation(panel, benchmark)
    observation["excluded_provisional_dates"] = provisional
    effective = observation.get("effective_as_of")
    base = {
        "schema": SCHEMA,
        "asof": effective,
        "status": "available" if effective else "unavailable",
        "windows": list(WINDOWS),
        "permissions": dict(_PERMISSIONS),
        "basis": {
            "session": "latest_exact_panel_and_benchmark_observation",
            "bar_status": "completed_sessions_only",
            "membership": "current_tree_snapshot_not_historical_pit",
            "historical_membership_replay": False,
            "parent": "deduplicated_union_of_current_child_members",
            "price": price_basis,
            "corporate_actions": "caller_basis_plus_extreme_move_exclusion_when_not_fully_adjusted",
            "returns": "equal_weight_member_endpoint_return",
            "relative_strength_slope": "mean_relative_log_return_per_session",
        },
        "membership_revision": dict(membership_revision or {
            "status": "unversioned_current_snapshot",
        }),
        "source_receipts": dict(source_receipts or {}),
        "observation": observation,
        "parents": [],
        "subthemes": [],
        "coverage": [],
        "data_quality": {},
    }
    if not effective:
        base["data_quality"] = {"reason_codes": ["NO_COMMON_CLOSED_SESSION"]}
        return base
    if volume is not None:
        volume = volume.reindex(panel.index)
    candidates = _corporate_action_candidates(panel)
    fully_adjusted = _fully_adjusted_basis(price_basis)
    excluded = set() if fully_adjusted else set(candidates)
    base["data_quality"] = {
        "corporate_action_candidates": candidates,
        "excluded_unadjusted_candidates": sorted(excluded),
        "price_basis_fully_adjusted": fully_adjusted,
        "corporate_action_candidate_threshold_abs_daily_return": 0.40,
        "reason_codes": (["UNADJUSTED_EXTREME_MOVE_EXCLUSION"] if excluded else []),
    }

    parents: list[dict] = []
    sub_specs: list[tuple[dict, dict]] = []
    for theme_raw in tree or ():
        theme = str(theme_raw.get("theme") or theme_raw.get("key") or "").strip()
        if not theme:
            continue
        flattened: list[str] = []
        raw_n = 0
        valid_subs: list[dict] = []
        for sub in theme_raw.get("subsectors") or ():
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            members = _members(sub.get("members") or ())
            raw_n += len(members)
            flattened.extend(members)
            valid_subs.append({"key": key, "name": str(sub.get("name") or key),
                               "theme": theme, "members": members})
        parent_members = _members(flattened)
        if not parent_members:
            continue
        parent = _row(
            key=theme, name=theme, theme=theme, members=parent_members,
            panel=panel, benchmark=benchmark, volume=volume,
            parent_horizons=None, excluded=excluded, asof=effective,
            min_members=min_members, min_coverage=min_coverage,
        )
        parent["duplicate_members_collapsed"] = raw_n - len(parent_members)
        parents.append(parent)
        for spec in valid_subs:
            sub_specs.append((spec, parent))

    subthemes: list[dict] = []
    for spec, parent in sub_specs:
        subthemes.append(_row(
            key=spec["key"], name=spec["name"], theme=spec["theme"],
            members=spec["members"], panel=panel, benchmark=benchmark,
            volume=volume, parent_horizons=parent["horizons"], excluded=excluded,
            asof=effective, min_members=min_members, min_coverage=min_coverage,
        ))
    base["parents"] = parents
    base["subthemes"] = subthemes
    base["coverage"] = _coverage(subthemes)
    return base
