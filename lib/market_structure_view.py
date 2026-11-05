"""Read-only presentation contract for Market Structure.

Keeps source observations, calendar gaps and model units intact. This module
does not calculate regimes, portfolio signals, fund flows or option ranges.
"""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from lib import nyse_calendar
from lib.illus import illus


def finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) else None


def number(value: Any, digits: int = 1, prefix: str = "", suffix: str = "", signed: bool = False) -> str:
    value = finite(value)
    if value is None:
        return "—"
    rounded = round(value, digits)
    sign = "−" if rounded < 0 else "+" if signed and rounded > 0 else ""
    return f"{sign}{prefix}{abs(value):,.{digits}f}{suffix}"


def direction(value: Any) -> str:
    value = finite(value)
    return "msp-up" if value is not None and value > 0 else "msp-down" if value is not None and value < 0 else ""


def clean(value: Any) -> Any:
    """JSON-safe without turning an unavailable measurement into zero."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def iso_day(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        day = date.fromisoformat(value[:10])
        return day.isoformat() if value[:10] == day.isoformat() else None
    except ValueError:
        return None


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def history_rows(history: Any, keys: tuple[str, ...]) -> list[dict]:
    """Retain at most 500 reported rows, insert only real NYSE session gaps.

The explicit null rows are important: chart lines must be segmented, not
connected across absent chain observations. Holidays are not missing readings.
"""
    by_day = {}
    for row in (history if isinstance(history, list) else [])[-2000:]:
        row = _obj(row)
        day = iso_day(row.get("date"))
        if day and nyse_calendar.is_session(date.fromisoformat(day)):
            by_day[day] = {"date": day, **{k: finite(row.get(k)) for k in keys}}
    days = sorted(by_day)[-500:]
    if not days:
        return []
    start, end = date.fromisoformat(days[0]), date.fromisoformat(days[-1])
    # Bound malformed input; do not expand an arbitrary multi-century interval.
    if (end - start).days > 3660:
        return [by_day[d] for d in days]
    return [by_day.get(d.isoformat(), {"date": d.isoformat(), **dict.fromkeys(keys)})
            for d in nyse_calendar.sessions_between(start, end)]


def _matching_day(block: dict, rows: list[dict], pairs: tuple[tuple[str, str], ...]) -> str | None:
    """Legacy artifacts may omit dates. Infer only from a matching endpoint."""
    if not rows:
        return None
    last = rows[-1]
    matches = [(finite(block.get(a)), finite(last.get(b))) for a, b in pairs]
    if matches and all(a is not None and b is not None and math.isclose(a, b, abs_tol=1e-5)
                       for a, b in matches):
        return last["date"]
    return None


def observation(day: Any, now: datetime) -> dict:
    day = iso_day(day)
    expected = nyse_calendar.expected_last_session(now)
    result = {"date": day, "state": "unknown", "behind": None,
              "expected": expected.isoformat(), "expires": None}
    if not day:
        return result
    observed = date.fromisoformat(day)
    if not nyse_calendar.is_session(observed) or observed > now.astimezone(nyse_calendar.ET).date():
        return result
    behind = nyse_calendar.sessions_behind(observed, now)
    result.update(state="stale" if behind else "snapshot", behind=behind)
    # Same calendar / 17:00 ET settlement convention as expected_last_session.
    # An already-open cached page can age without inventing today's data.
    following = nyse_calendar.sessions_between(observed + timedelta(days=1),
                                               observed + timedelta(days=14))
    if following:
        result["expires"] = datetime.combine(following[0], time(17), nyse_calendar.ET).isoformat()
    return result


def _week_view(block: dict, gamma: dict, now: datetime) -> dict:
    start, end = iso_day(block.get("week_start")), iso_day(block.get("week_end"))
    locked = iso_day(block.get("locked_at"))
    fields = ("band_2sigma_lo", "band_1sigma_lo", "locked_close", "band_1sigma_hi", "band_2sigma_hi")
    numbers = [finite(block.get(k)) for k in fields]
    valid = bool(start and end and locked and locked <= start <= end and
                 (date.fromisoformat(end) - date.fromisoformat(start)).days <= 7 and
                 all(v is not None and v > 0 for v in numbers))
    valid = valid and numbers == sorted(numbers) and numbers[0] < numbers[-1]
    today = now.astimezone(nyse_calendar.ET).date().isoformat()
    state = "unavailable" if not valid else "expired" if today > end else "upcoming" if today < start else "active"
    result = {"valid": valid, "state": state, "start": start, "end": end,
              "locked": locked, "positions": {}, "domain": []}
    if not valid:
        return result
    spot, flip = finite(gamma.get("spot")), finite(block.get("gamma_flip"))
    extras = [v for v in (spot, flip) if v is not None and v > 0]
    low, high = min([numbers[0], *extras]), max([numbers[-1], *extras])
    pad = (high - low) * 0.08
    low, high = low - pad, high + pad
    values = {**dict(zip(fields, numbers)), "spot": spot, "flip": flip}
    result["positions"] = {k: round((v - low) / (high - low) * 100, 4)
                           for k, v in values.items() if v is not None and v > 0}
    result["domain"] = [low, high]
    return result


def build_view(payload: dict | None, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    data = clean(_obj(payload))
    gamma = _obj(data.get("gamma"))
    systematic = _obj(data.get("systematic"))
    vc, cta = _obj(systematic.get("vc")), _obj(systematic.get("cta"))
    dispersion, vol, week = (_obj(data.get(k)) for k in ("dispersion", "vol", "week_map"))
    for block, fields in (
        (gamma, ("net_gex_bn", "net_gex_pctile", "spot", "gamma_flip", "dist_to_flip_pct", "days_in_regime", "days_in_regime_observed")),
        (vc, ("alloc_bn", "alloc_frac", "flow_1d_bn", "flow_5d_bn", "flow_window_n", "aum_bn", "target_vol_pct")),
        (cta, ("score", "z", "flow_1d", "flow_5d", "flow_window_n")),
        (systematic, ("flow_window_n",)),
        (dispersion, ("cor1m", "cor1m_1y_delta", "cor1m_pctile_2y", "cor1m_pctile_lo", "cor1m_pctile_hi")),
        (vol, ("rv21", "rv63", "vix_curve_slope")),
        (week, ("locked_close", "band_1sigma_lo", "band_1sigma_hi", "band_2sigma_lo", "band_2sigma_hi", "gamma_flip", "implied_weekly_pct")),
    ):
        for key in fields:
            block[key] = finite(block.get(key))
    coverage = _obj(gamma.get("coverage"))
    rows = {
        "gamma": history_rows(gamma.get("history"), ("net_gex_bn", "spot", "flip")),
        "systematic": history_rows(systematic.get("history"), ("vc_alloc_bn", "cta_score", "spx_close")),
        "dispersion": history_rows(dispersion.get("history"), ("cor1m",)),
    }
    gamma_day = (iso_day(coverage.get("last_obs")) or iso_day(gamma.get("asof")) or
                 _matching_day(gamma, rows["gamma"], (("net_gex_bn", "net_gex_bn"),)))
    sys_day = iso_day(systematic.get("asof")) or _matching_day(vc, rows["systematic"], (("alloc_bn", "vc_alloc_bn"),))
    cor_day = iso_day(dispersion.get("asof")) or _matching_day(dispersion, rows["dispersion"], (("cor1m", "cor1m"),))
    dates = {k: observation(day, now) for k, day in {
        "gamma": gamma_day, "systematic": sys_day, "dispersion": cor_day,
        "rv": vol.get("rv_asof"), "curve": vol.get("curve_asof"),
    }.items()}
    missing = sorted({d for key in ("missing_recent", "missing_in_regime")
                      for d in (coverage.get(key) or []) if iso_day(d)})
    chart_specs = {
        "gamma": {"primary": "net_gex_bn", "default": 126},
        "systematic": {"primary": "vc_alloc_bn", "default": 252},
        "dispersion": {"primary": "cor1m", "default": 252},
    }
    charts = {}
    for key, spec in chart_specs.items():
        selected = rows[key][-spec["default"]:]
        count = sum(row.get(spec["primary"]) is not None for row in selected)
        charts[key] = {**spec, "rows": rows[key], "selected": selected, "count": count,
                       "gaps": len(selected) - count,
                       "first": selected[0]["date"] if selected else None,
                       "last": selected[-1]["date"] if selected else None}
    curve = vol.get("vix_curve") if isinstance(vol.get("vix_curve"), list) else []
    curve = [_obj(row) for row in curve[:6]]
    curve_svg = ""
    if len(curve) >= 4 and all(finite(row.get("settle")) is not None for row in curve):
        curve_svg = illus({"dates": [str(row.get("tenor", "")) for row in curve],
                           "vals": [row["settle"] for row in curve]}, kind="line", height=100,
                          accent="var(--ink-info)", unit_en="VIX pts", unit_zh="VIX 点",
                          aria_en="VIX futures by maturity, equally spaced contracts",
                          aria_zh="按合约月份等距排列的 VIX 期货曲线")
    change_block = _obj(data.get("state_changes"))
    changes = [c for c in (change_block.get("items") or []) if isinstance(c, dict)][:6]
    return {
        "data": data, "gamma": gamma, "systematic": systematic, "vc": vc, "cta": cta,
        "dispersion": dispersion, "vol": vol, "week_map": week, "dates": dates,
        "week": _week_view(week, gamma, now), "charts": charts, "missing": missing,
        "curve": curve, "curve_svg": curve_svg, "changes": changes,
        "comparison_date": iso_day(change_block.get("vs_asof")),
        "comparison_gap": iso_day(change_block.get("vs_asof")) in missing,
        "asof": iso_day(data.get("asof")), "built": iso_day(data.get("built_at")),
    }
