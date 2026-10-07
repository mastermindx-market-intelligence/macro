"""Relative options-pricing comparison over the canonical options-skew ledger.

This module is display-tier only. It creates a two-axis historical lookup from
an already-persisted options-skew ledger; it does not fetch a chain, create a
new market-data store, forecast returns, or infer dealer inventory.
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd

SCHEMA = "options_compare.v1"
WINDOW_SESSIONS = 60
TRAIL_SESSIONS = 5
MIN_HISTORY = 20
FAST_FRACTION = 0.10
_REQUIRED_COLUMNS = ("date", "underlying", "atm_call_iv", "skew", "tenor_days")


def _finite(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _lookup_position(reference: list[float], current: float) -> float | None:
    """Empirical mid-rank position of current versus prior observations, 0..100."""
    vals = [v for item in reference if (v := _finite(item)) is not None]
    cur = _finite(current)
    if cur is None or not vals:
        return None
    less = sum(v < cur for v in vals)
    equal = sum(math.isclose(v, cur, rel_tol=0.0, abs_tol=1e-12) for v in vals)
    return 100.0 * (less + 0.5 * equal) / len(vals)


def _normalized_history(history, *, asof: str, tickers: set[str]) -> pd.DataFrame:
    """Return one clean weekday row per (ticker, date), bounded at asof."""
    if history is None or getattr(history, "empty", True):
        return pd.DataFrame(columns=_REQUIRED_COLUMNS)
    if not set(_REQUIRED_COLUMNS).issubset(history.columns):
        return pd.DataFrame(columns=_REQUIRED_COLUMNS)

    work = history.loc[:, list(_REQUIRED_COLUMNS)].copy()
    work["underlying"] = work["underlying"].astype(str).str.upper().str.strip()
    parsed = pd.to_datetime(work["date"], errors="coerce")
    work["date"] = parsed.dt.strftime("%Y-%m-%d")
    for col in ("atm_call_iv", "skew", "tenor_days"):
        work[col] = pd.to_numeric(work[col], errors="coerce")

    work = work.dropna(subset=list(_REQUIRED_COLUMNS))
    work = work[
        (parsed.loc[work.index].dt.weekday < 5)
        & work["underlying"].isin(tickers)
        & (work["date"] <= asof)
        & (work["atm_call_iv"] > 0)
        & (work["tenor_days"] > 0)
    ]
    if work.empty:
        return work
    work = work.sort_values(["underlying", "date"], kind="stable")
    return work.drop_duplicates(
        ["underlying", "date"], keep="last"
    ).reset_index(drop=True)


def _point_history(
    group: pd.DataFrame, *, window: int, minimum: int
) -> list[dict]:
    points: list[dict] = []
    rows = group.reset_index(drop=True)
    for i in range(len(rows)):
        start = max(0, i - window)
        reference = rows.iloc[start:i]
        if len(reference) < minimum:
            continue
        current = rows.iloc[i]
        x = _lookup_position(
            reference["atm_call_iv"].tolist(), current["atm_call_iv"]
        )
        y = _lookup_position(reference["skew"].tolist(), current["skew"])
        if x is None or y is None:
            continue
        points.append(
            {
                "date": str(current["date"]),
                "x": round(x, 1),
                "y": round(y, 1),
                "reference_n": int(len(reference)),
            }
        )
    return points


def _motion(points: list[dict]) -> float:
    total = 0.0
    for left, right in zip(points, points[1:]):
        total += math.hypot(
            float(right["x"]) - float(left["x"]),
            float(right["y"]) - float(left["y"]),
        )
    return total


def build_compare(
    history,
    latest_payload: dict | None,
    *,
    window: int = WINDOW_SESSIONS,
    trail: int = TRAIL_SESSIONS,
    minimum_history: int = MIN_HISTORY,
    fast_fraction: float = FAST_FRACTION,
) -> dict | None:
    """Build the display payload from options_skew history + latest ledger view.

    Both axes are point-in-time lookups against prior observations only:
      x: selected near-month ATM call IV versus that ticker's prior sessions;
      y: selected 25-delta put minus ATM-call IV skew versus prior sessions.

    fast is purely descriptive: the fastest fast_fraction of names by Euclidean
    movement across the two lookup axes over their last trail valid session
    readings. It is not a direction, confidence, or alpha label.
    """
    if not latest_payload or not isinstance(latest_payload, dict):
        return None
    if window < 1 or trail < 2 or minimum_history < 1:
        raise ValueError(
            "window/minimum_history must be positive and trail must be >= 2"
        )
    if not (0 < fast_fraction <= 1):
        raise ValueError("fast_fraction must be in (0, 1]")

    latest_names = latest_payload.get("names") or {}
    if not isinstance(latest_names, dict) or not latest_names:
        return None
    asof = str(
        latest_payload.get("ledger_asof")
        or (latest_payload.get("source_detail") or {}).get("asof")
        or ""
    )[:10]
    if len(asof) != 10:
        return None

    tickers = {
        str(key).upper().strip() for key in latest_names if str(key).strip()
    }
    work = _normalized_history(history, asof=asof, tickers=tickers)
    if work.empty:
        return None

    records: dict[str, dict] = {}
    for ticker in sorted(tickers):
        group = work[work["underlying"] == ticker]
        if group.empty or str(group.iloc[-1]["date"]) != asof:
            continue
        points = _point_history(
            group, window=window, minimum=minimum_history
        )
        if not points or points[-1]["date"] != asof:
            continue

        current_row = group.iloc[-1]
        current_meta = latest_names.get(ticker) or {}
        atm_iv = _finite(current_meta.get("atm_call_iv"))
        if atm_iv is None:
            atm_iv = _finite(current_row["atm_call_iv"])
        skew = _finite(current_meta.get("skew"))
        if skew is None:
            skew = _finite(current_row["skew"])
        tenor = _finite(current_meta.get("tenor_days"))
        if tenor is None:
            tenor = _finite(current_row["tenor_days"])
        if (
            atm_iv is None
            or atm_iv <= 0
            or skew is None
            or tenor is None
            or tenor <= 0
        ):
            continue

        recent = points[-trail:]
        current_point = recent[-1]
        expected_move = atm_iv * math.sqrt(tenor / 365.0) * 100.0
        records[ticker] = {
            "ticker": ticker,
            "date": asof,
            "options_pct": current_point["x"],
            "protection_pct": current_point["y"],
            "history_n": current_point["reference_n"],
            "atm_call_iv": round(atm_iv, 6),
            "skew_vol_points": round(skew * 100.0, 2),
            "tenor_days": round(tenor, 1),
            "expected_move_pct": round(expected_move, 1),
            "trail": recent,
            "motion_5d": round(_motion(recent), 1),
            "zone": "calm",
        }

    if not records:
        return None

    motion_pool = [
        row
        for row in records.values()
        if len(row["trail"]) == trail and row["motion_5d"] > 0
    ]
    motion_pool.sort(
        key=lambda row: (-float(row["motion_5d"]), row["ticker"])
    )
    fast_count = (
        max(1, math.ceil(len(motion_pool) * fast_fraction))
        if motion_pool
        else 0
    )
    fast_names = [row["ticker"] for row in motion_pool[:fast_count]]
    fast_set = set(fast_names)
    for ticker, row in records.items():
        if ticker in fast_set:
            row["zone"] = "fast"

    default_ticker = (
        fast_names[0]
        if fast_names
        else ("SPY" if "SPY" in records else sorted(records)[0])
    )
    detail = latest_payload.get("source_detail") or {}
    history_sources = latest_payload.get("history_sources") or []
    source_windows = latest_payload.get("source_windows") or []
    return {
        "schema": SCHEMA,
        "is_context_only": True,
        "scored": False,
        "asof": asof,
        "window_sessions": int(window),
        "trail_sessions": int(trail),
        "minimum_history": int(minimum_history),
        "n": len(records),
        "fast_count": len(fast_names),
        "calm_count": len(records) - len(fast_names),
        "fast_names": fast_names,
        "default_ticker": default_ticker,
        "source_state": latest_payload.get("source_state"),
        "stale_days": detail.get("stale_days"),
        "history_sources": [str(item) for item in history_sources],
        "source_windows": source_windows,
        "source_break": bool(latest_payload.get("source_break")),
        "source_break_date": latest_payload.get("source_break_date"),
        "partial_sessions_skipped": (
            detail.get("partial_sessions_skipped") or []
        ),
        "names": records,
    }
