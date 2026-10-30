"""Weekly sector relative-trend feed — ``sector_rotation.relative_trend.v1``.

Options R1 W2A (freeze §A–§D): the second, named method on Sector Central's rotation
map. Where the incumbent 63/21-session relative-return placement reads who moved most
lately, this module measures the WEEKLY EMA relative trend of each sector SPDR against
SPY, centred on 100: ``x = 100*EMA10(q)/EMA40(q)`` and ``y = 100*EMA3(x/x[-3])`` over
the weekly ratio ``q = asset/bench`` taken on completed calendar-week NYSE endpoints.
Nothing here is a forecast; every number is a measurement carrying its own per-week
``vintage`` hash, so a corrected close moves exactly the weeks at and after it.

Endpoints are decided by lib.nyse_calendar alone (a week ends on its last SESSION —
a Good Friday pushes the endpoint to that Thursday; there is no backshift). The math
is pure: floats and lists in, statuses out; no store reads, no clock reads. The one
store touch lives behind ``emit_relative_trend_additive``'s lazy loader, which is
additive by contract — any failure logs a warning and returns None, never a failed
build of scripts/build_sector_central.py.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from lib import nyse_calendar

log = logging.getLogger(__name__)

#: Wire schema the Terminal reader validates whole-file (freeze §C).
SCHEMA = "sector_rotation.relative_trend.v1"
#: First week measured: the calendar week containing this date.
ANCHOR = date(2016, 1, 1)
#: Valid weeks at or before this index are "warming_up" (1-based k).
WARMUP_WEEKS = 120
#: Benchmark fund the ratio divides by.
BENCHMARK = "SPY"
#: The centre of the map.
CENTER = 100.0
#: |x-100| or |y-100| within this sits on the boundary ring.
BOUNDARY_TOLERANCE = 0.05
#: Terminal display trailing window (metadata only; the chain is computed in full).
TRAIL_WEEKS = 12
#: Observations emitted per sector (trailing window; the chain starts at the anchor).
EMIT_WEEKS = 260

#: The method block exactly as the Terminal reader pins it — key order is contract.
METHOD = {
    "id": "relative_trend_ema",
    "version": "v1",
    "center": 100,
    "formula": "x=100*EMA10(q)/EMA40(q); y=100*EMA3(x/x[-3])",
    "alpha_rule": "2/(span+1)",
    "seed_rule": "sma_first_span",
    "anchor": ANCHOR.isoformat(),
    "warmup_weeks": WARMUP_WEEKS,
    "endpoint_policy": "completed_week_last_session_no_backshift",
    "basis": "tr",
    "benchmark": BENCHMARK,
    "calendar": "NYSE",
    "timezone": "America/New_York",
    "trail_weeks": TRAIL_WEEKS,
    "boundary_tolerance": BOUNDARY_TOLERANCE,
}


class InvalidVintage(ValueError):
    """A price series whose session rows make a per-week vintage untrustworthy."""


def completed_week_endpoints(asof: date, anchor: date = ANCHOR) -> list[date]:
    """Last NYSE session of every completed calendar week (Mon–Sun) from `anchor`.

    Walks weeks starting with the one containing `anchor`; each week's Sunday maps
    through ``nyse_calendar.last_session_on_or_before`` — a week closed on its Friday
    (Good Friday) ends on the Thursday, never a substitute from another week. Only
    sessions with ``anchor <= endpoint <= asof`` are kept; the walk stops once the
    Sunday passes ``asof + 7`` days."""
    out: list[date] = []
    seen: set[date] = set()
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    stop = asof + timedelta(days=7)
    while sunday <= stop:
        endpoint = nyse_calendar.last_session_on_or_before(sunday)
        if anchor <= endpoint <= asof and endpoint not in seen:
            seen.add(endpoint)
            out.append(endpoint)
        sunday += timedelta(days=7)
    return out


def latest_asof(closes, benchmark: str = BENCHMARK) -> date | None:
    """The last index date holding a finite `benchmark` close, as a date; else None."""
    if closes is None:
        return None
    cols = closes.columns if hasattr(closes, "columns") else closes
    if benchmark not in cols:
        return None
    series = closes[benchmark]
    vals = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    idx = np.flatnonzero(np.isfinite(vals))
    if idx.size == 0:
        return None
    ts = series.index[int(idx[-1])]
    return pd.Timestamp(ts).date()


def ema(values: Sequence[float], span: int) -> list[float | None]:
    """EMA with alpha = 2/(span+1) and an SMA first-span seed (freeze §B).

    out[i] is None for i < span-1; out[span-1] is the simple mean of the first span
    values; later entries recurse. ``ema([1,2,3,4,5], 3) == [None, None, 2.0, 3.0, 4.0]``.
    Fewer than `span` values -> all None."""
    if span < 1:
        raise ValueError("span must be >= 1")
    n = len(values)
    out: list[float | None] = [None] * n
    if n < span:
        return out
    alpha = 2.0 / (span + 1)
    acc = 0.0
    for i in range(span):
        acc += float(values[i])
    out[span - 1] = acc / span
    prev = out[span - 1]
    for i in range(span, n):
        prev = alpha * float(values[i]) + (1.0 - alpha) * prev
        out[i] = prev
    return out


def _series_value_map(series: pd.Series) -> dict[pd.Timestamp, float]:
    """Index -> float view of one price series, index normalized to midnight stamps."""
    return {pd.Timestamp(t): float(v) for t, v in series.items()}


def relative_trend(asset: pd.Series, bench: pd.Series, *, asof: date,
                   anchor: date = ANCHOR) -> list[dict]:
    """Per-week observations of the relative-trend chain for one series (freeze §B).

    Both series are indexed by session Timestamps. Every observation carries the
    vintage hash of exactly the rows at or before its week_end (one shared walk, so
    the cost is linear and a corrected close moves only its own week forward). Weeks
    whose endpoint close is absent are "missing_endpoint" — never backshifted to the
    previous session; weeks with a non-finite or non-positive close are
    "invalid_input"; both are skipped by the EMA chain and the valid-week counter.
    """
    a_idx, b_idx = asset.index, bench.index
    if a_idx.duplicated().any() or b_idx.duplicated().any():
        raise InvalidVintage("duplicate session rows — per-week vintage would be ambiguous")

    a_vals = _series_value_map(asset)
    b_vals = _series_value_map(bench)
    union = sorted({pd.Timestamp(t) for t in list(a_idx) + list(b_idx)})
    rows = [t for t in union if anchor <= t.date() <= asof]
    endpoints = completed_week_endpoints(asof, anchor)

    # Pass 1: classify each endpoint, collect the valid ratio sequence, and stamp
    # each observation's vintage off ONE running sha256 (rows <= its own week_end).
    h = hashlib.sha256()
    ri, n_rows = 0, len(rows)
    obs: list[dict] = []
    seq: list[float] = []
    for e in endpoints:
        e_ts = pd.Timestamp(e)
        while ri < n_rows and rows[ri].date() <= e:
            d = rows[ri]
            va = a_vals.get(d)
            vb = b_vals.get(d)
            sa = repr(va) if va is not None and math.isfinite(va) else ""
            sb = repr(vb) if vb is not None and math.isfinite(vb) else ""
            h.update(f"{d:%Y-%m-%d},{sa},{sb}\n".encode())
            ri += 1
        vintage = h.copy().hexdigest()
        a, b = a_vals.get(e_ts), b_vals.get(e_ts)
        if a is None or b is None:
            obs.append({"week_end": e.isoformat(), "x": None, "y": None,
                        "status": "missing_endpoint", "vintage": vintage})
            continue
        if (not math.isfinite(a)) or (not math.isfinite(b)) or a <= 0.0 or b <= 0.0:
            obs.append({"week_end": e.isoformat(), "x": None, "y": None,
                        "status": "invalid_input", "vintage": vintage})
            continue
        seq.append(a / b)
        obs.append({"week_end": e.isoformat(), "x": None, "y": None,
                    "status": None, "vintage": vintage})

    # Pass 2: one EMA pass over the full valid sequence; later data never touches
    # an earlier observation (the chain is causal, and so is the vintage walk).
    e10 = ema(seq, 10)
    e40 = ema(seq, 40)
    x_vals: list[float | None] = [None] * len(seq)
    r_vals: list[float | None] = [None] * len(seq)
    for i in range(len(seq)):
        if e10[i] is not None and e40[i] is not None:
            x_vals[i] = CENTER * e10[i] / e40[i]
    for i in range(3, len(seq)):
        if x_vals[i] is not None and x_vals[i - 3] is not None:
            r_vals[i] = x_vals[i] / x_vals[i - 3]
    r_pos = [i for i, r in enumerate(r_vals) if r is not None]
    e3 = ema([r_vals[i] for i in r_pos], 3)
    e3_at = {i: e3[j] for j, i in enumerate(r_pos)}

    k = 0
    for i, e in enumerate(endpoints):
        if obs[i]["status"] is not None:
            continue
        k += 1
        if k <= WARMUP_WEEKS:
            obs[i]["status"] = "warming_up"
            continue
        x = x_vals[k - 1]
        y = e3_at.get(k - 1)
        y = CENTER * y if y is not None else None
        x = round(x, 2) if x is not None else None
        y = round(y, 2) if y is not None else None
        if x is None or y is None or not math.isfinite(x) or not math.isfinite(y) \
                or not (1.0 <= x <= 10000.0) or not (1.0 <= y <= 10000.0):
            obs[i]["status"] = "invalid_input"
            continue
        obs[i]["x"], obs[i]["y"] = x, y
        obs[i]["status"] = ("boundary"
                            if abs(x - CENTER) <= BOUNDARY_TOLERANCE
                            or abs(y - CENTER) <= BOUNDARY_TOLERANCE
                            else "observed")
    return obs


def _sector_entry(sid: str, ticker: str, closes, benchmark: str,
                  asof: date, anchor: date, emit_weeks: int) -> dict:
    """One §C series record; every per-sector failure degrades to a reason string.

    `closes` is any ticker -> Series mapping (a wide DataFrame, or a plain dict of
    series — the latter is how a caller isolates a duplicated-index series to ONE
    sector, since a frame's index is shared by every column)."""
    entry: dict = {"id": sid, "ticker": ticker, "kind": "sector"}
    if ticker not in closes:
        entry["observations"] = []
        entry["reason"] = "no_series"
        return entry
    try:
        obs = relative_trend(closes[ticker], closes[benchmark], asof=asof, anchor=anchor)
        entry["observations"] = obs[-emit_weeks:] if emit_weeks and emit_weeks > 0 else obs
    except InvalidVintage:
        entry["observations"] = []
        entry["reason"] = "invalid_vintage"
    except Exception as e:  # noqa: BLE001 — one bad series must never fail the file
        log.warning("rotation_relative_trend: %s compute failed: %s", ticker, e)
        entry["observations"] = []
        entry["reason"] = "compute_error"
    return entry


def build_relative_trend_feed(closes, sectors: Sequence[tuple[str, str]],
                              *, benchmark: str = BENCHMARK, asof: date | None = None,
                              anchor: date = ANCHOR, emit_weeks: int = EMIT_WEEKS) -> dict:
    """The whole §C feed dict — pure; the caller decides where (and whether) it lands.

    `closes` is a wide DataFrame of session-indexed closes (or any ticker -> Series
    mapping). `asof` defaults to ``latest_asof(closes)``. Without a usable benchmark
    column (or without any finite benchmark close) every series is emitted empty with
    reason "no_benchmark" and meta.asOf falls back to the calendar's expected last
    session: a degenerate run is still a valid file, never a failed one."""
    usable = closes is not None and benchmark in closes
    if usable and asof is None:
        asof = latest_asof(closes, benchmark)
    if not usable or asof is None:
        asof = nyse_calendar.expected_last_session()
        series_out = [{"id": sid, "ticker": ticker, "kind": "sector",
                       "observations": [], "reason": "no_benchmark"}
                      for sid, ticker in sectors]
    else:
        series_out = [_sector_entry(sid, ticker, closes, benchmark, asof, anchor, emit_weeks)
                      for sid, ticker in sectors]

    feed = {
        "meta": {
            "schema": SCHEMA,
            "asOf": asof.isoformat(),
            "vintage": hashlib.sha256(
                json.dumps(series_out, separators=(",", ":"), sort_keys=True).encode()
            ).hexdigest(),
            "method": dict(METHOD),
        },
        "sectors": series_out,
    }
    return feed


def write_relative_trend_feed(path: Path, feed: dict) -> None:
    """Persist the feed in the Terminal's exact wire format (compact, key order kept)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(feed, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")


def emit_relative_trend_additive(fdir: Path, *, closes_loader=None,
                                 sectors: Sequence[tuple[str, str]] | None = None,
                                 log=None) -> Path | None:
    """Build + write the relative-trend feed beside sector_central.json. Never raises.

    The price store is touched only through `closes_loader` (default: a lazy import
    of ``engine.inputs.yahoo_closes``), and the sector list defaults to the same
    SPDR registry engine.sector_cycles builds its rows from. Any failure — loader,
    calendar, math, disk — is logged at warning and returned as None: the host
    build keeps its exit code and its existing artifacts."""
    log = log or logging.getLogger(__name__)
    try:
        if closes_loader is None:
            def closes_loader():
                from engine.inputs import yahoo_closes
                return yahoo_closes(basis="tr")
        if sectors is None:
            from engine.sector_cycles import SECTORS
            sectors = [(tk.lower(), tk) for tk in SECTORS]
        closes = closes_loader()
        feed = build_relative_trend_feed(closes, sectors)
        out = Path(fdir) / "sector_rotation_relative_trend.json"
        write_relative_trend_feed(out, feed)
        log.info("rotation_relative_trend: wrote %s (%d sector(s))",
                 out, len(feed["sectors"]))
        return out
    except Exception as e:  # noqa: BLE001 — additive embed, never fatal
        log.warning("rotation_relative_trend: additive emit skipped: %s", e)
        return None
