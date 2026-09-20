from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from engine.options_hub import _atm_iv_for_expiry, _iv30_from_term

SCHEMA = "skylit.r5.spot_iv_shock_distribution/v1"
LOCAL_SPOT_BOUND_PCT = 3.0
LOCAL_VOL_BOUND_PTS = 5.0


class R5ShockRefusal(ValueError):
    pass


def _default_calendar_api():
    from lib import nyse_calendar
    return nyse_calendar


def _canonical_session(value: str, calendar_api) -> date:
    try:
        parsed = date.fromisoformat(value)
    except Exception as exc:
        raise R5ShockRefusal(f"invalid asof date: {value!r}") from exc
    if not calendar_api.is_session(parsed):
        raise R5ShockRefusal(f"asof is not an NYSE session: {value}")
    return parsed


def _f(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _daily_state(frame: pd.DataFrame, session: str) -> dict[str, Any] | None:
    rows = frame[frame["date"] == session].copy()
    if rows.empty:
        return None

    spot_values = pd.to_numeric(rows["underlying_price"], errors="coerce")
    spot_values = spot_values[np.isfinite(spot_values) & (spot_values > 0)]
    if spot_values.empty:
        return None
    spot = float(spot_values.median())

    session_day = date.fromisoformat(session)
    term_rows: list[dict[str, Any]] = []
    for expiration, group in rows.groupby("expiration", sort=False):
        try:
            exp_stamp = pd.Timestamp(expiration)
        except Exception:
            continue
        if pd.isna(exp_stamp):
            continue
        exp_day = exp_stamp.date()
        dte = (exp_day - session_day).days
        if dte < 0:
            continue
        atm_iv = _atm_iv_for_expiry(group, spot)
        if atm_iv is None or not np.isfinite(atm_iv) or atm_iv <= 0:
            continue
        # options_hub's term payload and _iv30_from_term operate in vol points.
        term_rows.append({
            "dte": dte,
            "atm_iv": float(atm_iv) * 100.0,
        })

    iv30 = _iv30_from_term(term_rows)
    if iv30 is None or not np.isfinite(iv30) or iv30 <= 0:
        return None

    return {
        "session": session,
        "spot": spot,
        "iv30_vol_points": float(iv30),
        "n_term_expiries": len(term_rows),
    }


def _stats(values: np.ndarray) -> dict[str, Any]:
    if values.size == 0:
        return {
            "mean": None,
            "std": None,
            "q05": None,
            "q25": None,
            "q50": None,
            "q75": None,
            "q95": None,
        }
    std = float(np.std(values, ddof=1)) if values.size >= 2 else 0.0
    return {
        "mean": float(np.mean(values)),
        "std": std,
        "q05": float(np.quantile(values, 0.05)),
        "q25": float(np.quantile(values, 0.25)),
        "q50": float(np.quantile(values, 0.50)),
        "q75": float(np.quantile(values, 0.75)),
        "q95": float(np.quantile(values, 0.95)),
    }


def build_distribution(
    greeks_df: pd.DataFrame,
    *,
    asof: str,
    root: str,
    window_sessions: int = 252,
    min_samples: int = 126,
    calendar_api=None,
) -> dict[str, Any]:
    """Build an outcome-blind trailing empirical spot/IV shock distribution.

    The construction is deliberately PIT-conservative: for an as-of session S,
    the latest shock admitted ends on a session strictly BEFORE S. The object is
    therefore usable before S begins and cannot learn from S's realised move.

    Each accepted sample is one consecutive NYSE-session transition:
      spot_pct = 100 * (S_t / S_{t-1} - 1)
      vol_pts  = IV30_t - IV30_{t-1}

    IV30 uses the same owner-native Options Hub ATM-IV/30D interpolation helpers
    as the live product. Missing sessions do not become multi-session shocks:
    non-consecutive state pairs are excluded and counted.
    """
    if type(window_sessions) is not int or window_sessions < 2:
        raise R5ShockRefusal("window_sessions must be an integer >= 2")
    if type(min_samples) is not int or min_samples < 1:
        raise R5ShockRefusal("min_samples must be a positive integer")
    if min_samples > window_sessions:
        raise R5ShockRefusal("min_samples cannot exceed window_sessions")

    calendar_api = calendar_api or _default_calendar_api()
    asof_day = _canonical_session(asof, calendar_api)

    required = {
        "root", "date", "expiration", "strike",
        "implied_vol", "underlying_price",
    }
    missing = sorted(required - set(greeks_df.columns))
    if missing:
        raise R5ShockRefusal(f"greeks frame missing columns: {missing}")

    frame = greeks_df.copy()
    frame["root"] = frame["root"].astype(str).str.upper()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date.astype(str)
    frame["expiration"] = pd.to_datetime(frame["expiration"], errors="coerce").dt.date.astype(str)
    frame["strike"] = pd.to_numeric(frame["strike"], errors="coerce")
    frame["implied_vol"] = pd.to_numeric(frame["implied_vol"], errors="coerce")
    frame["underlying_price"] = pd.to_numeric(frame["underlying_price"], errors="coerce")
    frame = frame[
        (frame["root"] == root.upper())
        & frame["date"].ne("NaT")
        & (frame["date"] < asof)
    ].copy()

    sessions = sorted(frame["date"].dropna().unique().tolist())
    states: list[dict[str, Any]] = []
    invalid_session_rows = 0
    unqualified_state_sessions = 0
    for session in sessions:
        try:
            session_day = date.fromisoformat(session)
        except ValueError:
            invalid_session_rows += 1
            continue
        if not calendar_api.is_session(session_day):
            invalid_session_rows += 1
            continue
        state = _daily_state(frame, session)
        if state is None:
            unqualified_state_sessions += 1
            continue
        states.append(state)

    all_shocks: list[dict[str, Any]] = []
    nonconsecutive_pairs = 0
    for left, right in zip(states, states[1:]):
        left_day = date.fromisoformat(left["session"])
        expected = calendar_api.session_n_forward(left_day, 1)
        if expected is None or expected.isoformat() != right["session"]:
            nonconsecutive_pairs += 1
            continue

        spot_pct = 100.0 * (right["spot"] / left["spot"] - 1.0)
        vol_pts = right["iv30_vol_points"] - left["iv30_vol_points"]
        if not np.isfinite(spot_pct) or not np.isfinite(vol_pts):
            continue
        inside = (
            abs(spot_pct) <= LOCAL_SPOT_BOUND_PCT
            and abs(vol_pts) <= LOCAL_VOL_BOUND_PTS
        )
        all_shocks.append({
            "from_session": left["session"],
            "to_session": right["session"],
            "spot_pct": float(spot_pct),
            "vol_pts": float(vol_pts),
            "within_local_scenario_envelope": bool(inside),
        })

    selected = all_shocks[-window_sessions:]
    n = len(selected)
    weight = (1.0 / n) if n else None
    samples = [
        {**row, "empirical_weight": weight}
        for row in selected
    ]

    spot = np.array([row["spot_pct"] for row in selected], dtype=float)
    vol = np.array([row["vol_pts"] for row in selected], dtype=float)
    inside = np.array(
        [row["within_local_scenario_envelope"] for row in selected],
        dtype=bool,
    )
    if n >= 2 and np.std(spot) > 0 and np.std(vol) > 0:
        corr = float(np.corrcoef(spot, vol)[0, 1])
    else:
        corr = None

    local_n = int(inside.sum()) if n else 0
    spot_tail = int(np.sum(np.abs(spot) > LOCAL_SPOT_BOUND_PCT)) if n else 0
    vol_tail = int(np.sum(np.abs(vol) > LOCAL_VOL_BOUND_PTS)) if n else 0
    status = "DISTRIBUTION_COMPLETE" if n >= min_samples else "INSUFFICIENT_HISTORY"

    return {
        "schema": SCHEMA,
        "status": status,
        "research_authority": "research_only",
        "outcome_labels_opened": False,
        "root": root.upper(),
        "asof": asof_day.isoformat(),
        "distribution": "trailing_empirical_equal_weight",
        "construction_cutoff_session": selected[-1]["to_session"] if selected else None,
        "window_sessions": window_sessions,
        "min_samples": min_samples,
        "n_samples": n,
        "spot_pct": _stats(spot),
        "vol_pts": _stats(vol),
        "spot_vol_correlation": corr,
        "local_scenario_envelope": {
            "spot_abs_max_pct": LOCAL_SPOT_BOUND_PCT,
            "vol_abs_max_pts": LOCAL_VOL_BOUND_PTS,
            "n_inside": local_n,
            "mass_inside": (local_n / n if n else None),
            "n_outside": (n - local_n),
            "mass_outside": ((n - local_n) / n if n else None),
            "n_spot_tail": spot_tail,
            "n_vol_tail": vol_tail,
            "renormalized": False,
        },
        "coverage": {
            "raw_sessions_before_asof": len(sessions),
            "qualified_daily_states": len(states),
            "invalid_session_rows": invalid_session_rows,
            "unqualified_state_sessions": unqualified_state_sessions,
            "nonconsecutive_pairs_excluded": nonconsecutive_pairs,
            "eligible_consecutive_shocks": len(all_shocks),
        },
        "samples": samples,
        "limitations": [
            "construction uses only shocks ending strictly before the as-of session",
            "this first R5 shock law is unconditional; regime/event conditioning is a later preregistered extension",
            "samples outside the existing scenarioGrid local envelope remain explicit tail mass and are never clipped or silently renormalized",
            "ATM IV30 reuses owner-native Options Hub interpolation semantics",
            "no future return, range, PnL, whipsaw or other R5 outcome label is read",
        ],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Research-only R5 PIT spot/IV shock-distribution constructor"
    )
    p.add_argument("--greeks-parquet", required=True)
    p.add_argument("--root", required=True)
    p.add_argument("--asof", required=True)
    p.add_argument("--window-sessions", type=int, default=252)
    p.add_argument("--min-samples", type=int, default=126)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        frame = pd.read_parquet(Path(args.greeks_parquet))
        result = build_distribution(
            frame,
            asof=args.asof,
            root=args.root,
            window_sessions=args.window_sessions,
            min_samples=args.min_samples,
        )
    except (OSError, R5ShockRefusal, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result["status"] == "DISTRIBUTION_COMPLETE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
