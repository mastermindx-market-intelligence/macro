"""Subsector rotation & velocity — pure compute layer.

Turns Finviz's broad-universe **theme → subsector** performance snapshot
(``data/themes_heatmap/perf_snapshot.json``, 268 subsectors across 40 themes,
eight horizons) into a rotation read: which subsectors lead, which are turning,
and — the point — which are *accelerating* (an emerging-theme early-entry
signal). It is a separate lens from the 47 curated thematic baskets: those
are our own equal-weight indices; this rides Finviz's own broad numbers (which
include names we hold no prices for), so it stays a display/context layer.

Design
------
* **Pure.** Takes the already-loaded snapshot dicts and returns a JSON-ready
  payload. All disk/network I/O lives in ``scripts/build_subsector_rotation.py``.
* **Relative-strength, cross-sectional.** Every metric is computed *across*
  subsectors at each horizon (the benchmark is the median subsector), so a
  reading says "leading/lagging vs the rest of the market," not vs an index we
  may not have.
* **RRG-style quadrants.** ``rs_ratio`` (leadership level) × ``rs_mom`` (is that
  leadership improving) → Leading / Weakening / Lagging / Improving. The
  *Improving* quadrant (laggards turning up) plus positive ``accel`` is the
  early-rotation watchlist.
* **Turn read (additive).** ``engine/subsector_turn.py`` re-derives the same snapshot as a
  disjoint-segment pace curve plus a reconstructed level path, replays it over the
  append-only PIT archive, and attaches per-node cycle position, turn state
  (bottoming / turned up / topping / turned down) with cross-session confirmation, member
  breadth, and a parallel fast rank. Every incumbent field here is left byte-identical —
  the two reads are logged side by side and graded head-to-head by
  ``engine/subsector_track_record.py``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def _load_names_zh() -> dict:
    """Chinese translations for theme / subsector display names (i18n). Optional —
    a missing file just leaves names in English (degrade-never-raise)."""
    try:
        p = Path(__file__).resolve().parent.parent / "data" / "themes_heatmap" / "names_zh.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"themes": d.get("themes") or {}, "subsectors": d.get("subsectors") or {}}
    except Exception:  # noqa: BLE001
        return {"themes": {}, "subsectors": {}}


_NAMES_ZH = _load_names_zh()

# Finviz snapshot horizons (calendar MTD/YTD kept for display; the rolling ones
# drive momentum). Approx weeks per window normalise returns to a weekly pace.
HORIZONS = ["1D", "1W", "1M", "MTD", "3M", "6M", "1Y", "YTD"]
MOM_HORIZONS = ["1W", "1M", "3M", "6M", "1Y"]
WEEKS = {"1W": 1.0, "1M": 4.345, "3M": 13.04, "6M": 26.07, "1Y": 52.14}

# Lane C — closed-session leadership is an additive, descriptive observation.
# These windows are completed market sessions, never calendar-day approximations.
CLOSED_SESSION_WINDOWS = (1, 3, 5, 10, 20, 60)
CLOSED_SESSION_LEADERSHIP_SCHEMA = "subsector_rotation.closed_session_leadership.v1"
CLOSED_SESSION_PERMISSIONS = {
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "may_trade": False,
}



def _zscore(values: dict[str, float]) -> dict[str, float]:
    """Cross-sectional z-score of a {key: value} map (robust to tiny n / 0 std)."""
    keys = [k for k, v in values.items() if v is not None and np.isfinite(v)]
    if len(keys) < 2:
        return {k: 0.0 for k in values}
    arr = np.array([values[k] for k in keys], dtype=float)
    mu, sd = float(arr.mean()), float(arr.std())
    if sd <= 1e-9:
        return {k: 0.0 for k in values}
    return {k: ((values[k] - mu) / sd if (values[k] is not None and np.isfinite(values[k])) else 0.0)
            for k in values}


def _nanmean(*xs: float | None) -> float | None:
    vals = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.mean(vals)) if vals else None


def _quadrant(rs_ratio: float, rs_mom: float) -> str:
    if rs_ratio >= 0:
        return "leading" if rs_mom >= 0 else "weakening"
    return "improving" if rs_mom >= 0 else "lagging"


def _rotation_metrics(perf_by_key: Mapping[str, Mapping[str, float]]) -> dict[str, dict]:
    """Core pipeline over {key: {horizon: pct}} → per-key rotation metrics.

    Reused for both subsectors and theme rollups.
    """
    keys = list(perf_by_key)
    # market = median subsector at each horizon → relative strength.
    median = {}
    for h in HORIZONS:
        col = [perf_by_key[k].get(h) for k in keys]
        col = [v for v in col if v is not None and np.isfinite(v)]
        median[h] = float(np.median(col)) if col else None

    rs = {k: {h: ((perf_by_key[k].get(h) - median[h])
                  if (perf_by_key[k].get(h) is not None and median.get(h) is not None) else None)
              for h in HORIZONS} for k in keys}
    # z-score each horizon's RS across keys (the RRG axes live in z-space).
    zrs = {h: _zscore({k: rs[k][h] for k in keys}) for h in HORIZONS}

    # weekly pace per horizon → acceleration (recent pace vs the 3-month pace).
    rate = {k: {h: (perf_by_key[k].get(h) / WEEKS[h]
                    if (h in WEEKS and perf_by_key[k].get(h) is not None) else None)
                for h in MOM_HORIZONS} for k in keys}
    accel_raw = {k: ((rate[k]["1W"] - rate[k]["3M"]) if (rate[k]["1W"] is not None and rate[k]["3M"] is not None)
                     else (rate[k]["1W"] - rate[k]["1M"]) if (rate[k]["1W"] is not None and rate[k]["1M"] is not None)
                     else None) for k in keys}
    z_accel = _zscore(accel_raw)

    out: dict[str, dict] = {}
    for k in keys:
        rs_ratio = _nanmean(zrs["1M"].get(k), zrs["3M"].get(k)) or 0.0
        rs_mom = (_nanmean(zrs["1W"].get(k), zrs["1M"].get(k)) or 0.0) \
            - (_nanmean(zrs["3M"].get(k), zrs["6M"].get(k)) or 0.0)
        # emerging = accelerating + relative strength improving + recent strength.
        emerging = 0.5 * z_accel.get(k, 0.0) + 0.8 * rs_mom + 0.3 * (zrs["1W"].get(k) or 0.0)
        out[k] = {
            "perf": {h: (round(perf_by_key[k].get(h), 2) if perf_by_key[k].get(h) is not None else None)
                     for h in HORIZONS},
            "rs": {h: (round(rs[k][h], 2) if rs[k][h] is not None else None) for h in MOM_HORIZONS},
            "rs_ratio": round(rs_ratio, 3),
            "rs_mom": round(rs_mom, 3),
            "accel": round(accel_raw[k], 3) if accel_raw[k] is not None else None,
            "z_accel": round(z_accel.get(k, 0.0), 3),
            "quadrant": _quadrant(rs_ratio, rs_mom),
            "emerging_score": round(emerging, 3),
        }
    return out


def _history_with_today(history: Sequence[Mapping] | None,
                        perf_by_key: Mapping[str, Mapping],
                        asof: str | None) -> list[dict]:
    """Archive rows + today's snapshot, appended only if the archive doesn't already hold it.

    The archive (``subsector_perf_history.jsonl``) is appended by the fetcher, so on a normal
    nightly today is already the last row. On a render-only lane — or for a synthetic node
    like the Mag-7 composite, which is injected in memory and never archived — the snapshot
    is ahead of the archive, and the read must still see today.
    """
    rows = [dict(r) for r in (history or []) if (r or {}).get("subsectors")]
    day = str(asof or "").strip() or "today"
    if rows and str(rows[-1].get("asof") or "") == day:
        # Same session. The LIVE SNAPSHOT WINS over the archive row for today: the archive is
        # append-once-per-asof, so an intraday re-fetch leaves it holding the morning's
        # numbers while perf_snapshot.json carries the latest. Letting the archive win would
        # compute the turn read on a different vintage than the incumbent metrics in the same
        # payload. Archive-only keys are kept (same session, nothing to lose).
        merged = {**(rows[-1].get("subsectors") or {}), **dict(perf_by_key)}
        rows[-1] = {"asof": day, "subsectors": merged}
        return rows
    rows.append({"asof": day, "subsectors": dict(perf_by_key)})
    return rows


def attach_turn(rows: list[dict], perf_by_key: Mapping[str, Mapping],
                *, key_of=lambda r: r["key"],
                history: Sequence[Mapping] | None = None,
                member_map: Mapping | None = None,
                member_perf: Mapping | None = None,
                asof: str | None = None,
                min_members: int = 3) -> dict:
    """Compute the turn read for ``rows`` and attach it in place. Returns the summary block.

    Shared by subsectors, theme rollups and the sector-ETF cross-section so all three
    surfaces carry the same vocabulary. Degrade-safe: on any failure the rows are left
    exactly as the incumbent pipeline produced them and an empty summary comes back.
    """
    try:
        from engine import subsector_turn as st

        hist = _history_with_today(history, perf_by_key, asof)
        out = st.replay(hist, member_map=member_map, member_perf=member_perf,
                        keys=list(perf_by_key))
        reads = out.get("reads") or {}
        meta = {}
        for r in rows:
            k = key_of(r)
            rd = reads.get(k)
            if not rd:
                continue
            for f in st.ROW_FIELDS:
                if f in rd:
                    r[f] = rd[f]
            copy = st.STATE_COPY.get(rd.get("turn_state") or "", {})
            r["turn_label"] = copy.get("en")
            r["turn_label_zh"] = copy.get("zh")
            r["turn_say"] = copy.get("say_en")
            r["turn_say_zh"] = copy.get("say_zh")
            meta[k] = {"name": r.get("name") or r.get("theme") or k,
                       "name_zh": r.get("name_zh") or r.get("theme_zh"),
                       "theme": r.get("theme") or "", "theme_zh": r.get("theme_zh") or "",
                       "n_members": r.get("n_members")}   # None = unknown, not zero
        summary = st.summarize(reads, meta, min_members=min_members)
        summary["n_sessions"] = out.get("n_days")
        summary["warm"] = out.get("warm")
        summary["market"] = out.get("market")
        summary["nominations"] = st.handoff_nominations(reads, meta)
        summary["schema"] = st.SCHEMA
        return summary
    except Exception as e:  # noqa: BLE001 — additive layer, never fatal
        log.warning("turn read failed: %s", e)
        return {}


def _normalise_daily_frame(frame, sessions: pd.DatetimeIndex, asof: pd.Timestamp) -> dict | None:
    """Normalise one owner-provided daily tape onto the completed market calendar.

    The owner close series is not rewritten for corporate actions here. Internal gaps
    and stale tails remain null, and a return is unavailable on the first session after
    a gap. Missing-session counts are disclosed in coverage instead of hidden.
    """
    if frame is None:
        return None
    if isinstance(frame, pd.Series):
        df = frame.to_frame("close")
    elif isinstance(frame, pd.DataFrame):
        df = frame.copy()
    else:
        return None
    if "close" not in df or df["close"].dropna().empty:
        return None
    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index().loc[:asof]
    close = pd.to_numeric(df["close"], errors="coerce").where(lambda x: x > 0)
    close = close[~close.index.duplicated(keep="last")]
    if close.dropna().empty:
        return None
    raw_close = close.reindex(sessions)
    first = raw_close.first_valid_index()
    last = raw_close.last_valid_index()
    if first is None or last is None:
        return None
    all_internal_missing_sessions = int(raw_close.loc[first:last].isna().sum())
    trailing_missing_sessions = int((sessions > last).sum())
    observed_close = raw_close.copy()
    daily_return = observed_close.pct_change(fill_method=None)
    daily_return = daily_return.where(
        observed_close.notna() & observed_close.shift(1).notna()
    )

    volume = None
    if "volume" in df:
        volume = pd.to_numeric(df["volume"], errors="coerce").reindex(sessions)
    return {
        "close": observed_close,
        "raw_close": raw_close,
        "return": daily_return,
        "volume": volume,
        "first_observed_session": first.date().isoformat(),
        "last_observed_session": last.date().isoformat(),
        "all_internal_missing_sessions": all_internal_missing_sessions,
        "trailing_missing_sessions": trailing_missing_sessions,
    }


def _compound_on_dates(series: pd.Series | None, dates: pd.DatetimeIndex) -> float | None:
    if series is None or len(dates) == 0:
        return None
    vals = pd.to_numeric(series.reindex(dates), errors="coerce")
    if len(vals) != len(dates) or vals.isna().any():
        return None
    return float((1.0 + vals).prod() - 1.0)


def _pct(value: float | None) -> float | None:
    return round(value * 100.0, 4) if value is not None and np.isfinite(value) else None


def _relative_strength_summary(
    group_returns: pd.Series | None,
    benchmark_returns: pd.Series | None,
    dates: pd.DatetimeIndex,
) -> dict:
    """Relative-strength change and log-ratio slope over completed sessions."""
    unavailable = {
        "change_pct": None,
        "slope_pct_per_session": None,
    }
    if group_returns is None or benchmark_returns is None or len(dates) == 0:
        return unavailable
    frame = pd.concat(
        [
            pd.to_numeric(group_returns.reindex(dates), errors="coerce").rename("group"),
            pd.to_numeric(benchmark_returns.reindex(dates), errors="coerce").rename("benchmark"),
        ],
        axis=1,
    )
    if len(frame) != len(dates) or frame.isna().any().any():
        return unavailable
    if (frame <= -1.0).any().any():
        return unavailable
    relative_log = np.log1p(frame["group"]) - np.log1p(frame["benchmark"])
    if not np.isfinite(relative_log.to_numpy(dtype=float)).all():
        return unavailable
    cumulative_log = relative_log.cumsum()
    change = float(np.expm1(cumulative_log.iloc[-1]))
    slope = None
    if len(cumulative_log) >= 2:
        slope = float(np.polyfit(np.arange(len(cumulative_log)), cumulative_log, 1)[0])
    return {
        "change_pct": _pct(change),
        "slope_pct_per_session": _pct(slope),
    }


def _window_participation(
    member_returns: pd.DataFrame,
    dates: pd.DatetimeIndex,
    market_return: float | None,
    parent_return: float | None,
) -> tuple[dict, list[str]]:
    measured: dict[str, float] = {}
    for ticker in member_returns.columns:
        value = _compound_on_dates(member_returns[ticker], dates)
        if value is not None:
            measured[ticker] = value
    reasons: list[str] = []
    if not measured:
        return {
            "priced_members": 0,
            "positive_share": None,
            "beat_market_share": None,
            "beat_parent_share": None,
            "dispersion_pct": None,
            "top_abs_move_share": None,
            "top_abs_move_ticker": None,
        }, reasons

    vals = np.array(list(measured.values()), dtype=float)
    n = len(vals)
    total_abs = float(np.abs(vals).sum())
    top_ticker = max(measured, key=lambda t: abs(measured[t])) if total_abs > 0 else None
    top_share = abs(measured[top_ticker]) / total_abs if top_ticker else 0.0
    if n >= 3 and top_share >= 0.5:
        reasons.append("ONE_NAME_CONCENTRATION")
    return {
        "priced_members": n,
        "positive_share": round(float(np.mean(vals > 0)), 4),
        "beat_market_share": (
            round(float(np.mean(vals > market_return)), 4) if market_return is not None else None
        ),
        "beat_parent_share": (
            round(float(np.mean(vals > parent_return)), 4) if parent_return is not None else None
        ),
        "dispersion_pct": round(float(np.std(vals, ddof=0)) * 100.0, 4),
        "top_abs_move_share": round(top_share, 4),
        "top_abs_move_ticker": top_ticker,
    }, reasons


def _volume_reclaim_evidence(prepared: Mapping[str, Mapping], asof: pd.Timestamp) -> dict:
    high_volume_positive: list[bool] = []
    above_20d_mean: list[bool] = []
    reclaimed_20d_mean: list[bool] = []
    members_with_volume = 0
    members_with_reclaim = 0
    asof = pd.Timestamp(asof).normalize()
    for item in prepared.values():
        raw_close = item["raw_close"].loc[:asof]
        if asof not in raw_close.index or pd.isna(raw_close.loc[asof]):
            continue
        close = item["close"].loc[:asof].iloc[-21:]
        ret = item["return"].loc[:asof]
        if len(close) == 21 and not close.isna().any():
            latest = float(close.iloc[-1])
            previous = float(close.iloc[-2])
            prior_mean = float(close.iloc[:-1].mean())
            current_mean = float(close.iloc[-20:].mean())
            above_20d_mean.append(latest >= current_mean)
            reclaimed_20d_mean.append(previous < prior_mean and latest >= prior_mean)
            members_with_reclaim += 1
        volume = item.get("volume")
        if volume is not None:
            hist = volume.loc[:asof].iloc[-21:]
            latest_ret = ret.loc[asof] if asof in ret.index else np.nan
            if len(hist) == 21 and not hist.isna().any() and np.isfinite(latest_ret):
                high_volume_positive.append(
                    bool(hist.iloc[-1] > hist.iloc[:-1].mean() and latest_ret > 0)
                )
                members_with_volume += 1
    return {
        "members_with_volume": members_with_volume,
        "high_volume_positive_share": (
            round(float(np.mean(high_volume_positive)), 4) if high_volume_positive else None
        ),
        "members_with_20d_reclaim_evidence": members_with_reclaim,
        "above_20d_mean_share": (
            round(float(np.mean(above_20d_mean)), 4) if above_20d_mean else None
        ),
        "reclaimed_20d_mean_share": (
            round(float(np.mean(reclaimed_20d_mean)), 4) if reclaimed_20d_mean else None
        ),
    }


def _leadership_node(
    *,
    key: str,
    name: str,
    relationship_kind: str,
    declared_members: Sequence[str],
    prepared_all: Mapping[str, Mapping],
    market_returns: pd.Series,
    return_sessions: pd.DatetimeIndex,
    parent_returns: pd.Series | None,
    windows: Sequence[int],
) -> dict:
    declared = [str(t).strip().upper() for t in declared_members if str(t).strip()]
    unique = list(dict.fromkeys(declared))
    duplicate_count = len(declared) - len(unique)
    prepared = {t: prepared_all[t] for t in unique if t in prepared_all}
    member_returns = pd.DataFrame(
        {ticker: item["return"] for ticker, item in prepared.items()}, index=return_sessions
    )
    group_returns = member_returns.mean(axis=1, skipna=True) if len(member_returns.columns) else pd.Series(
        index=return_sessions, dtype=float
    )
    group_returns = group_returns.where(member_returns.notna().sum(axis=1) > 0)

    coverage_window_sessions = max(windows) if windows else 60
    coverage_dates = return_sessions[-coverage_window_sessions:]
    internal_missing_sessions = 0
    trailing_missing_sessions = 0
    pre_listing_sessions = 0
    stale_members = []
    short_history_members = []
    complete_window_members = 0
    for ticker, item in prepared.items():
        first_seen = pd.Timestamp(item["first_observed_session"])
        last_seen = pd.Timestamp(item["last_observed_session"])
        scoped_raw = item["raw_close"].reindex(coverage_dates)
        active = scoped_raw.loc[
            (scoped_raw.index >= first_seen) & (scoped_raw.index <= last_seen)
        ]
        internal_missing_sessions += int(active.isna().sum())
        lag_sessions = int((coverage_dates > last_seen).sum())
        trailing_missing_sessions += lag_sessions
        pre_listing = int((coverage_dates < first_seen).sum())
        pre_listing_sessions += pre_listing
        window_returns = item["return"].reindex(coverage_dates)
        first_return = window_returns.first_valid_index()
        leading_unavailable = (
            len(coverage_dates)
            if first_return is None
            else int((coverage_dates < first_return).sum())
        )
        complete_window = len(coverage_dates) > 0 and not window_returns.isna().any()
        if complete_window:
            complete_window_members += 1
        elif leading_unavailable:
            short_history_members.append({
                "ticker": ticker,
                "first_observed_session": item.get("first_observed_session"),
                "leading_unavailable_sessions": leading_unavailable,
            })
        if lag_sessions:
            stale_members.append({
                "ticker": ticker,
                "last_observed_session": item.get("last_observed_session"),
                "lag_sessions": lag_sessions,
            })
    missing_member_sessions = internal_missing_sessions + trailing_missing_sessions
    current_session_members = len(prepared) - len(stale_members)
    coverage = {
        "declared_member_assignments": len(declared),
        "unique_members": len(unique),
        "priced_members": len(prepared),
        "current_session_members": current_session_members,
        "members_with_complete_window_history": complete_window_members,
        "unpriced_members": sorted(set(unique) - set(prepared)),
        "short_history_members": short_history_members,
        "stale_members": stale_members,
        "duplicate_members_removed": duplicate_count,
        "coverage_window_sessions": coverage_window_sessions,
        "pre_listing_member_sessions": pre_listing_sessions,
        "internal_missing_member_sessions": internal_missing_sessions,
        "trailing_missing_member_sessions": trailing_missing_sessions,
        "missing_member_sessions": missing_member_sessions,
    }
    node_reasons = [
        "DESCRIPTIVE_SHADOW_ONLY",
        "CURRENT_MEMBERSHIP_TECHNICAL_WINDOW_NOT_PIT",
        "CORPORATE_ACTION_BASIS_INHERITED_UNVERIFIED",
    ]
    if len(unique) < 3:
        node_reasons.append("SPARSE_GROUP")
    if len(prepared) < len(unique):
        node_reasons.append("PARTIAL_MEMBER_COVERAGE")
    if duplicate_count:
        node_reasons.append("DUPLICATE_MEMBERS_DEDUPED")
    if internal_missing_sessions:
        node_reasons.append("MISSING_MEMBER_SESSIONS")
    if short_history_members:
        node_reasons.append("SHORT_MEMBER_HISTORY")
    if stale_members:
        node_reasons.append("STALE_MEMBER_TAPE")
    recent_member_returns = member_returns.tail(max(windows) if windows else 60)
    if not recent_member_returns.empty and (recent_member_returns.abs() >= 0.5).any().any():
        node_reasons.append("EXTREME_SINGLE_SESSION_MOVE")

    windows_out: dict[str, dict] = {}
    available_windows = 0
    for n in windows:
        dates = return_sessions[-n:] if len(return_sessions) >= n else pd.DatetimeIndex([])
        group_ret = _compound_on_dates(group_returns, dates)
        market_ret = _compound_on_dates(market_returns, dates)
        parent_ret = _compound_on_dates(parent_returns, dates) if parent_returns is not None else None
        reasons: list[str] = []
        if group_ret is None or market_ret is None:
            reasons.append("INSUFFICIENT_HISTORY")
        else:
            available_windows += 1
        participation, participation_reasons = _window_participation(
            member_returns, dates, market_ret, parent_ret
        )
        reasons.extend(participation_reasons)
        rs_market = _relative_strength_summary(group_returns, market_returns, dates)
        rs_parent = _relative_strength_summary(group_returns, parent_returns, dates)
        windows_out[str(n)] = {
            "return_pct": _pct(group_ret),
            "market_return_pct": _pct(market_ret),
            "excess_vs_market_pct": (
                _pct(group_ret - market_ret) if group_ret is not None and market_ret is not None else None
            ),
            "parent_return_pct": _pct(parent_ret),
            "excess_vs_parent_pct": (
                _pct(group_ret - parent_ret) if group_ret is not None and parent_ret is not None else None
            ),
            "relative_strength": {
                "change_vs_market_pct": rs_market["change_pct"],
                "slope_vs_market_pct_per_session": rs_market["slope_pct_per_session"],
                "change_vs_parent_pct": rs_parent["change_pct"],
                "slope_vs_parent_pct_per_session": rs_parent["slope_pct_per_session"],
            },
            "participation": participation,
            "reason_codes": sorted(set(reasons)),
        }

    short_return = windows_out.get("5", {}).get("return_pct")
    long_return = windows_out.get("60", {}).get("return_pct")
    if short_return is not None and long_return is not None:
        if short_return > 0 and long_return < 0:
            node_reasons.append("SHORT_WINDOW_POSITIVE_LONG_WINDOW_NEGATIVE")
        elif short_return < 0 and long_return > 0:
            node_reasons.append("SHORT_WINDOW_NEGATIVE_LONG_WINDOW_POSITIVE")

    level = windows_out.get("20", {})
    level_excess = level.get("excess_vs_market_pct")
    level_state = (
        "UNAVAILABLE" if level_excess is None else
        "LEADING" if level_excess > 0 else
        "LAGGING" if level_excess < 0 else "NEUTRAL"
    )

    current_dates = return_sessions[-5:] if len(return_sessions) >= 5 else pd.DatetimeIndex([])
    prior_dates = return_sessions[-10:-5] if len(return_sessions) >= 10 else pd.DatetimeIndex([])
    current_group = _compound_on_dates(group_returns, current_dates)
    prior_group = _compound_on_dates(group_returns, prior_dates)
    current_market = _compound_on_dates(market_returns, current_dates)
    prior_market = _compound_on_dates(market_returns, prior_dates)
    current_parent = _compound_on_dates(parent_returns, current_dates) if parent_returns is not None else None
    prior_parent = _compound_on_dates(parent_returns, prior_dates) if parent_returns is not None else None
    current_excess = (
        current_group - current_market if current_group is not None and current_market is not None else None
    )
    prior_excess = (
        prior_group - prior_market if prior_group is not None and prior_market is not None else None
    )
    change = current_excess - prior_excess if current_excess is not None and prior_excess is not None else None
    acceleration_state = (
        "UNAVAILABLE" if change is None else
        "IMPROVING" if change > 0 else
        "DETERIORATING" if change < 0 else "STABLE"
    )
    parent_change = None
    if all(v is not None for v in (current_group, current_parent, prior_group, prior_parent)):
        parent_change = (current_group - current_parent) - (prior_group - prior_parent)

    persistence_dates = return_sessions[-10:] if len(return_sessions) >= 10 else pd.DatetimeIndex([])
    relative_daily = (group_returns - market_returns).reindex(persistence_dates).dropna()
    parent_relative_daily = (
        (group_returns - parent_returns).reindex(persistence_dates).dropna()
        if parent_returns is not None else pd.Series(dtype=float)
    )

    volume_reclaim = _volume_reclaim_evidence(prepared, return_sessions[-1]) if len(return_sessions) else {
        "members_with_volume": 0,
        "high_volume_positive_share": None,
        "members_with_20d_reclaim_evidence": 0,
        "above_20d_mean_share": None,
        "reclaimed_20d_mean_share": None,
    }
    if volume_reclaim["members_with_volume"] == 0:
        node_reasons.append("MISSING_VOLUME_EVIDENCE")

    return {
        "key": key,
        "name": name,
        "relationship_kind": relationship_kind,
        "status": (
            "UNAVAILABLE" if available_windows == 0 else
            "MEASURED" if (
                available_windows == len(windows)
                and len(prepared) == len(unique)
                and complete_window_members == len(prepared)
                and missing_member_sessions == 0
            ) else "PARTIAL"
        ),
        "coverage": coverage,
        "windows": windows_out,
        "strength_level": {
            "window_sessions": 20,
            "excess_vs_market_pct": level_excess,
            "state": level_state,
        },
        "acceleration": {
            "window_sessions": 5,
            "current_excess_vs_market_pct": _pct(current_excess),
            "prior_excess_vs_market_pct": _pct(prior_excess),
            "change_pct_points": _pct(change),
            "change_vs_parent_pct_points": _pct(parent_change),
            "state": acceleration_state,
        },
        "persistence": {
            "window_sessions": 10,
            "measured_sessions": int(len(relative_daily)),
            "positive_excess_session_share": (
                round(float((relative_daily > 0).mean()), 4) if len(relative_daily) else None
            ),
            "positive_vs_parent_session_share": (
                round(float((parent_relative_daily > 0).mean()), 4)
                if len(parent_relative_daily) else None
            ),
        },
        "volume_reclaim": volume_reclaim,
        "reason_codes": sorted(set(node_reasons)),
    }


def compute_closed_session_leadership(
    tree: Sequence[Mapping],
    member_bars: Mapping[str, object],
    market_bars: object,
    *,
    asof: str | None = None,
    parent_keys: set[str] | None = None,
    windows: Sequence[int] = CLOSED_SESSION_WINDOWS,
) -> dict:
    """Measure parent/subtheme leadership over explicitly completed daily sessions.

    This is a current-constituency technical observation, not a historical membership
    replay and not a forecast. The caller supplies the completed-session cutoff; bars
    after that date are excluded. Parent returns count each instrument once even when a
    ticker appears in several subthemes.
    """
    if isinstance(market_bars, pd.Series):
        market_frame = market_bars.to_frame("close")
    elif isinstance(market_bars, pd.DataFrame):
        market_frame = market_bars.copy()
    else:
        market_frame = pd.DataFrame()
    if "close" not in market_frame or market_frame["close"].dropna().empty:
        return {
            "schema": CLOSED_SESSION_LEADERSHIP_SCHEMA,
            "status": "UNAVAILABLE",
            "asof": None,
            "benchmark": "SPY",
            "windows_sessions": list(windows),
            "basis": {
                "bars": "COMPLETED_DAILY_SESSIONS_ONLY",
                "membership": "CURRENT_SOURCE_TREE_TECHNICAL_WINDOW",
                "membership_is_point_in_time": False,
                "corporate_action_basis": "OWNER_CLOSE_SERIES_UNVERIFIED",
            },
            "permissions": dict(CLOSED_SESSION_PERMISSIONS),
            "is_context_only": True,
            "is_forecast": False,
            "bar_status": "UNCONFIRMED",
            "themes": {},
            "reason_codes": ["MARKET_BENCHMARK_UNAVAILABLE"],
        }
    market_idx = pd.DatetimeIndex(market_frame.index)
    if market_idx.tz is not None:
        market_idx = market_idx.tz_localize(None)
    market_frame.index = market_idx.normalize()
    market_frame = market_frame[~market_frame.index.duplicated(keep="last")].sort_index()
    market_close = pd.to_numeric(market_frame["close"], errors="coerce").where(lambda x: x > 0)
    requested = pd.Timestamp(asof).normalize() if asof else market_close.dropna().index.max()
    market_close = market_close.loc[:requested].dropna()
    if market_close.empty:
        completed_asof = requested
        sessions = pd.DatetimeIndex([])
        market_returns = pd.Series(dtype=float)
    else:
        completed_asof = pd.Timestamp(market_close.index[-1]).normalize()
        sessions = pd.DatetimeIndex(market_close.index)
        market_returns = market_close.pct_change(fill_method=None)
    return_sessions = pd.DatetimeIndex(market_returns.dropna().index)

    wanted = set(parent_keys) if parent_keys is not None else None
    selected = [th for th in tree if wanted is None or str(th.get("theme") or th.get("key") or "") in wanted]
    needed = {
        str(t).strip().upper()
        for th in selected for sub in (th.get("subsectors") or [])
        for t in (sub.get("members") or []) if str(t).strip()
    }
    prepared_all = {}
    for ticker in sorted(needed):
        item = _normalise_daily_frame(member_bars.get(ticker), sessions, completed_asof)
        if item is not None:
            prepared_all[ticker] = item

    themes: dict[str, dict] = {}
    all_statuses: list[str] = []
    for th in selected:
        theme = str(th.get("theme") or th.get("key") or "").strip()
        if not theme:
            continue
        subs = list(th.get("subsectors") or [])
        declared_parent = [
            str(t).strip().upper() for sub in subs for t in (sub.get("members") or []) if str(t).strip()
        ]
        unique_parent = list(dict.fromkeys(declared_parent))
        parent_returns_frame = pd.DataFrame(
            {t: prepared_all[t]["return"] for t in unique_parent if t in prepared_all},
            index=return_sessions,
        )
        parent_returns = (
            parent_returns_frame.mean(axis=1, skipna=True).where(parent_returns_frame.notna().sum(axis=1) > 0)
            if len(parent_returns_frame.columns) else pd.Series(index=return_sessions, dtype=float)
        )
        parent = _leadership_node(
            key=theme, name=theme, relationship_kind="PARENT_SOURCE_GROUP",
            declared_members=declared_parent, prepared_all=prepared_all,
            market_returns=market_returns, return_sessions=return_sessions,
            parent_returns=None, windows=windows,
        )
        subthemes = []
        for sub in subs:
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            subthemes.append(_leadership_node(
                key=key, name=str(sub.get("name") or key),
                relationship_kind="SUBTHEME_SOURCE_GROUP",
                declared_members=sub.get("members") or [], prepared_all=prepared_all,
                market_returns=market_returns, return_sessions=return_sessions,
                parent_returns=parent_returns, windows=windows,
            ))
        statuses = [parent["status"], *[row["status"] for row in subthemes]]
        theme_status = (
            "UNAVAILABLE" if all(x == "UNAVAILABLE" for x in statuses) else
            "MEASURED" if all(x == "MEASURED" for x in statuses) else "PARTIAL"
        )
        all_statuses.append(theme_status)
        themes[theme] = {
            "schema": CLOSED_SESSION_LEADERSHIP_SCHEMA,
            "status": theme_status,
            "asof": completed_asof.date().isoformat() if len(sessions) else None,
            "parent": parent,
            "subthemes": subthemes,
            "reason_codes": ["DESCRIPTIVE_SHADOW_ONLY"],
            "is_context_only": True,
            "is_forecast": False,
            "bar_status": "CLOSED",
        }

    overall = (
        "UNAVAILABLE" if not themes or all(x == "UNAVAILABLE" for x in all_statuses) else
        "MEASURED" if all(x == "MEASURED" for x in all_statuses) else "PARTIAL"
    )
    return {
        "schema": CLOSED_SESSION_LEADERSHIP_SCHEMA,
        "status": overall,
        "asof": completed_asof.date().isoformat() if len(sessions) else None,
        "benchmark": "SPY",
        "windows_sessions": list(windows),
        "basis": {
            "bars": "COMPLETED_DAILY_SESSIONS_ONLY",
            "membership": "CURRENT_SOURCE_TREE_TECHNICAL_WINDOW",
            "membership_is_point_in_time": False,
            "parent_weighting": "EQUAL_WEIGHT_UNIQUE_INSTRUMENT_DAILY_REBALANCED",
            "subtheme_weighting": "EQUAL_WEIGHT_UNIQUE_INSTRUMENT_DAILY_REBALANCED",
            "corporate_action_basis": "OWNER_CLOSE_SERIES_UNVERIFIED",
        },
        "permissions": dict(CLOSED_SESSION_PERMISSIONS),
        "is_context_only": True,
        "is_forecast": False,
        "bar_status": "CLOSED",
        "themes": themes,
        "reason_codes": ["DESCRIPTIVE_SHADOW_ONLY"],
    }


def perf_from_close(close, asof: str | None = None) -> dict | None:
    """Finviz-convention horizon returns (PERCENT) from a daily close series — the feed
    for SYNTHETIC rotation nodes computed from local stores (Rotation Command RC-R4: the
    mega-cap generals cohort has no Finviz group, so its rotate-IN flows had no home in
    this taxonomy). Sessions for 1W/1M/3M/6M/1Y; calendar anchors for MTD/YTD (last close
    of the prior month/year). None when the series is too thin."""
    import pandas as pd
    s = close.dropna()
    if asof:
        s = s.loc[:asof]
    if len(s) < 260:
        return None
    last = float(s.iloc[-1])
    out: dict = {}
    for h, n in (("1D", 1), ("1W", 5), ("1M", 21), ("3M", 63), ("6M", 126), ("1Y", 252)):
        prev = float(s.iloc[-(n + 1)])
        out[h] = round((last / prev - 1.0) * 100.0, 2) if prev else None
    end = s.index[-1]
    for h, anchor in (("MTD", pd.Timestamp(end.year, end.month, 1)),
                      ("YTD", pd.Timestamp(end.year, 1, 1))):
        prior = s.loc[:anchor - pd.Timedelta(days=1)]
        out[h] = round((last / float(prior.iloc[-1]) - 1.0) * 100.0, 2) if len(prior) else None
    return out


def compute_rotation(
    tree: Sequence[Mapping],
    subsector_perf: Mapping[str, Mapping[str, float]],
    member_perf: Mapping[str, Mapping[str, float]] | None = None,
    *,
    generated_utc: str | None = None,
    asof: str | None = None,
    top_members: int = 8,
    history: Sequence[Mapping] | None = None,
) -> dict:
    """Assemble the subsector-rotation payload.

    Parameters
    ----------
    tree           : ``[{theme, subsectors:[{key,name,members:[...]}]}]`` — the
                     committed Finviz structure.
    subsector_perf : ``{subsector_key: {horizon: pct}}``.
    member_perf    : ``{ticker: {horizon: pct}}`` (optional, for member chips + breadth).
    history        : append-only PIT archive rows ``[{asof, subsectors:{key:{horizon:pct}}}]``
                     (optional). Supplied → the turn read gets realised volatility,
                     cross-session confirmation and rotation tails; absent → the turn read
                     runs on today alone and stays unconfirmable (``vol_cold``).
    """
    member_perf = member_perf or {}
    # flatten subsectors, attach theme; keep only those with a perf row.
    meta: dict[str, dict] = {}
    for th in tree:
        theme = str(th.get("theme") or th.get("key") or "").strip()
        for sub in th.get("subsectors", []):
            key = str(sub.get("key") or "").strip()
            if not key or key not in subsector_perf:
                continue
            members = [str(m).strip().upper() for m in (sub.get("members") or []) if str(m).strip()]
            meta[key] = {"name": str(sub.get("name") or key), "theme": theme, "members": members}

    sub_metrics = _rotation_metrics({k: subsector_perf[k] for k in meta})

    subsectors = []
    for key, m in meta.items():
        met = sub_metrics[key]
        # member chips: best/worst movers (1M) we have a quote for.
        mem_rows = []
        for t in m["members"]:
            mp = member_perf.get(t)
            if mp:
                mem_rows.append({"t": t, "1W": mp.get("1W"), "1M": mp.get("1M")})
        mem_rows.sort(key=lambda r: (r["1M"] if r["1M"] is not None else -1e9), reverse=True)
        subsectors.append({
            "key": key, "name": m["name"], "theme": m["theme"],
            "name_zh": _NAMES_ZH["subsectors"].get(m["name"], m["name"]),
            "theme_zh": _NAMES_ZH["themes"].get(m["theme"], m["theme"]),
            "n_members": len(m["members"]),
            "members": mem_rows[:top_members],
            **met,
        })
    subsectors.sort(key=lambda s: s["emerging_score"], reverse=True)
    for i, s in enumerate(subsectors):
        s["rank"] = i + 1

    # ── turn read (additive; incumbent fields above are untouched) ──
    sub_turn = attach_turn(
        subsectors, {k: subsector_perf[k] for k in meta},
        history=history, asof=asof,
        member_map={k: m["members"] for k, m in meta.items()},
        member_perf=member_perf)
    # Parallel fast ranking — a second ORDER over the same rows, never a re-sort of them.
    ranked_v2 = sorted(subsectors, key=lambda s: (s.get("rank_score_v2") or -1e9),
                       reverse=True)
    for i, s in enumerate(ranked_v2):
        s["rank_v2"] = i + 1

    # theme rollup: each theme = mean of its subsectors' perf per horizon.
    theme_keys = {}
    theme_perf: dict[str, dict[str, float]] = {}
    for th in tree:
        theme = str(th.get("theme") or "").strip()
        subs = [s["key"] for s in subsectors if s["theme"] == theme]
        if not subs:
            continue
        theme_keys[theme] = subs
        agg = {}
        for h in HORIZONS:
            vals = [subsector_perf[k].get(h) for k in subs
                    if subsector_perf[k].get(h) is not None and np.isfinite(subsector_perf[k].get(h))]
            agg[h] = float(np.mean(vals)) if vals else None
        theme_perf[theme] = agg
    theme_metrics = _rotation_metrics(theme_perf)
    themes = []
    sub_by_theme = {t: [s for s in subsectors if s["theme"] == t] for t in theme_keys}
    for theme, subs in theme_keys.items():
        met = theme_metrics[theme]
        ranked = sorted(sub_by_theme[theme], key=lambda s: s["emerging_score"], reverse=True)
        themes.append({
            "theme": theme, "theme_zh": _NAMES_ZH["themes"].get(theme, theme),
            "n_subs": len(subs),
            "top_sub": ranked[0]["name"] if ranked else None,
            "top_sub_zh": _NAMES_ZH["subsectors"].get(ranked[0]["name"], ranked[0]["name"]) if ranked else None,
            **met,
        })
    themes.sort(key=lambda t: t["emerging_score"], reverse=True)

    # Theme-level turn read: the archive is subsector-grain, so each historical day's theme
    # perf is re-aggregated the same way today's is (mean of member subsectors per horizon).
    for t in themes:
        t["n_members"] = t.get("n_subs") or 0      # the breadth floor reads n_members
    theme_hist = _theme_history(history, theme_keys) if history else None
    theme_turn = attach_turn(themes, theme_perf, key_of=lambda r: r["theme"],
                             history=theme_hist, asof=asof, min_members=1)
    ranked_t2 = sorted(themes, key=lambda t: (t.get("rank_score_v2") or -1e9), reverse=True)
    for i, t in enumerate(ranked_t2):
        t["rank_v2"] = i + 1

    # highlights — only sensible candidates per bucket. A breadth floor keeps the
    # actionable emerging/fading calls off 1-2-member "subsectors" (those are a
    # stock or two, not a rotation) — signal hygiene, not a fitted parameter.
    MIN_BREADTH = 3
    emerging = [s["key"] for s in subsectors
                if s["n_members"] >= MIN_BREADTH and s["rs_mom"] > 0
                and (s["accel"] is None or s["accel"] >= 0)][:12]
    fading = [s["key"] for s in sorted(subsectors, key=lambda s: s["rs_mom"])
              if s["n_members"] >= MIN_BREADTH and s["rs_ratio"] > 0 and s["rs_mom"] < 0][:12]
    leaders = [s["key"] for s in sorted(subsectors, key=lambda s: s["rs_ratio"], reverse=True)][:12]
    laggards = [s["key"] for s in sorted(subsectors, key=lambda s: s["rs_ratio"])][:12]

    return {
        "asof": asof or "",
        "generated_utc": generated_utc or "",
        "source": "finviz-themes",
        "timeframes": HORIZONS,
        "mom_horizons": MOM_HORIZONS,
        "subsectors": subsectors,
        "themes": themes,
        "highlights": {"emerging": emerging, "fading": fading, "leaders": leaders, "laggards": laggards},
        "n_subsectors": len(subsectors),
        "n_themes": len(themes),
        # Turn read — buckets keyed on confirmed cycle turns rather than on the incumbent
        # score. Additive: `highlights` above is unchanged, so every consumer of the old
        # contract keeps working while the desk leads with the faster read.
        "turn": sub_turn,
        "turn_themes": theme_turn,
    }


def _theme_history(history: Sequence[Mapping] | None,
                   theme_keys: Mapping[str, Sequence[str]]) -> list[dict]:
    """Re-aggregate the subsector-grain archive into theme-grain rows, one per session.

    Uses the same rule as today's rollup (mean of the theme's subsectors at each horizon)
    so a theme's history is measured exactly like its present. Membership comes from
    TODAY's tree for every historical day — the tree is versioned separately in
    ``tree_history.jsonl`` and re-deriving past membership is a different job; the effect is
    that a theme which gained a subsector last week has that subsector in its back-history
    too. Disclosed rather than silently assumed.
    """
    out: list[dict] = []
    for row in history or ():
        subs = row.get("subsectors") or {}
        if not subs:
            continue
        agg: dict[str, dict] = {}
        for theme, keys in theme_keys.items():
            per_h: dict[str, float] = {}
            for h in HORIZONS:
                vals = [v for k in keys
                        if (p := subs.get(k)) and (v := p.get(h)) is not None
                        and np.isfinite(v)]
                if vals:
                    per_h[h] = float(np.mean(vals))
            if per_h:
                agg[theme] = per_h
        if agg:
            out.append({"asof": row.get("asof"), "subsectors": agg})
    return out


# ── Sector ETF cross-section ─────────────────────────────────────────────────

# 11 SPDR sector ETFs with display metadata.
SECTOR_ETFS = [
    ("XLB",  "Materials",          "材料"),
    ("XLC",  "Comm Services",      "通信"),
    ("XLE",  "Energy",             "能源"),
    ("XLF",  "Financials",         "金融"),
    ("XLI",  "Industrials",        "工业"),
    ("XLK",  "Technology",         "科技"),
    ("XLP",  "Cons Staples",       "必需消费"),
    ("XLRE", "Real Estate",        "房地产"),
    ("XLU",  "Utilities",          "公用事业"),
    ("XLV",  "Health Care",        "医疗保健"),
    ("XLY",  "Cons Discretionary", "可选消费"),
]

# Row-count offsets for rolling return horizons (approximate trading days).
# MTD/YTD use calendar anchors instead.
_ROW_OFFSETS: dict[str, int] = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "1Y": 252,
}


def _pct_return(close_series, n_rows: int) -> float | None:
    """Return (last / prior - 1)*100 using row offset; None if history too short."""
    if len(close_series) <= n_rows:
        return None
    prior = close_series.iloc[-(n_rows + 1)]
    last = close_series.iloc[-1]
    if prior is None or prior != prior or prior == 0:  # NaN or zero guard
        return None
    return float((last / prior - 1) * 100)


def _pct_return_to_date(close_series, anchor_date) -> float | None:
    """Return % change from the last close ON or BEFORE anchor_date to the latest close."""
    try:
        import pandas as pd
        candidates = close_series[close_series.index <= pd.Timestamp(anchor_date)]
        if candidates.empty:
            return None
        prior = float(candidates.iloc[-1])
        last = float(close_series.iloc[-1])
        if prior == 0:
            return None
        return (last / prior - 1) * 100
    except Exception:  # noqa: BLE001
        return None


def compute_sector_etf_perf(yahoo_dir: Path) -> dict[str, dict[str, float | None]]:
    """Load all 11 SPDR parquets and compute the same HORIZONS returns used by
    the subsector pipeline.  Returns ``{ticker: {horizon: pct}}``.

    Any horizon that cannot be computed is left as ``None`` — the downstream
    ``_rotation_metrics`` call degrades gracefully on nulls.
    """
    try:
        import pandas as pd
    except ImportError:
        log.error("pandas not available — sector ETF perf skipped")
        return {}

    result: dict[str, dict[str, float | None]] = {}
    for ticker, _name, _zh in SECTOR_ETFS:
        path = yahoo_dir / f"{ticker}.parquet"
        if not path.exists():
            log.warning("sector ETF parquet missing: %s", path)
            result[ticker] = {h: None for h in HORIZONS}
            continue
        try:
            df = pd.read_parquet(path, columns=["close"])
            closes = df["close"].sort_index().dropna()
            if closes.empty:
                result[ticker] = {h: None for h in HORIZONS}
                continue
            last_date = closes.index[-1]
            perfs: dict[str, float | None] = {}
            # Rolling horizons from row offsets
            for h, n in _ROW_OFFSETS.items():
                perfs[h] = _pct_return(closes, n)
            # MTD: from last trading day of prior month (i.e. closes on/before the
            # 1st calendar day of last_date's month minus 1 day).
            month_start = last_date.replace(day=1)
            import datetime as _dt
            prior_month_end = month_start - _dt.timedelta(days=1)
            perfs["MTD"] = _pct_return_to_date(closes, prior_month_end)
            # YTD: from last trading day of prior year
            year_start = last_date.replace(month=1, day=1)
            prior_year_end = year_start - _dt.timedelta(days=1)
            perfs["YTD"] = _pct_return_to_date(closes, prior_year_end)
            result[ticker] = perfs
        except Exception as exc:  # noqa: BLE001
            log.warning("sector ETF perf error for %s: %s", ticker, exc)
            result[ticker] = {h: None for h in HORIZONS}
    return result


def build_sectors_array(metrics: dict[str, dict]) -> list[dict]:
    """Turn ``_rotation_metrics`` output into the sectors contract array.

    Contract shape per item (mirrors subsector fields that the frontend reads):
    ``key, name, name_zh, theme, theme_zh, quadrant, rs_ratio, rs_mom, accel,
    emerging_score, perf, rs``
    """
    name_map = {t: (n, zh) for t, n, zh in SECTOR_ETFS}
    sectors = []
    for ticker, met in metrics.items():
        en_name, zh_name = name_map.get(ticker, (ticker, ticker))
        # Restrict perf to the horizons the contract specifies (1D/1W/1M/3M/6M/1Y)
        perf_full = met.get("perf") or {}
        perf_out = {h: perf_full.get(h) for h in ["1D", "1W", "1M", "3M", "6M", "1Y"]}
        rs_full = met.get("rs") or {}
        rs_out = {h: rs_full.get(h) for h in ["1W", "1M", "3M", "6M", "1Y"]}
        sectors.append({
            "key": ticker,
            "name": en_name,
            "name_zh": zh_name,
            "theme": "Sector ETFs",
            "theme_zh": "行业ETF",
            "quadrant": met.get("quadrant", "lagging"),
            "rs_ratio": met.get("rs_ratio"),
            "rs_mom": met.get("rs_mom"),
            "accel": met.get("accel"),
            "emerging_score": met.get("emerging_score"),
            "perf": perf_out,
            "rs": rs_out,
        })
    sectors.sort(key=lambda s: (s["emerging_score"] or 0), reverse=True)
    return sectors
