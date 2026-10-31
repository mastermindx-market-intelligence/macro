"""Build the Forex Vector dashboard -> site/forex.html.

Standalone like build_commodities.py (shares only the parquet store + theme
assets). Recomputes the forex signal engine every build for daily freshness, reads
the calibration verdicts (data/forex/conviction_calibration.json) when present,
builds a broad-dollar master view-model + per-pair risk-context view-models, renders
light-theme Plotly charts, fills templates/forex.html.j2, and writes
data/forex/latest.json for the hub card.

DOLLAR-FIRST: a broad-dollar master tile (dollar-smile regime) sits above the
board; each pair's signals are scored on the dollar-orthogonalized residual, and
the verdict headline is RISK-CONTEXT (LONG/SHORT-base secondary). Returns 0 on any
engine error so it can never break the rest of the site.

Usage: python -m scripts.build_forex
"""
from __future__ import annotations

import json
import hashlib
import math
import numbers
import logging
import sys
from datetime import datetime, timezone
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import config, store  # noqa: E402
from lib.pages import write_page  # noqa: E402
from lib.forex_kinematics_view import project_kinematics  # noqa: E402
from lib.forex_r26_consumer import project_r26_consumer  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("build_forex")

# shared Glassnode light palette (same as build_commodities for a consistent product)
C = {
    "blue": "#285FFF", "indigo": "#4559DC",
    "r1": "#E2E7FC", "r2": "#B8C6FA", "r3": "#8FA5F6", "r4": "#6888FB", "r5": "#285FFF",
    "ink": "#0B1733", "text": "#344054", "muted": "#4C5A6C", "faint": "#5F6A7A",
    "red": "#D30B0B", "redfill": "#FEB5B5", "amber": "#F5AD42", "green": "#1a7f43",
    "grid": "#EAECF0", "card": "#FFFFFF", "bg": "#F7F8FA", "gold": "#C8A53B",
}
PLOT = dict(
    template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font={"size": 11, "color": C["text"], "family": "Inter, sans-serif"},
    margin={"l": 48, "r": 52, "t": 10, "b": 28},
    legend={"orientation": "h", "y": 1.14, "x": 0},
    xaxis={"gridcolor": C["grid"], "zeroline": False},
    yaxis={"gridcolor": C["grid"], "zeroline": False},
)

# M5: single source for dollar flash threshold (abs(z) >= 2.0)
# Used by dollar_vm hero badge, dollar_day_block.flag, and dollar_flash_events.
# Do NOT change the config dollar_day_z key — it drives conviction confidence haircut.
FLASH_Z = 2.0

# m5: smile arc x-position map (regime → 0..1) — moved from template to Python so
# tests can validate the real constants, not a local copy in the test.
SMILE_X: dict[str, float] = {
    "US growth premium": 0.13,
    "US-specific stress": 0.34,
    "Global reflation": 0.50,
    "Neutral": 0.50,
    "Risk-off haven bid": 0.87,
}

# m5: trend n_up → plain label map (moved from template if/elif chain to Python dict)
TREND_LABEL_EN: dict[int, str] = {
    4: "Rising on all horizons",
    3: "Mostly rising",
    2: "Mixed",
    1: "Mostly falling",
    0: "Falling on all horizons",
}
TREND_LABEL_ZH: dict[int, str] = {
    4: "全线上行",
    3: "大多上行",
    2: "涨跌互现",
    1: "大多下行",
    0: "全线下行",
}

# per-pair display metadata (label, zh, base, quote, archetype label, color)
META = {
    "EURUSD": {"label": "EUR/USD", "zh": "欧元/美元", "base": "EUR", "quote": "USD",
               "arch": ("Major", "主要货币"), "color": "#285FFF"},
    "USDJPY": {"label": "USD/JPY", "zh": "美元/日元", "base": "JPY", "quote": "USD",
               "arch": ("Haven-funder", "避险/融资货币"), "color": "#D30B0B"},
    "GBPUSD": {"label": "GBP/USD", "zh": "英镑/美元", "base": "GBP", "quote": "USD",
               "arch": ("Major", "主要货币"), "color": "#4559DC"},
    "AUDUSD": {"label": "AUD/USD", "zh": "澳元/美元", "base": "AUD", "quote": "USD",
               "arch": ("Commodity-dollar", "商品货币"), "color": "#1a7f43"},
    "USDCAD": {"label": "USD/CAD", "zh": "美元/加元", "base": "CAD", "quote": "USD",
               "arch": ("Commodity-dollar", "商品货币"), "color": "#B5651D"},
    "USDCHF": {"label": "USD/CHF", "zh": "美元/瑞郎", "base": "CHF", "quote": "USD",
               "arch": ("Haven-funder", "避险/融资货币"), "color": "#9AA4B2"},
    "USDMXN": {"label": "USD/MXN", "zh": "美元/墨西哥比索", "base": "MXN", "quote": "USD",
               "arch": ("EM", "新兴市场"), "color": "#C8A53B"},
    "USDBRL": {"label": "USD/BRL", "zh": "美元/巴西雷亚尔", "base": "BRL", "quote": "USD",
               "arch": ("EM", "新兴市场"), "color": "#1F8A70"},
    "USDCNH": {"label": "USD/CNH", "zh": "美元/离岸人民币", "base": "CNH", "quote": "USD",
               "arch": ("EM · managed", "新兴市场·受管理"), "color": "#D85A30"},
}

# dollar-smile regime -> color + favored-currency strip (en/zh)
REGIME_COLOR = {
    "Risk-off haven bid": C["red"], "US growth premium": C["blue"],
    "Global reflation": C["green"], "US-specific stress": C["amber"], "Neutral": C["ink"],
}
REGIME_ZH = {
    "Risk-off haven bid": "全球避险", "US growth premium": "美国强势",
    "Global reflation": "平静增长", "US-specific stress": "美国走弱",
    "Neutral": "中间地带",
}
# Plain zone words per regime (for "Why the dollar is here:" line — P2)
REGIME_ZONE_EN = {
    "Risk-off haven bid": "World stressed",
    "US growth premium": "US booming",
    "Global reflation": "Calm growth",
    "US-specific stress": "US wobble",
    "Neutral": "In between",
}
REGIME_ZONE_ZH = {
    "Risk-off haven bid": "全球避险",
    "US growth premium": "美国强势",
    "Global reflation": "平静增长",
    "US-specific stress": "美国走弱",
    "Neutral": "中间地带",
}
FAVORED = {
    "Risk-off haven bid": (["USD", "JPY", "CHF"], ["美元", "日元", "瑞郎"]),
    "US growth premium": (["USD"], ["美元"]),
    "Global reflation": (["AUD", "commodity FX", "EM"], ["澳元", "商品货币", "新兴市场"]),
    "US-specific stress": (["EUR", "JPY", "gold"], ["欧元", "日元", "黄金"]),
    "Neutral": ([], []),
}


def _html(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displayModeBar": False, "responsive": True})


def _r(v, n=2):
    return round(float(v), n) if v is not None and pd.notna(v) else None


# --------------------------------------------------------------------------- #
# F2 — inline SVG sparkline helper
# --------------------------------------------------------------------------- #
def _spark_pts(values, w: int, h: int, n: int = 126) -> str:
    """Convert an iterable of floats to an SVG polyline points string.

    Takes the tail `n` values, drops NaN, min-max normalises into the
    viewBox (w × h) with 2px top/bottom padding, returns "x1,y1 x2,y2 …"
    with 1-decimal coords.  Returns "" when fewer than 2 finite points.
    """
    try:
        s = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
        s = s.tail(n)
        if len(s) < 2:
            return ""
        lo, hi = float(s.min()), float(s.max())
        pad = 2
        h_inner = h - 2 * pad
        pts = []
        n_pts = len(s)
        for i, v in enumerate(s):
            x = round(i / (n_pts - 1) * w, 1)
            if hi == lo:
                y = round(pad + h_inner / 2, 1)
            else:
                y = round(pad + (1.0 - (float(v) - lo) / (hi - lo)) * h_inner, 1)
            pts.append(f"{x},{y}")
        return " ".join(pts)
    except Exception:  # noqa: BLE001
        return ""


def _window_segments(values, w: int, h: int) -> list[str]:
    """SVG polyline segment strings over FIXED window slots (hero sparkline only).

    Unlike _spark_pts — which drops NaN and re-spreads the survivors — the input
    is an already-aligned window: every slot keeps its own x-position and each
    run of consecutive finite values becomes its OWN polyline, so a line breaks
    across a gap instead of bridging it.  Missing / non-finite slots stay
    missing; a 1-value run returns a 1-point segment the template draws as a
    dot.  y uses _spark_pts's min-max viewbox, over this window's finite values.
    """
    try:
        s = pd.to_numeric(pd.Series(list(values)), errors="coerce").astype(float)
        s = s.where(np.isfinite(s))
        if s.empty or not s.notna().any():
            return []
        lo, hi = float(s.min()), float(s.max())
        pad = 2
        h_inner = h - 2 * pad
        denom = max(len(s) - 1, 1)
        segs: list[str] = []
        run: list[str] = []

        def _xy(i: int, v: float) -> str:
            x = round(i / denom * w, 1)
            y = (round(pad + h_inner / 2, 1) if hi == lo else
                 round(pad + (1.0 - (v - lo) / (hi - lo)) * h_inner, 1))
            return f"{x},{y}"

        for i, v in enumerate(s):
            if pd.isna(v):
                if run:
                    segs.append(" ".join(run))
                    run = []
            else:
                run.append(_xy(i, float(v)))
        if run:
            segs.append(" ".join(run))
        return segs
    except Exception:  # noqa: BLE001
        return []


def _tail_years(df: pd.DataFrame, years: float) -> pd.DataFrame:
    cutoff = df.index.max() - pd.Timedelta(days=int(365 * years))
    return df.loc[df.index >= cutoff]


# --- plotly weight helpers (mirror scripts/build_vector.py) ---------------- #
def _plot_idx(index, daily_days: int = 400, weekly_days: int = 1825,
              weekly_step: int = 7, monthly_step: int = 30):
    """Resolution-adaptive index for the heavy full-history overlay charts: daily
    for the last ~400d, ~weekly out to 5y, ~monthly before that. Older points are
    sub-pixel at 5Y/All zoom and the recent window stays full daily, so the line
    is visually identical at every zoom — but ~5x fewer points get serialized
    (plotly emits one full date-string + value array PER trace)."""
    if len(index) == 0:
        return index
    end = index.max()
    d0 = end - pd.Timedelta(days=daily_days)
    w0 = end - pd.Timedelta(days=weekly_days)
    daily = index[index >= d0]
    weekly = index[(index < d0) & (index >= w0)][::weekly_step]
    monthly = index[index < w0][::monthly_step]
    return monthly.union(weekly).union(daily)


def _plot_y(s: pd.Series, n: int):
    """Round a y-series to n places and return a plain Python list (NaN -> null).
    plotly base64-packs numpy float64 arrays at a fixed ~10.7 chars/point whatever
    the value; a rounded text list is smaller and shrinks with fewer decimals.
    n<=0 emits ints."""
    if n <= 0:
        return [None if pd.isna(v) else int(round(float(v))) for v in s]
    return [None if pd.isna(v) else round(float(v), n) for v in s]


def _dx(index):
    """Date-only x strings ('2015-08-17') for a daily DatetimeIndex — plotly's
    default datetime serialization emits the full '...T00:00:00.000' per point PER
    trace, so date strings ~halve every x array while still rendering on a normal
    plotly date axis."""
    return [t.strftime("%Y-%m-%d") for t in index]


def _pdec(s) -> int:
    """Decimals giving a price series ~5 significant figures regardless of
    magnitude (EUR/USD ~1.08 -> 4dp, USD/JPY ~150 -> 2dp)."""
    a = np.abs(pd.Series(s).to_numpy(dtype="float64"))
    a = a[np.isfinite(a) & (a > 0)]
    if a.size == 0:
        return 2
    return max(0, 4 - int(np.floor(np.log10(float(np.median(a))))))


# --------------------------------------------------------------------------- #
# charts
# --------------------------------------------------------------------------- #
def chart_pair(df: pd.DataFrame, pair: str, years: float = 6) -> str:
    """Quote price + dollar-orthogonalized residual index (rebased) + risk index."""
    d = _tail_years(df, years)
    meta = META[pair]
    invert = config.load()["forex"]["assets"][pair].get("invert")
    quote = (1.0 / d["close"]) if invert else d["close"]      # show the market quote (USD/JPY etc.)
    # downsample only the heavy full-history line traces; the sparse shock markers
    # below stay full-resolution and exact.
    pidx = _plot_idx(d.index)
    px = _dx(pidx)
    qdec = _pdec(quote)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=px, y=_plot_y(quote.reindex(pidx), qdec), name=meta["label"],
                             line={"color": meta["color"], "width": 1.8}, yaxis="y"))
    if "resid_close" in d:
        rb = 100 * d["resid_close"] / d["resid_close"].iloc[0]
        fig.add_trace(go.Scatter(x=px, y=_plot_y(rb.reindex(pidx), 2), name="Idiosyncratic (ex-$)",
                                 line={"color": C["indigo"], "width": 1.2, "dash": "dot"}, yaxis="y2",
                                 hovertemplate="ex-$ %{y:.0f}<extra></extra>"))
    if "shock_state" in d:
        for state, col, sym in (("exogenous_bid", C["blue"], "triangle-up"),
                                ("exogenous_pressure", C["red"], "triangle-down")):
            m = d[d["shock_state"] == state]
            if len(m):
                my = (1.0 / m["close"]) if invert else m["close"]
                fig.add_trace(go.Scatter(x=_dx(m.index), y=_plot_y(my, qdec),
                                         mode="markers", name=state.replace("_", " "),
                                         marker={"color": col, "size": 5, "symbol": sym}, yaxis="y"))
    fig.update_layout(**{**PLOT, "height": 290,
                         "yaxis": {"gridcolor": C["grid"], "title": meta["label"]},
                         "yaxis2": {"overlaying": "y", "side": "right", "showgrid": False,
                                    "title": "ex-$ idx"}})
    return _html(fig)


