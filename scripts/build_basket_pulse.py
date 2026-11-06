"""scripts/build_basket_pulse.py — intraday basket-level tape pulse.

Consumes the ALREADY-FETCHED live-quotes snapshot from site/live/quotes.json
(written there by the intraday-fastpath workflow's quotes step, or fetched from
the live-data branch by git fetch) and produces site/live/basket_pulse.json.

MARKETS (GAP-3 HK extension): ``--market us`` (default) builds the US pulse
exactly as before; ``--market hk`` builds site/live/basket_pulse_hk.json from
data/baskets_hk/membership.json with HKEX session detection (09:30–16:00 HKT,
pre-opening auction 09:00–09:30, lib.hk_calendar holidays). The HKEX lunch
break (12:00–13:00 HKT) is folded into rth: quotes age past the stale bound
during lunch, so the mode machine degrades to 'delayed' with the true age —
honest by construction. HK quotes ride the same live-quotes snapshot (Yahoo
path resolves .HK symbols, ~15-min delayed); the US-only organs (offense/
defense spread, AI-capex complex, shock-day relative bid) stay null/empty for
HK. HK EOD fallback reads data/basket_levels/hk.parquet levels (there is no
per-symbol HK OHLCV store on the render path).

QUOTES SOURCE DECISION:
  The canonical live-quotes snapshot is force-pushed to the `live-data` branch by
  live-quotes.yml (runs on ubuntu-latest every 10 min, all day). The intraday-fastpath
  workflow already writes a LOCAL site/live/quotes.json (the BTC-only hourly snapshot)
  via btc-live.yml, so that path already exists but contains only BTC-USD. The
  correct equity snapshot is from live-data.

  Resolution: the fastpath step that calls this script first fetches the live-data
  branch and checks out just quotes.json into a temp path. We read that file.
  Specifically, the step does:
    git fetch origin live-data:refs/remotes/origin/live-data
    git show origin/live-data:quotes.json > /tmp/quotes_live.json
  and this script reads LIVE_QUOTES_PATH env (default: /tmp/quotes_live.json) or
  falls back to site/live/quotes.json if it exists and has >1 quote.

  NO new per-symbol network fetching is ever done here.

OUTPUT: site/live/basket_pulse.json  +  site/live/basket_pulse_lastgood.json
  Tier: display/de-escalation only (FT-R1, FT-R2).
  FT-R3: shock_day_relative_bid is a same-session descriptive readout with no
  beneficiary/casualty/direction fields and carries the T+1 fade note.
  FT-R5: writes site/ only, data/ discard guard in the workflow.

GRADED MODES (TS-R1 honest-delay law):
  live      — quotes present, median member delayMin <= LIVE_STALE_MIN, pre/rth session.
  delayed   — quotes present but older (median delayMin > LIVE_STALE_MIN), pre/rth session.
              COMPUTE per-basket values from the delayed quotes anyway; stamp delay_min_median.
              A delayed value with its true age is better than a null.
  last_rth  — session post/closed. Serve the sidecar basket_pulse_lastgood.json (persisted
              whenever a live or delayed compute succeeds). Original as_of stamps preserved.
  eod       — no lastgood sidecar yet (first deploy or data gap). Compute 1d EW %chg from
              the last two EOD closes in data/baskets/ohlcv/<SYM>.parquet, stamp bar date.

  The per-basket 'stale' flag is kept for backwards compat.
  Disagreement chips (FT-R12) stay suppressed when mode != live.
"""
from __future__ import annotations

import json
import logging
import math
import os
import statistics
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

log = logging.getLogger("basket_pulse_build")

# ── constants ─────────────────────────────────────────────────────────────────

# Quote age (minutes) beyond which we mark a basket stale (used for live/delayed boundary)
LIVE_STALE_MIN: int = 20

# Minimum coverage fraction for a basket to compute a live EW avg.
# Below this threshold live_ew_chg_pct is set to None (honest null).
MIN_COVERAGE: float = 0.30

# Sidecar file name for last-good pulse (US; per-market name in MARKETS)
LASTGOOD_FILENAME: str = "basket_pulse_lastgood.json"

# Per-market wiring. us_features gates the US-only organs (od spread, AI-capex
# complex, shock-day relative bid, market_drivers read); eod_source picks the
# closed-market fallback (per-symbol OHLCV for US, basket levels for HK).
MARKETS: dict[str, dict[str, Any]] = {
    "us": {
        "membership_parts": ("baskets", "membership.json"),
        "levels_parquet": "us.parquet",
        "tz": "America/New_York",
        "out_name": "basket_pulse.json",
        "lastgood_name": LASTGOOD_FILENAME,
        "names_dir": "basketdata",
        "us_features": True,
        "eod_source": "ohlcv",
    },
    "hk": {
        "membership_parts": ("baskets_hk", "membership.json"),
        "levels_parquet": "hk.parquet",
        "tz": "Asia/Hong_Kong",
        "out_name": "basket_pulse_hk.json",
        "lastgood_name": "basket_pulse_hk_lastgood.json",
        "names_dir": "hkbasketdata",
        "us_features": False,
        "eod_source": "levels",
    },
}

# Mode literals (TS-R1)
MODE_LIVE: str = "live"
MODE_DELAYED: str = "delayed"
MODE_LAST_RTH: str = "last_rth"
MODE_EOD: str = "eod"

# ── TS-U5 settled-close recompute ────────────────────────────────────────────
# A post-session quote may describe the DAY only when its basis pins the regular
# session. Yahoo 'regular' = regularMarketPrice (never an AH print; require the
# stamp at/after the bell so a delayed intraday print is not mistaken for the
# settle). Polygon 'day' = today's session close. Polygon 'trade'/'minute' only
# when printed at or within ~90s of the bell (closing auction); later prints are
# extended-hours drift — the exact contamination this mode exists to reject.
_SETTLE_TOL_MS: int = 90_000
# Minimum fraction of quoted members that must pass the settle filter before a
# settled-close recompute is claimed (else the sidecar serve stands).
SETTLE_MIN_FRACTION: float = 0.60

# ETFs for the offense/defense spread (print-only, no z claims, FT-R3)
DEFENSE_ETFS: list[str] = ["XLP", "XLU", "XLV"]
OFFENSE_ETFS: list[str] = ["SMH", "XLK"]

# Session boundary hours in ET
_PRE_OPEN_START_ET = 4    # 04:00 ET = premarket open
_RTH_START_ET = 9         # 09:30 ET
_RTH_START_MINUTE = 30
_RTH_END_ET = 16          # 16:00 ET
_POST_CLOSE_END_ET = 20   # 20:00 ET = after-hours end

# Shock day relative-bid gate (FT-R3)
_SHOCK_PRIMARY_KEYS: frozenset[str] = frozenset({"oil_shock"})
_SHOCK_FAMILIES: frozenset[str] = frozenset({"geopolitical"})
# Plain-word form per docs/DESIGN_DOCTRINE.md Laws 2/3 (matches the #2246
# notifier copy); the precise receipt (58% at T+1, n=26) lives on Tier-2 tips.
_T1_FADE_NOTE: str = "in 26 past cases about 6 in 10 sharp flips faded within a day"


# ── session detection ──────────────────────────────────────────────────────────

def _market_calendar(market: str):
    """The trading-day calendar module for a market (same API surface:
    is_session, expected_last_session)."""
    if market == "hk":
        from lib import hk_calendar
        return hk_calendar
    from lib import nyse_calendar
    return nyse_calendar


def _market_session(now_utc: datetime, market: str) -> str:
    """Per-market session state (pre|rth|post|closed) from the UTC clock."""
    return _hk_session(now_utc) if market == "hk" else _et_session(now_utc)


