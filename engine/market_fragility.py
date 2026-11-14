"""Non-directional gamma-structure observations; not a risk/position-sizing engine.

The existing market_gamma producer supplies the same-source SPX frame. Dealer
inventory is NOT observed: upstream gamma_regime is assumption-signed. This module
adds no price model, data store, fit, ranking weight, trading rule or scheduler.
Historical counts describe observations, not independent predictive trials.
"""
from __future__ import annotations

import math
from collections import Counter
from datetime import date, datetime, timezone
from numbers import Number
from typing import Any

import pandas as pd

from lib import nyse_calendar

SCHEMA = "market_fragility/v1"
SOURCE = "cboe/gex_SPX"
_REGIMES = {"short", "long"}


def _number(value: Any, *, positive: bool = False) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Number):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(result) or (positive and result <= 0):
        return None
    return result


def _session(value: Any) -> date | None:
    # An index is a session LABEL, not an observation timestamp. Do not timezone-
    # shift a midnight UTC label into the preceding New York date.
    if isinstance(value, Number) or value is None:
        return None
    try:
        stamp = pd.Timestamp(value)
        return None if pd.isna(stamp) else stamp.date()
    except (TypeError, ValueError, OverflowError):
        return None


def _clock(value: Any) -> datetime | None:
    # A historical availability clock needs a timezone. Never invent UTC for it.
    if isinstance(value, Number) or value is None:
        return None
    try:
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tzinfo is None:
            return None
        return stamp.to_pydatetime().astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _sign(value: Any) -> str | None:
    return value if isinstance(value, str) and value in _REGIMES else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def _absent(value: Any) -> bool:
    return value is None or (pd.api.types.is_scalar(value) and bool(pd.isna(value)))


def _row_issues(row: dict[str, Any], day: date, now: datetime) -> list[str]:
    issues: list[str] = []
    tier = row.get("tier")
    if not _absent(tier) and (not isinstance(tier, str) or tier != "full"):
        issues.append("source_thin_chain" if isinstance(tier, str) and tier == "thin_chain" else "source_tier_unusable")
    clocks = {key: _clock(row.get(key)) for key in ("observed_at", "available_at")}
    for key, clock in clocks.items():
        if not _absent(row.get(key)) and clock is None:
            issues.append(f"invalid_{key}")
        elif clock is not None and clock > now:
            issues.append(f"future_{key}")
        elif clock is not None and clock.astimezone(nyse_calendar.ET).date() < day:
            issues.append(f"{key}_precedes_source_session")
    observed, available = clocks["observed_at"], clocks["available_at"]
    if observed is not None and available is not None and available < observed:
        issues.append("availability_precedes_observation")
    return issues


