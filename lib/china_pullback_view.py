"""China's display-only pullback projection and shared presentation adapter.

Reads raw daily price stores, never the forward-filled feature frame. The JSON
travels in the existing China Market State snapshot; there is no second feed,
ledger, probability model or capital-policy decision here.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from math import isfinite
from typing import Callable

from lib import cn_calendar
from lib.pullback_observation import SCHEMA, observe

PRIMARY = "000001.SS"
LABELS = {
    "monitoring": ("Pullback monitor", "回撤观察"),
    "developing": ("Pullback developing", "回撤初现"),
    "underway": ("Pullback underway", "回撤进行中"),
    "stabilizing": ("Stabilizing", "止跌观察"),
    "recovering": ("Recovering", "修复中"),
    "repaired": ("Trend repaired", "趋势修复"),
    "unavailable": ("Price status unavailable", "价格状态暂不可用"),
}
MEANINGS = {
    "monitoring": ("No confirmed decline in the settled benchmark.", "收盘基准尚未确认回撤。"),
    "developing": ("A decline is taking shape; confirmation is pending.", "下跌初现，仍待收盘确认。"),
    "underway": ("The decline is observed, not just forecast.", "回撤已经发生，不只是风险预测。"),
    "stabilizing": ("Selling has paused; the prior high remains unrecovered.", "下跌暂缓，尚未收复前高。"),
    "recovering": ("Price repair is building; this is not an all-clear.", "价格正在修复，并不代表风险解除。"),
    "repaired": ("The down-leg has resolved; risk forecasts remain separate.", "本轮下跌已修复，前瞻风险仍需单独观察。"),
    "unavailable": ("A current settled-price assessment is not available.", "当前收盘价格评估暂不可用。"),
}
QUALITY_COPY = {
    "delayed": ("Settled prices delayed", "收盘价格延迟"),
    "calendar_disagreement": ("Session dates need review", "交易日期待核实"),
    "insufficient_history": ("More price history needed", "价格历史不足"),
    "no_history": ("Price history unavailable", "价格历史暂不可用"),
    "source_unavailable": ("Price source unavailable", "价格来源暂不可用"),
}


def _rows(frame) -> list[tuple[str, float]]:
    if frame is None or "close" not in frame.columns:
        return []
    # Store indices are date-like objects. Do not normalize an intraday row into
    # a settled close, silently drop a bad close, or synthesize a missing day.
    rows = []
    for stamp, value in frame["close"].items():
        if hasattr(stamp, "time") and stamp.time() != time(0):
            label = stamp.isoformat()
        else:
            label = stamp.date().isoformat() if hasattr(stamp, "date") else str(stamp)
        rows.append((label, value))
    return rows


def snapshot(*, now: datetime | None = None, read: Callable | None = None) -> dict:
    from engine.market_state_cn import CN_PROFILE
    if read is None:
        from lib import store
        read = store.read
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("China pullback snapshot requires an aware observation clock")
    expected = cn_calendar.expected_last_session(now)
    observations = {}
    indices = []
    for ticker, en, zh in CN_PROFILE.indices:
        try:
            item = observe(_rows(read("china", ticker)), expected_session=expected,
                           is_session=cn_calendar.is_session)
        except (OSError, ValueError, TypeError, KeyError, ArithmeticError):
            item = {"schema": SCHEMA, "available": False, "quality": "source_unavailable",
                    "asof": None, "expected_session": expected.isoformat(),
                    "phase": "unavailable", "active": None, "drawdown_pct": None,
                    "loss_recovered_pct": None}
        observations[ticker] = item
        proxy = ticker == "510300.SS"
        if proxy:
            en, zh = "CSI 300 ETF proxy", "沪深300 ETF代理"
        indices.append({
            "ticker": ticker, "label_en": en, "label_zh": zh, "proxy": proxy,
            "available": item["available"], "quality": item["quality"], "asof": item["asof"],
            "drawdown_pct": item.get("recent_63_drawdown_pct"),
            "declining": (item["below_20_close_average"] and item["recent_63_drawdown_pct"] <= -2.0)
                         if item["available"] else None,
            "source_digest": item.get("source_digest"),
        })
    primary = observations.get(PRIMARY)
    if primary is None:
        raise ValueError("The commissioned Shanghai benchmark is absent from CN_PROFILE")
    next_day = expected + timedelta(days=1)
    for _ in range(32):
        if cn_calendar.is_session(next_day):
            break
        next_day += timedelta(days=1)
    else:
        raise ValueError("Next settled China session could not be established")
    # Reuse the owning calendar's settlement buffer, not a copied hours table.
    expires = datetime.combine(next_day, cn_calendar._CLOSE_PLUS_SETTLE,
                               tzinfo=cn_calendar.CST).astimezone(timezone.utc)
    available = [item for item in indices if item["available"]]
    return {**primary, "market": "cn", "benchmark": PRIMARY,
            "benchmark_en": "Shanghai Composite", "benchmark_zh": "上证综指",
            "clock": "settled_close", "produced_at": now.astimezone(timezone.utc).isoformat(),
            "valid_until": expires.isoformat(), "indices": indices,
            "index_confirmation": {"declining": sum(item["declining"] for item in available),
                                   "available": len(available), "total": len(indices),
                                   "basis": "recent_63_close_high_and_20_close_average"}}


def _finite(value, lower: float, upper: float) -> float | None:
    if value is None or isinstance(value, (bool, str)):
        return None
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return number if isfinite(number) and lower <= number <= upper else None


def present(observation: dict, radar: dict | None = None) -> dict:
    """One adapter for the hero, rack and existing dialog; never persisted HTML."""
    from lib import illus
    radar = radar or {}
    phase = observation.get("phase", "unavailable")
    if phase not in LABELS:
        phase = "unavailable"
    if not observation.get("available"):
        phase = "unavailable"
    labels = LABELS[phase]
    if phase == "monitoring" and radar.get("state") in ("caution", "elevated", "risk-off"):
        labels = ("Pullback risk", "回撤风险")
    if phase == "unavailable":
        labels = QUALITY_COPY.get(observation.get("quality"), labels)
    if observation.get("resolution") == "prior_high_reclaimed":
        labels = ("Prior high reclaimed", "收复前高")
    dd = _finite(observation.get("drawdown_pct"), -100, 0) if phase != "unavailable" else None
    value = ("0.0%" if abs(dd) < 0.05 else f"{dd:.1f}%") if dd is not None else "—"
    score = _finite(radar.get("top_score"), 0, 100)
    probability = _finite(radar.get("dd21"), 0, 1)
    chart = detail_chart = ""
    if phase != "unavailable" and observation.get("price_path"):
        chart = illus.illus(observation["price_path"], kind="drawdown", height=104,
                            accent="var(--down)", value_fmt="{:.1f}%",
                            aria_en="Observed Shanghai closing drawdown from the labelled reference high")
        # The supported reference changes the SVG identity and adds a useful
        # peak waterline in detail. Reusing identical fragments would duplicate
        # gradient IDs when both the rack and dialog are in the same document.
        detail_chart = illus.illus(observation["price_path"], kind="drawdown", height=188,
                                   accent="var(--down)", reference=0, value_fmt="{:.1f}%",
                                   aria_en="Observed Shanghai closing drawdown, zero marks the reference high")
    return {
        "observation": observation, "phase": phase,
        "headline_en": labels[0], "headline_zh": labels[1],
        "meaning_en": MEANINGS[phase][0], "meaning_zh": MEANINGS[phase][1],
        "value": value, "chart_html": chart, "detail_chart_html": detail_chart,
        "score": score, "probability": probability,
        "forecast_state": radar.get("state"),
        "show_card": phase != "monitoring" or radar.get("state") in ("caution", "elevated", "risk-off"),
        "tone": "down" if phase == "underway" else (
            "info" if phase in ("stabilizing", "recovering", "repaired") else "warn"),
    }