def _hk_session(now_utc: datetime) -> str:
    """HKEX session from the UTC clock (Asia/Hong_Kong has no DST).

    pre  09:00–09:30 HKT (pre-opening auction)
    rth  09:30–16:00 HKT — the lunch break (12:00–13:00) is NOT special-cased:
         quotes freeze, their age grows past the stale bound, and the mode
         machine reports 'delayed' with the true age (honest degrade).
    post 16:00–16:30 HKT (closing auction ~16:08 + the settle tick window)
    """
    from zoneinfo import ZoneInfo
    from lib import hk_calendar

    hkt = now_utc.astimezone(ZoneInfo("Asia/Hong_Kong"))
    if not hk_calendar.is_session(hkt.date()):
        return "closed"

    h, m = hkt.hour, hkt.minute
    if h < 9:
        return "closed"
    if h == 9 and m < 30:
        return "pre"
    if h < 16:
        return "rth"
    if h == 16 and m < 30:
        return "post"
    return "closed"


def _et_session(now_utc: datetime) -> str:
    """Return pre|rth|post|closed from the UTC clock.

    Uses the existing US calendar and actual session close, including half days.
    A weekend/holiday never opens; no second holiday or DST calendar is added.
    """
    from zoneinfo import ZoneInfo
    from lib import nyse_calendar

    et = now_utc.astimezone(ZoneInfo("America/New_York"))
    if not nyse_calendar.is_session(et.date()):
        return "closed"

    h, m = et.hour, et.minute
    if h < _PRE_OPEN_START_ET:
        return "closed"
    if h < _RTH_START_ET or (h == _RTH_START_ET and m < _RTH_START_MINUTE):
        return "pre"
    from engine.session_digest import session_window_et
    _, actual_close = session_window_et(et.date())
    if et < actual_close:
        return "rth"
    if h < _POST_CLOSE_END_ET:
        return "post"
    return "closed"


# ── quotes loading ─────────────────────────────────────────────────────────────

def _load_quotes(quotes_path: Path | None) -> tuple[dict[str, Any], Path | None]:
    """Return (quotes_dict {SYM: {...}}, resolved_path).

    Search order:
    1. $LIVE_QUOTES_PATH env var
    2. Explicit quotes_path argument
    3. /tmp/quotes_live.json (written by workflow git-fetch step)
    4. site/live/quotes.json (fall-through; may be BTC-only)
    """
    from lib import config

    candidates: list[Path] = []
    env_path = os.environ.get("LIVE_QUOTES_PATH")
    if env_path:
        candidates.append(Path(env_path))
    if quotes_path is not None:
        candidates.append(quotes_path)
    candidates.append(Path("/tmp/quotes_live.json"))
    site_dir = config.ROOT / config.load()["storage"]["site_dir"]
    candidates.append(site_dir / "live" / "quotes.json")

    for p in candidates:
        if not p.exists() or p.stat().st_size < 10:
            continue
        try:
            data = json.loads(p.read_text())
        except Exception:
            continue
        qs = data.get("quotes") or {}
        if len(qs) < 2:
            # site/live/quotes.json is BTC-only when live-data hasn't been fetched
            log.debug("skipping %s — only %d quotes", p, len(qs))
            continue
        log.info("loaded %d quotes from %s (asof=%s)", len(qs), p, data.get("asof"))
        return qs, p

    # Bare print, NOT a logger call: GitHub only parses a workflow command when
    # "::" STARTS the line, and this module's logging format prefixes every
    # record (e.g. "WARNING ::warning ..."), which silently drops the annotation.
    print("::warning::no usable quotes file found; pulse will have null coverage", flush=True)
    return {}, None


# ── membership loading ─────────────────────────────────────────────────────────

def _load_membership(membership_path: Path | None, market: str = "us") -> dict[str, Any]:
    """Load the market's membership.json. Returns the baskets dict."""
    from lib import config

    p = membership_path or config.data_dir().joinpath(*MARKETS[market]["membership_parts"])
    try:
        data = json.loads(p.read_text())
    except Exception as e:
        print(f"::warning::cannot read membership.json: {e}", flush=True)
        return {}
    return data.get("baskets") or {}


def _active_members(basket: dict[str, Any]) -> list[str]:
    """Return tickers of non-removed members."""
    return [
        m["ticker"]
        for m in (basket.get("members") or [])
        if m.get("removed") is None and m.get("ticker")
    ]


# ── staleness check ────────────────────────────────────────────────────────────

def _quote_source_ms(quote: dict[str, Any], now_ms: int) -> int | None:
    """Observed epoch milliseconds only; build/future/synthetic clocks are not evidence."""
    if not isinstance(quote, dict) or quote.get("tsSynthetic"):
        return None
    stamp = quote.get("ts")
    if (isinstance(stamp, bool) or not isinstance(stamp, (int, float))
            or stamp <= 0 or stamp > now_ms or not math.isfinite(stamp)):
        return None
    return int(stamp)


def _quote_delay_min(quote: dict[str, Any], now_ms: int) -> float | None:
    """Age advances from the observed source clock; declared delay remains a floor.

    The snapshot's delayMin is measured when its producer ran. Reusing that
    scalar alone freezes age forever. A missing/synthetic/future timestamp is
    unknown, not a fresh observation rescued by delayMin or this build's clock.
    """
    stamp = _quote_source_ms(quote, now_ms)
    if stamp is None:
        return None
    age = (now_ms - stamp) / 60_000
    delay = quote.get("delayMin")
    if not isinstance(delay, bool):
        try:
            floor = float(delay)
            if math.isfinite(floor) and floor >= 0:
                age = max(age, floor)
        except (TypeError, ValueError, OverflowError):
            pass
    return age


def _observed_change(quote: dict[str, Any], now_ms: int, stale_min: int,
                     include_delayed: bool) -> tuple[float, int] | None:
    """One shared qualification rule for arithmetic and its source-clock receipt."""
    delay = _quote_delay_min(quote, now_ms)
    if delay is None or (not include_delayed and delay > stale_min):
        return None
    value = quote.get("changePct")
    if isinstance(value, bool):
        return None
    try:
        change = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(change):
        return None
    stamp = _quote_source_ms(quote, now_ms)
    if stamp is None:
        return None
    return change, stamp


def _source_clock_evidence(tickers: list[str], quotes: dict[str, Any], now_ms: int,
                           stale_min: int, include_delayed: bool) -> dict[str, Any]:
    """Clock range of actual priced contributors, not an assertion of synchronization."""
    clocks = []
    for ticker in dict.fromkeys(tickers):
        observation = _observed_change(quotes.get(ticker), now_ms, stale_min, include_delayed)
        if observation is not None:
            clocks.append(observation[1])
    def iso(stamp: int) -> str:
        return datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat()
    return {
        "n_priced": len(clocks),
        "source_asof": iso(max(clocks)) if clocks else None,
        "source_oldest_at": iso(min(clocks)) if clocks else None,
        "source_time_span_seconds": (max(clocks) - min(clocks)) / 1000 if clocks else None,
    }


# Keep backward-compat alias used by existing callers
def _quote_age_min(quote: dict[str, Any], now_ms: int) -> float | None:
    return _quote_delay_min(quote, now_ms)


def _is_stale(quote: dict[str, Any], now_ms: int, stale_min: int = LIVE_STALE_MIN) -> bool:
    delay = _quote_delay_min(quote, now_ms)
    if delay is None:
        return True
    return delay > stale_min


def _median_member_delay(tickers: list[str], quotes: dict[str, Any], now_ms: int) -> float | None:
    """Median delayMin across tickers that are present in quotes."""
    delays: list[float] = []
    for tk in tickers:
        q = quotes.get(tk)
        if q is not None:
            d = _quote_delay_min(q, now_ms)
            if d is not None:
                delays.append(d)
    if not delays:
        return None
    return statistics.median(delays)


# ── EW computation ─────────────────────────────────────────────────────────────

