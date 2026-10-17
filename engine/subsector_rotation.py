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
  breadth, and a parallel fast rank. The existing formula is retained for complete comparable inputs; incomplete
  legacy axes are explicitly unmeasured rather than zero-filled. The two reads
  are logged side by side and graded head-to-head by
  ``engine/subsector_track_record.py``.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

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


def _rotation_number(value) -> float | None:
    """Finite numeric feed value; booleans and numeric-looking strings are not data."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, float, np.integer, np.floating)):
        return None
    try:
        value = float(value)
        return value if np.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None

def _rotation_perf(row) -> dict:
    row = row if isinstance(row, Mapping) else {}
    return {h: _rotation_number(row.get(h)) for h in HORIZONS}

def _rotation_sort(row: Mapping, field: str = 'emerging_score') -> float:
    value = _rotation_number(row.get(field))
    return value if value is not None else float('-inf')

def _zscore(values: dict[str, float]) -> dict[str, float | None]:
    """Comparable numeric peers only; unavailable values never become zero."""
    clean = {k: _rotation_number(v) for k, v in values.items()}
    keys = [k for k, v in clean.items() if v is not None]
    empty = dict.fromkeys(values, None)
    if len(keys) < 2:
        return empty
    arr = np.array([clean[k] for k in keys], dtype=float)
    with np.errstate(over='ignore', invalid='ignore'):
        mu, sd = float(arr.mean()), float(arr.std())
    if not np.isfinite(mu) or not np.isfinite(sd):
        return empty
    if sd <= 1e-9:
        # A known cross-sectional tie is zero deviation; missing values stay absent.
        return {k: 0.0 if clean[k] is not None else None for k in values}
    return {k: _rotation_number((clean[k] - mu) / sd) if clean[k] is not None else None
            for k in values}


def _nanmean(*xs: float | None) -> float | None:
    vals = [x for x in xs if x is not None and np.isfinite(x)]
    return float(np.mean(vals)) if vals else None


def _quadrant(rs_ratio: float | None, rs_mom: float | None) -> str:
    if _rotation_number(rs_ratio) is None or _rotation_number(rs_mom) is None:
        return 'unavailable'
    if rs_ratio == 0 and rs_mom == 0:
        return 'neutral'
    if rs_ratio >= 0:
        return 'leading' if rs_mom >= 0 else 'weakening'
    return 'improving' if rs_mom >= 0 else 'lagging'


def _rotation_metrics(perf_by_key: Mapping[str, Mapping[str, float]]) -> dict[str, dict]:
    """Legacy formula on one comparable cohort; incomplete rows stay unmeasured.

    The four horizons used by the two axes must be available together. This
    prevents different peer populations at each horizon masquerading as momentum.
    Full finite comparable inputs retain the existing arithmetic and weights.
    """
    required = ('1W', '1M', '3M', '6M')
    clean = {k: _rotation_perf(row) for k, row in perf_by_key.items()}
    keys = list(clean)
    peers = [k for k in keys if all(clean[k][h] is not None for h in required)]
    peer_set = set(peers)
    median = {}
    for h in HORIZONS:
        values = [clean[k][h] for k in peers if clean[k][h] is not None]
        with np.errstate(over='ignore', invalid='ignore'):
            median[h] = _rotation_number(np.median(values)) if values else None
    rs = {k: {h: (_rotation_number(clean[k][h] - median[h])
                  if clean[k][h] is not None and median[h] is not None else None)
              for h in HORIZONS} for k in keys}
    zrs = {h: _zscore({k: rs[k][h] if k in peer_set else None for k in keys})
           for h in HORIZONS}
    accel = {k: (_rotation_number(clean[k]['1W'] - clean[k]['3M'] / WEEKS['3M'])
                 if clean[k]['1W'] is not None and clean[k]['3M'] is not None else None)
             for k in keys}
    z_accel = _zscore({k: accel[k] if k in peer_set else None for k in keys})
    out = {}
    for k in keys:
        missing = [h for h in required if clean[k][h] is None]
        ratio = momentum = score = None
        reason = ('missing_required_horizons' if missing else
                  'insufficient_comparable_groups' if len(peers) < 2 else None)
        zs = [zrs[h][k] for h in required]
        if reason is None and all(v is not None for v in zs) and z_accel[k] is not None:
            ratio = _rotation_number((zs[1] + zs[2]) / 2)
            momentum = _rotation_number((zs[0] + zs[1]) / 2 - (zs[2] + zs[3]) / 2)
            if ratio is not None and momentum is not None:
                score = _rotation_number(.5 * z_accel[k] + .8 * momentum + .3 * zs[0])
        if reason is None and score is None:
            reason = 'nonfinite_derived_metric'
        if reason is not None:
            ratio = momentum = score = None
        def rounded(value, precision=3):
            return round(value, precision) if value is not None else None
        out[k] = {
            'perf': {h: rounded(clean[k][h], 2) for h in HORIZONS},
            'rs': {h: rounded(rs[k][h], 2) for h in MOM_HORIZONS},
            'rs_ratio': rounded(ratio), 'rs_mom': rounded(momentum),
            'accel': rounded(accel[k]), 'z_accel': rounded(z_accel[k]) if reason is None else None,
            'quadrant': _quadrant(ratio, momentum), 'emerging_score': rounded(score),
            'rotation_status': 'MEASURED' if reason is None else 'UNAVAILABLE',
            'rotation_reason': reason, 'rotation_missing_horizons': missing,
            'rotation_comparison_groups': len(peers),
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
    member_perf = {t: _rotation_perf(row) for t, row in (member_perf or {}).items()}
    subsector_perf = {k: _rotation_perf(row) for k, row in subsector_perf.items()}
    # Flatten expected subsectors; absent performance remains visible and unmeasured.
    meta: dict[str, dict] = {}
    for th in tree:
        theme = str(th.get("theme") or th.get("key") or "").strip()
        for sub in th.get("subsectors", []):
            key = str(sub.get("key") or "").strip()
            if not key:
                continue
            subsector_perf.setdefault(key, _rotation_perf(None))
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
    subsectors.sort(key=_rotation_sort, reverse=True)
    for i, s in enumerate(subsectors):
        s["rank"] = i + 1 if s["emerging_score"] is not None else None

    # ── turn read (additive; incumbent fields above are untouched) ──
    sub_turn = attach_turn(
        subsectors, {k: subsector_perf[k] for k in meta},
        history=history, asof=asof,
        member_map={k: m["members"] for k, m in meta.items()},
        member_perf=member_perf)
    # Parallel fast ranking — a second ORDER over the same rows, never a re-sort of them.
    ranked_v2 = sorted(subsectors, key=lambda s: _rotation_sort(s, "rank_score_v2"),
                       reverse=True)
    for i, s in enumerate(ranked_v2):
        s["rank_v2"] = i + 1 if _rotation_number(s.get("rank_score_v2")) is not None else None

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
        ranked = sorted((s for s in sub_by_theme[theme] if s["emerging_score"] is not None),
                        key=_rotation_sort, reverse=True)
        themes.append({
            "theme": theme, "theme_zh": _NAMES_ZH["themes"].get(theme, theme),
            "n_subs": len(subs),
            "top_sub": ranked[0]["name"] if ranked else None,
            "top_sub_zh": _NAMES_ZH["subsectors"].get(ranked[0]["name"], ranked[0]["name"]) if ranked else None,
            **met,
        })
    themes.sort(key=_rotation_sort, reverse=True)

    # Theme-level turn read: the archive is subsector-grain, so each historical day's theme
    # perf is re-aggregated the same way today's is (mean of member subsectors per horizon).
    for t in themes:
        t["n_members"] = t.get("n_subs") or 0      # the breadth floor reads n_members
    theme_hist = _theme_history(history, theme_keys) if history else None
    theme_turn = attach_turn(themes, theme_perf, key_of=lambda r: r["theme"],
                             history=theme_hist, asof=asof, min_members=1)
    ranked_t2 = sorted(themes, key=lambda t: _rotation_sort(t, "rank_score_v2"), reverse=True)
    for i, t in enumerate(ranked_t2):
        t["rank_v2"] = i + 1 if _rotation_number(t.get("rank_score_v2")) is not None else None

    # highlights — only sensible candidates per bucket. A breadth floor keeps the
    # actionable emerging/fading calls off 1-2-member "subsectors" (those are a
    # stock or two, not a rotation) — signal hygiene, not a fitted parameter.
    MIN_BREADTH = 3
    eligible = [s for s in subsectors if s['rotation_status'] == 'MEASURED']
    emerging = [s['key'] for s in eligible
                if s['n_members'] >= MIN_BREADTH and s['rs_mom'] > 0
                and s['accel'] is not None and s['accel'] >= 0][:12]
    fading = [s['key'] for s in sorted(eligible, key=lambda s: s['rs_mom'])
              if s['n_members'] >= MIN_BREADTH and s['rs_ratio'] > 0 and s['rs_mom'] < 0][:12]
    leaders = [s['key'] for s in sorted(eligible, key=lambda s: s['rs_ratio'], reverse=True)
               if s['rs_ratio'] > 0][:12]
    laggards = [s['key'] for s in sorted(eligible, key=lambda s: s['rs_ratio'])
                if s['rs_ratio'] < 0][:12]

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
            "quadrant": met.get("quadrant", "unavailable"),
            **{field: met.get(field) for field in ("rotation_status", "rotation_reason",
              "rotation_missing_horizons", "rotation_comparison_groups")},
            "rs_ratio": met.get("rs_ratio"),
            "rs_mom": met.get("rs_mom"),
            "accel": met.get("accel"),
            "emerging_score": met.get("emerging_score"),
            "perf": perf_out,
            "rs": rs_out,
        })
    sectors.sort(key=_rotation_sort, reverse=True)
    return sectors
