"""Nightly as-observed rotation-context record — CAPTURE ONLY (2026-11-11).

Sector Intelligence v1.1, COO ruling 8 (lane 10). The rates, credit and
index-concentration questions about sector/style rotation can only be tested
FORWARD, and only if each night's record says which value was actually known
that night. Prices and holdings files can be re-derived later; what was known on
the night cannot (FRED re-serves revised/extended history, the ICE OAS window
rolls, and a store's last row moves every night). This module freezes, once per
NYSE session, the latest stored level of each rotation-context series the
repository ALREADY collects, with that value's own observation date and the
stored file's modification time, plus two index-concentration levels read from
the latest STORED fund-holdings snapshot for SPY and QQQ.

Output: ``data/rotation_context/<asof>.json.gz`` — one immutable file per session.

What this module does NOT do (binding, ruling 8 A/C):
  * no network fetch — it only reads files the collectors already wrote;
  * no series the repository does not already collect (no MOVE, no issuance,
    no Baa-minus-Treasury spread: the repo stores the Baa YIELD ``DBAA``, so that
    level is captured as stored and no spread is derived);
  * no derived change, average, ratio, z-score or flag — levels only. The two
    holdings figures (top-10 weight, sum of squared weights) are the levels the
    order names, computed from that one snapshot's own weights, not renormalised;
  * nulls, never fills: a missing/unreadable store yields ``null`` fields;
  * nothing is backfilled. The first file is the first night this runs.

Mechanics (same as the member-perf archive of PR #11024):
  * an existing ``<asof>`` file is SKIPPED and logged, never overwritten;
  * write goes through a fixed-name ``.tmp`` + ``os.replace`` (no torn file);
  * payload is byte-deterministic for the same inputs (sorted keys, compact
    separators, gzip ``mtime=0``);
  * :func:`run_nightly` swallows every exception — an error is logged and never
    fails or slows the collect run.

``file_mtime_utc`` is the stored file's modification time at capture. On the
nightly runner the collector rewrites a store when it fetched; a store the
collector did not touch that night keeps the time it was last written or checked
out. It is evidence of "when this file last changed on disk", nothing more.
"""
from __future__ import annotations

import gzip
import json
import logging
import math
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

SCHEMA = "rotation_context.v1"
OUT_SUBDIR = "rotation_context"

# (record key, store group, store file stem, stored column). Every entry is a file
# an existing collector already writes: collectors/fred.py (config.yml fred.series:
# rates/credit/risk/curve/bonds_extra) and collectors/cboe_indices.CboeCorVolAdapter.
SERIES: tuple[tuple[str, str, str, str], ...] = (
    ("us10y",          "fred", "DGS10",        "us10y"),          # 10-year Treasury yield
    ("us10y_real",     "fred", "DFII10",       "us10y_real"),     # 10-year TIPS real yield
    ("breakeven_10y",  "fred", "T10YIE",       "breakeven_10y"),  # 10-year breakeven
    ("spread_2s10s",   "fred", "T10Y2Y",       "spread_2s10s"),   # 10y minus 2y (FRED-published)
    ("spread_10y3m",   "fred", "T10Y3M",       "spread_10y3m"),   # 10y minus 3m (FRED-published)
    ("hy_oas",         "fred", "BAMLH0A0HYM2", "hy_oas"),         # ICE BofA HY OAS
    ("baa_yield",      "fred", "DBAA",         "baa_corp"),       # Moody's Baa yield (level as stored)
    ("vix",            "fred", "VIXCLS",       "vix_close"),      # VIX close
    ("cor1m",          "cboe", "cor1m",        "close"),          # CBOE 1m implied correlation
    ("cor3m",          "cboe", "cor3m",        "close"),          # CBOE 3m implied correlation
    ("dspx",           "cboe", "dspx",         "close"),          # CBOE S&P 500 dispersion index
)

HOLDINGS_FUNDS: tuple[str, ...] = ("SPY", "QQQ")
_SNAPSHOT_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.parquet$")


def _default_data_dir() -> Path:
    from lib import config
    return config.data_dir()


def _mtime_utc(p: Path) -> str:
    ts = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
    return ts.isoformat(timespec="seconds")


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _null_series(rel: str, column: str) -> dict:
    return {"source": rel, "column": column, "value": None,
            "obs_date": None, "file_mtime_utc": None}


def _read_series(data_dir: Path, group: str, stem: str, column: str) -> dict:
    """Latest stored non-null level of one series, with its own observation date."""
    rel = f"data/{group}/{stem}.parquet"
    out = _null_series(rel, column)
    p = data_dir / group / f"{stem}.parquet"
    try:
        if not p.exists():
            return out
        import pandas as pd
        df = pd.read_parquet(p)
        if column not in df.columns:
            out["file_mtime_utc"] = _mtime_utc(p)
            return out
        s = pd.to_numeric(df[column], errors="coerce")
        s.index = pd.to_datetime(df.index)
        s = s.dropna().sort_index()
        out["file_mtime_utc"] = _mtime_utc(p)
        if s.empty:
            return out
        out["value"] = _num(s.iloc[-1])
        out["obs_date"] = s.index[-1].date().isoformat()
    except Exception as e:  # noqa: BLE001 — one bad store yields nulls, never a fill
        log.warning("rotation_context: series %s unreadable (null): %s", rel, e)
        return _null_series(rel, column)
    return out