def _ew_chg(tickers: list[str], quotes: dict[str, Any], now_ms: int,
             stale_min: int = LIVE_STALE_MIN,
             include_delayed: bool = False) -> tuple[float | None, int, int, bool]:
    """Equal-weight average of changePct across quoted tickers.

    When include_delayed=False (default, live mode): only fresh quotes (delay <=
    stale_min) contribute to the EW average. Stale quotes are counted in n_quoted
    but excluded from changes.

    When include_delayed=True (delayed mode): All finite, source-clocked quotes contribute to the
    EW average regardless of age. Unknown clocks are never made observable. This implements the honest-delay law: a delayed
    value with its true age beats a null.

    Returns (ew_chg_pct, n_quoted, n_members, any_stale).
    If coverage < MIN_COVERAGE returns (None, n_quoted, n_members, any_stale).
    """
    changes: list[float] = []
    n_quoted = 0
    any_stale = False
    for tk in tickers:
        q = quotes.get(tk)
        if q is None:
            continue
        n_quoted += 1
        is_q_stale = _is_stale(q, now_ms, stale_min)
        if is_q_stale:
            any_stale = True
            if not include_delayed:
                continue  # live mode: skip stale
        observation = _observed_change(q, now_ms, stale_min, include_delayed)
        if observation is not None:
            changes.append(observation[0])

    n_members = len(tickers)
    coverage = len(changes) / n_members if n_members > 0 else 0.0
    if coverage < MIN_COVERAGE:
        return None, n_quoted, n_members, any_stale
    return round(sum(changes) / len(changes), 3), n_quoted, n_members, any_stale


# ── frozen-levels chain gate ───────────────────────────────────────────────────

def _chain_spans(anchors: Any, d1: Any, d2: Any) -> bool:
    """True iff the frozen rows at d1 < d2 sit on the same chain segment.

    `anchors` is the basket's `{id}__anchor` column (engine/basket_freeze.py schema
    v2): the ISO date the row's chain segment is based on.  A ratio d1→d2 is a real
    return only when d2's segment already covered d1 — i.e. anchor(d2) <= d1.  A
    missing/NaN anchor is a pre-v2 row (its base moved with the price window) and a
    later anchor means the chain BROKE in between; both are honest nulls, not returns.
    """
    try:
        import pandas as pd
        a2 = anchors.get(d2)
        if a2 is None or (not isinstance(a2, str) and pd.isna(a2)):
            return False
        return pd.Timestamp(a2) <= pd.Timestamp(d1)
    except Exception:  # noqa: BLE001 — unparseable anchor → honest null
        return False


# ── cum_2d computation ─────────────────────────────────────────────────────────

def _cum_2d(basket_id: str, live_ew_chg_pct: float | None,
            market: str = "us") -> float | None:
    """Yesterday close-to-close + today's live move.

    Uses data/basket_levels/<market>.parquet `{id}__level_price` column.
    The 2d pct change is (yesterday_close / 2_days_ago_close - 1) + live_chg_pct/100,
    expressed as percentage.

    CHAIN GATE (2026-08): the ratio of two frozen rows is only a return when both sit
    on the SAME chain segment.  Rows written before the chain-linked freeze writer were
    each rebased on that night's rolling price window, so their ratio silently carries
    the EW return of the day that dropped out of the window front — the same order of
    magnitude as the 1d signal it is being read as.  Valid iff the newer row's
    `{id}__anchor` is present and at/before the older row's date; otherwise honest null.

    Returns None if data unavailable, unchained, or live_ew_chg_pct is None.
    """
    if live_ew_chg_pct is None:
        return None
    try:
        import pandas as pd
        from lib import config

        p = config.data_dir() / "basket_levels" / MARKETS[market]["levels_parquet"]
        col = f"{basket_id}__level_price"
        anchor_col = f"{basket_id}__anchor"
        # A store with no anchor column raises here → honest null (nothing is chained).
        df = pd.read_parquet(p, columns=[col, anchor_col])
        if df.empty or len(df) < 2:
            return None
        # last two rows: yesterday and day before
        vals = df[col].dropna()
        if len(vals) < 2:
            return None
        d1, d2 = vals.index[-2], vals.index[-1]
        if not _chain_spans(df[anchor_col], d1, d2):
            return None
        yesterday = float(vals.iloc[-1])
        day_before = float(vals.iloc[-2])
        if day_before == 0:
            return None
        yday_chg = (yesterday / day_before - 1) * 100
        return round(yday_chg + live_ew_chg_pct, 3)
    except Exception as e:
        log.debug("cum_2d unavailable for %s: %s", basket_id, e)
        return None


# ── cross-sectional rank ───────────────────────────────────────────────────────

def _tape_ranks(baskets_data: list[dict[str, Any]]) -> dict[str, int | None]:
    """Cross-sectional rank of live_ew_chg_pct (1=weakest, N=strongest).
    Baskets with null live_ew_chg_pct get rank None.
    """
    ranked = [(b["id"], b["live_ew_chg_pct"])
              for b in baskets_data if b["live_ew_chg_pct"] is not None]
    ranked.sort(key=lambda x: x[1])
    result: dict[str, int | None] = {b["id"]: None for b in baskets_data}
    for i, (bid, _) in enumerate(ranked):
        result[bid] = i + 1
    return result


# ── offense/defense spread ─────────────────────────────────────────────────────

def _od_spread(quotes: dict[str, Any], now_ms: int,
               stale_min: int = LIVE_STALE_MIN) -> float | None:
    """EW(XLP,XLU,XLV) vs EW(SMH,XLK) live changePct spread.
    Print-only intraday descriptive (FT-R3). Returns None if any ETF missing/stale.
    """
    def _ew_etfs(tickers: list[str]) -> float | None:
        vals = []
        for tk in tickers:
            q = quotes.get(tk)
            if q is None or _is_stale(q, now_ms, stale_min):
                return None
            chg = q.get("changePct")
            if chg is None:
                return None
            vals.append(float(chg))
        return sum(vals) / len(vals) if vals else None

    def_ew = _ew_etfs(DEFENSE_ETFS)
    off_ew = _ew_etfs(OFFENSE_ETFS)
    if def_ew is None or off_ew is None:
        return None
    # spread = defensive - offensive (positive = defense leading)
    return round(def_ew - off_ew, 3)


# ── EOD fallback ──────────────────────────────────────────────────────────────

def _eod_basket_chg(basket_id: str, members: list[str]) -> tuple[float | None, str | None]:
    """Equal-weight 1d % change from the last two EOD closes for all members.

    Reads data/baskets/ohlcv/<SYM>.parquet (close column) for each member.
    Returns (ew_chg_pct, bar_date_str) or (None, None) if data unavailable.
    This is the honest-null fallback when no quotes and no lastgood exist.
    """
    try:
        import pandas as pd
        from lib import config

        ohlcv_dir = config.data_dir() / "baskets" / "ohlcv"
        changes: list[float] = []
        bar_dates: list[str] = []

        for sym in members:
            p = ohlcv_dir / f"{sym}.parquet"
            if not p.exists():
                continue
            try:
                df = pd.read_parquet(p, columns=["close"])
                vals = df["close"].dropna()
                if len(vals) < 2:
                    continue
                prev_close = float(vals.iloc[-2])
                last_close = float(vals.iloc[-1])
                if prev_close == 0:
                    continue
                chg = (last_close / prev_close - 1) * 100
                changes.append(chg)
                # Capture the bar date from index
                bar_date = vals.index[-1]
                if hasattr(bar_date, "date"):
                    bar_dates.append(str(bar_date.date()))
                else:
                    bar_dates.append(str(bar_date)[:10])
            except Exception as e:
                log.debug("eod_basket_chg: skip %s: %s", sym, e)
                continue

        if len(changes) < max(1, len(members) * MIN_COVERAGE):
            return None, None

        ew_chg = round(sum(changes) / len(changes), 3)
        # Use the most common bar date (mode)
        bar_date_out = max(set(bar_dates), key=bar_dates.count) if bar_dates else None
        return ew_chg, bar_date_out

    except Exception as e:
        log.debug("_eod_basket_chg failed for %s: %s", basket_id, e)
        return None, None


