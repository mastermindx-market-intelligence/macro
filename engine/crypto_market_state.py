"""Crypto-class display state assembled from existing, governed stores.

The outputs are descriptive market context.  They do not alter Bitcoin Vector
scores, final exposure, strategy rules, or any measured authority.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from lib import store

Reader = Callable[[str, str], pd.DataFrame | None]


def _series(reader: Reader, group: str, name: str, columns: tuple[str, ...]) -> pd.Series:
    frame = reader(group, name)
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    for column in columns:
        if column in frame.columns:
            out = pd.to_numeric(frame[column], errors="coerce").dropna()
            out.index = pd.to_datetime(out.index).tz_localize(None).normalize()
            return out[~out.index.duplicated(keep="last")].sort_index()
    return pd.Series(dtype=float)


def _value(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _delta(series: pd.Series, periods: int = 30, pct: bool = False) -> float | None:
    clean = series.dropna()
    if len(clean) <= periods:
        return None
    now, then = float(clean.iloc[-1]), float(clean.iloc[-periods - 1])
    if pct:
        return None if then == 0 else 100 * (now / then - 1)
    return now - then


_BASIS_SOURCE = {
    "direct": "coingecko.global_market.total_mcap_usd",
    "derived": "coinmetrics.mcap_usd / (bgeo.btc_dominance/100)",
}
_OBS_LABEL = {
    "pending": ("Pending — no print expected on this date", "待公布 — 此日不预期发布"),
    "stale": ("Stale — later than this source's cadence", "过期 — 晚于该来源的发布节奏"),
    "zero": ("Measured zero", "测得为零"),
    "current": ("Current print", "已有最新发布"),
    "unavailable": ("Unavailable", "暂无"),
}
# Percentage points. Below this, a leg is not treated as the cause of a cap move.
_MATERIAL_PCT = 1.0


def _derived_cap(btc_cap: pd.Series, dominance: pd.Series) -> pd.Series:
    if btc_cap.empty or dominance.empty:
        return pd.Series(dtype=float)
    aligned = pd.concat(
        [btc_cap.rename("btc"), dominance.rename("dom")], axis=1, sort=False
    )
    aligned = aligned.sort_index().ffill(limit=3).dropna()
    derived = aligned["btc"] / (aligned["dom"] / 100).replace(0, np.nan)
    return derived.replace([np.inf, -np.inf], np.nan).dropna()


def _cap_assembly(reader: Reader) -> tuple[pd.Series, dict]:
    """Snapshot-preferred class cap, with splice metadata and a continuity series.

    The returned series keeps each source's reported level. `_regime_series` is
    the same path with level gaps removed at basis changes, so a splice is not
    read as a market transition. Callers must drop `_regime_series` before the
    dict is shown or serialized.
    """
    btc_cap = _series(reader, "coinmetrics", "mcap_usd", ("mcap_usd",))
    dominance = _series(
        reader, "bgeo", "btc_dominance", ("btc_dominance", "btc_dominance_pct")
    )
    derived = _derived_cap(btc_cap, dominance)
    snapshot = _series(reader, "coingecko", "global_market", ("total_mcap_usd",))
    empty = pd.Series(dtype=float)
    if derived.empty and snapshot.empty:
        return empty, {"segments": [], "splices": [], "_regime_series": empty}

    idx = derived.index.union(snapshot.index).sort_values()
    derived_a = derived.reindex(idx)
    snapshot_a = snapshot.reindex(idx)
    values = snapshot_a.combine_first(derived_a).dropna().sort_index()
    basis = pd.Series(index=values.index, dtype="object")
    basis.loc[values.index.isin(snapshot.dropna().index)] = "direct"
    missing = basis.isna()
    basis.loc[missing] = "derived"

    segments: list[dict] = []
    labels = basis.to_list()
    dates = list(basis.index)
    start_i = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start_i]:
            label = labels[start_i]
            segments.append(
                {
                    "basis": label,
                    "start": str(pd.Timestamp(dates[start_i]).date()),
                    "end": str(pd.Timestamp(dates[i - 1]).date()),
                    "support": i - start_i,
                    "source": _BASIS_SOURCE[label],
                }
            )
            start_i = i

    splices: list[dict] = []
    parts: list[pd.Series] = []
    prev_last: float | None = None
    for seg_i, seg in enumerate(segments):
        chunk = values.loc[pd.Timestamp(seg["start"]) : pd.Timestamp(seg["end"])]
        if seg_i == 0:
            parts.append(chunk)
            prev_last = float(chunk.iloc[-1])
            continue
        splice_ts = chunk.index[0]
        raw_first = float(chunk.iloc[0])
        level_ratio = None
        if splice_ts in derived.index and splice_ts in snapshot.index:
            derived_level = float(derived.loc[splice_ts])
            direct_level = float(snapshot.loc[splice_ts])
            if np.isfinite(derived_level) and derived_level != 0 and np.isfinite(direct_level):
                level_ratio = direct_level / derived_level
        elif (
            prev_last is not None
            and np.isfinite(prev_last)
            and prev_last != 0
            and np.isfinite(raw_first)
        ):
            level_ratio = raw_first / prev_last
        factor = (
            prev_last / raw_first
            if prev_last is not None
            and np.isfinite(prev_last)
            and np.isfinite(raw_first)
            and raw_first != 0
            else 1.0
        )
        scaled = chunk * factor
        parts.append(scaled)
        splices.append(
            {
                "date": str(pd.Timestamp(splice_ts).date()),
                "from_basis": segments[seg_i - 1]["basis"],
                "to_basis": seg["basis"],
                "support_before": segments[seg_i - 1]["support"],
                "support_after": seg["support"],
                "level_ratio": None if level_ratio is None else float(level_ratio),
                "regime_treatment": "continuity_adjusted",
            }
        )
        prev_last = float(scaled.iloc[-1])
    regime_series = (
        pd.concat(parts).pipe(lambda s: s[~s.index.duplicated(keep="last")]).sort_index()
        if parts
        else empty
    )
    meta = {
        "segments": segments,
        "splices": splices,
        "regime_note_en": (
            "Regime bands use a continuity adjustment across a basis splice. "
            "The level gap is disclosed and is not a regime transition."
        ),
        "regime_note_zh": "阶段带在口径切换处做衔接调整。水平跳变会披露，不视为阶段转换。",
        "_regime_series": regime_series,
    }
    return values, meta


def total_market_cap_history(reader: Reader = store.read) -> pd.Series:
    """Derive class market cap from BTC cap / BTC share, then splice snapshots.

    The series keeps reported levels. `attrs['regime_series']` is the continuity
    adjustment `class_regimes` uses so a splice gap is not a transition.
    """
    series, meta = _cap_assembly(reader)
    regime = meta.pop("_regime_series")
    series.attrs["cap_basis"] = meta
    series.attrs["regime_series"] = regime
    return series


def class_regimes(total_cap: pd.Series, *, continuity: pd.Series | None = None) -> list[dict]:
    """Collapse a trend/momentum read into calendar-true visual bands.

    When `continuity` is passed, or the series carries `attrs['regime_series']`
    from `total_market_cap_history`, bands are read from that adjusted path.
    """
    sample = continuity
    if sample is None:
        carried = total_cap.attrs.get("regime_series")
        if isinstance(carried, pd.Series):
            sample = carried
    if sample is None or sample.empty:
        sample = total_cap
    clean = sample.dropna().sort_index()
    if len(clean) < 100:
        return []
    state = pd.Series("neutral", index=clean.index)
    ma = clean.rolling(90, min_periods=60).mean()
    mom = clean.pct_change(30)
    state[(clean > ma) & (mom > 0.03)] = "bull"
    state[(clean < ma) & (mom < -0.03)] = "bear"
    out: list[dict] = []
    start = state.index[0]
    previous = state.iloc[0]
    for date, tone in state.iloc[1:].items():
        if tone != previous:
            out.append(
                {"start": str(start.date()), "end": str(date.date()), "tone": previous}
            )
            start, previous = date, tone
    out.append(
        {
            "start": str(start.date()),
            "end": str(state.index[-1].date()),
            "tone": previous,
        }
    )
    return out


def _direction(value: float | None, up: float, down: float) -> tuple[str, str]:
    if value is None:
        return "Unavailable", "neutral"
    if value >= up:
        return "Rising", "bull"
    if value <= down:
        return "Falling", "bear"
    return "Steady", "neutral"


def _fear_state(value: float | None) -> tuple[str, str]:
    if value is None:
        return "Unavailable", "neutral"
    if value <= 24:
        return "Extreme fear", "bear"
    if value <= 44:
        return "Fearful", "bear"
    if value < 56:
        return "Neutral", "neutral"
    if value < 76:
        return "Greedy", "bull"
    return "Extreme greed", "bull"


def _latest_signals(reader: Reader) -> pd.Series:
    frame = reader("vector", "signals")
    if frame is None or frame.empty:
        return pd.Series(dtype=object)
    return frame.sort_index().iloc[-1]


def _clock(today: pd.Timestamp | str | None) -> pd.Timestamp:
    if today is None:
        stamp = pd.Timestamp.now(tz="UTC")
    else:
        stamp = pd.Timestamp(today)
        if stamp.tzinfo is None:
            return stamp.normalize()
    return stamp.tz_convert("UTC").tz_localize(None).normalize()


def _business_day_on_or_before(day: pd.Timestamp) -> pd.Timestamp:
    """Weekends only. Exchange holidays are not in this cadence."""
    cursor = day
    while cursor.weekday() >= 5:
        cursor -= pd.Timedelta(days=1)
    return cursor


def observation_status(
    last_date,
    today,
    *,
    cadence: str,
    latest_value: float | None,
    has_observation: bool,
) -> str:
    """pending | stale | zero | current | unavailable.

    `us_business_day` (ETF creations): a print is expected Mon–Fri. Saturday and
    Sunday, with that Friday on file, are pending — expected nonpublication, not
    a zero and not a stale feed. A missed weekday is stale.
    `calendar_day` (stablecoin supply): a print is expected every calendar date.
    Any gap before `today` is stale. The same calendar lag is therefore pending
    for the ETF and stale for stablecoins.
    `zero` is a print on the expected date whose measured value is 0. A missing
    row is never stored as 0.
    """
    if not has_observation or last_date is None:
        return "unavailable"
    last = pd.Timestamp(last_date).tz_localize(None).normalize()
    today_ts = _clock(today)
    measured_zero = latest_value is not None and float(latest_value) == 0.0
    if cadence == "us_business_day":
        expected = _business_day_on_or_before(today_ts)
        if last < expected:
            return "stale"
        if today_ts.weekday() >= 5 and last == expected:
            return "pending"
        if last == expected and measured_zero:
            return "zero"
        return "current"
    if cadence == "calendar_day":
        if last < today_ts:
            return "stale"
        if last == today_ts and measured_zero:
            return "zero"
        return "current"
    raise ValueError(f"unknown cadence {cadence}")


def _observation_fields(status: str) -> dict:
    en, zh = _OBS_LABEL[status]
    return {
        "observation": status,
        "observation_label_en": en,
        "observation_label_zh": zh,
    }


def _cap_attribution(btc_price: pd.Series, btc_cap: pd.Series) -> dict:
    """Separate a capitalization move into price, token supply, or neither.

    Supply is coinmetrics BTC cap divided by the coinbase BTC close. It is not
    a subscription tape.
    """
    supply = pd.Series(dtype=float)
    if not btc_price.empty and not btc_cap.empty:
        aligned = pd.concat(
            [btc_cap.rename("mcap"), btc_price.rename("px")], axis=1, sort=False
        ).dropna()
        aligned = aligned[aligned["px"] != 0]
        supply = (aligned["mcap"] / aligned["px"]).replace([np.inf, -np.inf], np.nan).dropna()
    price_30d = _delta(btc_price, 30, pct=True)
    supply_30d = _delta(supply, 30, pct=True)
    if price_30d is None or supply_30d is None:
        kind = "unavailable"
    else:
        price_moved = abs(price_30d) >= _MATERIAL_PCT
        supply_moved = abs(supply_30d) >= _MATERIAL_PCT
        if supply_moved and not price_moved:
            kind = "issuance"
        elif price_moved and not supply_moved:
            kind = "valuation"
        elif price_moved and supply_moved:
            kind = "mixed"
        else:
            kind = "share_or_flat"
    notes = {
        "issuance": (
            "The 30-day capitalization change tracks token supply, not a measured subscription.",
            "30日市值变化对应代币供应量，不是已测量的申购。",
        ),
        "valuation": (
            "The 30-day capitalization change tracks price, not a measured subscription.",
            "30日市值变化对应价格，不是已测量的申购。",
        ),
        "mixed": (
            "Price and token supply both moved. This is capitalization, not a measured subscription.",
            "价格与代币供应量都变了。这是市值变化，不是已测量的申购。",
        ),
        "share_or_flat": (
            "Bitcoin price and token supply were little changed. A total-cap move here is the complement of bitcoin's market share, not a measured subscription.",
            "比特币价格与代币供应量几乎没变。此处总市值变化是比特币市值占比的余项，不是已测量的申购。",
        ),
        "unavailable": (
            "Token supply could not be separated from price. This is not a measured subscription.",
            "无法把代币供应量与价格分开。这不是已测量的申购。",
        ),
    }
    note_en, note_zh = notes[kind]
    return {
        "kind": kind,
        "price_30d_pct": price_30d,
        "supply_30d_pct": supply_30d,
        "supply_basis": "coinmetrics.mcap_usd / coinbase.btc_daily.close",
        "note_en": note_en,
        "note_zh": note_zh,
    }


def _hero(total_30d: float | None, attribution: dict) -> tuple[str, str, str, str, str]:
    """Headline is a capitalization sentence. It does not claim inflow or breadth."""
    kind = attribution["kind"]
    if total_30d is None:
        return (
            "Market-cap read unavailable",
            "No total-cap history is on file. Other measurements stay on their own tiles.",
            "总市值读数暂无",
            "没有总市值历史。其他测量仍在各自条目中。",
            "neutral",
        )
    if kind == "issuance":
        return (
            "Market cap moved with token issuance",
            attribution["note_en"],
            "市值变化来自代币发行",
            attribution["note_zh"],
            "neutral",
        )
    if kind == "mixed":
        tone = "bull" if total_30d > 3 else ("bear" if total_30d < -3 else "neutral")
        return (
            "Market cap moved with price and issuance",
            attribution["note_en"],
            "市值变化同时来自价格与发行",
            attribution["note_zh"],
            tone,
        )
    if kind == "share_or_flat" and abs(total_30d) > 3:
        tone = "bull" if total_30d > 3 else "bear"
        return (
            "Market cap moved apart from bitcoin price",
            attribution["note_en"],
            "总市值变化并非来自比特币价格",
            attribution["note_zh"],
            tone,
        )
    if total_30d > 3:
        summary = attribution["note_en"] if kind == "unavailable" else (
            "Total market cap is higher over 30 days. That is a price change in capitalization, not a measured subscription."
        )
        summary_zh = attribution["note_zh"] if kind == "unavailable" else (
            "30日总市值较高。这是市值中的价格变化，不是已测量的申购。"
        )
        return ("Market cap is higher", summary, "总市值较高", summary_zh, "bull")
    if total_30d < -3:
        summary = attribution["note_en"] if kind == "unavailable" else (
            "Total market cap is lower over 30 days. That is a price change in capitalization, not a measured redemption."
        )
        summary_zh = attribution["note_zh"] if kind == "unavailable" else (
            "30日总市值较低。这是市值中的价格变化，不是已测量的赎回。"
        )
        return ("Market cap is lower", summary, "总市值较低", summary_zh, "bear")
    return (
        "Market cap is little changed",
        "No decisive 30-day capitalization move.",
        "总市值变化不大",
        "30日市值没有明确方向。",
        "neutral",
    )


def _dated_totals(frame: pd.DataFrame | None) -> pd.Series:
    if frame is None or frame.empty or "total" not in frame.columns:
        return pd.Series(dtype=float)
    totals = pd.to_numeric(frame["total"], errors="coerce").dropna()
    if totals.empty:
        return totals
    totals.index = pd.to_datetime(totals.index).tz_localize(None).normalize()
    return totals[~totals.index.duplicated(keep="last")].sort_index()


def build_market_state(
    reader: Reader = store.read, *, today: pd.Timestamp | str | None = None
) -> dict:
    clock = _clock(today)
    total, cap_meta = _cap_assembly(reader)
    regime_series = cap_meta.pop("_regime_series")
    dominance = _series(
        reader, "bgeo", "btc_dominance", ("btc_dominance", "btc_dominance_pct")
    )
    fear = _series(reader, "sentiment_crypto", "fear_greed", ("fear_greed",))
    stable = _series(
        reader, "defillama", "stablecoins", ("stablecoin_mcap_usd",)
    )
    btc = _series(reader, "coinbase", "btc_daily", ("close", "Close"))
    btc_volume = _series(reader, "coinbase", "btc_daily", ("volume", "Volume"))
    eth = _series(reader, "yahoo", "ETH-USD", ("close", "close_price", "Close"))
    etf_frame = reader("farside", "etf_flows")
    signals = _latest_signals(reader)

    total_30d = _delta(total, 30, pct=True)
    dom_30d = _delta(dominance, 30)
    total_state, total_tone = _direction(total_30d, 3, -3)
    dom_state, dom_tone = _direction(dom_30d, 1, -1)
    fear_value = _value(fear.iloc[-1]) if not fear.empty else None
    fear_state, fear_tone = _fear_state(fear_value)
    btc_cap = _series(reader, "coinmetrics", "mcap_usd", ("mcap_usd",))
    attribution = _cap_attribution(btc, btc_cap)
    stance, summary, stance_zh, summary_zh, hero_tone = _hero(total_30d, attribution)

    stable_30d_pct = _delta(stable, 30, pct=True)
    stable_30d_usd = _delta(stable, 30)
    stable_level = _value(stable.iloc[-1]) if not stable.empty else None
    stable_asof = str(pd.Timestamp(stable.index[-1]).date()) if not stable.empty else None
    stable_obs = observation_status(
        stable.index[-1] if not stable.empty else None,
        clock,
        cadence="calendar_day",
        latest_value=stable_level,
        has_observation=not stable.empty,
    )
    stable_state, stable_tone = _direction(stable_30d_pct, 1, -1)
    if stable_obs in {"stale", "unavailable"}:
        stable_state, stable_tone = "Unavailable", "neutral"

    totals = _dated_totals(etf_frame if isinstance(etf_frame, pd.DataFrame) else None)
    etf_5d = float(totals.tail(5).sum()) if not totals.empty else None
    etf_latest = _value(totals.iloc[-1]) if not totals.empty else None
    etf_asof = str(pd.Timestamp(totals.index[-1]).date()) if not totals.empty else None
    etf_obs = observation_status(
        totals.index[-1] if not totals.empty else None,
        clock,
        cadence="us_business_day",
        latest_value=etf_latest,
        has_observation=not totals.empty,
    )
    etf_state, etf_tone = _direction(etf_5d, 100, -100)
    if etf_obs in {"stale", "unavailable"}:
        etf_state, etf_tone = "Unavailable", "neutral"

    volume_pctile = None
    if len(btc_volume) >= 90:
        window = btc_volume.tail(365)
        volume_pctile = round(100 * float((window <= window.iloc[-1]).mean()))
    if volume_pctile is None:
        volume_state, volume_tone = "Unavailable", "neutral"
    elif volume_pctile >= 70:
        volume_state, volume_tone = "High participation", "bull"
    elif volume_pctile <= 30:
        volume_state, volume_tone = "Quiet tape", "bear"
    else:
        volume_state, volume_tone = "Normal", "neutral"

    funding_annual = _value(signals.get("funding_annual_pct"))
    funding_state = (
        "Longs crowded"
        if funding_annual is not None and funding_annual >= 15
        else (
            "Shorts paying"
            if funding_annual is not None and funding_annual <= -5
            else ("Balanced" if funding_annual is not None else "Unavailable")
        )
    )
    funding_tone = (
        "bear"
        if funding_annual is not None and funding_annual >= 15
        else ("bull" if funding_annual is not None and funding_annual <= -5 else "neutral")
    )
    oi_ratio = _value(signals.get("oi_mcap_ratio"))
    oi_pctile = _value(signals.get("oi_mcap_pctile"))
    oi_state = (
        "Leverage elevated"
        if oi_pctile is not None and oi_pctile >= 75
        else (
            "Leverage light"
            if oi_pctile is not None and oi_pctile <= 25
            else ("Leverage normal" if oi_pctile is not None else "Unavailable")
        )
    )
    oi_tone = (
        "bear"
        if oi_pctile is not None and oi_pctile >= 75
        else ("bull" if oi_pctile is not None and oi_pctile <= 25 else "neutral")
    )
    vol_value = _value(signals.get("dvol"))
    vol_pctile = _value(signals.get("dvol_pctile"))
    vol_state = (
        "Volatility hot"
        if vol_pctile is not None and vol_pctile >= 75
        else (
            "Volatility compressed"
            if vol_pctile is not None and vol_pctile <= 25
            else ("Volatility normal" if vol_pctile is not None else "Unavailable")
        )
    )
    vol_tone = "bear" if vol_pctile is not None and vol_pctile >= 75 else "neutral"

    alt_score = None
    alt_state = "Unavailable" if dom_30d is None else "Building history"
    alt_tone = "neutral"
    if dom_30d is not None and not btc.empty and not eth.empty and len(btc) > 90 and len(eth) > 90:
        aligned = pd.concat(
            [eth.rename("eth"), btc.rename("btc")], axis=1, sort=False
        ).dropna()
        if len(aligned) > 90:
            rel = aligned["eth"] / aligned["btc"]
            rel_90d = 100 * (rel.iloc[-1] / rel.iloc[-91] - 1)
            alt_score = round(float(np.clip(50 + rel_90d * 1.5 - dom_30d * 4, 0, 100)))
    if alt_score is not None and alt_score >= 65:
        alt_state, alt_tone = "ETH leading on relative trend", "bull"
    elif alt_score is not None and alt_score <= 35:
        alt_state, alt_tone = "BTC leading on relative trend", "bear"
    elif alt_score is not None:
        alt_state, alt_tone = "Mixed relative trend", "neutral"

    asof_candidates = [
        s.index[-1]
        for s in (total, dominance, fear, stable, btc)
        if not s.empty
    ]
    as_of = str(pd.Timestamp(max(asof_candidates)).date()) if asof_candidates else "—"
    history = total.tail(1460)
    regime_history = regime_series.reindex(history.index).dropna()
    return {
        "as_of": as_of,
        "stance": stance,
        "stance_zh": stance_zh,
        "summary": summary,
        "summary_zh": summary_zh,
        "tone": hero_tone,
        "total_market_cap": _value(total.iloc[-1]) if not total.empty else None,
        "total_30d_pct": total_30d,
        "total_state": total_state,
        "total_tone": total_tone,
        "btc_dominance": _value(dominance.iloc[-1]) if not dominance.empty else None,
        "dominance_30d": dom_30d,
        "dominance_state": dom_state,
        "dominance_tone": dom_tone,
        "fear_greed": fear_value,
        "fear_state": fear_state,
        "fear_tone": fear_tone,
        "history": {
            "dates": [str(pd.Timestamp(x).date()) for x in history.index],
            "vals": [float(x) for x in history.to_numpy()],
        },
        "regimes": class_regimes(history, continuity=regime_history),
        "cap_basis": cap_meta,
        "cap_attribution": attribution,
        "flows": {
            "etf": {
                "kind": "subscription",
                "expected_cadence": "us_business_day",
                "value": etf_5d,
                "latest": etf_latest,
                "state": etf_state,
                "tone": etf_tone,
                "as_of": etf_asof,
                **_observation_fields(etf_obs),
            },
            "stablecoins": {
                "kind": "issuance",
                "expected_cadence": "calendar_day",
                "value": stable_level,
                "change_30d_pct": stable_30d_pct,
                "change_30d_usd": stable_30d_usd,
                "state": stable_state,
                "tone": stable_tone,
                "as_of": stable_asof,
                **_observation_fields(stable_obs),
            },
            "volume": {
                "kind": "participation",
                "value": _value(btc_volume.iloc[-1]) if not btc_volume.empty else None,
                "percentile": volume_pctile,
                "state": volume_state,
                "tone": volume_tone,
                "proxy": "BTC spot-volume proxy",
            },
        },
        "heat": {
            "funding": {
                "value": funding_annual,
                "state": funding_state,
                "tone": funding_tone,
            },
            "open_interest": {
                "value": oi_ratio,
                "percentile": oi_pctile,
                "state": oi_state,
                "tone": oi_tone,
            },
            "volatility": {
                "value": vol_value,
                "percentile": vol_pctile,
                "state": vol_state,
                "tone": vol_tone,
            },
            "altseason": {
                "kind": "relative_price",
                "value": alt_score,
                "state": alt_state,
                "tone": alt_tone,
            },
        },
    }
