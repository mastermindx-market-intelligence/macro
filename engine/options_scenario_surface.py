"""Conditional price x future-time Greek scenario surface.

Additive Options Workbench R2 model. This is not observed strike x clock history
and not a predicted price path. It reuses engine.intraday_greeks.bs_greeks_vec,
so it creates no second Greek or pricing kernel.

V1 assumptions are explicit: fixed input OI, sticky-strike input IV,
deterministic time roll-forward, incumbent +call/-put dealer-sign assumption.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np

from engine.intraday_greeks import (
    CONTRACT_MULTIPLIER,
    DEFAULT_Q,
    DEFAULT_R,
    PCT_MOVE,
    bs_greeks_vec,
    implied_vol_vec,
)

SCHEMA = "options.scenario_surface/v1"
PRODUCT_KIND = "conditional_price_time_scenario"
VOL_MAP_STICKY_STRIKE = "sticky_strike"
IV_SOURCE_PROVIDED = "provided_iv"
IV_SOURCE_MID_SOLVE = "solve_from_mid"
MINUTES_PER_YEAR = 365.0 * 24.0 * 60.0
ET = ZoneInfo("America/New_York")


def _finite_positive(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) and out > 0 else None


def _finite_number(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _sum_or_none(values: np.ndarray) -> float | None:
    with np.errstate(over="ignore", invalid="ignore"):
        total = float(np.sum(values))
    return total if np.isfinite(total) else None


def _source_clock_bounds(
    contracts: list[dict],
    field: str,
    *,
    observed_dt: datetime,
) -> tuple[str | None, str | None]:
    """Fail a source-clock envelope closed when any contributing member is unknown.

    This mirrors the incumbent live-flow provenance rule: known-only min/max bounds are
    dishonest for a mixed known/unknown contract set. A known source instant after the
    market observation is an impossible PIT state and is rejected instead of backdated.
    """
    if not contracts:
        return None, None
    instants: list[datetime] = []
    observed_utc = observed_dt.astimezone(ZoneInfo("UTC"))
    for contract in contracts:
        raw = contract.get(field)
        if not isinstance(raw, str) or not raw.strip():
            return None, None
        try:
            dt = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            return None, None
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None, None
        dt = dt.astimezone(ZoneInfo("UTC"))
        if dt > observed_utc:
            raise ValueError(f"{field} cannot be after observed_at")
        instants.append(dt)
    instants.sort()
    return (
        instants[0].isoformat().replace("+00:00", "Z"),
        instants[-1].isoformat().replace("+00:00", "Z"),
    )


def _require_aware_iso(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("observed_at must be a non-empty timezone-aware ISO timestamp")
    raw = value.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be a timezone-aware ISO timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")
    return raw


def _price_grid(values: Iterable[Any]) -> list[float]:
    out = sorted({x for v in values if (x := _finite_positive(v)) is not None})
    if len(out) < 2:
        raise ValueError("price_grid must contain at least two distinct positive prices")
    return out


def _horizons(values: Iterable[Any]) -> list[int]:
    out: set[int] = set()
    for value in values:
        if isinstance(value, bool):
            raise ValueError("horizons_minutes must contain non-negative integers")
        try:
            x = int(value)
            same = float(value) == float(x)
        except (TypeError, ValueError) as exc:
            raise ValueError("horizons_minutes must contain non-negative integers") from exc
        if not same or x < 0:
            raise ValueError("horizons_minutes must contain non-negative integers")
        out.add(x)
    if not out:
        raise ValueError("horizons_minutes must not be empty")
    return sorted(out)


def _normalize_contracts(
    contracts: list[dict],
    *,
    expiry_scope: set[str] | None,
    max_dte_days: float | None,
    iv_source: str,
) -> tuple[list[dict], dict[str, int]]:
    valid: list[dict] = []
    counts = {
        "input": len(contracts),
        "valid_snapshot": 0,
        "omitted_invalid": 0,
        "omitted_scope": 0,
        "iv_input": 0,
        "iv_solved": 0,
        "omitted_iv_unsolved": 0,
    }
    for raw in contracts:
        if not isinstance(raw, dict):
            counts["omitted_invalid"] += 1
            continue
        strike = _finite_positive(raw.get("strike"))
        T = _finite_positive(raw.get("exp_years"))
        oi = _finite_positive(raw.get("oi"))
        right = str(raw.get("right", "")).upper()[:1]
        expiry_raw = raw.get("expiry")
        exp_str_raw = raw.get("exp_str")
        expiry = str(expiry_raw).strip()[:10] if expiry_raw is not None and str(expiry_raw).strip() else None
        exp_str = str(exp_str_raw).strip()[:10] if exp_str_raw is not None and str(exp_str_raw).strip() else None
        if expiry is not None and exp_str is not None and expiry != exp_str:
            counts["omitted_invalid"] += 1
            continue
        expiry = expiry or exp_str
        iv = _finite_positive(raw.get("iv")) if iv_source == IV_SOURCE_PROVIDED else None
        mid = _finite_positive(raw.get("mid")) if iv_source == IV_SOURCE_MID_SOLVE else None
        source_value = iv if iv_source == IV_SOURCE_PROVIDED else mid
        if strike is None or T is None or source_value is None or oi is None or right not in {"C", "P"}:
            counts["omitted_invalid"] += 1
            continue
        if expiry_scope is not None and expiry not in expiry_scope:
            counts["omitted_scope"] += 1
            continue
        if max_dte_days is not None and T * 365.0 > max_dte_days:
            counts["omitted_scope"] += 1
            continue
        row = {
            "strike": strike,
            "exp_years": T,
            "oi": oi,
            "right": right,
            "expiry": expiry,
            "trade_at": raw.get("trade_at"),
            "quote_at": raw.get("quote_at"),
        }
        if iv_source == IV_SOURCE_PROVIDED:
            row["iv"] = iv
            counts["iv_input"] += 1
        else:
            row["mid"] = mid
        valid.append(row)
    counts["valid_snapshot"] = len(valid)
    return valid, counts


def _zero_crossings(xs: list[float], ys: list[float | None]) -> list[float]:
    out: list[float] = []
    for i in range(len(xs) - 1):
        y0, y1 = ys[i], ys[i + 1]
        if y0 is None or y1 is None:
            continue
        x0, x1 = xs[i], xs[i + 1]
        if y0 == 0.0:
            x = x0
        elif (y0 < 0) != (y1 < 0):
            x = x0 - y0 * (x1 - x0) / (y1 - y0) if y1 != y0 else x0
        else:
            continue
        if not out or abs(out[-1] - x) > 1e-10:
            out.append(float(x))
    if ys and ys[-1] == 0.0:
        x = float(xs[-1])
        if not out or abs(out[-1] - x) > 1e-10:
            out.append(x)
    return out


def build_scenario_surface(
    contracts: list[dict],
    *,
    root: str,
    observed_at: str,
    spot: float,
    price_grid: list[float],
    horizons_minutes: list[int],
    expiry_scope: list[str] | None = None,
    max_dte_days: float | None = None,
    oi_vintage: str | None = None,
    iv_observed_at: str | None = None,
    vol_map: str = VOL_MAP_STICKY_STRIKE,
    iv_source: str = IV_SOURCE_PROVIDED,
    r: float = DEFAULT_R,
    q: float = DEFAULT_Q,
    mult: float = CONTRACT_MULTIPLIER,
    pm: float = PCT_MOVE,
) -> dict:
    """Build a typed conditional price x future-time exposure field."""
    root = str(root or "").upper().strip()
    if not root:
        raise ValueError("root is required")
    observed_at = _require_aware_iso(observed_at)
    S0 = _finite_positive(spot)
    if S0 is None:
        raise ValueError("spot must be positive and finite")
    prices = _price_grid(price_grid)
    horizons = _horizons(horizons_minutes)
    if vol_map != VOL_MAP_STICKY_STRIKE:
        raise ValueError("v1 supports only vol_map='sticky_strike'")
    if iv_source not in {IV_SOURCE_PROVIDED, IV_SOURCE_MID_SOLVE}:
        raise ValueError(
            "iv_source must be 'provided_iv' or 'solve_from_mid'"
        )
    r_clean = _finite_number(r)
    q_clean = _finite_number(q)
    mult_clean = _finite_positive(mult)
    pm_clean = _finite_positive(pm)
    if r_clean is None or q_clean is None or mult_clean is None or pm_clean is None:
        raise ValueError("r/q must be finite and mult/pm must be positive finite values")
    r, q, mult, pm = r_clean, q_clean, mult_clean, pm_clean
    observed_dt = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if iv_observed_at is not None:
        iv_observed_at = _require_aware_iso(iv_observed_at)
        iv_dt = datetime.fromisoformat(iv_observed_at.replace("Z", "+00:00"))
        if iv_dt > observed_dt:
            raise ValueError("iv_observed_at cannot be after observed_at")
    elif iv_source == IV_SOURCE_MID_SOLVE:
        raise ValueError("iv_observed_at is required when iv_source='solve_from_mid'")

    oi_vintage = str(oi_vintage).strip() if oi_vintage is not None else None
    oi_vintage = oi_vintage or None
    if oi_vintage is not None:
        try:
            oi_date = date.fromisoformat(oi_vintage)
        except ValueError as exc:
            raise ValueError("oi_vintage must be an ISO YYYY-MM-DD date") from exc
        if oi_date >= observed_dt.astimezone(ET).date():
            raise ValueError("oi_vintage must be strictly before the observation ET date")
    if max_dte_days is not None:
        max_dte_days = _finite_positive(max_dte_days)
        if max_dte_days is None:
            raise ValueError("max_dte_days must be positive and finite")
    expiry_set = {str(x) for x in expiry_scope} if expiry_scope is not None else None
    normalized, counts = _normalize_contracts(
        contracts,
        expiry_scope=expiry_set,
        max_dte_days=max_dte_days,
        iv_source=iv_source,
    )

    if iv_source == IV_SOURCE_MID_SOLVE and normalized:
        K0 = np.asarray([c["strike"] for c in normalized], dtype=float)
        T0 = np.asarray([c["exp_years"] for c in normalized], dtype=float)
        mids0 = np.asarray([c["mid"] for c in normalized], dtype=float)
        calls0 = np.asarray([c["right"] == "C" for c in normalized], dtype=bool)
        solved = implied_vol_vec(mids0, S0, K0, T0, calls0, r=r, q=q)
        frozen: list[dict] = []
        for contract, solved_iv in zip(normalized, solved):
            if not np.isfinite(solved_iv) or solved_iv <= 0:
                counts["omitted_iv_unsolved"] += 1
                continue
            row = dict(contract)
            row.pop("mid", None)
            row["iv"] = float(solved_iv)
            frozen.append(row)
        normalized = frozen
        counts["iv_solved"] = len(normalized)
        counts["valid_snapshot"] = len(normalized)

    trade_at_first, trade_at_last = _source_clock_bounds(
        normalized, "trade_at", observed_dt=observed_dt
    )
    quote_at_first, quote_at_last = _source_clock_bounds(
        normalized, "quote_at", observed_dt=observed_dt
    )

    grids = {"gex": [], "vex": [], "cex": []}
    horizon_meta: list[dict] = []
    zero_crossings: dict[str, list[dict]] = {key: [] for key in grids}

    for horizon in horizons:
        dt_years = horizon / MINUTES_PER_YEAR
        live = [c for c in normalized if c["exp_years"] - dt_years > 0]
        if not live:
            none_row = [None for _ in prices]
            for key in grids:
                grids[key].append(list(none_row))
            horizon_meta.append({
                "horizon_minutes": horizon,
                "active_contracts": 0,
                "active_snapshot_fraction": 0.0 if normalized else None,
            })
            for metric in zero_crossings:
                zero_crossings[metric].append({
                    "horizon_minutes": horizon,
                    "prices": [],
                })
            continue

        K = np.asarray([c["strike"] for c in live], dtype=float)
        T = np.asarray([c["exp_years"] - dt_years for c in live], dtype=float)
        iv = np.asarray([c["iv"] for c in live], dtype=float)
        oi = np.asarray([c["oi"] for c in live], dtype=float)
        is_call = np.asarray([c["right"] == "C" for c in live], dtype=bool)
        sign = np.where(is_call, 1.0, -1.0)

        row_g: list[float | None] = []
        row_v: list[float | None] = []
        row_c: list[float | None] = []
        for sx in prices:
            _, gamma, vanna, charm = bs_greeks_vec(sx, K, T, iv, is_call, r=r, q=q)
            finite = np.isfinite(gamma) & np.isfinite(vanna) & np.isfinite(charm)
            if not finite.any():
                row_g.append(None)
                row_v.append(None)
                row_c.append(None)
                continue
            with np.errstate(over="ignore", invalid="ignore"):
                g = sign[finite] * gamma[finite] * oi[finite] * mult * sx * sx * pm
                v = sign[finite] * vanna[finite] * oi[finite] * mult * sx * pm
                c = sign[finite] * (charm[finite] / 365.0) * oi[finite] * mult * sx
            row_g.append(_sum_or_none(g))
            row_v.append(_sum_or_none(v))
            row_c.append(_sum_or_none(c))

        grids["gex"].append(row_g)
        grids["vex"].append(row_v)
        grids["cex"].append(row_c)
        horizon_meta.append({
            "horizon_minutes": horizon,
            "active_contracts": len(live),
            "active_snapshot_fraction": round(len(live) / len(normalized), 6) if normalized else None,
        })
        for metric, row in (
            ("gex", row_g),
            ("vex", row_v),
            ("cex", row_c),
        ):
            zero_crossings[metric].append({
                "horizon_minutes": horizon,
                "prices": _zero_crossings(prices, row),
            })

    return {
        "schema": SCHEMA,
        "product_kind": PRODUCT_KIND,
        "root": root,
        "observed_at": observed_at,
        "spot_at_observation": float(S0),
        "price_grid": prices,
        "horizons_minutes": horizons,
        "grids": grids,
        "zero_crossings": zero_crossings,
        "gamma_zero_crossings": [
            {
                "horizon_minutes": row["horizon_minutes"],
                "gamma_zeros": list(row["prices"]),
            }
            for row in zero_crossings["gex"]
        ],
        "horizon_meta": horizon_meta,
        "source_counts": counts,
        "source_clocks": {
            "market_observed_at": observed_at,
            "iv_observed_at": iv_observed_at,
            "oi_vintage": oi_vintage,
            "trade_at_first": trade_at_first,
            "trade_at_last": trade_at_last,
            "quote_at_first": quote_at_first,
            "quote_at_last": quote_at_last,
        },
        "expiry_scope": sorted(expiry_set) if expiry_set is not None else None,
        "max_dte_days": max_dte_days,
        "conventions": {
            "r": r,
            "q": q,
            "contract_multiplier": mult,
            "pct_move": pm,
        },
        "assumptions": {
            "inventory": "fixed_input_oi_snapshot",
            "vol_map": VOL_MAP_STICKY_STRIKE,
            "iv_source": iv_source,
            "time": "deterministic_roll_forward_from_input_exp_years",
            "dealer_sign": "assumed_long_call_short_put",
            "price_axis": "scenario_not_forecast",
            "observed_history": False,
        },
        "units": {
            "gex": "usd_per_1pct_spot_move",
            "vex": "usd_delta_per_1_vol_point",
            "cex": "usd_delta_per_calendar_day",
        },
        "warnings": [
            "modeled conditional field; not observed history",
            "scenario prices are not a predicted path",
            "open interest and frozen per-contract IV are fixed at the observation snapshot",
            "missing OI/IV source clocks remain null rather than inheriting market_observed_at",
            "dealer sign is assumption-based, not observed participant inventory",
        ],
    }