def _eod_basket_chg_levels(basket_id: str, market: str) -> tuple[float | None, str | None]:
    """1d % change from the last two rows of the market's basket-levels parquet.

    The EOD fallback for markets without a per-symbol OHLCV store on the render
    path (HK). The level series IS the EW-chained basket, so its 1d change is
    the same quantity the member-OHLCV path computes for US. A basket absent
    from the levels file (e.g. a freshly seeded split whose levels have not
    accrued yet) returns (None, None) — honest null.

    CHAIN GATE (2026-08): two frozen rows only divide into a return when they share a
    chain segment.  Pre-v2 rows were each rebased on that night's rolling price
    window, so their ratio carries the EW return of the day that fell out of the
    window front — an error the size of the signal.  Gated on `{id}__anchor`
    (anchor at the newer row must be at/before the older row's date); otherwise the
    same honest (None, None) a missing basket returns.
    """
    try:
        import pandas as pd
        from lib import config

        p = config.data_dir() / "basket_levels" / MARKETS[market]["levels_parquet"]
        col = f"{basket_id}__level_price"
        anchor_col = f"{basket_id}__anchor"
        # A store with no anchor column raises here → honest null (nothing is chained).
        df = pd.read_parquet(p, columns=[col, anchor_col])
        vals = df[col].dropna()
        if len(vals) < 2:
            return None, None
        if not _chain_spans(df[anchor_col], vals.index[-2], vals.index[-1]):
            return None, None
        prev, last = float(vals.iloc[-2]), float(vals.iloc[-1])
        if prev == 0:
            return None, None
        bar_date = vals.index[-1]
        bar_date_out = (str(bar_date.date()) if hasattr(bar_date, "date")
                        else str(bar_date)[:10])
        return round((last / prev - 1) * 100, 3), bar_date_out
    except Exception as e:  # noqa: BLE001 — missing column/file → honest null
        log.debug("_eod_basket_chg_levels failed for %s: %s", basket_id, e)
        return None, None


# ── lastgood sidecar ──────────────────────────────────────────────────────────

# One transient comparison baseline in the EXISTING last-good sidecar. This is
# not a historical ledger, prediction, ranking input, or independent data store.
_COMPARISON_SCHEMA = "basket_intraday_comparison.v1"
_BASELINE_SCHEMA = "basket_observation_baseline.v1"
_COMPARISON_MAX_SKEW_MS = 60_000  # explicit sampling tolerance, not a fitted signal


def _comparison_point(quote: Any, observed_at: datetime,
                      opened: datetime, closed: datetime, *,
                      settled_close: bool = False) -> dict[str, Any] | None:
    stamp = _quote_source_ms(quote, int(observed_at.timestamp() * 1000))
    if stamp is None:
        return None
    source_time = datetime.fromtimestamp(stamp / 1000, timezone.utc)
    if settled_close:
        # Explicit regular/day-price evidence at settlement, not arbitrary AH
        # prints. Retain the true source stamp; never clamp it to the bell.
        close_ms = int(closed.timestamp() * 1000)
        if (quote.get("basis") not in ("regular", "day")
                or not close_ms - 60_000 <= stamp <= close_ms + _SETTLE_TOL_MS
                or not _settle_quote_ok(quote, close_ms)):
            return None
    elif not opened <= source_time <= closed:
        return None
    if quote.get("currency") != "USD":
        return None
    for key in ("source", "basis"):
        if not isinstance(quote.get(key), str) or not quote[key].strip():
            return None
    values = {}
    for key in ("price", "prevClose"):
        value = quote.get(key)
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number) or number <= 0:
            return None
        values[key] = number
    return {**values, "ts": stamp, "source": quote["source"],
            "basis": quote["basis"], "currency": "USD"}


def _comparison_signature(point: dict[str, Any]) -> tuple:
    return tuple(point[key] for key in ("source", "basis", "currency", "prevClose"))


def _intraday_comparisons(baskets: dict[str, Any], quotes: dict[str, Any],
                         previous: dict | None, *, now: datetime, market: str,
                         session: str, settled_close: bool = False) -> tuple[dict[str, dict], dict | None]:
    """Matched-member returns between two observed regular-session snapshots.

    The interval is named by benchmark source clocks, never by polling cadence.
    Members must advance and stay within 60 seconds AND one tenth of the
    interval of BOTH benchmark endpoints. This is a disclosed sampling tolerance.
    Membership, quote source/basis and the same-session reference close must agree.
    Missing observations remain missing; no overnight/open-price reconstruction.
    A subset mean is explicitly identified and never presented as the full basket.
    """
    memberships = {key: _active_members(value) for key, value in baskets.items()}
    observation_kind = "settled_regular" if settled_close else "regular"
    common = {"schema": _COMPARISON_SCHEMA, "benchmark": "SPY",
              "method": "matched_member_equal_weight", "max_clock_skew_seconds": 60,
              "observation_kind": observation_kind,
              "settlement_tolerance_seconds": _SETTLE_TOL_MS / 1000 if settled_close else 0}

    def unavailable(reason: str) -> dict[str, dict]:
        return {key: {**common, "status": reason} for key in memberships}

    expected_session = "post" if settled_close else "rth"
    if market != "us" or session != expected_session:
        return unavailable("unsupported_session"), None
    if now.tzinfo is None:
        return unavailable("invalid_evaluation_clock"), None
    # Reuse the calendar owner, including early closes; do not copy holiday math.
    from engine.session_digest import session_window_et
    from zoneinfo import ZoneInfo
    session_date = now.astimezone(ZoneInfo("America/New_York")).date()
    opened, closed = session_window_et(session_date)
    if ((settled_close and now < closed)
            or (not settled_close and not opened <= now <= closed)):
        return unavailable("outside_regular_session"), None
    tickers = sorted({"SPY"}.union(*(set(v) for v in memberships.values())))
    points = {}
    for ticker in tickers:
        point = _comparison_point(quotes.get(ticker), now, opened, closed,
                                  settled_close=settled_close)
        if point is not None:
            points[ticker] = point
    baseline = {"schema": _BASELINE_SCHEMA, "market": market, "session": "rth",
                "observation_kind": observation_kind,
                "session_date": session_date.isoformat(), "observed_at": now.isoformat(),
                "memberships": memberships, "quotes": points}
    prior = previous.get("observation_baseline") if isinstance(previous, dict) else None
    if not isinstance(prior, dict):
        return unavailable("baseline_missing"), baseline
    if prior.get("schema") != _BASELINE_SCHEMA:
        return unavailable("baseline_invalid"), baseline
    if any(prior.get(k) != baseline[k] for k in ("market", "session", "session_date")):
        return unavailable("session_boundary"), baseline
    try:
        prior_observed = datetime.fromisoformat(prior["observed_at"])
        if prior_observed.tzinfo is None:
            raise ValueError("naive baseline")
    except (KeyError, TypeError, ValueError):
        return unavailable("baseline_invalid"), baseline
    if prior_observed >= now:
        # A delayed/reordered build cannot rewind a retained newer baseline.
        return unavailable("baseline_nonadvancing"), prior
    prior_quotes, prior_members = prior.get("quotes"), prior.get("memberships")
    if not isinstance(prior_quotes, dict) or not isinstance(prior_members, dict):
        return unavailable("baseline_invalid"), baseline
    prior_kind = prior.get("observation_kind", "regular")
    if prior_kind not in ("regular", "settled_regular"):
        return unavailable("baseline_invalid"), baseline
    def prior_point(ticker: str) -> dict[str, Any] | None:
        return _comparison_point(prior_quotes.get(ticker), prior_observed, opened, closed,
                                 settled_close=prior_kind == "settled_regular")
    bench = points.get("SPY")
    prior_bench = prior_point("SPY")
    if bench is None or prior_bench is None:
        return unavailable("benchmark_unavailable"), prior if prior_bench is not None else baseline
    if bench["ts"] < prior_bench["ts"]:
        return unavailable("benchmark_nonadvancing"), prior
    if bench["ts"] == prior_bench["ts"]:
        # A vendor correction is not a new interval, but future comparisons
        # must not use the superseded price. Reset on an equal-time revision;
        # retain the prior baseline on a byte-equivalent market observation.
        corrected = False
        for ticker, point in points.items():
            old = prior_point(ticker)
            if old is not None and point["ts"] == old["ts"] and point != old:
                corrected = True
        if corrected:
            return unavailable("baseline_corrected"), baseline
        result = unavailable("benchmark_nonadvancing")
        if settled_close and prior_kind == "settled_regular" and bench == prior_bench:
            # A measurement is not an event delivery. Keep the already-measured
            # closing interval visible while its unchanged source remains fresh;
            # explicitly mark this delivery as retained, never a new observation.
            rows_raw = previous.get("baskets")
            old_rows = {row.get("id"): row for row in (rows_raw if isinstance(rows_raw, list) else [])
                        if isinstance(row, dict) and isinstance(row.get("id"), str)}
            endpoint = datetime.fromtimestamp(bench["ts"] / 1000, timezone.utc).isoformat()
            for key, members in memberships.items():
                old_members = prior_members.get(key)
                if (not isinstance(old_members, list)
                        or not all(isinstance(member, str) for member in old_members)
                        or len(members) != len(set(members))
                        or len(old_members) != len(set(old_members))
                        or set(members) != set(old_members)):
                    continue
                if any(points.get(ticker) != prior_point(ticker) for ticker in members):
                    continue
                old = old_rows.get(key, {}).get("intraday_comparison")
                if (not isinstance(old, dict) or old.get("schema") != _COMPARISON_SCHEMA
                        or old.get("status") != "observed"
                        or old.get("observation_kind") != "settled_regular"
                        or old.get("session_date") != session_date.isoformat()
                        or old.get("source_asof") != endpoint):
                    continue
                result[key] = {**old, "delivery_state": "retained", "is_new_observation": False}
        return result, prior
    if _comparison_signature(bench) != _comparison_signature(prior_bench):
        return unavailable("benchmark_basis_changed"), baseline
    bench_return = bench["price"] / prior_bench["price"] - 1
    if not math.isfinite(bench_return) or bench_return <= -1:
        return unavailable("benchmark_invalid_return"), baseline
    allowed_skew_ms = min(_COMPARISON_MAX_SKEW_MS, (bench["ts"] - prior_bench["ts"]) / 10)
    clock = {
        "max_clock_skew_seconds": allowed_skew_ms / 1000,
        "reference_asof": datetime.fromtimestamp(prior_bench["ts"] / 1000, timezone.utc).isoformat(),
        "source_asof": datetime.fromtimestamp(bench["ts"] / 1000, timezone.utc).isoformat(),
        "elapsed_minutes": (bench["ts"] - prior_bench["ts"]) / 60_000,
        "session_date": session_date.isoformat(),
    }
    result = {}
    for key, members in memberships.items():
        old_members = prior_members.get(key)
        if (len(members) != len(set(members)) or not isinstance(old_members, list)
                or not all(isinstance(member, str) for member in old_members)
                or len(old_members) != len(set(old_members))
                or set(old_members) != set(members)):
            result[key] = {**common, "status": "membership_changed"}
            continue
        returns = []
        excluded: dict[str, int] = {}
        for ticker in members:
            point = points.get(ticker)
            old = prior_point(ticker)
            reason = None
            if point is None or old is None:
                reason = "missing_observation"
            elif point["ts"] <= old["ts"]:
                reason = "nonadvancing_source"
            elif _comparison_signature(point) != _comparison_signature(old):
                reason = "basis_or_anchor_changed"
            elif (abs(point["ts"] - bench["ts"]) > allowed_skew_ms
                  or abs(old["ts"] - prior_bench["ts"]) > allowed_skew_ms):
                reason = "source_clock_skew"
            else:
                value = point["price"] / old["price"] - 1
                if math.isfinite(value) and value > -1:
                    returns.append(value)
                else:
                    reason = "invalid_return"
            if reason is not None:
                excluded[reason] = excluded.get(reason, 0) + 1
        count, total = len(returns), len(members)
        coverage = count / total if total else 0
        row = {**common, **clock, "matched_members": count, "total_members": total,
               "coverage_pct": round(100 * coverage, 3), "excluded": excluded}
        if not returns or coverage < MIN_COVERAGE:
            result[key] = {**row, "status": "insufficient_matched_coverage"}
            continue
        absolute = math.fsum(value / count for value in returns)
        relative = (1 + absolute) / (1 + bench_return) - 1
        if not math.isfinite(relative):
            result[key] = {**row, "status": "invalid_return"}
            continue
        result[key] = {
            **row, "status": "observed", "delivery_state": "new", "is_new_observation": True,
            "absolute_change_pct": round(100 * absolute, 6),
            "benchmark_change_pct": round(100 * bench_return, 6),
            "relative_change_pct": round(100 * relative, 6),
            "positive_relative_breadth_pct": round(100 * sum(r > bench_return for r in returns) / count, 3),
        }
    return result, baseline