def chart_dollar(dol: pd.DataFrame, years: float = 8) -> str:
    """Broad dollar + DXY (rebased) and the risk-off composite (right axis)."""
    d = _tail_years(dol, years)
    fig = go.Figure()
    for col, name, color in (("broad", "Broad USD", C["indigo"]), ("dxy", "DXY", C["blue"])):
        s = d[col].dropna()
        if len(s):
            rb = 100 * s / s.iloc[0]
            pidx = _plot_idx(s.index)
            fig.add_trace(go.Scatter(x=_dx(pidx), y=_plot_y(rb.reindex(pidx), 2), name=name,
                                     line={"color": color, "width": 1.8}))
    if "risk_off" in d:
        pidx = _plot_idx(d.index)
        fig.add_trace(go.Scatter(x=_dx(pidx), y=_plot_y(d["risk_off"].reindex(pidx), 3), name="Risk-off",
                                 line={"color": C["red"], "width": 0}, fill="tozeroy",
                                 fillcolor="rgba(211,11,11,0.07)", yaxis="y2",
                                 hovertemplate="risk-off %{y:.2f}<extra></extra>"))
    fig.update_layout(**{**PLOT, "height": 300,
                         "yaxis": {"title": "Rebased = 100", "gridcolor": C["grid"]},
                         "yaxis2": {"overlaying": "y", "side": "right", "range": [-1, 1],
                                    "showgrid": False, "title": "risk-off"}})
    return _html(fig)


def chart_real_rate(drivers: dict, years: float = 9) -> str:
    """Broad USD (rebased) vs the US 10y real yield — the dollar's structural anchor."""
    broad = drivers.get("broad_dollar")
    real = drivers.get("us10y_real")
    if broad is None or real is None:
        return ""
    cut = max(broad.index.max(), real.index.max()) - pd.Timedelta(days=int(365 * years))
    b = broad[broad.index >= cut].dropna()
    r = real[real.index >= cut].dropna()
    if b.empty or r.empty:
        return ""
    fig = go.Figure()
    rb = 100 * b / b.iloc[0]
    pidx = _plot_idx(b.index)
    fig.add_trace(go.Scatter(x=_dx(pidx), y=_plot_y(rb.reindex(pidx), 2), name="Broad USD",
                             line={"color": C["indigo"], "width": 1.8}))
    pidx2 = _plot_idx(r.index)
    fig.add_trace(go.Scatter(x=_dx(pidx2), y=_plot_y(r.reindex(pidx2), 2), name="US 10y real yield",
                             line={"color": C["blue"], "width": 1.6}, yaxis="y2",
                             hovertemplate="real %{y:.2f}%<extra></extra>"))
    fig.update_layout(**{**PLOT, "height": 270,
                         "yaxis": {"title": "Broad USD = 100", "gridcolor": C["grid"]},
                         "yaxis2": {"overlaying": "y", "side": "right", "showgrid": False,
                                    "title": "10y real %"}})
    return _html(fig)


def chart_transmission(tr: dict) -> str:
    """Horizontal diverging bars of each asset's fast correlation to the broad dollar."""
    rows = [r for r in tr.get("rows", []) if r.get("corr_fast") is not None]
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r["corr_fast"])     # most negative at bottom
    labels = [r["label"] for r in rows]
    vals = [r["corr_fast"] for r in rows]
    colors = [C["green"] if v >= 0 else C["red"] for v in vals]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h",
                           marker={"color": colors}, width=0.62,
                           hovertemplate="%{y}: corr %{x:.2f}<extra></extra>"))
    fig.update_layout(**{**PLOT, "height": 30 + 30 * len(rows),
                         "margin": {"l": 96, "r": 24, "t": 6, "b": 26},
                         "xaxis": {"range": [-1, 1], "gridcolor": C["grid"], "zeroline": True,
                                   "zerolinecolor": C["faint"], "title": "63d corr to broad USD"},
                         "yaxis": {"gridcolor": "rgba(0,0,0,0)"}})
    return _html(fig)


# --------------------------------------------------------------------------- #
# view-models
# --------------------------------------------------------------------------- #

def _r4_currency_rows(strength: dict, horizon: str = "1m") -> dict:
    """Build R4 comparison rows on one explicit currency-vs-USD basis.

    strength_meter intentionally exposes both a cross-sectional strength value and
    the actual trailing vs_usd_pct move.  The R4 decision surface must not mix
    those scales: ordering, visible values and zero-anchored bar geometry all use
    vs_usd_pct for the selected horizon.

    USD is the zero reference, not a ranked currency. Missing/non-finite moves stay
    visible as unavailable rows and never become neutral zeroes.
    """
    horizon_rows = (((strength or {}).get("horizons") or {}).get(horizon) or [])
    rows: list[dict] = []
    finite_abs: list[float] = []

    for source in horizon_rows:
        ccy = str(source.get("ccy") or "")
        if not ccy or ccy == "USD":
            continue
        raw = source.get("vs_usd_pct")
        # Retain #8096's one-basis comparison, using R26's numeric admission.
        move = _r4_number(raw)
        if move is not None:
            finite_abs.append(abs(move))
        rows.append({
            "ccy": ccy,
            "ccy_zh": source.get("ccy_zh") or ccy,
            "em": bool(source.get("em")),
            "move_pct": move,
            "available": move is not None,
            "cross_section_strength": source.get("strength"),
        })

    domain = max(finite_abs, default=0.0)
    scale = domain if domain > 0 else 1.0
    for row in rows:
        row["bar_frac"] = (row["move_pct"] / scale) if row["available"] else None

    rows.sort(key=lambda row: (
        not row["available"],
        -(row["move_pct"] if row["move_pct"] is not None else 0.0),
        row["ccy"],
    ))
    available = [row for row in rows if row["available"]]
    return {
        "basis": "vs_usd",
        "horizon": horizon,
        "rows": rows,
        "domain_abs_pct": domain,
        "leader": available[0] if available else None,
        "n_available": len(available),
        "n_above_usd": sum(row["move_pct"] > 0 for row in available),
        "n_below_usd": sum(row["move_pct"] < 0 for row in available),
    }


def _r4_number(value):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
        return None
    return float(value) if math.isfinite(float(value)) else None


