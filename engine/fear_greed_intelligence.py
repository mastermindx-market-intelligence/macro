"""Transparent Fear/Greed extension; published ONLY by the existing fear_greed owner.

Six equally weighted families, seven explicit measures. Breadth's two measures
share ONE family vote. VIX acceleration, VVIX and curve changes are diagnostics,
not extra sentiment votes. No legacy dial, regime score, alert or sizing change.

Source stores contain observation dates, not complete publication vintages.
History is explicitly a causal reconstruction, never a prospective backtest.
"""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from engine.vol_velocity import causal_midrank, compute_vix_dynamics, session_series
from lib import nyse_calendar, store

VERSION = "mastermind.fear_greed_intelligence.v1"
# key, family, English, Chinese, orientation, units, formula, source, proxy
COMPONENTS = (
    ("momentum", "momentum", "Market momentum", "市场动量", 1, "%",
     "100 * (SPY / SMA125(SPY) - 1)", "yahoo/SPY", True),
    ("strength", "participation", "New-high participation", "新高参与度", 1, "ratio",
     "new highs / (new highs + new lows)", "breadth/breadth:nh,nl", True),
    ("breadth", "participation", "Advancing-stock breadth", "上涨家数广度", 1, "oscillator",
     "EMA19(RANA) - EMA39(RANA); RANA=1000*(adv-dec)/(adv+dec)", "breadth/breadth:adv,dec", True),
    ("credit", "credit", "Credit risk appetite", "信用风险偏好", -1, "percent",
     "ICE BofA US HY option-adjusted spread; inverted rank", "fred/BAMLH0A0HYM2:hy_oas", True),
    ("haven", "haven", "Stocks versus Treasuries", "股票对比国债", 1, "percentage points",
     "100 * (SPY / SPY[-20] - TLT / TLT[-20])", "yahoo/SPY,yahoo/TLT", True),
    ("options", "options", "ETF-chain put/call proxy", "ETF 期权链看跌看涨代理", -1, "ratio",
     "SMA5(SPY+QQQ+IWM delayed-chain put volume / call volume); inverted rank", "cboe/putcall:equity_pc_ratio (ETF-chain proxy, not official equity ratio)", True),
    ("volatility", "volatility", "Volatility premium", "波动率溢价", -1, "%",
     "100 * (VIX / SMA50(VIX) - 1); inverted rank", "yahoo/_VIX", True),
)
FAMILIES = {
    "momentum": ("Momentum", "动量"), "participation": ("Participation", "参与度"),
    "credit": ("Credit", "信用"), "haven": ("Safe havens", "避险"),
    "options": ("Options", "期权"), "volatility": ("Volatility", "波动率"),
}


def _number(value, digits=3):
    try:
        return round(float(value), digits) if np.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return None


def _change(s: pd.Series, n=5) -> pd.Series:
    """Difference only across complete windows, not across missing sessions."""
    return s.diff(n).where(s.rolling(n + 1, min_periods=n + 1).count().eq(n + 1))


def _features(inputs: dict[str, pd.Series], as_of) -> tuple[dict, dict]:
    clean = {k: session_series(v, as_of, positive=k in {"spy", "tlt", "vix", "vix3m", "vix9d", "vvix"})
             for k, v in inputs.items()}
    empty = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    get = lambda k: clean.get(k, empty)
    spy, tlt, vix = get("spy"), get("tlt"), get("vix")
    nh, nl, adv, dec = get("nh"), get("nl"), get("adv"), get("dec")
    # Missing partners and zero denominators remain unknown, NEVER zero-filled.
    nh, nl = nh.where(nh >= 0), nl.where(nl >= 0)
    adv, dec = adv.where(adv >= 0), dec.where(dec >= 0)
    rana = 1000 * (adv - dec) / (adv + dec).replace(0, np.nan)
    groups = rana.isna().cumsum()
    osc = rana.groupby(groups).transform(
        lambda x: x.ewm(span=19, min_periods=39, adjust=False).mean()
        - x.ewm(span=39, min_periods=39, adjust=False).mean())
    spyret = spy / spy.shift(20)
    tltret = tlt / tlt.shift(20)
    complete = spy.rolling(21).count().eq(21) & tlt.rolling(21).count().eq(21)
    raw = {
        "momentum": 100 * (spy / spy.rolling(125, min_periods=125).mean() - 1),
        "strength": nh / (nh + nl).replace(0, np.nan), "breadth": osc,
        "credit": get("credit").where(get("credit") >= 0),
        "haven": (100 * (spyret - tltret)).where(complete),
        "options": get("putcall").where(get("putcall") > 0).rolling(5, min_periods=5).mean(),
        "volatility": 100 * (vix / vix.rolling(50, min_periods=50).mean() - 1),
    }
    return raw, clean