def _load_lastgood(out_dir: Path, name: str = LASTGOOD_FILENAME) -> dict[str, Any] | None:
    """Load the lastgood sidecar from out_dir. Returns None if absent."""
    p = out_dir / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as e:
        log.debug("lastgood load failed: %s", e)
        return None


def _save_lastgood(result: dict[str, Any], out_dir: Path,
                   name: str = LASTGOOD_FILENAME, *,
                   observation_baseline: dict | None = None) -> None:
    """Persist a live/delayed pulse result as the lastgood sidecar."""
    p = out_dir / name
    temporary: Path | None = None
    try:
        retained = dict(result)
        if observation_baseline is not None:
            retained["observation_baseline"] = observation_baseline
        encoded = json.dumps(retained, separators=(",", ":"), allow_nan=False) + "\n"
        # The sole existing sidecar is replaced atomically: readers must see
        # either the old complete baseline or the new one, never partial JSON.
        candidate = out_dir / f".{name}.{uuid.uuid4().hex}.tmp"
        # O_EXCL owns this temporary file; 0666 preserves normal process-umask
        # behavior on first creation. Existing read permissions survive replace.
        descriptor = os.open(candidate, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        temporary = candidate
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            try:
                old_mode = p.stat().st_mode & 0o777
            except FileNotFoundError:
                old_mode = None
            if old_mode is not None:
                os.fchmod(handle.fileno(), old_mode)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, p)
        temporary = None
        log.info("saved lastgood sidecar → %s", p)
    except Exception as e:
        print(f"::warning::could not save lastgood sidecar: {e}", flush=True)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


# ── shock-day relative bid ─────────────────────────────────────────────────────

def _shock_day_relative_bid(
    market_drivers: dict[str, Any] | None,
    baskets_data: list[dict[str, Any]],
    quotes: dict[str, Any],
    now_ms: int,
    stale_min: int = LIVE_STALE_MIN,
) -> dict[str, Any] | None:
    """Populate ONLY when market_drivers shows oil_shock/geopolitical-family primary
    AND index is down. Returns the same-session descriptive readout per FT-R3.

    NO beneficiary/casualty/direction fields. Carries T+1 fade note.
    """
    if not market_drivers:
        return None

    primary = market_drivers.get("primary", "")
    family = market_drivers.get("family", "")
    # Gate: oil_shock primary OR geopolitical family
    if primary not in _SHOCK_PRIMARY_KEYS and family not in _SHOCK_FAMILIES:
        return None

    # Gate: index (SPY) must be down today
    spy = quotes.get("SPY") or quotes.get("^GSPC")
    if spy is None:
        return None
    spy_chg = spy.get("changePct")
    if spy_chg is None or float(spy_chg) >= 0:
        return None

    # Build rows: observed live move for each basket — descriptive, no ranking
    rows = []
    for b in baskets_data:
        if b["live_ew_chg_pct"] is not None:
            rows.append({"id": b["id"], "live_ew_chg_pct": b["live_ew_chg_pct"]})

    if not rows:
        return None

    return {
        "active_driver": primary or family,
        "index_chg_pct": round(float(spy_chg), 3),
        "rows": rows,
        "t1_fade_note": _T1_FADE_NOTE,
    }


# ── market_drivers loading ─────────────────────────────────────────────────────

def _load_market_drivers(drivers_path: Path | None) -> dict[str, Any] | None:
    """Load site/live/market_drivers.json. Returns None if unavailable."""
    from lib import config

    p = drivers_path
    if p is None:
        site_dir = config.ROOT / config.load()["storage"]["site_dir"]
        p = site_dir / "live" / "market_drivers.json"
    if not p or not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


# ── W5: AI-capex complex rollup ───────────────────────────────────────────────