def _r4_clock(value):
    if value is None or isinstance(value, (bool, int, float)):
        return None
    try:
        ts = pd.Timestamp(value)
        return ts.tz_convert("UTC") if pd.notna(ts) and ts.tzinfo is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def _r4_readiness(dependencies: dict[str, dict], *, asof=None, checked_at=None,
                  action_requirements=None) -> dict:
    """Hardened continuation of #8096's view-contract helper.

    Source-specific clocks/expiry are supplied by owners. This function never
    promotes build time, calculation date, an empty dependency set or a label
    into available evidence. It does not activate or persist a watch.
    """
    now = _r4_clock(checked_at)
    receipts, identities = {}, {}
    for name, source in (dependencies or {}).items():
        receipt = dict(source) if isinstance(source, dict) else {}
        identity = receipt.get("dependency_id")
        reasons = [] if isinstance(source, dict) else ["invalid_source_receipt"]
        if not isinstance(identity, str) or not identity.strip():
            reasons.append("missing_or_invalid_dependency_identity")
            identity = str(name)
        identities.setdefault(identity, []).append(str(name))
        if receipt.get("state") not in {"fresh", "slow"}:
            reasons.append("source_not_qualified")
        value = receipt.get("value")
        if receipt.get("value_kind") == "number":
            if _r4_number(value) is None:
                reasons.append("missing_or_invalid_value")
                receipt["value"] = None
            if not receipt.get("unit"):
                reasons.append("missing_unit")
        elif receipt.get("value_kind") == "state":
            if not isinstance(value, str) or value.strip().lower() in {"", "unknown", "unavailable", "nan", "none", "—"}:
                reasons.append("missing_or_invalid_value")
        else:
            reasons.append("unsupported_or_missing_value_kind")
            receipt["value"] = None
        observed = _r4_clock(receipt.get("source_observed_at"))
        available = _r4_clock(receipt.get("source_available_at"))
        expires = _r4_clock(receipt.get("expires_at"))
        if any(x is None for x in (now, observed, available, expires)):
            reasons.append("unknown_source_clock_or_expiry")
        elif observed > available or available > now or expires < available:
            reasons.append("invalid_source_clock_order")
        elif now >= expires:
            reasons.append("source_expired")
        receipt.update(dependency_id=identity, usable=not reasons, withheld_reasons=reasons)
        receipts[str(name)] = receipt
    for identity, names in identities.items():
        if len(names) > 1:
            for name in names:
                receipts[name]["usable"] = False
                receipts[name]["withheld_reasons"].append("duplicate_dependency_identity")
    actions = {}
    for action, required in (action_requirements or {}).items():
        blocked = [name for name in required if not receipts.get(name, {}).get("usable")]
        if not required:
            blocked = ["no_declared_dependencies"]
        actions[action] = {"allowed": not blocked, "blocked_by": blocked}
    bad = [name for name, r in receipts.items() if not r["usable"]]
    critical = [name for name in bad if receipts[name].get("critical")]
    verdict = "unavailable" if not receipts else "stale" if critical else "degraded" if bad else "ok"
    return {"checked_at": checked_at, "asof": asof, "dependencies": receipts,
            "verdict": verdict, "banner_message": None if verdict == "ok" else {
                "en": "Some required evidence is unavailable; affected checks are paused.",
                "zh": "部分必需证据不可用；相关检查已暂停。"}, "actions": actions}


def _decision_context(results, pairs, dollar, kinematics_view, cfg, events, *,
                      checked_at, source_revision=None, event_withheld=None):
    """One display-only projection consumed by both template and latest.json.

    Existing producers retain calculations, event IDs and timestamps. Unknown
    source observation/availability clocks remain null. Current daily inputs do
    not establish finalized intraday closes; no intraday capability is admitted.
    """
    dependencies, requirements, pair_rows, seen = {}, {}, [], set()
    for p in pairs:
        key = p.get("key")
        if not isinstance(key, str) or len(key) != 6 or key in seen:
            raise ValueError("missing_or_duplicate_pair_identity")
        seen.add(key)
        df = results.get(key)
        asof = str(df.index[-1].date()) if df is not None and not df.empty else None
        source = dict((getattr(df, "attrs", {}).get("source_receipts") or {}).get("literal_quote") or {})
        quote = _r4_number(p.get("quote"))
        dep_id = key + ":literal_quote"
        dependencies[dep_id] = {**source, "dependency_id": dep_id,
            "source": "forex_inputs.load_price", "field": "literal_market_quote",
            "value": quote, "value_kind": "number", "unit": key[3:] + " per " + key[:3],
            "calculated_asof": asof, "state": source.get("state", "unknown"),
            "source_observed_at": source.get("source_observed_at"),
            "source_available_at": source.get("source_available_at"),
            "expires_at": source.get("expires_at"), "critical": True}
        # Explicit source capability, not a synthetic-OHLC assumption.
        final_id = key + ":final_4h_close"
        dependencies[final_id] = {"dependency_id": final_id, "value": None,
            "value_kind": "number", "unit": key[3:] + " per " + key[:3],
            "state": "missing", "critical": False, "source_observed_at": None,
            "source_available_at": None, "expires_at": None,
            "reason": "current_owner_supplies_daily_close_not_finalized_4h_bars"}
        requirements[key + ":price_close_4h"] = [final_id]
        assessed = p.get("base")
        if assessed not in {key[:3], key[3:]}:
            raise ValueError("assessed_currency_not_in_pair")
        meta = (cfg.get("assets") or {}).get(key) or {}
        inverted = meta.get("invert", False)
        convention_ok = (type(inverted) is bool and meta.get("base") == assessed
                         and inverted == (assessed == key[3:]))
        pair_rows.append({"pair": key, "display_base": key[:3], "display_quote": key[3:],
            "quote_convention": {"status": "qualified" if convention_ok else "unavailable",
                "inverted_from_assessed": inverted if type(inverted) is bool else None,
                "basis": "configured_assessed_currency_and_literal_quote_inversion",
                "reason": None if convention_ok else "missing_or_contradictory_instrument_convention"},
            "assessed_currency": assessed, "assessed_to_pair_direction": "same" if assessed == key[:3] else "opposite",
            "literal_quote": quote, "calculated_asof": asof,
            "technical_state": {"trend": p.get("ts_trend"), "structure": p.get("structure_state"),
                "sampling": "daily_observations", "pipeline": "forex_signals.compute_asset",
                "source_fields": ["ts_trend", "structure_state"],
                "basis": "assessed_currency_residual_pipeline",
                "trend_lookback_observations": (cfg.get("trend") or {}).get("lookback_d"),
                "structure_swing_observations": (cfg.get("structure") or {}).get("swing_window_d"),
                "structure_breakout_observations": (cfg.get("structure") or {}).get("breakout_lookback_d"),
                "residual_method": (str(df.iloc[-1].get("residual_method")) if df is not None and not df.empty and pd.notna(df.iloc[-1].get("residual_method")) else None),
                "residual_dollar_carried": (bool(df.iloc[-1].get("residual_dollar_carried")) if df is not None and not df.empty and pd.notna(df.iloc[-1].get("residual_dollar_carried")) else None),
                "provenance_projection": "kinematics_view"},
            "multi_timeframe": {"source": "forex_mtf.mtf_ladder via pair_vm", "basis": "assessed_currency_price", "rows": p.get("mtf_rows") or []},
            "quote_dependency_id": dep_id, "price_rule_capability_id": key + ":price_close_4h"})
    readiness = _r4_readiness(dependencies, checked_at=checked_at, action_requirements=requirements)
    canonical_changes = [{k: e.get(k) for k in ("id", "ts", "type", "asset", "context", "anchor", "headline", "headline_zh", "severity", "display_headline_en", "display_headline_zh", "display_assessed_currency", "display_basis", "display_residual_method", "display_basis_en", "display_basis_zh")} for e in events]
    snapshot = {"schema": "mastermind.forex.decision-context.v1", "source_revision": source_revision,
        "pairs": pair_rows, "current_read": {"risk": dollar.get("risk_word"), "regime": dollar.get("regime"),
            "calculated_asof": dollar.get("asof"),
            "available": bool(dollar.get("current_available")), "reason": dollar.get("unavailable_reason"),
            "last_confirmed": dollar.get("last_confirmed")},
        "changes": canonical_changes, "change_window": "recent_48_hours_not_user_last_seen",
        "withheld_event_refs": event_withheld or [],
        "authority": "display_only", "probability_policy": "withheld",
        "movement_projection_schema": kinematics_view.get("schema_version") if isinstance(kinematics_view, dict) else None,
        "dependencies": readiness["dependencies"], "capabilities": readiness["actions"]}
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)
    snapshot.update(snapshot_id=hashlib.sha256(encoded.encode()).hexdigest(), assembled_at=checked_at,
                    readiness=readiness["verdict"])
    return snapshot


def dollar_vm(dol: pd.DataFrame) -> dict:
    last = dol.iloc[-1]
    raw_reg = last.get("smile_regime")
    risk = _r4_number(last.get("risk_off"))
    roc = _r4_number(last.get("dollar_roc"))
    reg = raw_reg if risk is not None and roc is not None and isinstance(raw_reg, str) and raw_reg in REGIME_ZH else None
    fav_en, fav_zh = FAVORED.get(reg, ([], []))
    # F2 — hero sparkline: broad-dollar rebased to 100 + risk-off composite.
    # R26 (#8315): cut the COMMON 126-row window FIRST, then read both series
    # at exactly those row slots.  Each series used to be dropna().tail(126) on
    # its own, so sparser risk-off pulled observations from OUTSIDE the dollar
    # window and _spark_pts re-spread survivors so distinct dates shared an x.
    _SPARK_W, _SPARK_H, _SPARK_N = 440, 60, 126
    _win = dol.tail(_SPARK_N)
    _broad_w = (pd.to_numeric(_win["broad"], errors="coerce")
                if "broad" in _win.columns else pd.Series(dtype=float))
    _riskoff_w = (pd.to_numeric(_win["risk_off"], errors="coerce")
                  if "risk_off" in _win.columns else pd.Series(dtype=float))
    # rebase to the first finite positive broad value IN the window (missing,
    # zero, malformed slots are never a base); plot unrebased without one
    _base = next((float(v) for v in _broad_w
                  if pd.notna(v) and np.isfinite(v) and v > 0), None)
    _broad_rebased = 100.0 * _broad_w / _base if _base else _broad_w
    _dollar_segs = _window_segments(_broad_rebased, _SPARK_W, _SPARK_H)
    _riskoff_segs = _window_segments(_riskoff_w, _SPARK_W, _SPARK_H)

    def _safe_pts(segs: list[str]) -> str:
        # legacy single-polyline fields, kept for compatibility: filled only
        # when gap-free, so an old renderer never draws a bridged path
        return segs[0] if len(segs) == 1 else ""

    _last_val = float(_broad_rebased.iloc[-1]) if _base is not None and len(_broad_rebased) else None
    if _last_val is not None and not np.isfinite(_last_val):
        _last_val = None  # missing last slot -> unavailable
    _win_start = _win_end = None
    if len(_win):
        try:
            _win_start, _win_end = str(_win.index[0].date()), str(_win.index[-1].date())
        except AttributeError:  # non-date index
            _win_start, _win_end = str(_win.index[0]), str(_win.index[-1])
    hero_spark = {
        "dollar_pts": _safe_pts(_dollar_segs),
        "riskoff_pts": _safe_pts(_riskoff_segs),
        "dollar_segments": _dollar_segs,
        "riskoff_segments": _riskoff_segs,
        "dollar_scale": "rebased_100" if _base is not None else "reported_index",
        "rebase_available": _base is not None,
        "w": _SPARK_W, "h": _SPARK_H,
        "last_rebased": _r(_last_val, 1),
        "n": int(np.isfinite(_broad_w).sum()),
        # shared-window metadata: same row slots as both segment lists
        "window_start": _win_start, "window_end": _win_end, "count": len(_win),
    }
    return {
        "regime": reg, "regime_zh": REGIME_ZH.get(reg),
        "asof": str(dol.index[-1].date()) if hasattr(dol.index[-1], "date") else None,
        "current_available": reg is not None,
        "unavailable_reason": last.get("smile_unavailable_reason") if reg is None else None,
        "last_confirmed": {
            "regime": last.get("smile_last_confirmed") if pd.notna(last.get("smile_last_confirmed")) else None,
            "asof": str(last.get("smile_last_confirmed_asof")) if pd.notna(last.get("smile_last_confirmed_asof")) else None,
        },
        "zone_en": REGIME_ZONE_EN.get(reg, reg),
        "zone_zh": REGIME_ZONE_ZH.get(reg, reg),
        "color": REGIME_COLOR.get(reg, C["ink"]),
        "dollar_dir": None if roc is None else ("weakening" if roc < 0 else ("strengthening" if roc > 0 else "flat")),
        "dollar_dir_zh": None if roc is None else ("走软" if roc < 0 else ("走强" if roc > 0 else "持平")),
        "roc": _r(100 * roc, 1) if roc is not None else None,
        "risk_off": _r(risk, 2),
        "risk_word": None if risk is None else ("risk-off" if risk > 0 else "risk-on"),
        "risk_word_zh": None if risk is None else ("避险" if risk > 0 else "偏好风险"),
        "broad": _r(last.get("broad"), 2), "dxy": _r(last.get("dxy"), 2),
        "afe": _r(last.get("broad_afe"), 1), "eme": _r(last.get("broad_eme"), 1),
        "dollar_day_z": _r(last.get("dollar_day_z"), 2),
        # M5: hero badge uses the same abs>=FLASH_Z threshold as dollar_day_block.flag
        "dollar_day": bool(abs(float(last.get("dollar_day_z") or 0.0)) >= FLASH_Z),
        "favored": fav_en, "favored_zh": fav_zh,
        "hero_spark": hero_spark,
        "chart": chart_dollar(dol),
    }