def _bands(score):
    if score is None:
        return "Insufficient fresh data", "新鲜数据不足"
    for threshold, en, zh in ((20, "Extreme fear", "极度恐惧"), (40, "Fear", "恐惧"),
                              (60, "Balanced", "均衡"), (80, "Greed", "贪婪"), (101, "Extreme greed", "极度贪婪")):
        if score < threshold:
            return en, zh


def _pivot_context(raw: dict, clean: dict, dynamics: dict) -> dict:
    """Observable turn evidence, never a calibrated bottom/top probability."""
    def last_change(s):
        value = _change(s).iloc[-1] if len(s) else None
        return _number(value)

    empty = pd.Series(dtype=float)
    changes = {"price": last_change(clean.get("spy", empty)),
               "breadth": last_change(raw["breadth"]),
               "credit": last_change(raw["credit"]),
               "curve": dynamics.get("term_change_5d")}
    return classify_pivot_context(dynamics, changes)


def classify_pivot_context(dynamics: dict, changes: dict) -> dict:
    """Shared snapshot/replay classification; observation rules, not fitted forecasts."""
    checks = []
    for key, en, zh, lower in (("price", "Stocks", "股价", False), ("breadth", "Participation", "参与度", False),
                                ("credit", "Credit spreads", "信用利差", True), ("curve", "Volatility curve", "波动率曲线", True)):
        v = changes[key]
        improving = (v < 0 if lower else v > 0) if v is not None else None
        worsening = (v > 0 if lower else v < 0) if v is not None else None
        checks.append({"key": key, "name_en": en, "name_zh": zh, "change_5d": v,
                       "improving": improving, "worsening": worsening})
    base = checks[:3]  # curve and VVIX are NOT independent equity/credit families.
    improves = sum(x["improving"] is True for x in base)
    worsens = sum(x["worsening"] is True for x in base)
    available = sum(x["improving"] is not None for x in base)
    up, down = dynamics["up_sessions"], dynamics["down_sessions"]
    phase = dynamics["phase"]
    if not dynamics["mature"]:
        state, en, zh = "unavailable", "More fresh history needed", "需要更多新鲜历史数据"
    elif up >= 2 and worsens == 3:
        state, en, zh = "stress_broadening", "Stress is spreading", "压力正在扩散"
    elif down >= 2 and improves == 3:
        state, en, zh = "relief_broadening", "Relief is broadening", "风险缓解正在扩散"
    elif (phase == "stress_accelerating" and (dynamics.get("velocity_percentile") or 0) >= 90
          and (dynamics.get("acceleration_percentile") or 0) >= 90):
        state, en, zh = "shock_watch", "Sharp volatility repricing", "波动率显著重定价"
    elif phase == "stress_decelerating":
        state, en, zh = "exhaustion_watch", "Pressure may be tiring", "压力可能正在衰减"
    elif down >= 2:
        state, en, zh = "relief_watch", "Relief needs confirmation", "风险缓解仍需确认"
    elif up >= 2:
        state, en, zh = "stress_watch", "Watch rising pressure", "关注上升的压力"
    elif phase == "relief_decelerating":
        state, en, zh = "relief_fading", "Relief is slowing", "风险缓解正在放缓"
    else:
        state, en, zh = "mixed", "No broad turn evidence", "暂无广泛拐点证据"
    return {"state": state, "label_en": en, "label_zh": zh, "checks": checks,
            "independent_available": available, "improving": improves, "worsening": worsens,
            "required_for_broadening": 3, "persistence_sessions": max(up, down),
            "forecast_validated": False, "probability": None,
            "stance_en": "Watch; do not treat this as a buy or sell signal.",
            "stance_zh": "保持观察；勿将此视为买入或卖出信号。"}