# AI-capex complex basket ids (mirrors engine/demand_capex.AI_CAPEX_THEMES keys).
# FT-R10: FTR creates no new theme vocabulary; we import the canonical set.
def _ai_capex_ids() -> frozenset[str]:
    try:
        from engine.demand_capex import AI_CAPEX_THEMES
        return frozenset(AI_CAPEX_THEMES.keys())
    except Exception:
        # Fallback hard-coded to avoid dependency failures making the build fatal
        return frozenset({
            "memory_storage", "ai_semiconductors", "semicap_equipment",
            "data_center_power", "grid_electrification", "nuclear_power",
        })


def _compute_complexes(
    baskets_data: list[dict[str, Any]],
    quotes: dict[str, Any],
    now_ms: int,
    stale_min: int = LIVE_STALE_MIN,
) -> list[dict[str, Any]]:
    """W5: aggregate live basket pulse to the AI-capex complex.

    For the ai_capex complex (engine/demand_capex.AI_CAPEX_THEMES keys):
    - live_ew_chg_pct: EW over member baskets' live_ew_chg_pct (skipping nulls)
    - n_baskets: total baskets in the complex
    - n_live: baskets with a non-null live_ew_chg_pct
    - only_green_complex: bool — this complex EW positive while SPY proxy negative
      AND all other computable complexes negative (descriptive, same-session)

    Coverage-null rules: if no member basket has live_ew_chg_pct, live_ew_chg_pct
    is None (honest null). FT-R3: descriptive same-session only.
    """
    ai_ids = _ai_capex_ids()

    # Index baskets by id
    by_id: dict[str, dict[str, Any]] = {b["id"]: b for b in baskets_data}

    # Compute EW for ai_capex complex
    ai_chgs: list[float] = []
    n_baskets = 0
    for bid in ai_ids:
        if bid in by_id:
            n_baskets += 1
            chg = by_id[bid].get("live_ew_chg_pct")
            if chg is not None:
                ai_chgs.append(float(chg))

    ai_ew = round(sum(ai_chgs) / len(ai_chgs), 3) if ai_chgs else None

    # SPY proxy: read from quotes directly (stale-gated)
    spy_q = quotes.get("SPY") or quotes.get("^GSPC")
    spy_chg: float | None = None
    if spy_q is not None and not _is_stale(spy_q, now_ms, stale_min):
        raw = spy_q.get("changePct")
        if raw is not None:
            spy_chg = float(raw)

    # only_green_complex: ai_capex EW positive while SPY negative
    # AND all other computable complex EWs are also negative.
    # "Other computable complexes" = there are none yet in v1 (only ai_capex).
    # Per the spec: "all other computable complexes negative" — with only one
    # complex in v1, this condition is satisfied vacuously when SPY is down.
    only_green: bool = (
        ai_ew is not None
        and spy_chg is not None
        and ai_ew > 0
        and spy_chg < 0
    )

    return [
        {
            "complex_id": "ai_capex",
            "live_ew_chg_pct": ai_ew,
            "n_baskets": n_baskets,
            "n_live": len(ai_chgs),
            "only_green_complex": only_green,
        }
    ]


# ── mode detection ────────────────────────────────────────────────────────────

def _detect_mode(quotes: dict[str, Any], session: str, now_ms: int,
                 stale_min: int, all_members: list[str]) -> str:
    """Determine which pulse mode applies given the current state.

    Rules (TS-R1):
      live     — pre/rth session + quotes present + median member delay <= stale_min
      delayed  — pre/rth session + quotes present + median member delay > stale_min
      last_rth — post/closed session (serve from sidecar)
      eod      — post/closed session with no sidecar (EOD fallback)

    Note: last_rth vs eod distinction is made by the caller (it checks for sidecar).
    This function only returns live, delayed, or a placeholder for post/closed.
    """
    if session in ("post", "closed"):
        return MODE_LAST_RTH  # caller will check for sidecar and may downgrade to eod

    if not quotes:
        return MODE_LAST_RTH  # no quotes at all → try sidecar

    med = _median_member_delay(all_members, quotes, now_ms)
    if med is None:
        return MODE_LAST_RTH  # no member quotes at all

    return MODE_LIVE if med <= stale_min else MODE_DELAYED


# ── main build ─────────────────────────────────────────────────────────────────

def _session_close_utc(now: datetime, market: str = "us") -> datetime | None:
    """Existing US actual close as UTC; preserve the incumbent HK fallback.

    US half days reuse engine.session_digest. HK's existing 16:00-local
    behavior is unchanged by the US closing-comparison increment.
    """
    from zoneinfo import ZoneInfo

    cal = _market_calendar(market)
    local = now.astimezone(ZoneInfo(MARKETS[market]["tz"]))
    if not cal.is_session(local.date()):
        return None
    if market == "us":
        from engine.session_digest import session_window_et
        _, close_local = session_window_et(local.date())
    else:
        close_local = local.replace(hour=16, minute=0, second=0, microsecond=0)
    return close_local.astimezone(timezone.utc)


def _settle_quote_ok(q: dict[str, Any], close_ms: int) -> bool:
    """True when this quote's price basis pins the completed regular session."""
    basis = q.get("basis")
    ts = q.get("ts")
    if basis == "regular":
        # regularMarketPrice; require the stamp at/after the bell (delayed feeds
        # show intraday 'regular' prints until ~16:15 ET).
        return ts is None or ts >= close_ms - 60_000
    if basis == "day":
        return True
    if basis in ("trade", "minute"):
        # only prints AT the bell (closing auction) — a pre-close delayed print
        # is the frozen-tape problem this mode exists to replace, and a later
        # print is extended-hours drift
        return (ts is not None
                and close_ms - _SETTLE_TOL_MS <= ts <= close_ms + _SETTLE_TOL_MS)
    return False


def _settled_ew_chg(members: list[str], quotes: dict[str, Any],
                    close_ms: int) -> tuple[float | None, int, int]:
    """EW day move over settle-clean member quotes.

    Returns (ew_chg_pct or None, n_quoted, n_settle_ok). Coverage gate uses
    MIN_COVERAGE over the full membership, same as the live path.
    """
    vals: list[float] = []
    n_quoted = 0
    for m in members:
        q = quotes.get(m)
        if not q or q.get("changePct") is None:
            continue
        n_quoted += 1
        if not _settle_quote_ok(q, close_ms):
            continue
        vals.append(float(q["changePct"]))
    n_ok = len(vals)
    if not vals or n_ok < max(1, len(members) * MIN_COVERAGE):
        return None, n_quoted, n_ok
    return round(sum(vals) / len(vals), 3), n_quoted, n_ok


def _settled_build(now: datetime, session: str, quotes: dict[str, Any],
                   resolved_path: Path | None, baskets_meta: dict[str, Any],
                   stale_min: int, now_ms: int,
                   market: str = "us") -> dict[str, Any] | None:
    """Recompute the completed session's EW basket moves from settle-clean quotes.

    Returns the full result dict (mode=last_rth + settled_close=True +
    session_date, TS-R2) or None when the snapshot cannot honestly describe the
    close — too few settle-basis records (e.g. the feed's US records still carry
    extended-hours prints) or not a session day.
    """
    close_dt = _session_close_utc(now, market)
    if close_dt is None:
        return None
    close_ms = int(close_dt.timestamp() * 1000)

    baskets_data: list[dict[str, Any]] = []
    n_quoted_total = 0
    n_settled_total = 0
    for basket_id, basket in baskets_meta.items():
        members = _active_members(basket)
        if not members:
            continue
        ew, n_quoted, n_ok = _settled_ew_chg(members, quotes, close_ms)
        n_quoted_total += n_quoted
        n_settled_total += n_ok
        baskets_data.append({
            "id": basket_id,
            "n_members": len(members),
            "n_quoted": n_quoted,
            "live_ew_chg_pct": ew,
            "cum_2d_pct": _cum_2d(basket_id, ew, market),
            "tape_rank": None,
            "stale": False,
            "delay_min": None,
        })
    if not baskets_data or n_quoted_total == 0:
        return None
    if n_settled_total / n_quoted_total < SETTLE_MIN_FRACTION:
        log.info("settled-close recompute declined — %d/%d quotes settle-basis",
                 n_settled_total, n_quoted_total)
        return None

    rank_map = _tape_ranks(baskets_data)
    for b in baskets_data:
        b["tape_rank"] = rank_map.get(b["id"])

    from zoneinfo import ZoneInfo
    session_date = now.astimezone(ZoneInfo(MARKETS[market]["tz"])).date().isoformat()
    n_non_null = sum(1 for b in baskets_data if b["live_ew_chg_pct"] is not None)
    log.info("settled-close recompute: %d baskets, %d/%d settle-basis quotes",
             len(baskets_data), n_settled_total, n_quoted_total)
    us_features = MARKETS[market]["us_features"]
    return {
        "schema": "basket_pulse.v1",
        "market": market,
        "as_of_utc": now.isoformat(),
        "as_of_quotes": close_dt.isoformat(),
        "built": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "session": session,
        "mode": MODE_LAST_RTH,
        "settled_close": True,
        "session_date": session_date,
        "delay_min_median": None,
        "coverage_pct": round(n_non_null / len(baskets_data) * 100, 1),
        "quotes_source": str(resolved_path) if resolved_path else None,
        "n_quotes_total": len(quotes),
        "stale_min": stale_min,
        "baskets": baskets_data,
        "od_spread_print": None,
        "shock_day_relative_bid": None,
        "complexes": (_compute_complexes(baskets_data, {}, now_ms, stale_min)
                      if us_features else []),
    }