def _null_holdings(fund: str) -> dict:
    return {"source": None, "snapshot_date": None, "top10_weight": None,
            "sum_sq_weight": None, "file_mtime_utc": None}


def _read_holdings(data_dir: Path, fund: str, asof: str) -> dict:
    """Top-10 weight and sum of squared weights from the latest STORED snapshot
    dated on or before ``asof`` (never a later one). Weights are the stored
    ``weight_pct`` / 100, as stored — not renormalised to sum to 1."""
    out = _null_holdings(fund)
    d = data_dir / "etf_holdings" / fund
    try:
        if not d.is_dir():
            return out
        dated = sorted(m.group(1) for m in (_SNAPSHOT_RE.match(f.name) for f in d.iterdir())
                       if m and m.group(1) <= asof)
        if not dated:
            return out
        snap = dated[-1]
        p = d / f"{snap}.parquet"
        out["source"] = f"data/etf_holdings/{fund}/{snap}.parquet"
        out["snapshot_date"] = snap
        out["file_mtime_utc"] = _mtime_utc(p)
        import pandas as pd
        df = pd.read_parquet(p, columns=["weight_pct"])
        w = pd.to_numeric(df["weight_pct"], errors="coerce").dropna() / 100.0
        if w.empty:
            return out
        w = w.sort_values(ascending=False, kind="mergesort")
        out["top10_weight"] = _num(round(float(w.iloc[:10].sum()), 10))
        out["sum_sq_weight"] = _num(round(float((w * w).sum()), 10))
    except Exception as e:  # noqa: BLE001 — unreadable snapshot yields nulls
        log.warning("rotation_context: holdings %s unreadable (null): %s", fund, e)
        nul = _null_holdings(fund)
        nul["source"], nul["snapshot_date"] = out["source"], out["snapshot_date"]
        return nul
    return out


def build_record(asof: str, data_dir: Path, captured_at_utc: str) -> dict:
    series = {key: _read_series(data_dir, group, stem, col)
              for key, group, stem, col in SERIES}
    holdings = {fund: _read_holdings(data_dir, fund, asof) for fund in HOLDINGS_FUNDS}
    return {"schema": SCHEMA, "asof": asof, "captured_at_utc": captured_at_utc,
            "series": series, "holdings": holdings}


def encode(record: dict) -> bytes:
    text = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return gzip.compress((text + "\n").encode("utf-8"), compresslevel=9, mtime=0)


def write_capture(asof: str, data_dir: Path | None = None,
                  now_utc: datetime | None = None) -> tuple[bool, Path, int]:
    """Write ``data/rotation_context/<asof>.json.gz``.

    Returns ``(written, path, bytes)``; ``written`` is False when the session file
    already exists (skip, never overwrite — the file is immutable once written).
    Raises on an I/O failure; :func:`run_nightly` is the never-raising wrapper."""
    base = data_dir if data_dir is not None else _default_data_dir()
    out_dir = base / OUT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{asof}.json.gz"
    if p.exists():
        return False, p, 0
    now = now_utc or datetime.now(timezone.utc)
    payload = encode(build_record(asof, base, now.isoformat(timespec="seconds")))
    tmp = out_dir / f"{asof}.json.gz.tmp"
    tmp.write_bytes(payload)
    os.replace(tmp, p)
    return True, p, len(payload)


def run_nightly(asof: str | date | None = None, data_dir: Path | None = None,
                now_utc: datetime | None = None) -> dict:
    """Never-raising nightly entry point. Returns a small status dict for the log."""
    t0 = time.perf_counter()
    try:
        if asof is None:
            from lib.nyse_calendar import session_date
            asof = session_date(now_utc)
        asof_s = asof.isoformat() if isinstance(asof, date) else str(asof)
        written, p, n = write_capture(asof_s, data_dir=data_dir, now_utc=now_utc)
        dt = time.perf_counter() - t0
        if written:
            log.info("rotation_context/%s: wrote %d bytes (%.2fs)", p.name, n, dt)
        else:
            log.info("rotation_context/%s: skipped (session file exists) (%.2fs)", p.name, dt)
        return {"status": "written" if written else "skipped", "path": str(p),
                "bytes": n, "seconds": round(dt, 3)}
    except Exception as e:  # noqa: BLE001 — capture must never break or fail collect
        dt = time.perf_counter() - t0
        log.error("rotation_context capture FAILED (non-fatal, %.2fs): %r", dt, e)
        return {"status": "error", "error": repr(e), "seconds": round(dt, 3)}