def pair_vm(pair: str, df: pd.DataFrame, calib: dict, dollar_day: float) -> dict:
    from engine import forex_conviction
    meta = config.load()["forex"]["assets"][pair]
    last = df.iloc[-1]
    invert = meta.get("invert")
    quote = (1.0 / last["close"]) if invert else last["close"]
    quote_prev = (1.0 / df["close"].iloc[-22]) if invert else df["close"].iloc[-22]
    conv = forex_conviction.conviction(pair, df, meta, calib, dollar_day=dollar_day)
    cd, cs_ = last.get("carry_diff"), last.get("carry_score")

    # multi-timeframe technical confluence on the FX-CALIBRATED cycle preset
    # (forex_mtf -> cycles.analyze(kind="fx"): measured ~35d daily / ~34wk intermediate
    # cycle). The macro-fusion (driver/trend lean) gracefully zeroes out for FX, so the
    # verdict is a PURE technical read — a tactical timing overlay.
    from engine import forex_mtf
    mtf_a = forex_mtf.mtf_ladder(df["close"])
    cal_a = (calib.get("assets", {}) or {}).get(pair, {})
    verdict = forex_mtf.confluence_verdict(mtf_a, pair, last, cal_a)
    _TF = (("D", "Daily", "日线"), ("3D", "3-Day", "3日"), ("W", "Weekly", "周线"),
           ("2W", "Biweekly", "双周"), ("ME", "Monthly", "月线"))
    mtf_rows = []
    for key, lbl, lbl_zh in _TF:
        s = (mtf_a.get("mtf") or {}).get(key) or {}
        if not s:
            continue
        macd = ("up" if s.get("macd_cross_up") or s.get("macd_curl_up") else
                "down" if s.get("macd_cross_dn") or s.get("macd_curl_dn") else
                "pos" if s.get("macd_pos") else "neg")
        mtf_rows.append({"key": key, "label": lbl, "label_zh": lbl_zh,
                         "rsi14": _r(s.get("rsi14"), 0), "stoch": _r(s.get("stoch"), 0),
                         "macd": macd, "trend": (verdict.get("per_tf") or {}).get(key, "flat")})

    vm = {
        "key": pair, "label": META[pair]["label"], "zh": META[pair]["zh"],
        "base": META[pair]["base"], "quote_ccy": META[pair]["quote"],
        "arch": META[pair]["arch"][0], "arch_zh": META[pair]["arch"][1],
        "quote": _r(quote, 4), "chg": _r(100 * (quote / quote_prev - 1), 1),
        "resid_chg": _r(100 * (last.get("resid_close", 1) / df["resid_close"].iloc[-22] - 1), 1)
        if "resid_close" in df else None,
        "dollar_beta": _r(last.get("dollar_beta"), 2),
        "ts_trend": last.get("ts_trend", "—"), "ts_momentum": _r(last.get("ts_momentum"), 2),
        "structure": _r(last.get("structure"), 2), "structure_state": last.get("structure_state", "—"),
        "risk_index": _r(last.get("risk_index"), 0),
        "risk_word": "Calm" if (last.get("risk_regime") == "low_risk") else "Elevated",
        "shock_z": _r(last.get("shock_z"), 2), "shock_state": last.get("shock_state", "—"),
        "pos_pctile": _r(last.get("pos_pctile"), 0), "pos_state": last.get("pos_state"),
        "carry_diff": _r(cd, 2), "carry_score": _r(cs_, 2),
        "carry_to_vol": _r(last.get("carry_to_vol"), 2),
        "carry_context": meta.get("carry") == "context",
        "reer_gap": _r(100 * last.get("reer_gap"), 1) if pd.notna(last.get("reer_gap")) else None,
        "rate_diff_10y": _r(last.get("rate_diff_10y"), 2) if pd.notna(last.get("rate_diff_10y")) else None,
        "cnh_basis": _r(last.get("cnh_basis_bps"), 0) if pd.notna(last.get("cnh_basis_bps")) else None,
        "cnh_state": last.get("cnh_basis_state") if pd.notna(last.get("cnh_basis_state")) else None,
        "conviction": conv,
        "mtf_rows": mtf_rows,
        "verdict": {"headline": verdict.get("headline"), "headline_zh": verdict.get("headline_zh"),
                    "sub": verdict.get("sub"), "sub_zh": verdict.get("sub_zh"),
                    "grade": verdict.get("grade"), "grade_zh": verdict.get("grade_zh"),
                    "ladder_label": verdict.get("ladder_label"), "ladder_label_zh": verdict.get("ladder_label_zh")},
        # F2 — per-pair sparkline (126d close series, 300×36 viewBox)
        "spark_pts": _spark_pts(
            (1.0 / df["close"]).tolist() if invert else df["close"].tolist(),
            300, 36, n=126),
        "chart": chart_pair(df, pair),
    }
    return vm


# archetype -> board section (label en/zh, order)
SECTIONS = [
    ("major", "Majors", "主要货币"),
    ("commodity-dollar", "Commodity dollars", "商品货币"),
    ("haven-funder", "Haven-funders", "避险/融资货币"),
    ("em", "Emerging markets", "新兴市场"),
]


def group_sections(pairs: list[dict]) -> list[dict]:
    by_arch: dict[str, list] = {}
    for vm in pairs:
        a = config.load()["forex"]["assets"][vm["key"]].get("archetype", "major")
        by_arch.setdefault("em" if a.startswith("em") else a, []).append(vm)
    out = []
    for arch, label, zh in SECTIONS:
        members = by_arch.get(arch, [])
        if members:
            out.append({"label": label, "zh": zh, "pairs": members})
    return out


def carry_table(pairs: list[dict]) -> list[dict]:
    rows = []
    for vm in pairs:
        rows.append({"label": vm["label"], "base": vm["base"],
                     "carry": None if vm["carry_context"] else vm["carry_diff"],
                     "ctv": None if vm["carry_context"] else vm["carry_to_vol"],
                     "beta": vm["dollar_beta"], "reer_gap": vm["reer_gap"],
                     "rate10": vm["rate_diff_10y"]})
    rows.sort(key=lambda r: (r["carry"] is None, -(r["carry"] or -99)))   # high carry first
    return rows


# --------------------------------------------------------------------------- #
# alert timeline (mirrors build_commodities._group_timeline)
# --------------------------------------------------------------------------- #
TYPE_LABEL = {"residual_shock": "Shock", "risk_regime": "Risk", "trend_flip": "Trend",
              "momentum": "Momentum", "structure": "Structure", "positioning": "COT",
              "carry_flip": "Carry", "peg_approach": "Peg", "smile_regime": "Dollar",
              "cnh_basis": "CNH",
              # MSX-1 additions
              "smile_regime_flip": "Dollar Flip", "triple_red": "Triple-Red",
              "scenario_active": "Scenario"}


def _r26_price_history(results: dict, cfg: dict, reference_date) -> dict:
    """Display literal quotes on a dated, contiguous part of the source window.

    No interpolation or synthetic residual series. An invalid row ends the
    drawable run; an invalid final row withholds the chart rather than carrying
    an older value forward as the endpoint.
    """
    histories = {}
    for key, frame in results.items():
        if key != "_dollar" and key not in (cfg.get("assets") or {}):
            continue
        name = "broad_dollar" if key == "_dollar" else key
        record = {"status": "unavailable", "basis": "reported_index" if key == "_dollar" else "literal_quote",
                  "series": {"dates": [], "vals": []}, "first_date": None,
                  "last_date": None, "observations": 0, "window_observations": 0}
        histories[name] = record
        column, invert = ("broad", False) if key == "_dollar" else ("close", False)
        if key != "_dollar":
            meta = (cfg.get("assets") or {}).get(key) or {}
            invert = meta.get("invert", False)
            if (len(key) != 6 or meta.get("base") not in (key[:3], key[3:])
                    or type(invert) is not bool or invert != (meta["base"] == key[3:])):
                continue
        if not isinstance(frame, pd.DataFrame) or frame.empty or column not in frame:
            continue
        window = frame.tail(126)
        record["window_observations"] = len(window)
        run = []
        try:
            for day, raw in window[column].items():
                stamp = pd.Timestamp(day)
                number = _r4_number(raw)
                valid = (not pd.isna(stamp) and stamp.date() <= reference_date
                         and number is not None and (key == "_dollar" or number > 0))
                if not valid:
                    run = []
                    continue
                value = _r4_number(1.0 / number if invert else number)
                if value is None:
                    run = []
                    continue
                if run and stamp.date().isoformat() <= run[-1][0]:
                    run = []
                run.append((stamp.date().isoformat(), value))
        except (TypeError, ValueError, OverflowError):
            continue
        if len(run) < 2:
            continue
        record.update(status="available" if len(run) == len(window) else "partial",
                      first_date=run[0][0], last_date=run[-1][0],
                      observations=len(run),
                      series={"dates": [day for day, _ in run], "vals": [value for _, value in run]})
    return histories