def _load_theme_flow(path: Path | None = None,
                     market: str = "us") -> tuple[dict[str, dict], str | None]:
    """Per-basket nightly stock-flow context from site/<names_dir>/baskets.json.

    Plucks theme_intel.themes[].tape.flow (engine/basket_tape — dollar-volume
    surge + CMF; directional:false, DT-W1a: descriptive only). ({}, None) on any
    failure — additive, degrade-never-raise. (HK theme_intel carries no tape.flow
    today, so the HK attach is a natural no-op until that organ accrues.)
    """
    try:
        if path is None:
            from lib import config
            path = (config.ROOT / config.load()["storage"]["site_dir"]
                    / MARKETS[market]["names_dir"] / "baskets.json")
        data = json.loads(Path(path).read_text())
    except Exception as e:  # noqa: BLE001
        log.debug("theme flow unavailable: %s", e)
        return {}, None
    ti = data.get("theme_intel") or {}
    out: dict[str, dict] = {}
    for th in ti.get("themes") or []:
        tape = th.get("tape") or {}
        flow = tape.get("flow") or {}
        if not flow or not th.get("id"):
            continue
        out[th["id"]] = {
            "dollar_vol_surge": flow.get("dollar_vol_surge"),
            "cmf": flow.get("cmf"),
            "label_en": flow.get("label_en"),
            "label_zh": flow.get("label_zh"),
            "as_of": tape.get("as_of"),
        }
    return out, (ti.get("as_of") or data.get("as_of"))


def _attach_day_flow(result: dict[str, Any], market: str = "us") -> None:
    """Attach nightly stock-flow context to a post/closed pulse (rows gain
    day_flow; top level gains day_flow_as_of). Descriptive only — the consuming
    band prints the as-of stamp and the no-forward-edge note. Additive: absent
    or malformed data leaves the result untouched."""
    try:
        flow_map, flow_as_of = _load_theme_flow(market=market)
        if not flow_map:
            return
        for b in result.get("baskets") or []:
            f = flow_map.get(b.get("id"))
            if f:
                b["day_flow"] = f
        result["day_flow_as_of"] = flow_as_of
    except Exception as e:  # noqa: BLE001
        log.debug("day_flow attach skipped: %s", e)