def build_intelligence(inputs: dict[str, pd.Series], *, as_of=None) -> dict:
    """Pure deterministic snapshot from existing caches; no I/O, fitting or authority."""
    end = pd.Timestamp(as_of or nyse_calendar.expected_last_session()).tz_localize(None).normalize()
    end = pd.Timestamp(nyse_calendar.last_session_on_or_before(end.date()))
    raw, clean = _features(inputs, end)
    components, ranked = [], {}
    for key, family, en, zh, direction, unit, formula, source, proxy in COMPONENTS:
        s = raw[key].replace([np.inf, -np.inf], np.nan)
        rank = causal_midrank(s)
        if direction < 0:
            rank = 100 - rank
        ranked[key] = rank
        valid = s.dropna()
        last = valid.index[-1] if len(valid) else None
        current = last is not None and last == end
        value = _number(valid.iloc[-1]) if len(valid) else None
        pct = _number(rank.iloc[-1], 1) if len(rank) and current else None
        status = "missing" if last is None else ("stale" if not current else ("young" if pct is None else "fresh"))
        components.append({"key": key, "family": family, "name_en": en, "name_zh": zh,
                           "value": value, "score": pct, "status": status, "unit": unit,
                           "as_of": last.strftime("%Y-%m-%d") if last is not None else None,
                           "observations": int(s.notna().sum()), "formula": formula,
                           "source": source, "cnn_proxy": proxy,
                           "orientation": "higher=greed" if direction > 0 else "lower=greed"})
    scores = pd.DataFrame(ranked)
    families, family_series = [], {}
    for key, (en, zh) in FAMILIES.items():
        keys = [x["key"] for x in components if x["family"] == key]
        series = scores.reindex(columns=keys).mean(axis=1)
        family_series[key] = series
        value = _number(series.get(end), 1)
        families.append({"key": key, "name_en": en, "name_zh": zh, "score": value,
                         "members": keys, "weight": None, "contribution": None})
    fh = pd.DataFrame(family_series)
    count = fh.notna().sum(axis=1)
    eligible = count.ge(4) & fh.momentum.notna() & fh.volatility.notna()
    composite = fh.mean(axis=1).where(eligible)
    # One coherent, explicitly dated snapshot. Never mix today's VIX with
    # yesterday's breadth under a single "today" label. A latest qualifying
    # snapshot may lag at most two sessions; beyond that the score is withheld.
    usable = composite.dropna()
    candidate = usable.index[-1] if len(usable) else None
    age = len(nyse_calendar.sessions_strictly_between(candidate.date(), end.date())) + 1 if candidate is not None and candidate < end else 0
    recent = candidate is not None and age <= 2
    score_date = candidate if recent else end
    current_score = _number(composite.get(score_date), 1) if recent else None
    for f in families:
        f["score"] = _number(fh[f["key"]].get(score_date), 1)
    for c in components:
        series = raw[c["key"]].loc[:score_date].dropna()
        last = series.index[-1] if len(series) else None
        c["as_of"] = last.strftime("%Y-%m-%d") if last is not None else None
        c["value"] = _number(series.iloc[-1]) if len(series) else None
        c["score"] = _number(scores[c["key"]].get(score_date), 1)
        c["observations"] = int(len(series))
        c["status"] = "missing" if last is None else ("stale" if last != score_date else ("young" if c["score"] is None else "fresh"))
    composite, scores, count = composite.loc[:score_date], scores.loc[:score_date], count.loc[:score_date]
    active = [x for x in families if x["score"] is not None]
    if current_score is not None:
        for f in active:
            f["weight"] = round(1 / len(active), 6)
            f["contribution"] = round((f["score"] - 50) / len(active), 3)
    en, zh = _bands(current_score)
    dynamics = compute_vix_dynamics(clean.get("vix"), vix3m=clean.get("vix3m"),
                                    vix9d=clean.get("vix9d"), vvix=clean.get("vvix"), as_of=end)
    pivot = _pivot_context(raw, clean, dynamics)
    # Deltas require the EXACT same component set; composition changes are not momentum.
    masks = scores.notna().apply(lambda row: "|".join(row.index[row]), axis=1)
    changes, comparability = {}, {}
    for h in (1, 5, 20):
        value, comparable = None, False
        if len(composite) > h and current_score is not None:
            tail = composite.iloc[-h - 1:]
            comparable = bool(tail.notna().all() and masks.iloc[-h - 1:].nunique() == 1)
            if comparable:
                value = _number(tail.iloc[-1] - tail.iloc[0], 1)
        changes[f"change_{h}d"] = value
        comparability[f"change_{h}d"] = comparable
    history = [{"date": d.strftime("%Y-%m-%d"), "score": _number(v, 1),
                "families": int(count.loc[d]), "components": masks.loc[d]}
               for d, v in composite.tail(60).items()]
    warnings = ["delayed_snapshot"] if recent and age else []
    if len(active) < 6:
        warnings.append("incomplete_coverage")
    if dynamics.get("term_ratio") is not None and dynamics["term_ratio"] >= 1:
        warnings.append("near_term_volatility_inverted")
    if dynamics["down_sessions"] >= 2 and (dynamics.get("vvix_change_5d_pct") or 0) > 0:
        warnings.append("vol_of_vol_not_confirming_relief")
    return {"schema": VERSION, "as_of": score_date.strftime("%Y-%m-%d") if recent else None,
            "expected_session": end.strftime("%Y-%m-%d"), "age_sessions": age if recent else None, "score": current_score,
            "label_en": en, "label_zh": zh, "status": ("delayed" if age else "available") if current_score is not None else "insufficient_data",
            "coverage": {"available": len(active), "total": 6, "minimum": 4,
                         "requires": ["momentum", "volatility"]},
            "families": families, "components": components, "dynamics": dynamics, "pivot": pivot,
            "disagreement": _number(np.std([f["score"] for f in active]), 1) if active else None,
            "warnings": warnings, **changes, "change_comparable": comparability, "history": history,
            "history_kind": "reconstructed_observation_history_not_point_in_time", "forecast_validated": False,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "method_en": "252-observation midranks within at most 504 sessions; six equal family votes. Correlated breadth measures share one vote. Missing observations are excluded, not neutral. At least four families including momentum and volatility are required.",
            "method_zh": "最多504个交易日内252次有效观测的中位秩；六类等权投票。相关广度指标共用一票。缺失值排除而非记为中性。至少需要四类，且必须包含动量和波动率。"}