def _project_event_display(events: list[dict], results: dict, cfg: dict) -> list[dict]:
    """Qualify display captions without changing event/ledger identity or math."""
    projected = []
    for event in events:
        item = deepcopy(event)
        pair = item.get("asset")
        meta = (cfg.get("assets") or {}).get(pair) or {}
        assessed = meta.get("base")
        if item.get("type") in {"momentum", "structure", "trend_flip", "residual_shock"} and assessed:
            method = None
            frame = results.get(pair)
            try:
                event_day = pd.Timestamp(item["ts"]).date()
                rows = frame.loc[frame.index.date == event_day] if frame is not None else None
                if rows is not None and len(rows) == 1:
                    raw = rows.iloc[0].get("residual_method")
                    method = raw if isinstance(raw, str) and raw in {"adjusted", "raw_fallback", "zero_filled", "unavailable"} else None
            except (AttributeError, TypeError, ValueError):
                pass
            en = item.get("headline") or "Technical evidence changed"
            zh = item.get("headline_zh") or "技术证据发生变化"
            body_en = en.split(": ", 1)[-1]
            body_zh = zh.split("：", 1)[-1]
            item["display_headline_en"] = body_en if body_en.startswith(assessed + " ") else assessed + ": " + body_en
            item["display_headline_zh"] = body_zh if body_zh.startswith(assessed) else assessed + "：" + body_zh
            item["display_assessed_currency"] = assessed
            item["display_basis"] = "assessed_currency_residual_pipeline"
            item["display_residual_method"] = method
            suffix_en = {"adjusted": "event-day input dollar-adjusted", "raw_fallback": "raw-price fallback at this event", "zero_filled": "missing return filled by the source", "unavailable": "event-day adjustment unavailable"}.get(method, "event-day adjustment not supplied")
            suffix_zh = {"adjusted": "该日输入已调整美元影响", "raw_fallback": "该日使用原始价格回退", "zero_filled": "来源对缺失收益作了填补", "unavailable": "该日调整不可用"}.get(method, "未提供该日调整方法")
            item["display_basis_en"] = f"Assessed {assessed} residual technical series; {suffix_en}."
            item["display_basis_zh"] = f"受评估货币 {assessed} 的残差技术序列；{suffix_zh}。"
        projected.append(item)
    return projected


def _group_timeline(events: list[dict]) -> list[dict]:
    days: dict[str, list] = {}
    for e in events:
        ts = pd.Timestamp(e["ts"])
        asset = e.get("asset")
        lab = "Dollar" if asset == "dollar" else META.get(asset, {}).get("label", asset or "")
        e = {**e, "label": TYPE_LABEL.get(e["type"], e["type"]), "asset_label": lab,
             "headline": e.get("display_headline_en") or e.get("headline"),
             "headline_zh": e.get("display_headline_zh") or e.get("headline_zh"),
             "daylabel": ts.strftime("%a %b %d")}
        days.setdefault(ts.strftime("%Y-%m-%d"), []).append(e)
    return [{"day": d, "daylabel": evs[0]["daylabel"], "events": evs}
            for d, evs in sorted(days.items(), reverse=True)]


# --------------------------------------------------------------------------- #
# dollar desk / transmission / strength assembly
# --------------------------------------------------------------------------- #
def _extra_inputs() -> dict:
    """Multi-column / specially-named series the dollar desk needs (not in drivers)."""
    extra: dict = {}
    cotd = store.read("cot", "cot_dollar")
    if cotd is not None and "net_spec_pct_oi" in cotd.columns:
        s = pd.to_numeric(cotd["net_spec_pct_oi"], errors="coerce")
        s.index = pd.to_datetime(s.index)
        extra["cot_dollar"] = s[~s.index.duplicated(keep="last")].sort_index().dropna()
    extra["zq_path"] = store.read("rate_futures", "zq_path")
    return extra


def _transmission_assets(cfg: dict) -> dict:
    """Load each cross-asset series for the transmission map (close, or the level)."""
    out: dict = {}
    for key, spec in cfg["transmission"]["assets"].items():
        grp, name = spec[0], spec[1]
        df = store.read(grp, name)
        if df is None or df.empty:
            continue
        s = df["close"] if "close" in df.columns else df.iloc[:, 0]
        s = pd.to_numeric(s, errors="coerce").copy()
        s.index = pd.to_datetime(s.index)
        out[key] = s[~s.index.duplicated(keep="last")].sort_index().dropna()
    return out


def _desk_latest(desk: dict) -> dict:
    """Compact, scalar-only dollar-desk summary for latest.json (auto-archived +
    read by cross_asset_confirm / master_brain / the hub card)."""
    if not desk:
        return {}
    rr, fp, po = desk.get("real_rate"), desk.get("fed_path"), desk.get("positioning")
    va, trd, lq = desk.get("valuation"), desk.get("trend"), desk.get("liquidity")
    sm = desk.get("smile") or {}
    # lean_zh + lean_net let a DISPLAY consumer (e.g. the sector-page dollar-context chip,
    # W3-C4b) render the lean bilingually and know its direction (+ = dollar-supportive) —
    # display only, never a scored input.
    out = {"lean": desk.get("lean"), "lean_zh": desk.get("lean_zh"),
           "lean_net": desk.get("lean_net"), "lean_n": desk.get("lean_n")}
    if rr:
        out.update(real_rate_regime=rr.get("regime"), real_rate_z=rr.get("real_z"))
    if fp:
        out.update(fed_path_bps=fp.get("path_bps"), fed_path_lean=fp.get("lean"))
    if po:
        out.update(usd_pos_pctile=po.get("pctile"), usd_pos_state=po.get("state"))
    if va:
        out.update(usd_reer_gap_pct=va.get("gap_pct"), usd_valuation=va.get("label"))
    if trd:
        out.update(trend=trd.get("label"), trend_n_up=trd.get("n_up"))
    if lq:
        out.update(liquidity_dir=lq.get("dir"))
    out.update(smile_confidence=sm.get("confidence"), triple_red=sm.get("triple_red"))
    # BUG FIX (MSX-1): smile_decomp was omitted — build_intl.py:281 and
    # flow_regime.py:1536 both read dollar_desk.smile_decomp and got null.
    # Forward the full dict verbatim; it is already JSON-serializable (all floats/strings/bools/lists).
    sd = desk.get("smile_decomp")
    if sd is not None:
        out["smile_decomp"] = sd
    return out


def _transmission_latest(tr: dict) -> dict:
    """Compact transmission summary for latest.json."""
    if not tr:
        return {}
    out = {"usd_dir": tr.get("usd_dir"),
           "corr": {r["key"]: r.get("corr_fast") for r in tr.get("rows", [])},
           "headwind_for": tr.get("headwind_for", []),
           "tailwind_for": tr.get("tailwind_for", []),
           "unstable": tr.get("unstable", [])}
    # B1.1: per-asset corr_fast, corr_slow, effect, stability
    out["assets"] = {
        r["key"]: {
            "corr_fast": r.get("corr_fast"),
            "corr_slow": r.get("corr_slow"),
            "effect": r.get("effect"),
            "stability": r.get("stability"),
        }
        for r in tr.get("rows", [])
    }
    out["as_of"] = tr.get("as_of")
    return out


# ---------------------------------------------------------------------------
# B1.3 Stance derivation (deterministic map)
# ---------------------------------------------------------------------------
# Plain-copy asset name tables (B1.5 — used by sentence generation)
# Keys: both ticker symbols AND forex_transmission label strings (for headwind_for/tailwind_for)
_PLAIN_ASSET_EN = {
    # ticker keys
    "SPY": "US stocks", "EEM": "EM stocks", "GC=F": "gold",
    "CL=F": "oil", "HG=F": "copper", "UST10": "US bonds", "BTC": "Bitcoin",
    # transmission label keys (from forex_transmission._ASSET_META)
    "US equities": "US stocks", "EM equities": "EM stocks",
    "Gold": "gold", "Oil (WTI)": "oil", "Copper": "copper",
    "10y Treasury": "US bonds", "Bitcoin": "Bitcoin",
}
_PLAIN_ASSET_ZH = {
    # ticker keys
    "SPY": "美股", "EEM": "新兴市场股票", "GC=F": "黄金",
    "CL=F": "原油", "HG=F": "铜", "UST10": "美债", "BTC": "比特币",
    # transmission label keys
    "US equities": "美股", "EM equities": "新兴市场股票",
    "Gold": "黄金", "Oil (WTI)": "原油", "Copper": "铜",
    "10y Treasury": "美债", "Bitcoin": "比特币",
}


def _stance(dollar_dir: str | None, active_scenarios: list[str],
            dollar_day_flag: bool, triple_red: bool | None,
            risk_word: str | None,
            headwind_for: list[str] | None = None,
            tailwind_for: list[str] | None = None) -> dict:
    """Deterministic stance map (B1.3) — NO LLM, NO randomness.

    Returns dict with: word_en, word_zh, tone, headline_en, headline_zh,
    sentence_en, sentence_zh.
    """
    has_active = bool(active_scenarios) or bool(triple_red)

    if has_active:
        word_en, word_zh, tone = "Get ready", "做好准备", "alert"
    elif dollar_day_flag:
        word_en, word_zh, tone = "Watch — don't chase", "观望，别追", "watch"
    elif risk_word not in {"risk-on", "risk-off"}:
        word_en, word_zh, tone = "Risk context unavailable", "风险背景不可用", "unavailable"
    else:
        word_en, word_zh, tone = "Watch — don't chase", "观望，别追", "calm"

    # headline from dollar_dir
    _dir = (dollar_dir or "").lower()
    if "up" in _dir or "strength" in _dir or "support" in _dir:
        headline_en, headline_zh = "Dollar strong", "美元偏强"
    elif "down" in _dir or "soft" in _dir or "weak" in _dir:
        headline_en, headline_zh = "Dollar soft", "美元偏弱"
    else:
        headline_en, headline_zh = "Dollar mixed", "美元分化"

    # plain sentence (≤14 words). Ripple-table contract
    # (templates/forex.html.j2:473/:494/:495), column "If USD rises":
    #   headwind_for → "Leaning on it" / 压制中
    #   tailwind_for → "Giving it a lift" / 提振中
    # Correlation is linear and symmetric, so a falling dollar inverts the verbs:
    #   USD firm: leans on headwind_for, lifts tailwind_for
    #   USD soft: lifts headwind_for, leans on tailwind_for
    # Quiet only when direction is mixed/flat or both lists are empty.
    hw = headwind_for or []
    tw = tailwind_for or []
    hw_names = [_PLAIN_ASSET_EN.get(k, k) for k in hw[:2]]
    tw_names = [_PLAIN_ASSET_EN.get(k, k) for k in tw[:1]]
    hw_names_zh = [_PLAIN_ASSET_ZH.get(k, k) for k in hw[:2]]
    tw_names_zh = [_PLAIN_ASSET_ZH.get(k, k) for k in tw[:1]]

    dir_word = ("firm" if "up" in _dir or "strength" in _dir
                else ("soft" if "down" in _dir or "soft" in _dir or "weak" in _dir
                      else "mixed"))
    dir_word_zh = "走强" if dir_word == "firm" else ("偏软" if dir_word == "soft" else "走势分化")

    if dir_word == "firm":
        lean_en, lean_zh = hw_names, hw_names_zh
        lift_en, lift_zh = tw_names, tw_names_zh
    elif dir_word == "soft":
        lean_en, lean_zh = tw_names, tw_names_zh
        lift_en, lift_zh = hw_names, hw_names_zh
    else:
        lean_en, lean_zh, lift_en, lift_zh = [], [], [], []

    # Firm prefers lean (existing, both-lists tape). Soft prefers lift so a
    # typical inverse-only tape is not a false "quiet" beside "Dollar soft".
    use_lift = bool(lift_en) and (dir_word == "soft" or not lean_en)
    use_lean = bool(lean_en) and not use_lift
    if use_lift:
        sentence_en = f"A {dir_word} dollar is giving {' and '.join(lift_en)} a lift."
        sentence_zh = f"美元{dir_word_zh}，正提振{'与'.join(lift_zh)}。"
    elif use_lean:
        sentence_en = f"A {dir_word} dollar is leaning on {' and '.join(lean_en)}."
        sentence_zh = f"美元{dir_word_zh}，正压制{'与'.join(lean_zh)}。"
    else:
        sentence_en = "Risk context is unavailable; no calm state is inferred." if risk_word not in {"risk-on", "risk-off"} else "The dollar is quiet today."
        sentence_zh = "风险背景不可用；不推断平静状态。" if risk_word not in {"risk-on", "risk-off"} else "美元今日平静。"

    return {
        "word_en": word_en, "word_zh": word_zh, "tone": tone,
        "headline_en": headline_en, "headline_zh": headline_zh,
        "sentence_en": sentence_en, "sentence_zh": sentence_zh,
    }