def observe(
    frame: pd.DataFrame | None,
    *,
    now: datetime | None = None,
    window_sessions: int = 20,
) -> dict[str, Any]:
    """Describe canonical daily SPX gamma rows without inferring price direction.

    Current source age uses the incumbent NYSE completed-session calendar. A source
    row for today's session may be a partial observation; it is not counted in the
    completed-session history until the calendar's close/settlement boundary.
    Duplicate labels are ambiguous (no arbitrary keep-last correction policy).
    Missing/invalid rows break runs and adjacent-pair transitions. A malformed or
    future latest source cannot be hidden by silently selecting an older good row.

    Source date and known-at time remain separate. Snapshot-only history is never
    promoted to a PIT-qualified dataset merely because a timestamp column exists.
    All returned numeric values are finite or None (strict JSON-safe).
    """
    if isinstance(window_sessions, bool) or not isinstance(window_sessions, int):
        raise ValueError("window_sessions must be an integer in [1, 252]")
    if not 1 <= window_sessions <= 252:
        raise ValueError("window_sessions must be an integer in [1, 252]")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)  # repository convention for 'now'
    now = now.astimezone(timezone.utc)
    today = now.astimezone(nyse_calendar.ET).date()
    completed = nyse_calendar.expected_last_session(now)
    first = nyse_calendar.session_n_back(completed, window_sessions - 1)
    if first is None:
        raise ValueError("calendar cannot resolve requested observation window")
    sessions = nyse_calendar.sessions_between(first, completed)
    reasons: list[str] = []
    bad = Counter()
    rows: dict[date, dict[str, Any]] = {}
    counts: Counter = Counter()
    source_day: date | None = None
    current: dict[str, Any] = {}
    invalid_schema = frame is not None and (
        not isinstance(frame, pd.DataFrame)
        or not frame.columns.is_unique
        or "gamma_regime" not in frame.columns
    )
    if invalid_schema:
        reasons.append("invalid_source_schema")
    elif frame is None or frame.empty:
        reasons.append("source_absent")
    else:
        for label, series in frame.iterrows():
            day = _session(label)
            if day is None:
                bad["invalid_session_label"] += 1
                continue
            counts[day] += 1
            # Values are retained only for one row per label; duplicates below
            # are invalidated regardless of order or apparent agreement.
            rows[day] = series.to_dict()
            if day > today:
                bad["future_session"] += 1
            elif not nyse_calendar.is_session(day):
                bad["non_session"] += 1
        if rows:
            source_day = max(rows)
            current = rows[source_day] if counts[source_day] == 1 else {}
        bad["duplicate_session"] = sum(n for n in counts.values() if n > 1)
    if bad["invalid_session_label"]:
        reasons.append("invalid_session_labels")
    if source_day is None and not reasons:
        reasons.append("source_absent")

    observed_at = _clock(current.get("observed_at"))
    available_at = _clock(current.get("available_at"))
    reported_sign = _sign(current.get("gamma_regime"))
    age: int | None = None
    if source_day is not None:
        if source_day > today:
            reasons.append("future_source_session")
        elif not nyse_calendar.is_session(source_day):
            reasons.append("source_is_not_a_trading_session")
        elif counts[source_day] != 1:
            reasons.append("ambiguous_latest_session")
        else:
            age = nyse_calendar.sessions_behind(source_day, now)
            if age > 0:
                reasons.append("source_stale")
        if reported_sign is None:
            reasons.append("gamma_sign_unavailable")
        reasons.extend(_row_issues(current, source_day, now))
    usable = not reasons and reported_sign in _REGIMES
    state = {"short": "amplifying", "long": "damping"}.get(reported_sign, "unknown") if usable else "unknown"

    # Fixed completed-session grid, not the last N non-null rows. Missingness is
    # therefore visible in the denominator and never joins two separate runs.
    signs: list[str | None] = []
    missing: list[str] = []
    invalid: list[str] = []
    for day in sessions:
        row = rows.get(day)
        sign = _sign(row.get("gamma_regime")) if row is not None else None
        if row is None:
            missing.append(day.isoformat())
        elif counts[day] != 1 or sign is None:
            invalid.append(day.isoformat())
            sign = None
        elif _row_issues(row, day, now):
            invalid.append(day.isoformat())
            sign = None
        signs.append(sign)
    n_short, n_long = signs.count("short"), signs.count("long")
    n_known = n_short + n_long
    pairs = [(a, b) for a, b in zip(signs, signs[1:]) if a is not None and b is not None]
    flips = sum(a != b for a, b in pairs)
    longest_long = run_long = runs = 0
    previous = None
    for sign in signs:
        if sign is not None and sign != previous:
            runs += 1
        run_long = run_long + 1 if sign == "long" else 0
        longest_long = max(longest_long, run_long)
        previous = sign
    terminal_sign = signs[-1] if signs else None
    terminal_run = 0
    if terminal_sign is not None:
        for sign in reversed(signs):
            if sign != terminal_sign:
                break
            terminal_run += 1

    flip = _number(current.get("gamma_flip"), positive=True)
    spot = _number(current.get("spot"), positive=True)
    net_gex = _number(current.get("net_gex_bn"))
    distance = _number(current.get("dist_to_flip_pct")) if flip is not None else None
    limitations = [
        "dealer_inventory_is_assumed_not_observed",
        "gamma_sign_does_not_predict_price_direction",
        "snapshot_history_is_not_point_in_time_validated",
        "gamma_is_not_a_complete_liquidity_or_volatility_model",
        "no_intraday_inventory_or_cross_product_netting",
    ]
    if flip is None:
        limitations.append("gamma_flip_unavailable_sign_is_independent")
    if available_at is None:
        limitations.append("source_availability_clock_absent")
    if n_known < window_sessions:
        limitations.append("incomplete_history_window")
    if not usable:
        en = "Gamma-structure state is unknown: " + ", ".join(reasons) + "."
        zh = "Gamma\u7ed3\u6784\u72b6\u6001\u672a\u77e5\uff1a" + ", ".join(reasons) + "\u3002"
    elif state == "amplifying":
        en = "The assumed dealer-gamma sign can amplify both rises and falls; this is not a bearish forecast."
        zh = "\u5047\u8bbe\u7684\u505a\u5e02\u5546Gamma\u7b26\u53f7\u53ef\u80fd\u653e\u5927\u6da8\u8dcc\uff1b\u8fd9\u4e0d\u662f\u770b\u7a7a\u9884\u6d4b\u3002"
    else:
        en = "The assumed dealer-gamma sign can damp moves; this does not guarantee a calm market."
        zh = "\u5047\u8bbe\u7684\u505a\u5e02\u5546Gamma\u7b26\u53f7\u53ef\u80fd\u6291\u5236\u6ce2\u52a8\uff1b\u4e0d\u4ee3\u8868\u5e02\u573a\u5fc5\u7136\u5e73\u9759\u3002"
    return {
        "schema": SCHEMA,
        "scope": "gamma_structure_observation",
        "state": state,
        "data_status": ("ready" if n_known == window_sessions else "partial") if usable else (
            "stale" if reasons == ["source_stale"] else "unavailable"
        ),
        "source": {
            "id": SOURCE, "instrument": "SPX", "regime_field": "gamma_regime",
            "methodology": "engine.gex_engine", "position_basis": "assumption",
            "expiry_scope": "upstream_chain_filter", "actual_dealer_inventory_observed": False,
        },
        "clocks": {
            "computed_at": _iso(now), "source_session": source_day.isoformat() if source_day else None,
            "source_observed_at": _iso(observed_at), "source_available_at": _iso(available_at),
            "expected_completed_session": completed.isoformat(), "age_sessions": age,
            "source_session_complete": source_day <= completed if source_day else None,
        },
        "current": {
            "usable": usable, "reported_gamma_regime": reported_sign,
            "source_tier": current.get("tier") if isinstance(current.get("tier"), str) else None,
            "gamma_flip": flip, "spot": spot, "dist_to_flip_pct": distance,
            "reported_net_gex_bn": net_gex, "net_gex_unit": "USD_bn_per_1pct_underlying_move",
            "regime_basis": "engine_direct_sign" if reported_sign else "unavailable",
            "hedge_response": ("with_price" if state == "amplifying" else "against_price") if usable else None,
            "directional_forecast": None,
        },
        "history": {
            "source": SOURCE, "window_sessions": window_sessions,
            "window_start": first.isoformat(), "window_end": completed.isoformat(),
            "observed_sessions": n_known, "short_sessions": n_short, "long_sessions": n_long,
            "unknown_sessions": window_sessions - n_known,
            "short_share_observed": n_short / n_known if n_known else None,
            "coverage_fraction": n_known / window_sessions,
            "adjacent_pairs_observed": len(pairs), "sign_changes": flips if pairs else None,
            "terminal_regime": terminal_sign, "terminal_run_sessions": terminal_run if terminal_sign else None,
            "terminal_run_left_censored": terminal_run == window_sessions if terminal_sign else None,
            "max_long_run_sessions": longest_long if n_known else None,
            "observed_regime_runs": runs if n_known else None,
            "missing_sessions": missing, "invalid_sessions": sorted(set(invalid)),
            "counts_are_independent_trials": False,
        },
        "quality": {
            "reasons": reasons, "excluded_row_counts": {k: int(v) for k, v in sorted(bad.items()) if v},
            "freshness_sla_sessions": 0, "point_in_time_qualified": False,
            "predictive_validation": "not_established", "limitations": limitations,
        },
        "authority": {
            "display_only": True, "directional_signal": False, "ranking": False,
            "position_sizing": False, "risk_override": False, "trade_execution": False,
        },
        "summary": {"en": en, "zh": zh},
    }