def read_intelligence_inputs() -> dict[str, pd.Series]:
    """Read existing source caches for the snapshot and offline replay."""
    inputs = {}
    for key, category, name, col in (
        ("spy", "yahoo", "SPY", "close"), ("tlt", "yahoo", "TLT", "close"),
        ("vix", "yahoo", "_VIX", "close"), ("vix3m", "yahoo", "_VIX3M", "close"),
        ("vix9d", "yahoo", "_VIX9D", "close"), ("vvix", "cboe", "vvix", "vvix"),
        ("credit", "fred", "BAMLH0A0HYM2", "hy_oas"), ("putcall", "cboe", "putcall", "equity_pc_ratio"),
    ):
        try:
            df = store.read(category, name)
            if df is not None:
                selected = col if col in df.columns else ("close" if key == "vvix" and "close" in df.columns else None)
                if selected:
                    inputs[key] = df[selected]
        except (OSError, ValueError, KeyError):
            continue
    try:
        breadth = store.read("breadth", "breadth")
        if breadth is not None:
            for key in ("nh", "nl", "adv", "dec"):
                if key in breadth.columns:
                    inputs[key] = breadth[key]
    except (OSError, ValueError, KeyError):
        pass
    return inputs


def compute_intelligence(*, as_of=None) -> dict:
    """Existing Fear/Greed owner extension; no new publisher or collector."""
    return build_intelligence(read_intelligence_inputs(), as_of=as_of)