def build(
    *,
    quotes_path: Path | None = None,
    membership_path: Path | None = None,
    drivers_path: Path | None = None,
    stale_min: int = LIVE_STALE_MIN,
    now: datetime | None = None,
    out_dir: Path | None = None,
    market: str = "us",
) -> dict[str, Any]:
    """Build the basket pulse JSON. Returns the full output dict.

    Implements graded modes (TS-R1 honest-delay law):
      live/delayed — compute from quotes; save lastgood sidecar.
      last_rth     — load lastgood sidecar; stamp mode=last_rth.
      eod          — compute 1d EW from OHLCV closes (US) / basket levels (HK);
                     stamp mode=eod + bar date.

    Exit-0-always contract: any unexpected exception is caught; the caller will
    emit ::warning:: and write a degraded output (see main()).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("basket pulse evaluation clock must be timezone-aware")
    now_ms = int(now.timestamp() * 1000)

    mcfg = MARKETS[market]
    us_features = mcfg["us_features"]
    lastgood_name = mcfg["lastgood_name"]

    session = _market_session(now, market)
    quotes, resolved_path = _load_quotes(quotes_path)
    baskets_meta = _load_membership(membership_path, market)
    # market_drivers is a US-session artifact (shock/driver detection) — never
    # gate another market's tape on it.
    market_drivers = _load_market_drivers(drivers_path) if us_features else None

    # Collect all active members for global delay median
    all_members: list[str] = []
    for basket in baskets_meta.values():
        all_members.extend(_active_members(basket))

    # Determine mode
    mode = _detect_mode(quotes, session, now_ms, stale_min, all_members)

    # ── last_rth / eod branch ─────────────────────────────────────────────────
    if mode == MODE_LAST_RTH:
        # TS-U5: settled-close recompute — on a post-session tick the quotes
        # snapshot (live-quotes keeps running after the bell) already carries
        # the official settle for every member whose record pins the regular
        # session. A recompute of the DAY's move beats serving a tape frozen
        # at the last RTH tick (~15:30 ET on the delayed feed). Only the same
        # evening (session == "post"): later runs risk vendor prevClose rolls.
        if session == "post" and quotes:
            settled = _settled_build(now, session, quotes, resolved_path,
                                     baskets_meta, stale_min, now_ms, market)
            if settled is not None:
                baseline = None
                if market == "us":
                    previous = _load_lastgood(out_dir, lastgood_name) if out_dir is not None else None
                    comparisons, baseline = _intraday_comparisons(
                        baskets_meta, quotes, previous, now=now, market=market,
                        session=session, settled_close=True)
                    for row in settled["baskets"]:
                        row["intraday_comparison"] = comparisons.get(row["id"])
                if out_dir is not None:
                    _save_lastgood(settled, out_dir, lastgood_name, observation_baseline=baseline)
                _attach_day_flow(settled, market)
                return settled

        # Try to load the lastgood sidecar
        if out_dir is not None:
            lastgood = _load_lastgood(out_dir, lastgood_name)
        else:
            lastgood = None

        if lastgood is not None:
            # TS-U0 age guard: if the sidecar is older than the last completed NYSE
            # session (e.g. intraday lane was down over a weekend/holiday), fall through
            # to eod so we don't serve a multi-day-old read stamped "LAST SESSION".
            sidecar_ok = False
            try:
                cal = _market_calendar(market)  # lazy, avoids circular at module level
                as_of_str = lastgood.get("as_of_utc") or lastgood.get("as_of_quotes")
                if as_of_str:
                    sidecar_date = datetime.fromisoformat(as_of_str).date()
                    last_completed = cal.expected_last_session(now)
                    sidecar_ok = (sidecar_date >= last_completed)
                    if not sidecar_ok:
                        log.info(
                            "lastgood sidecar date %s is older than last session %s — "
                            "falling through to eod",
                            sidecar_date, last_completed,
                        )
            except Exception as exc:  # noqa: BLE001
                # If calendar check fails, be conservative and serve the sidecar anyway
                log.debug("lastgood age-check error (serving anyway): %s", exc)
                sidecar_ok = True

            if sidecar_ok:
                # Serve the last good read with updated mode stamp
                lastgood = dict(lastgood)
                lastgood.pop("observation_baseline", None)
                lastgood["mode"] = MODE_LAST_RTH
                lastgood["built"] = now.strftime("%Y-%m-%d %H:%M:%S UTC")
                # Preserve original as_of_quotes from lastgood; add a served_utc stamp
                lastgood["served_utc"] = now.isoformat()
                lastgood["session"] = session
                _attach_day_flow(lastgood, market)
                log.info("serving lastgood sidecar (mode=last_rth) from %s",
                         lastgood.get("as_of_utc", "?"))
                return lastgood

        # No sidecar → EOD fallback
        log.info("no lastgood sidecar — attempting EOD fallback (mode=eod)")
        from_levels = mcfg["eod_source"] == "levels"
        baskets_data: list[dict[str, Any]] = []
        bar_dates: list[str] = []
        for basket_id, basket in baskets_meta.items():
            members = _active_members(basket)
            if not members:
                continue
            eod_chg, bar_date = (_eod_basket_chg_levels(basket_id, market)
                                 if from_levels
                                 else _eod_basket_chg(basket_id, members))
            baskets_data.append({
                "id": basket_id,
                "n_members": len(members),
                "n_quoted": 0,
                "live_ew_chg_pct": eod_chg,
                "cum_2d_pct": None,
                "tape_rank": None,
                "stale": True,
                "delay_min": None,
                "bar_date": bar_date,
            })
            if bar_date:
                bar_dates.append(bar_date)

        rank_map = _tape_ranks(baskets_data)
        for b in baskets_data:
            b["tape_rank"] = rank_map.get(b["id"])

        n_non_null = sum(1 for b in baskets_data if b["live_ew_chg_pct"] is not None)
        eod_bar_date = (max(set(bar_dates), key=bar_dates.count)
                        if bar_dates else None)
        eod_result: dict[str, Any] = {
            "schema": "basket_pulse.v1",
            "market": market,
            "as_of_utc": now.isoformat(),
            "as_of_quotes": eod_bar_date,
            "built": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "session": session,
            "mode": MODE_EOD,
            "delay_min_median": None,
            "coverage_pct": round(n_non_null / len(baskets_data) * 100, 1) if baskets_data else 0.0,
            "quotes_source": None,
            "n_quotes_total": 0,
            "stale_min": stale_min,
            "baskets": baskets_data,
            "od_spread_print": None,
            "shock_day_relative_bid": None,
            "complexes": (_compute_complexes(baskets_data, {}, now_ms, stale_min)
                          if us_features else []),
        }
        _attach_day_flow(eod_result, market)
        return eod_result

    # ── live / delayed branch ─────────────────────────────────────────────────
    include_delayed = (mode == MODE_DELAYED)

    # Global delay median
    delay_med = _median_member_delay(all_members, quotes, now_ms)

    baskets_data_live: list[dict[str, Any]] = []
    coverage_sum = 0.0
    coverage_count = 0

    for basket_id, basket in baskets_meta.items():
        members = _active_members(basket)
        if not members:
            continue
        n_members = len(members)

        live_ew, n_quoted, _, any_stale = _ew_chg(
            members, quotes, now_ms, stale_min,
            include_delayed=include_delayed)

        # Per-basket delay median
        basket_delay = _median_member_delay(members, quotes, now_ms)

        source_clock = _source_clock_evidence(
            members, quotes, now_ms, stale_min, include_delayed)
        coverage_frac = source_clock["n_priced"] / n_members if n_members > 0 else 0.0
        coverage_sum += coverage_frac
        coverage_count += 1

        cum_2d = _cum_2d(basket_id, live_ew, market)

        baskets_data_live.append({
            "id": basket_id,
            "n_members": n_members,
            "n_quoted": n_quoted,
            "live_ew_chg_pct": live_ew,
            "cum_2d_pct": cum_2d,
            "tape_rank": None,  # filled below
            "stale": bool(any_stale),
            "delay_min": round(basket_delay, 1) if basket_delay is not None else None,
            **source_clock,
        })

    # ── cross-sectional ranks ──────────────────────────────────────────────────
    rank_map = _tape_ranks(baskets_data_live)
    for b in baskets_data_live:
        b["tape_rank"] = rank_map.get(b["id"])

    # ── offense/defense spread (fresh-gated: only in live mode; US organ) ─────
    od_spread = (_od_spread(quotes, now_ms, stale_min)
                 if (mode == MODE_LIVE and us_features) else None)

    # ── shock-day relative bid (US organ — market_drivers is None otherwise) ──
    shock_bid = _shock_day_relative_bid(
        market_drivers, baskets_data_live, quotes, now_ms, stale_min)

    # ── coverage summary ───────────────────────────────────────────────────────
    coverage_pct = round(coverage_sum / coverage_count * 100, 1) if coverage_count else 0.0

    # ── W5: AI-capex complex rollup (US organ) ─────────────────────────────────
    complexes = (_compute_complexes(baskets_data_live, quotes, now_ms, stale_min)
                 if us_features else [])

    source_clock = _source_clock_evidence(
        all_members, quotes, now_ms, stale_min, include_delayed)

    # ── assemble output ────────────────────────────────────────────────────────
    result: dict[str, Any] = {
        "schema": "basket_pulse.v1",
        "market": market,
        "as_of_utc": now.isoformat(),
        "as_of_quotes": source_clock["source_asof"],
        **source_clock,
        "built": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "session": session,
        "mode": mode,
        "delay_min_median": round(delay_med, 1) if delay_med is not None else None,
        "coverage_pct": coverage_pct,
        "quotes_source": str(resolved_path) if resolved_path else None,
        "n_quotes_total": len(quotes),
        "stale_min": stale_min,
        "baskets": baskets_data_live,
        "od_spread_print": od_spread,
        "shock_day_relative_bid": shock_bid,
        "complexes": complexes,
    }

    previous = _load_lastgood(out_dir, lastgood_name) if out_dir is not None else None
    comparisons, baseline = _intraday_comparisons(
        baskets_meta, quotes, previous, now=now, market=market, session=session)
    for row in result["baskets"]:
        row["intraday_comparison"] = comparisons.get(row["id"])

    # Reuse the existing single-writer last-good file; no history store or ledger.
    if out_dir is not None:
        _save_lastgood(result, out_dir, lastgood_name, observation_baseline=baseline)

    return result


def main() -> None:
    import argparse
    from lib import config

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    ap = argparse.ArgumentParser(description="Build site/live/basket_pulse.json.")
    ap.add_argument("--out", default=None, help="output path (default: site/live/<market pulse name>)")
    ap.add_argument("--quotes", default=None, help="path to quotes.json snapshot")
    ap.add_argument("--drivers", default=None, help="path to market_drivers.json")
    ap.add_argument("--stale-min", type=int, default=LIVE_STALE_MIN)
    ap.add_argument("--market", default="us", choices=sorted(MARKETS),
                    help="which market's baskets to pulse (default: us)")
    args = ap.parse_args()

    site_dir = config.ROOT / config.load()["storage"]["site_dir"]
    out_path = (Path(args.out) if args.out
                else site_dir / "live" / MARKETS[args.market]["out_name"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_dir = out_path.parent

    try:
        result = build(
            quotes_path=Path(args.quotes) if args.quotes else None,
            drivers_path=Path(args.drivers) if args.drivers else None,
            stale_min=args.stale_min,
            out_dir=out_dir,
            market=args.market,
        )
    except Exception as exc:
        print(f"::warning::basket_pulse build failed: {exc}", flush=True)
        # Emit a degraded placeholder — exit 0 always per contract
        now = datetime.now(timezone.utc)
        result = {
            "schema": "basket_pulse.v1",
            "market": args.market,
            "as_of_utc": now.isoformat(),
            "as_of_quotes": None,
            "built": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "session": "unknown",
            "mode": "error",
            "delay_min_median": None,
            "coverage_pct": 0.0,
            "error": str(exc),
            "baskets": [],
            "od_spread_print": None,
            "shock_day_relative_bid": None,
            "complexes": [],
        }

    out_path.write_text(
        json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n")
    n_baskets = len(result.get("baskets") or [])
    n_quoted = sum(b.get("n_quoted", 0) for b in (result.get("baskets") or []))
    log.info("wrote %s — %d baskets, %d symbols quoted, session=%s, mode=%s, coverage=%.1f%%",
             out_path, n_baskets, n_quoted,
             result.get("session"), result.get("mode", "?"), result.get("coverage_pct", 0))


if __name__ == "__main__":
    main()