def published_context(latest: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Project already-published sibling observations, never fuse or rescore them.

    VIX/VVIX retain the volatility owner's as-of. A conditions/liquidity frame
    date is NOT an independent raw-input clock, and macro balance-sheet liquidity
    is NOT executable market depth. No reading here changes the gamma state.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)
    today = now.astimezone(nyse_calendar.ET).date()
    latest = latest if isinstance(latest, dict) else {}

    def mapping(value):
        return value if isinstance(value, dict) else {}

    def leaf(value, source, asof, unit, *, raw_clock_verified=False, degraded=False):
        day = _session(asof)
        eligible_day = day is not None and day <= today and nyse_calendar.is_session(day)
        age = nyse_calendar.sessions_behind(day, now) if eligible_day else None
        status = ("unavailable" if value is None else "invalid_source_session" if not eligible_day
                  else "stale" if age else "degraded" if degraded else "reported")
        return {
            "value": value, "unit": unit, "source": source,
            "source_session": day.isoformat() if day else None,
            "age_sessions": age, "status": status,
            "raw_input_clocks_verified": raw_clock_verified,
            "current_publication": status == "reported",
            "trade_authority": False,
        }

    vol = mapping(latest.get("vol_regime"))
    risk = mapping(mapping(latest.get("conditions")).get("risk_appetite"))
    liquidity = mapping(latest.get("liquidity_quality"))
    label = liquidity.get("label")
    if not isinstance(label, str) or label not in {"benign-expansion", "stress-expansion", "neutral", "neutral-hollow", "contracting"}:
        label = None
    return {
        "vix": leaf(_number(vol.get("vix"), positive=True), "engine.vol_regime/vix",
                    vol.get("asof"), "annualized_volatility_percent", degraded=vol.get("available") is not True),
        "vvix": leaf(_number(vol.get("vvix"), positive=True), "engine.vol_regime/vvix",
                     vol.get("asof"), "volatility_index_points", degraded=vol.get("available") is not True),
        "vix_term_ratio": leaf(_number(vol.get("ts_slope"), positive=True), "engine.vol_regime/ts_slope",
                               vol.get("asof"), "VIX_over_VIX3M", degraded=vol.get("available") is not True),
        "realized_volatility": {
            **leaf(_number(risk.get("realized_vol")), "engine.conditions/risk_appetite/realized_vol",
                   latest.get("date"), "annualized_volatility_percent"),
            "clock_basis": "conditions_frame_date_not_raw_price_vintage",
            "window_owner": "engine.conditions configured vrp.realized_window_d",
        },
        "macro_liquidity": {
            **leaf(label, "engine.regime/liquidity_quality", liquidity.get("asof"), "categorical",
                   degraded=liquidity.get("degraded") is not False),
            "clock_basis": "liquidity_frame_date_not_each_balance_sheet_release",
            "is_market_depth": False,
        },
        "market_depth": {"status": "unavailable", "value": None, "reason": "no_order_book_depth_contract"},
        "gamma_spot_sensitivity": {
            "status": "unavailable", "value": None,
            "reason": "no_fixed_inventory_spot_scenario_surface_in_daily_summary",
        },
        "independence": "shared_inputs_not_independent_confirmation_votes",
        "composite_score": None,
        "policy": "descriptive_only_no_change_to_existing_gates_or_sizing",
    }