# --------------------------------------------------------------------------- #
# state_changes block (MSX-1 §2.1)
# --------------------------------------------------------------------------- #
_STATE_KEYS = ("smile_regime", "lean", "risk", "fed_path_lean", "liquidity_dir",
               "trend", "triple_red", "cnh_basis_state", "regime_radar_dominant")


def _state_history_path() -> "Path":
    return config.data_dir() / "forex" / "state_history.jsonl"


def _read_state_history() -> list[dict]:
    p = _state_history_path()
    if not p.exists():
        return []
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _state_changes(today_vals: dict, dol: "pd.DataFrame") -> dict:
    """Compute state_changes block from state_history.jsonl + today's values.

    Appends a row to state_history.jsonl ONLY when nightly_advance_enabled().
    Keep-first by date: re-run on the same date is a no-op.
    Off-lane: compute from existing history without appending (prev/changed_on/
    days_in_state may be null if history is empty, but never raises).

    For smile_regime we seed changed_on from the _dollar frame's smile_regime
    series when history is shorter than the actual run length — the frame is
    authoritative for that key.
    """
    from engine.ledger_lane import nightly_advance_enabled

    today_date = today_vals.get("_date", "")
    hist = _read_state_history()

    if nightly_advance_enabled() and today_date:
        existing_dates = {r["date"] for r in hist}
        if today_date not in existing_dates:
            row = {"date": today_date}
            for k in _STATE_KEYS:
                v = today_vals.get(k)
                # JSON-safe: bools/strings/None all fine; convert to plain type
                row[k] = bool(v) if isinstance(v, (bool, np.bool_)) else (
                    str(v) if v is not None else None
                )
            try:
                p = _state_history_path()
                p.parent.mkdir(parents=True, exist_ok=True)
                with open(p, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(row) + "\n")
                hist = _read_state_history()
            except Exception as e:  # noqa: BLE001
                log.warning("state_history append failed (%s)", e)

    hist_by_date = {r["date"]: r for r in hist}
    sorted_dates = sorted(hist_by_date)

    out: dict[str, dict] = {}
    for k in _STATE_KEYS:
        cur = today_vals.get(k)
        if isinstance(cur, (bool, np.bool_)):
            cur = bool(cur)
        elif cur is not None:
            cur = str(cur)

        prev_val = None
        changed_on = None
        days_in = None
        if cur is None:
            out[k] = {"current": None, "prev": None, "changed_on": None, "days_in_state": None}
            continue

        if k == "smile_regime" and dol is not None and not dol.empty and "smile_regime" in dol:
            values = dol["smile_regime"]
            i = len(values) - 1
            while i >= 0 and pd.notna(values.iloc[i]) and values.iloc[i] == cur:
                i -= 1
            if i >= 0 and pd.isna(values.iloc[i]):
                out[k] = {"current": cur, "prev": None, "changed_on": None,
                          "days_in_state": None,
                          "observed_since": str(values.index[i + 1].date()),
                          "continuity": "resumed_after_gap"}
                continue

        if sorted_dates:
            # walk back to find the last different value
            for d in reversed(sorted_dates):
                row_val = hist_by_date[d].get(k)
                if row_val != cur:
                    prev_val = row_val
                    changed_on = d
                    break
            # days_in_state: count from changed_on to today (inclusive of today_date).
            # When no flip is found in history we report None (unknown ≠ log age).
            if changed_on and today_date:
                try:
                    t0 = datetime.strptime(changed_on, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    t1 = datetime.strptime(today_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    days_in = max(1, (t1 - t0).days + 1)
                except ValueError:
                    days_in = None

        # seed smile_regime changed_on from the _dollar frame when history is thin
        if k == "smile_regime" and changed_on is None and dol is not None and not dol.empty:
            if "smile_regime" in dol.columns:
                sr = dol["smile_regime"].dropna()
                if len(sr) >= 2:
                    cur_r = sr.iloc[-1]
                    transitions = sr[sr != sr.shift()]
                    transitions = transitions[transitions != cur_r]
                    if not transitions.empty:
                        changed_on = transitions.index[-1].strftime("%Y-%m-%d")
                        # prev: the value at the last non-current transition point
                        # (i.e. the regime that existed before the current one took hold)
                        prev_val = str(transitions.iloc[-1])
                        if today_date and changed_on:
                            try:
                                t0 = datetime.strptime(changed_on, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                t1 = datetime.strptime(today_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                days_in = max(1, (t1 - t0).days + 1)
                            except ValueError:
                                pass

        out[k] = {"current": cur, "prev": prev_val,
                  "changed_on": changed_on, "days_in_state": days_in}
    return out


# --------------------------------------------------------------------------- #
# context_forward_log (MSX-1 §2.4)
# --------------------------------------------------------------------------- #
_FORWARD_LOG_KEYS = ("triple_red", "cnh_stress", "carry_unwind",
                     "dollar_wrecking_ball", "smile_regime")


def _context_forward_log_path() -> "Path":
    return config.data_dir() / "forex" / "context_forward_log.jsonl"


def _append_context_forward_log(asof: str, today_vals: dict, regime: dict) -> None:
    """One row per key per nightly; keep-first by (asof, key).

    intensity_pct from regime_radar intensity where applicable else null.
    Lane-gated: off-lane is a no-op (no write).
    """
    from engine.ledger_lane import nightly_advance_enabled
    if not nightly_advance_enabled():
        return
    if not asof:
        return

    try:
        p = _context_forward_log_path()
        p.parent.mkdir(parents=True, exist_ok=True)

        existing: set[tuple[str, str]] = set()
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        existing.add((r.get("asof", ""), r.get("key", "")))
                    except json.JSONDecodeError:
                        continue

        # intensity_pct lookup from regime_radar
        intensity_map: dict[str, "float | None"] = {}
        for s in (regime.get("scenarios") or []):
            _s_key = s.get("key")
            if not _s_key:
                log.warning("_append_context_forward_log: scenario missing 'key'; skipping row")
                continue
            intensity_map[_s_key] = s.get("intensity_today")

        rows_to_write = []
        for key in _FORWARD_LOG_KEYS:
            if (asof, key) in existing:
                continue
            if key == "smile_regime":
                state = today_vals.get("smile_regime")
                intensity_pct = None
            elif key == "triple_red":
                state = bool(today_vals.get("triple_red")) if today_vals.get("triple_red") is not None else None
                intensity_pct = None
            else:
                # map log keys to regime scenario keys
                scenario_key_map = {
                    "cnh_stress": "em_crisis_capital_flight",
                    "carry_unwind": "carry_unwind",
                    "dollar_wrecking_ball": "dollar_wrecking_ball",
                }
                scen_key = scenario_key_map.get(key, key)
                # state = whether the scenario is active
                active_set = {s.get("key") for s in (regime.get("scenarios") or []) if s.get("active") and s.get("key")}
                state = scen_key in active_set
                intensity_pct = intensity_map.get(scen_key)

            row = {
                "asof": asof,
                "key": key,
                "state": bool(state) if isinstance(state, (bool, np.bool_)) else state,
                "intensity_pct": round(float(intensity_pct), 1) if intensity_pct is not None else None,
                "graded": None,
            }
            rows_to_write.append(row)

        if rows_to_write:
            with open(p, "a", encoding="utf-8") as fh:
                for row in rows_to_write:
                    fh.write(json.dumps(row) + "\n")
    except Exception as e:  # noqa: BLE001
        log.warning("context_forward_log append failed (%s)", e)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    from engine import forex_inputs, forex_signals, forex_conviction
    try:
        cfg = config.load()["forex"]
        inputs = forex_inputs.load_all(cfg)
        if not inputs:
            log.error("no forex inputs loaded; skipping forex page")
            return 0
        results = forex_signals.compute_all(inputs, cfg)
    except Exception as e:  # noqa: BLE001 — never break the site build
        log.error("forex engine failed (%s); skipping forex page", e)
        return 0

    dol = results.get("_dollar")
    if dol is None or dol.empty:
        log.error("no dollar master frame; skipping forex page")
        return 0
    dollar = dollar_vm(dol)
    dollar_day = float(dol.iloc[-1].get("dollar_day_z") or 0.0)
    calib = forex_conviction.load_calibration()

    order = [p for p in cfg["active"] if p in results and len(results[p]) >= 300]
    pairs = [pair_vm(p, results[p], calib, dollar_day) for p in order]
    sections = group_sections(pairs)
    ctable = carry_table(pairs)

    # NEW — Dollar Desk, cross-asset transmission, strength meter, scorecards.
    # Each degrades to {} on any failure (the page renders without the section).
    from engine import forex_dollar, forex_transmission, forex_scorecards
    drivers = next(iter(inputs.values()))["drivers"] if inputs else {}
    # fold any radar-only drivers (e.g. the MOVE bond-vol index) into the shared dict
    rcfg = cfg.get("regime", {})
    if rcfg.get("enabled") and rcfg.get("add_drivers"):
        for nm, spec in rcfg["add_drivers"].items():
            if nm in drivers:
                continue
            try:
                df = store.read(spec[0], spec[1])
                if df is not None and not df.empty:
                    s = pd.to_numeric(df.iloc[:, 0], errors="coerce")
                    s.index = pd.to_datetime(s.index)
                    drivers[nm] = s[~s.index.duplicated(keep="last")].sort_index().dropna().rename(nm)
            except Exception as e:  # noqa: BLE001
                log.warning("regime driver %s load failed (%s)", nm, e)
    try:
        desk = forex_dollar.dollar_desk(dol, drivers, _extra_inputs(), cfg)
        # attach the calibrated REER-value verdict to the valuation leg (display-only
        # grade from scripts.calibrate_forex's dollar-index leg — CONFIRMED on IC but
        # gated by deflated Sharpe; never wired into a score)
        dcal = calib.get("dollar") or {}
        if desk.get("valuation") and dcal:
            desk["valuation"]["verdict"] = dcal.get("verdict")
            desk["valuation"]["ic_full"] = dcal.get("ic_full")
            desk["valuation"]["promotable"] = dcal.get("promotable")
    except Exception as e:  # noqa: BLE001
        log.warning("dollar desk failed (%s)", e)
        desk = {}
    try:
        tassets = _transmission_assets(cfg)
        transmission = forex_transmission.transmission(
            drivers.get("broad_dollar"), tassets, drivers.get("us10y_real"),
            dol.get("risk_off"), cfg["transmission"])
        if transmission:
            transmission["chart"] = chart_transmission(transmission)
    except Exception as e:  # noqa: BLE001
        log.warning("transmission failed (%s)", e)
        transmission = {}
    try:
        strength = forex_dollar.strength_meter(results, cfg["strength"], cfg["assets"])
    except Exception as e:  # noqa: BLE001
        log.warning("strength meter failed (%s)", e)
        strength = {}
    try:
        dxy_df = store.read("yahoo", "DX-Y.NYB")
        dxy_close = dxy_df["close"] if dxy_df is not None and "close" in dxy_df.columns else None
        scorecards = forex_scorecards.scorecards(results, cfg["assets"], dxy_close,
                                                 cfg["scorecards"], risk_off=dol.get("risk_off"))
    except Exception as e:  # noqa: BLE001
        log.warning("scorecards failed (%s)", e)
        scorecards = []

    # NEW — FX Stress & Regime Radar: read the JOINT currency configuration (velocity +
    # level) into named scenarios + an empirical conditional base rate. Display-only;
    # each call degrades to {} so the page renders without the section on any failure.
    from engine import forex_regime
    try:
        regime = forex_regime.fx_stress_regime(results, dol, drivers, cfg) if rcfg.get("enabled") else {}
    except Exception as e:  # noqa: BLE001 — radar must never break the page
        log.warning("forex_regime stress failed (%s)", e)
        regime = {}
    try:
        kinematics = forex_regime.fx_kinematics_table(results, drivers, cfg) if rcfg.get("enabled") else {}
    except Exception as e:  # noqa: BLE001
        log.warning("forex_regime kinematics failed (%s)", e)
        kinematics = {}

    real_rate_chart = chart_real_rate(drivers)

    # ---------------------------------------------------------------------------
    # B1.1: build derived latest.json fields before writing page + json
    # ---------------------------------------------------------------------------

    # dollar_day block (B1.1)
    _dol_last = dol.iloc[-1]
    _dol_day_z = _r(_dol_last.get("dollar_day_z"), 2)
    # M5: use FLASH_Z (2.0) for the exported flag — config dollar_day_z drives conviction haircut only
    _dol_day_flag = bool(abs(float(_dol_last.get("dollar_day_z") or 0.0)) >= FLASH_Z)
    _dol_roc = _dol_last.get("dollar_roc") or 0.0
    _dol_dir = "up" if _dol_roc > 0 else ("down" if _dol_roc < 0 else None)
    dollar_day_block = {"z": _dol_day_z, "flag": _dol_day_flag, "dir": _dol_dir}

    # EM block (B1.1) — CNH basis from USDCNH results, risk_off from dollar master
    _cnh_df = results.get("USDCNH")
    _cnh_last = _cnh_df.iloc[-1] if _cnh_df is not None and not _cnh_df.empty else pd.Series(dtype=object)
    em_block = {
        "cnh_basis_bps": _r(_cnh_last.get("cnh_basis_bps"), 0) if not _cnh_last.empty else None,
        "cnh_basis_state": (_cnh_last.get("cnh_basis_state")
                            if not _cnh_last.empty and pd.notna(_cnh_last.get("cnh_basis_state")) else None),
        "risk_off_composite": _r(_dol_last.get("risk_off"), 3),
    }

    # pairs.DXY entry (B1.1) — quote-only from DXY driver series
    _dxy_val = _r(_dol_last.get("dxy"), 2)
    _dxy_prev = _r(dol["dxy"].iloc[-22], 2) if "dxy" in dol.columns and len(dol) >= 22 else None
    _dxy_chg = _r(100 * (_dxy_val / _dxy_prev - 1), 1) if _dxy_val and _dxy_prev and _dxy_prev != 0 else None
    pairs_dxy = {"label": "DXY", "quote": _dxy_val, "chg": _dxy_chg}

    # regime_radar.scenarios (B1.1)
    _scenarios_export = {}
    for s in (regime.get("scenarios") or []):
        p = s.get("prob") or {}
        _scenarios_export[s["key"]] = {
            "intensity": round(s.get("intensity_today") or 0, 1),
            "n_fired": s.get("n_fired", 0),
            "min_legs": s.get("min_legs", 2),
            "active": bool(s.get("active")),
            "illustrative": bool(s.get("illustrative")),
            "fired_legs": [leg.get("key") for leg in (s.get("fired_legs") or [])],
            "prob": {
                "p_cond": p.get("p_cond"),
                "base_rate": p.get("base_rate"),
                "wilson_lo": p.get("wilson_lo"),
                "wilson_hi": p.get("wilson_hi"),
                "ci_separated": p.get("ci_separated"),
                "n_eff": p.get("n_eff"),
                "status": p.get("status"),
            },
        }

    # strength block (B1.1) — {CCY: {'1w': z, '1m': z, '3m': z}}
    _strength_export: dict = {}
    if strength and strength.get("horizons"):
        for hk, rows in strength["horizons"].items():
            for r in rows:
                ccy = r.get("ccy")
                if ccy:
                    _strength_export.setdefault(ccy, {})[hk] = r.get("strength")

    # stance (B1.1 + B1.3)
    _desk_lq = desk.get("liquidity") or {}
    _tr_latest = _transmission_latest(transmission)
    _active_scn = [s["key"] for s in (regime.get("scenarios") or []) if s.get("active")]
    _triple_red = bool((desk.get("smile") or {}).get("triple_red"))
    _desk_trend = desk.get("trend") or {}
    _dollar_dir_for_stance = (
        "up" if (dollar["dollar_dir"] or "").startswith("strength") or dollar["dollar_dir"] == "up"
        else ("down" if (dollar["dollar_dir"] or "").startswith("weak") or dollar["dollar_dir"] == "down"
              else "mixed"))
    stance = _stance(
        dollar_dir=_dollar_dir_for_stance,
        active_scenarios=_active_scn,
        dollar_day_flag=_dol_day_flag,
        triple_red=_triple_red,
        risk_word=dollar.get("risk_word"),
        headwind_for=_tr_latest.get("headwind_for"),
        tailwind_for=_tr_latest.get("tailwind_for"),
    )

    # pairs additive fields (B1.1)
    for p in pairs:
        conv = p.get("conviction") or {}
        p["reliable"] = conv.get("reliable", False)
        p["headline"] = conv.get("headline") or ""
        p["headline_zh"] = conv.get("headline_zh") or ""

    from engine import forex_alerts
    acfg = cfg["alerts"]

    # F3 — load previous transmission.assets before rebuild so transmission_shift_events
    # gets a real prev snapshot (not None, which silently skips all shift events).
    # M3: also read prior regime_radar.active for scenario edge detection.
    _transmission_prev: dict | None = None
    _scenario_prev_active: set | None = None
    try:
        _prev_path = config.data_dir() / "forex" / "latest.json"
        if _prev_path.exists():
            _prev_json = json.loads(_prev_path.read_text())
            _prev_tr = (_prev_json.get("transmission") or {})
            # Reconstruct prev transmission in the shape transmission_shift_events expects:
            # {rows: [{key, corr_fast, corr_slow, effect, stability}, ...]}
            _prev_assets = _prev_tr.get("assets") or {}
            if _prev_assets:
                _transmission_prev = {
                    "rows": [
                        {"key": k, **v}
                        for k, v in _prev_assets.items()
                    ]
                }
            # M3: prior active scenario set from regime_radar.active list
            _prev_rr = (_prev_json.get("regime_radar") or {})
            _scenario_prev_active = set(_prev_rr.get("active") or [])
    except Exception as _e_prev:  # noqa: BLE001
        log.debug("could not load prev transmission for shift events (%s)", _e_prev)

    # daily alert timeline (deterministic, recomputed each build; no intraday for FX)
    # F3: pass transmission_prev so transmission_shift_events fires correctly.
    # M3: pass scenario_prev_active so scenario_events only fires on edges.
    # F4: fx_state is assembled AFTER rebuild so changes_today has fresh events.
    try:
        all_events = forex_alerts.rebuild(
            results, desk=desk, regime=regime,
            transmission=transmission,
            transmission_prev=_transmission_prev,
            scenario_prev_active=_scenario_prev_active)
    except Exception as e:  # noqa: BLE001 — timeline is optional, never break the page
        log.warning("forex alerts rebuild failed (%s)", e)
        all_events = forex_alerts.load_events()
    event_projection = forex_alerts.qualified_current_events(all_events, dol)
    visible_events = _project_event_display(event_projection["events"], results, cfg)
    recent_events = forex_alerts.recent(visible_events, acfg["timeline_days"])
    timeline = _group_timeline(recent_events)

    # F4 — assemble fx_state AFTER rebuild; load_events() now returns tonight's events.
    # F1 — normalize tz on each event ts before comparing to tz-aware now.
    _cutoff_utc = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=2)
    _changes_today = []
    for _ev in visible_events:
        try:
            _t = pd.Timestamp(_ev["ts"])
            _t = _t.tz_localize("UTC") if _t.tzinfo is None else _t.tz_convert("UTC")
            if _t >= _cutoff_utc:
                _changes_today.append(_ev)
        except Exception:  # noqa: BLE001 — skip malformed ts
            pass
    _changes_today = sorted(_changes_today, key=lambda e: e["ts"], reverse=True)[:12]

    fx_state = {
        "smile_regime": dollar["regime"],
        "dollar_dir": _dol_dir,
        "dollar_day_flag": _dol_day_flag,
        "risk_word": dollar.get("risk_word"),
        "active_scenarios": _active_scn,
        "cnh_basis_state": em_block.get("cnh_basis_state"),
        "transmission_effects": {k: v.get("effect") for k, v in _tr_latest.get("assets", {}).items()},
        "changes_today": [
            {
                "id": e.get("id"), "ts": e.get("ts"),
                "context": e.get("context"), "anchor": e.get("anchor"),
                "type": e.get("type"),
                "asset": e.get("asset"),
                "headline_en": e.get("display_headline_en") or e.get("headline"),
                "headline_zh": e.get("display_headline_zh") or e.get("headline_zh"),
                "display_basis": e.get("display_basis"),
                "display_basis_en": e.get("display_basis_en"),
                "display_basis_zh": e.get("display_basis_zh"),
                "severity": e.get("severity"),
            }
            for e in _changes_today
        ],
    }

    as_of = max((results[p].index.max() for p in order), default=dol.index.max()).strftime("%b %d, %Y")
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cal_span = f"{min(results[p].index.min() for p in order).date()}..{max(results[p].index.max() for p in order).date()}"
    cot_ok = any("pos_pctile" in results[p].columns and results[p]["pos_pctile"].notna().any() for p in order)

    # One validated display projection serves both the page and machine snapshot.
    kinematics_view = project_kinematics(kinematics, cfg)
    decision_context = _decision_context(
        results, pairs, dollar, kinematics_view, cfg, _changes_today,
        checked_at=datetime.now(timezone.utc).isoformat(),
        event_withheld=event_projection["withheld"])

    # hub latest.json (consumed by build_vector's hub card; build_forex runs before it)
    outdir = config.data_dir() / "forex"
    outdir.mkdir(parents=True, exist_ok=True)
    _asof_raw = max((results[p].index.max() for p in order), default=dol.index.max())
    _asof_str = _asof_raw.strftime("%Y-%m-%d")

    # ---- MSX-1: enrich pairs dict with conviction narratives + signal-frame fields ----
    last_dol = dol.iloc[-1]
    cnh_basis_state_today: "str | None" = None
    _pairs_latest: dict[str, dict] = {}
    for p in pairs:
        pk = p["key"]
        conv = p.get("conviction") or {}
        df_p = results.get(pk)
        last_p = df_p.iloc[-1] if df_p is not None and not df_p.empty else pd.Series(dtype=object)
        prow: dict = {
            "label": p["label"], "quote": p["quote"], "chg": p["chg"],
            "calculated_asof": str(df_p.index[-1].date()) if df_p is not None and not df_p.empty else None,
            "chg_horizon": "1m", "chg_lookback_observations": 21,
            "action": conv.get("action"), "score": conv.get("score"),
            # MSX-1 additions (additive-only):
            "headline": conv.get("headline"), "head_zh": conv.get("headline_zh"),
            "sub": conv.get("sub"), "sub_zh": conv.get("sub_zh"),
            "shock_state": (last_p.get("shock_state") if pd.notna(last_p.get("shock_state", None)) else None),
            "cycle_position": (conv.get("cycle") or {}).get("label"),
        }
        # B1.1 additive fields: reliable + plain-copy headlines
        prow["reliable"] = conv.get("reliable", False)
        prow["headline"] = conv.get("headline") or ""
        prow["headline_zh"] = conv.get("headline_zh") or ""
        if pk == "USDCNH":
            cnh_bps = last_p.get("cnh_basis_bps")
            cnh_st = last_p.get("cnh_basis_state")
            prow["cnh_basis_bps"] = _r(cnh_bps, 0) if pd.notna(cnh_bps) else None
            prow["cnh_basis_state"] = cnh_st if (cnh_st and pd.notna(cnh_st)) else None
            cnh_basis_state_today = prow["cnh_basis_state"]
        _pairs_latest[pk] = prow

    # ---- MSX-1: state_changes block ----
    smile = (desk.get("smile") or {})
    fed_p = (desk.get("fed_path") or {})
    liq = (desk.get("liquidity") or {})
    trd = (desk.get("trend") or {})
    _today_vals = {
        "_date": _asof_str,
        "smile_regime": last_dol.get("smile_regime"),
        "lean": desk.get("lean"),
        "risk": dollar.get("risk_word"),
        "fed_path_lean": fed_p.get("lean"),
        "liquidity_dir": liq.get("dir"),
        "trend": trd.get("label"),
        "triple_red": smile.get("triple_red"),
        "cnh_basis_state": cnh_basis_state_today,
        "regime_radar_dominant": regime.get("dominant") if regime else None,
    }
    try:
        sc_block = _state_changes(_today_vals, dol)
    except Exception as e:  # noqa: BLE001
        log.warning("state_changes failed (%s)", e)
        sc_block = {}

    # ---- MSX-1: context_forward_log ----
    try:
        _append_context_forward_log(_asof_str, _today_vals, regime or {})
    except Exception as e:  # noqa: BLE001
        log.warning("context_forward_log failed (%s)", e)

    # ---- MSX-1: regime_radar scenarios compact receipts ----
    def _scenario_receipt(s: dict) -> dict:
        p_raw = s.get("prob") or {}
        return {
            "key": s.get("key"),
            "name_en": s.get("name_en"),
            "name_zh": s.get("name_zh"),
            "intensity": _r(s.get("intensity_today"), 1),
            "active": bool(s.get("active")),
            "illustrative": bool(s.get("illustrative")),
            "prob": {
                "status": p_raw.get("status"),
                "p_cond": _r(p_raw.get("p_cond"), 4),
                "base_rate": _r(p_raw.get("base_rate"), 4),
                "wilson_lo": _r(p_raw.get("wilson_lo"), 4),
                "wilson_hi": _r(p_raw.get("wilson_hi"), 4),
                "n_raw": p_raw.get("n_raw"),
                "n_eff": p_raw.get("n_eff"),
                "N": p_raw.get("N"),
            },
        }

    latest = {
        "date": as_of, "asof": _asof_str,
        "regime": dollar["regime"], "favored": dollar["favored"],
        "risk": dollar["risk_word"],
        "risk_off": dollar.get("risk_off"),
        "current_available": dollar.get("current_available", False),
        "last_confirmed": dollar.get("last_confirmed"),
        "pairs": _pairs_latest,
        # the deepened dollar read
        "dollar_desk": _desk_latest(desk),
        "transmission": _transmission_latest(transmission),
        # MSX-1: strength meter forwarded verbatim (was display-dead-end)
        "strength": strength if strength else {},
        # R12: existing computed values, explicit units and unknown per-metric clocks.
        "kinematics": kinematics_view,
        "decision_context": decision_context,
        # MSX-1: regime_radar gains 'scenarios' compact receipts (additive)
        "regime_radar": ({"as_of": regime.get("as_of"), "dominant": regime.get("dominant"),
                          "active": [s["key"] for s in regime.get("scenarios", []) if s.get("active")],
                          "intensity": {s["key"]: _r(s.get("intensity_today"), 1)
                                        for s in regime.get("scenarios", [])},
                          # MSX-1 addition: per-scenario probability receipts
                          "scenarios": [_scenario_receipt(s) for s in regime.get("scenarios", [])]}
                         if regime else {}),
        # MSX-1: state_changes block
        "state_changes": sc_block,
        # MSX-1: additive-only warning for future editors
        "schema_note": (
            "MSX-1 additive-only enrichment: do not rename/remove existing keys. "
            "new keys: dollar_desk.smile_decomp, strength, regime_radar.scenarios, "
            "pairs.<KEY>.{headline,head_zh,sub,sub_zh,shock_state,cycle_position}, "
            "pairs.USDCNH.{cnh_basis_bps,cnh_basis_state}, state_changes."
        ),
    }
    # Additive exports (B1.1/B1.2 spec) — wrapped in try/except so any
    # failure degrades to the MSX-1 latest.json rather than crashing the nightly.
    try:
        latest["dollar_day"] = dollar_day_block
        latest["em"] = em_block
        latest["stance"] = stance
        latest["fx_state"] = fx_state
        # B1.1: inject DXY into pairs block (quote-only entry)
        latest["pairs"]["DXY"] = pairs_dxy
    except Exception as _e_export:  # noqa: BLE001
        # Bare print, NOT a logger call: GitHub only parses a workflow command when
        # "::" STARTS the line, and this module's logging format prefixes every
        # record (e.g. "WARNING ::warning ..."), which silently drops the annotation.
        print(f"::warning :: forex additive export assembly failed ({_e_export}) — writing "
              "without dollar_day/em/stance/fx_state/DXY",
              flush=True)
    # Assemble once, then project/render/write the same in-memory snapshot.
    # The prior on-disk publication above is used only by incumbent event-edge
    # detection; it must never become this build's rendered consumer input.
    reference_date = datetime.now(timezone.utc).date()
    r26_view = project_r26_consumer(latest, reference_date=reference_date)
    latest["price_history"] = _r26_price_history(results, cfg, reference_date)
    latest["r26_consumer"] = r26_view
    r26_by_pair = {row["pair"]: row for row in r26_view["destinations"]["today"]["pair_tabs"]}
    from engine.i18n import tr, td
    from lib.illus import illus
    env = Environment(loader=FileSystemLoader(str(config.ROOT / "templates")), autoescape=True)
    env.globals.update(tr=tr, td=td, illus=illus)
    html = env.get_template("forex.html.j2").render(
        C=C, as_of=as_of, built=built, cal_span=cal_span,
        r26_view=r26_view, r26_by_pair=r26_by_pair, r26_histories=latest["price_history"],
        dollar=dollar, desk=desk, real_rate_chart=real_rate_chart,
        transmission=transmission, strength=strength, scorecards=scorecards,
        regime=regime, kinematics=kinematics, kinematics_view=kinematics_view, decision_context=decision_context,
        pairs=pairs, sections=sections, carry_table=ctable, cot_ok=cot_ok,
        timeline=timeline, timeline_days=acfg["timeline_days"], n_alerts=len(recent_events),
        # B1.4 new view-model vars (populated in the new template; stub values for
        # the existing template so it does not crash if the template is not yet updated)
        hero=None, why_tiles=None, trans_rows=None, stress=None,
        scoreboard=None, recent=None,
        footer_en=None, footer_zh=None, stance=stance)
    site = config.ROOT / config.load()["storage"]["site_dir"]
    site.mkdir(parents=True, exist_ok=True)
    for asset in ("forex_r26.css", "forex_watch_client.js", "forex_r26.js"):
        (site / asset).write_bytes((config.ROOT / "templates" / asset).read_bytes())
    write_page(site / "forex.html", html)
    log.info("wrote %s/forex.html (%d KB)", site, len(html) // 1024)

    (outdir / "latest.json").write_text(json.dumps(latest, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
