"""Own-history valuation percentiles for A-share names (keyless, via Baidu).

How A-share investors actually read valuation: not the absolute P/E, but where today's
P/E sits inside the stock's OWN multi-year band ("市盈率分位" — PE percentile). A name on
12× looks cheap until you see 12× is its 85th percentile. The US page leans on a
cross-sectional sector percentile (engine/stock_fundamentals._context_frame); A-shares get
the native own-history band instead.

  stock_zh_valuation_baidu(symbol, indicator, period="近五年")  -> a [date, value] daily
      history of one valuation indicator (市盈率(TTM) / 市净率 / 市销率 / 总市值).

Per name we fetch the trailing-5y P/E-TTM, P/B and P/S, then store the CURRENT value and
its percentile within that band (lower percentile = cheaper than the stock's own norm).
This is a per-name call, so it DRIPS — capped + freshness-cached per build (the
collectors/equity_profile.py pattern) — and accrues full coverage over a few builds; an
uncovered name simply has no percentile chip.

DISPLAY-ONLY context. On ~35y of A-share data value is NOT a validated cross-sectional
edge (cheap is often a value trap; research/CHINA_HK_STOCK_SIGNALS.md), so the band is a
"where in its own range" backdrop, never a buy ranking.
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import threading
import time

import pandas as pd
import requests

from lib import config
from collectors.china_analyst import _num

log = logging.getLogger("china_valuation")

OUT = config.data_dir() / "china_valuation" / "percentiles.parquet"
INDICATORS = {"市盈率(TTM)": "pe", "市净率": "pb", "市销率": "ps"}
BAIDU_VALUATION_URL = "https://gushitong.baidu.com/opendata"
REQUEST_TIMEOUT_SECONDS = 8.0
REFRESH_BUDGET_SECONDS = 180.0


def _bounded_get(*, params: dict, timeout: float):
    """GET Baidu with a true wall-clock deadline, including DNS resolution.

    ``requests`` timeouts bound socket connect/read phases but do not bound the
    resolver on every platform. Production render runs on Unix main threads, so
    SIGALRM gives this optional context fetch an outer deadline. Any unsupported
    execution context fails closed rather than silently becoming unbounded.
    """
    if timeout <= 0:
        raise TimeoutError("china valuation request budget exhausted")
    if not hasattr(signal, "SIGALRM") or threading.current_thread() is not threading.main_thread():
        raise RuntimeError("bounded China valuation transport requires a Unix main thread")
    if signal.getitimer(signal.ITIMER_REAL)[0] > 0:
        raise RuntimeError("refusing to replace an existing process wall-clock timer")

    previous_handler = signal.getsignal(signal.SIGALRM)

    def _deadline(_signum, _frame):
        raise TimeoutError(f"Baidu valuation request exceeded {timeout:.2f}s wall-clock deadline")

    signal.signal(signal.SIGALRM, _deadline)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return requests.get(BAIDU_VALUATION_URL, params=params, timeout=timeout)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)


def ak_symbol(ticker: str) -> str:
    """600519.SS / 000001.SZ -> 600519 / 000001 (Baidu's bare 6-digit code)."""
    return ticker.split(".")[0]


def _band(sym: str, indicator: str, *, timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict | None:
    """Current value + percentile within the trailing-5y band for one indicator.

    AkShare's ``stock_zh_valuation_baidu`` adapter currently calls
    ``requests.get`` without a timeout. That made this best-effort context drip
    capable of pinning the entire production render until the workflow's 180m
    timeout. Keep the same public Baidu payload contract, but own the transport
    timeout here so provider degradation fails closed to "no context".
    """
    params = {
        "openapi": "1", "dspName": "iphone", "tn": "tangram",
        "client": "app", "query": indicator, "code": sym, "word": "",
        "resource_id": "51171", "market": "ab", "tag": indicator,
        "chart_select": "近五年", "industry_select": "",
        "skip_industry": "1", "finClientType": "pc",
    }
    try:
        response = _bounded_get(params=params, timeout=timeout)
        response.raise_for_status()
        body = response.json()["Result"][0]["DisplayData"]["resultData"]["tplData"]["result"]["chartInfo"][0]["body"]
        df = pd.DataFrame(body)
        if df.empty or len(df.columns) != 2:
            return None
        df.columns = ["date", "value"]
    except Exception as e:  # noqa: BLE001 — optional context must never break a render
        log.debug("%s %s failed: %s", sym, indicator, e)
        return None
    s = pd.to_numeric(df["value"], errors="coerce").dropna()
    if indicator != "总市值":
        s = s[s > 0]
    if len(s) < 60:                       # need a meaningful band (~3 months)
        return None
    cur = float(s.iloc[-1])
    pct = float((s <= cur).mean() * 100.0)
    return {"v": round(cur, 2), "pctile": round(pct, 0),
            "lo": round(float(s.min()), 2), "hi": round(float(s.max()), 2),
            "n": int(len(s))}


def fetch_one(ticker: str, *, timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict | None:
    sym = ak_symbol(ticker)
    out: dict = {}
    for ind, key in INDICATORS.items():
        b = _band(sym, ind, timeout=timeout)
        if b is not None:
            out[key] = b
    return out or None


def _universe(limit: int) -> list[str]:
    """Names to (re)fetch — A-share search members ordered by market cap (the names
    users actually click), capped this run."""
    p = config.data_dir() / "china_search" / "members.parquet"
    if not p.exists():
        return []
    try:
        m = pd.read_parquet(p)
    except Exception:  # noqa: BLE001
        return []
    if m.index.name == "ticker" and "ticker" not in m.columns:
        m = m.reset_index()
    tcol = "ticker" if "ticker" in m.columns else m.columns[0]
    if "mktcap_yi" in m.columns:
        m = m.sort_values("mktcap_yi", ascending=False)
    return [str(t) for t in m[tcol].tolist()]


def refresh(
    max_new: int = 60,
    max_age_days: int = 14,
    max_runtime_seconds: float = REFRESH_BUDGET_SECONDS,
) -> int:
    """Refresh stale names without allowing optional context to pin a render.

    Each provider request is bounded, and the whole drip has a wall-clock budget.
    Budget exhaustion preserves the existing cache and resumes coverage next build.
    """
    cache: dict[str, dict] = {}
    if OUT.exists():
        try:
            old = pd.read_parquet(OUT)
            for _, r in old.iterrows():
                cache[r["ticker"]] = {"payload": r["payload"], "asof": r["asof"]}
        except Exception as e:  # noqa: BLE001
            log.warning("china valuation cache read failed: %s", e)
    fresh_cut = (pd.Timestamp.now() - pd.Timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    todo = [t for t in _universe(max_new)
            if not (t in cache and cache[t].get("asof", "") >= fresh_cut)][:max_new]
    if not todo:
        log.info("china valuation: all fresh (%d cached)", len(cache))
        return 0
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    got = 0
    started = time.monotonic()
    for t in todo:
        remaining = max_runtime_seconds - (time.monotonic() - started)
        if remaining <= 0:
            log.warning(
                "china valuation: runtime budget exhausted after %d/%d names; preserving cache",
                got, len(todo),
            )
            break
        per_request_timeout = min(
            REQUEST_TIMEOUT_SECONDS,
            max(0.5, remaining / max(len(INDICATORS), 1)),
        )
        rec = fetch_one(t, timeout=per_request_timeout)
        if rec:
            cache[t] = {"payload": json.dumps(rec, default=str), "asof": today}
            got += 1
    if got:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        rows = [{"ticker": k, "payload": v["payload"], "asof": v["asof"]}
                for k, v in sorted(cache.items())]
        pd.DataFrame(rows).to_parquet(OUT, index=False)
        log.info("china valuation: wrote %s (%d total, +%d this run)", OUT, len(rows), got)
    return got


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args()
    return 0 if refresh(max_new=args.limit) >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
