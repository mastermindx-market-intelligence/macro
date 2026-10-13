"""The live overlay: the thin "fast brain" that sits on top of the nightly build.

Doctrine (see research/LIVE_DATA_ARCHITECTURE.md and the design discussion):
  - The nightly build is the SLOW BRAIN. Its scores — regime/quad, conviction,
    GTAA allocation — are anchored to daily->quarterly data and are deliberately
    hysteresis-gated. Intraday ticks must NOT rewrite them, or a noisy print
    would manufacture false regime flips.
  - This module is the FAST LAYER. Given a live last-price it recomputes only the
    cheap price-sensitive leaves (technicals snapshot) and answers ONE extra
    question the slow brain can't: "has the live move invalidated a nightly
    assumption?" — i.e. has the single-session move breached the nightly
    EXPECTED-MOVE band. That is the *divergence flag*; it never silently edits a
    baseline score, it surfaces the conflict so a consumer can question it.

So the contract a consumer (Mastermind, the browser) follows is:
  baseline (nightly) = the decision spine; overlay (live) = timing + invalidation.

Everything here is pure and importable (no network, no disk writes) so it is
fully unit-testable and so the trading bot can call the SAME recompute the
website uses — reading the nightly baseline JSON + splicing a live price.
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from engine import technicals
from functools import lru_cache
from lib import config, store
from lib.market_observations import filter_session_observations
from lib.market_session import (cash_market_for_symbol, market_local_date,
                                missed_sessions, session_freshness, session_status)

log = logging.getLogger("live_overlay")

# A single-session move beyond this is treated as a bad print, not a signal — it
# routes the leg to "stale" so a glitch tick can't manufacture a divergence or a
# bogus allocation mark. Overridable per-build from config.yml live.max_chg_pct.
DEFAULT_MAX_CHG_PCT = 35.0
_Z90 = 1.645  # ~5th/95th-pct multiplier for a (log)normal one-session move


# --------------------------------------------------------- baseline reads ----

@lru_cache(maxsize=6)
def _wide_close_panel(path: str, _mtime_ns: int, _size: int) -> pd.DataFrame:
    """Process-local reuse of an existing panel, invalidated by its file version."""
    return pd.read_parquet(path)


def _cash_history(close: pd.Series | None, market: str, now=None) -> pd.Series | None:
    if close is None or close.empty:
        return None
    values = pd.to_numeric(close, errors="coerce").replace(
        [float("inf"), float("-inf")], float("nan")).dropna()
    values = values.loc[values > 0]
    frame = filter_session_observations(values.to_frame("close"), market, now=now)
    return frame["close"].sort_index() if not frame.empty else None


def read_close(ticker: str) -> pd.Series | None:
    """Read a whole adjusted series from the incumbent regional price owners.

    The freshest regional through-date wins; deep regional OHLCV wins ties.
    US and unrelated assets retain the incumbent yahoo-then-stocks precedence.
    Never stitch independently adjusted series, or invent a new persistent cache.
    """
    market = cash_market_for_symbol(ticker)
    regional = {
        "cn": (("china_stocks", "china"), (("china_search", "closes"),
                                           ("china_breadth", "_closes_cache"))),
        "hk": (("hk_stocks", "hk_stocks_ext", "hk"), (("hk_search", "closes_deep"),
                                                     ("hk_breadth", "_closes_cache"))),
        "ca": (("canada",), (("canada_search", "closes"),
                              ("canada_breadth", "_closes_cache"))),
    }
    groups, panels = regional.get(market, ((), ()))
    candidates = []
    for group in (*groups, "yahoo", "stocks"):
        df = store.read(group, ticker)
        if df is not None and not df.empty and "close" in df:
            s = _cash_history(df["close"], market) if market else df["close"].astype(float).dropna()
            if s is not None and not s.empty:
                if market not in regional:
                    return s.copy()
                candidates.append(s)
    for group, name in panels:
        path = config.data_dir() / group / f"{name}.parquet"
        try:
            stat = path.stat()
            frame = _wide_close_panel(str(path), stat.st_mtime_ns, stat.st_size)
            if ticker in frame:
                s = _cash_history(frame[ticker], market)
                if s is not None and not s.empty:
                    candidates.append(s)
        except (OSError, ValueError, KeyError):
            continue
    if not candidates:
        return None
    # Python's max preserves the first candidate on an equal date, keeping the
    # regional adjusted source's precedence without mixing adjustment bases.
    return max(candidates, key=lambda s: pd.Timestamp(s.index.max())).copy()

def splice(close: pd.Series, live_price: float,
           ts: datetime | None = None) -> pd.Series:
    """Return a copy of ``close`` with today's bar set to ``live_price`` —
    overwriting the last bar if it is already today, else appending a new bar.
    This is what makes the recomputed indicators reflect the live tick while
    keeping all prior history intact."""
    ts = ts or datetime.now(timezone.utc)
    day = pd.Timestamp(ts).normalize().tz_localize(None)
    out = close.copy()
    out.index = pd.to_datetime(out.index).tz_localize(None)
    if len(out) and out.index[-1].normalize() == day:
        out.iloc[-1] = float(live_price)
    else:
        out.loc[day] = float(live_price)
    return out.sort_index()


# ------------------------------------------------------------ fast leaves ----

def live_tech(close: pd.Series, live_price: float,
              ts: datetime | None = None) -> dict:
    """Technicals snapshot recomputed on the live-spliced series. Same shape as
    the nightly engine.technicals.snapshot so it is a drop-in refresh."""
    return technicals.snapshot(splice(close, live_price, ts))


# ----------------------------------------------------------- market region ----

def region_for(symbol: str) -> str:
    """Coarse exchange region from a (canonical) symbol suffix or caret-index name.

    Mirrors the client-side ``regionOf()`` in live.js so consumers calling this
    server-side function get the same session lookup the browser uses.
    """
    supported = cash_market_for_symbol(symbol)
    if supported:
        return supported
    s = str(symbol or "").upper()
    if s.endswith(".HK"):
        return "hk"
    if s.endswith((".SS", ".SZ", ".BJ")):
        return "cn"
    if s.endswith((".TO", ".V")):
        return "ca"
    # Foreign caret-index tickers: explicit mapping mirrors live.js regionOf().
    if s == "^HSI":
        return "hk"
    if s == "^GSPC":
        return "us"
    if s == "^GSPTSE":
        return "ca"
    if s == "^N225":
        return "jp"
    if s == "^KS11":
        return "kr"
    if s == "^TWII":
        return "tw"
    if s == "^FTSE":
        return "gb"
    if s == "^STOXX50E":
        return "eu"
    return "us"  # plain US tickers, =F futures, -USD crypto


# Local-time trading windows per region (DST handled via zoneinfo). These are an
# fallback for the unrelated regions below. CN/HK/US/CA and Connect use the
# shared projection of the existing exchange calendars, including verified
# holidays and half days. Closure never upgrades missing or stale source data.
#
# Hours cross-verified against the globe-data lunch fields in site/index.html:
#   JP 09:00-15:00 with lunch 11:30-12:30 Asia/Tokyo
#   KR 09:00-15:30 no lunch     Asia/Seoul
#   TW 09:00-13:30 no lunch     Asia/Taipei
#   GB 08:00-16:30 no lunch     Europe/London
#   EU 09:00-17:30 no lunch     Europe/Berlin (STOXX50E / XETRA)
_REGION_HOURS = {
    "us": ("America/New_York", [("09:30", "16:00")]),
    "ca": ("America/Toronto", [("09:30", "16:00")]),
    "cn": ("Asia/Shanghai", [("09:30", "11:30"), ("13:00", "15:00")]),
    "hk": ("Asia/Hong_Kong", [("09:30", "12:00"), ("13:00", "16:00")]),
    "jp": ("Asia/Tokyo",     [("09:00", "11:30"), ("12:30", "15:00")]),
    "kr": ("Asia/Seoul",     [("09:00", "15:30")]),
    "tw": ("Asia/Taipei",    [("09:00", "13:30")]),
    "gb": ("Europe/London",  [("08:00", "16:30")]),
    "eu": ("Europe/Berlin",  [("09:00", "17:30")]),
}


def market_session(region: str, now: datetime | None = None) -> dict:
    """Cash-session status; verified holiday detail for the four supported venues."""
    if str(region).lower() in {"us", "ca", "cn", "hk", "connect"}:
        return session_status(region, now)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    tzname, windows = _REGION_HOURS.get(region, _REGION_HOURS["us"])
    local = now.astimezone(ZoneInfo(tzname))
    open_now = False
    if local.weekday() < 5:  # Mon-Fri
        hm = local.hour * 60 + local.minute
        for start, end in windows:
            sh, sm = map(int, start.split(":"))
            eh, em = map(int, end.split(":"))
            if sh * 60 + sm <= hm < eh * 60 + em:
                open_now = True
                break
    return {"region": region, "open": open_now,
            "local_time": local.strftime("%Y-%m-%d %H:%M %Z")}


# ------------------------------------------------------------- divergence ----

# Flag severities — a consumer can gate on these without re-deriving them.
_SEV = {"no_quote": "info", "within_band": "none", "rsi_cross": "watch",
        "macd_flip": "watch", "band_breach_up": "alert", "band_breach_down": "alert",
        "bad_print": "info", "baseline_stale": "info"}


def expected_move_1d(baseline: dict) -> tuple[float | None, float | None, str | None]:
    """The nightly ONE-SESSION expected-move band (lo%, hi%, source).

    Primary: derive from the cone's annualised vol (``vol_cone_ann``) — a true
    1-day sigma — so the band matches the single-session move we test. Fallback:
    de-annualise the short-horizon (multi-day) cone return quantiles by the
    horizon length. Returns (None, None, None) when neither is available.

    This fixes the original horizon mismatch: comparing a 1-session move to the
    raw 5-day cone quantiles made breaches statistically near-impossible.
    """
    ant = baseline.get("anticipation") or {}
    vca = ant.get("vol_cone_ann")
    if vca:
        sigma_1d = float(vca) / math.sqrt(252.0) * 100.0
        band = round(_Z90 * sigma_1d, 2)
        return -band, band, "vol_cone_ann"
    short = (ant.get("horizons") or {}).get("short") or {}
    ret_q = short.get("ret_q") or {}
    p5, p95 = ret_q.get("p5"), ret_q.get("p95")
    win = short.get("window_td") or 5
    if p5 is not None and p95 is not None and win:
        k = math.sqrt(float(win))
        return round(p5 / k, 2), round(p95 / k, 2), "scaled_short_cone"
    return None, None, None


def divergence(baseline: dict, live_price: float,
               live_tech_snap: dict | None = None) -> dict:
    """Has the live single-session move breached the nightly expected-move band?

    Compares the live close-to-live % move against the nightly ONE-SESSION band
    (expected_move_1d). A breach = the nightly assumption is likely invalidated.
    A move ALSO beyond the multi-day cone tails in a single session is annotated
    ``extreme``. Threshold crossings (RSI/MACD) are a lower-priority signal. Pure;
    does not recompute the cone (a nightly artifact).
    """
    tech = baseline.get("tech") or {}
    prev_close = tech.get("price")
    if prev_close in (None, 0):
        return {"flag": "no_quote", "severity": "info",
                "detail": "no baseline close to compare", "chg_pct": None}

    chg_pct = round((float(live_price) / float(prev_close) - 1) * 100, 2)
    lo, hi, src = expected_move_1d(baseline)

    flag, detail, extreme = "within_band", "live move inside the nightly 1-day band", False
    if hi is not None and chg_pct >= hi:
        flag, detail = "band_breach_up", f"+{chg_pct}% breached the nightly 1-day band (+{hi}%)"
    elif lo is not None and chg_pct <= lo:
        flag, detail = "band_breach_down", f"{chg_pct}% breached the nightly 1-day band ({lo}%)"

    # "extreme": a single session that also clears the MULTI-day cone tail.
    if flag.startswith("band_breach"):
        short = (baseline.get("anticipation") or {}).get("horizons", {}).get("short") or {}
        rq = short.get("ret_q") or {}
        if rq.get("p95") is not None and chg_pct >= rq["p95"]:
            extreme, detail = True, detail + f"; extreme — also through the 5-day cone p95 (+{rq['p95']}%)"
        elif rq.get("p5") is not None and chg_pct <= rq["p5"]:
            extreme, detail = True, detail + f"; extreme — also through the 5-day cone p5 ({rq['p5']}%)"

    # Threshold crossings (lower priority than a band breach).
    rsi_from, rsi_to = tech.get("rsi14"), (live_tech_snap or {}).get("rsi14")
    macd_from, macd_to = tech.get("macd_pos"), (live_tech_snap or {}).get("macd_pos")
    crossings = []
    if rsi_from is not None and rsi_to is not None:
        for level in (70, 30):
            if (rsi_from < level <= rsi_to) or (rsi_from > level >= rsi_to):
                crossings.append(f"RSI crossed {level} ({rsi_from:.0f}->{rsi_to:.0f})")
    if macd_from is not None and macd_to is not None and bool(macd_from) != bool(macd_to):
        crossings.append(f"MACD flipped {'+' if macd_to else '-'}")
    if flag == "within_band" and crossings:
        flag = "rsi_cross" if crossings[0].startswith("RSI") else "macd_flip"
        detail = "; ".join(crossings)

    return {"flag": flag, "severity": _SEV.get(flag, "watch"), "detail": detail,
            "chg_pct": chg_pct, "band": [lo, hi], "band_source": src,
            "horizon": "1d", "extreme": extreme, "crossings": crossings,
            "rsi_from": rsi_from, "rsi_to": rsi_to}


# ------------------------------------------------------------- staleness ----

def staleness(quote: dict | None, stale_after_min: float,
              now: datetime | None = None, session_open: bool | None = None,
              *, require_timestamp: bool = False) -> dict:
    """Is this quote fresh enough to act on, and WHY is it stale?

    Distinguishes the two states the old code conflated: a quote can be stale
    because the market is CLOSED (a 16h-old print at 3am is correct) or because
    the FEED BROKE during RTH (a 40-min-old print when the tape should be moving
    is a real problem). ``session_open`` (advisory) routes the reason so a
    consumer treats "closed" as normal and "feed_stale_during_rth" as a warning.
    A price that is not from a live trade (price_basis day/prev) is never "live".
    """
    if not quote or quote.get("price") is None:
        reason = "market closed" if session_open is False else "no live quote"
        return {"stale": True, "age_min": None, "reason": reason}
    if quote.get("quote_ts_synthetic"):
        return {"stale": True, "age_min": None, "reason": "synthetic quote timestamp"}
    if require_timestamp and not quote.get("quote_ts"):
        return {"stale": True, "age_min": None, "reason": "missing quote timestamp"}
    # A vendor's latency estimate cannot reset the actual observation clock.
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    ages = []
    try:
        delay = float(quote.get("delay_min"))
        if math.isfinite(delay) and delay >= 0:
            ages.append(delay)
    except (TypeError, ValueError):
        pass
    if quote.get("quote_ts"):
        try:
            ts = datetime.fromisoformat(str(quote["quote_ts"]).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            elapsed = (now - ts).total_seconds() / 60.0
            if elapsed < -1:
                return {"stale": True, "age_min": None, "reason": "future quote timestamp"}
            ages.append(max(0.0, elapsed))
        except (TypeError, ValueError, OverflowError):
            return {"stale": True, "age_min": None, "reason": "invalid quote timestamp"}
    age = max(ages) if ages else None
    not_live_basis = quote.get("price_basis") in ("day", "prev")
    stale = age is None or age > float(stale_after_min) or not_live_basis
    if not stale:
        reason = "fresh"
    elif not_live_basis:
        reason = "not a live trade (prior close)"
    elif session_open is False:
        reason = "market closed"
    elif session_open is True:
        reason = "feed stale during RTH"
    else:
        reason = "quote older than stale_after"
    return {"stale": bool(stale), "age_min": round(age, 1) if age is not None else None,
            "reason": reason}


def _baseline_age_days(asof: str | None, now: datetime, market: str | None = None) -> int | None:
    if not asof:
        return None
    try:
        d0 = pd.Timestamp(asof).normalize()
        if market:
            return missed_sessions(market, d0.date(), market_local_date(market, now))
        d1 = pd.Timestamp(now).tz_localize(None).normalize()
        return int(pd.bdate_range(d0, d1).size) - 1 if d1 >= d0 else 0
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------ per-ticker overlay ----

def build_ticker_overlay(ticker: str, baseline: dict, quote: dict | None,
                         close: pd.Series | None, stale_after_min: float,
                         now: datetime | None = None,
                         max_chg_pct: float = DEFAULT_MAX_CHG_PCT) -> dict:
    """Assemble the full live record for one ticker. Degrades to a stale record
    (keyed on the nightly close) when there is no fresh quote, no history, a bad
    print (|move|>max_chg_pct), or a non-live price basis — the file is always
    valid and ``stale`` tells the consumer to trust the nightly baseline."""
    now = now or datetime.now(timezone.utc)
    region = region_for(ticker)
    cash_market = cash_market_for_symbol(ticker)
    # The legacy region fallback also labels derivatives/FX/crypto "us"; it is
    # not an exchange-session authority for those instruments.
    session = ({"open": None} if not cash_market and region == "us" else
               market_session(cash_market or region, now))
    base_tech = baseline.get("tech") or {}
    base_close = base_tech.get("price")
    if cash_market:
        close = _cash_history(close, cash_market, now)
    has_history = close is not None and not close.empty
    health = session_freshness(cash_market, baseline.get("asof"), now) if cash_market else None
    history = (session_freshness(cash_market, close.index[-1].date() if has_history else None, now)
               if cash_market else None)
    history_bad = bool(history and history["state"] != "current")
    frozen = bool(cash_market and session.get("data_frozen"))
    age_days = _baseline_age_days(baseline.get("asof"), now, cash_market)
    baseline_stale = ((health["state"] != "current" or history_bad) if health else
                      age_days is not None and age_days > 1)
    data_state = health["state"] if health else None
    if history_bad and data_state == "current":
        data_state = history["state"]
    data_meta = {
        "data_frozen": frozen, "data_state": data_state,
        "baseline_data_state": health["state"] if health else None,
        "history_state": history["state"] if history else None,
        "history_through": history["observed_session"] if history else None,
        "data_through": health["observed_session"] if health else baseline.get("asof"),
        "session_state": session.get("state") if cash_market else None,
        "baseline_age_days": age_days, "baseline_stale": baseline_stale,
        "lag_sessions": health["lag_sessions"] if health else None,
        "expected_session": health["expected_session"] if health else None,
    }

    # The bad-print rejection stays visible even during an expected closure.
    bad_print = False
    if quote and quote.get("price") is not None and base_close:
        if abs(float(quote["price"]) / float(base_close) - 1) > max_chg_pct / 100.0:
            bad_print = True
    stale = staleness(quote, stale_after_min, now,
                      session_open=session["open"] if cash_market else None,
                      require_timestamp=bool(cash_market))
    quote_clock_invalid = stale["reason"] in {
        "future quote timestamp", "invalid quote timestamp",
        "missing quote timestamp", "synthetic quote timestamp"}
    # Keep clock integrity even when bad_print wins the display reason. An
    # invalid clock cannot outrank a subsequent real provider observation.
    data_meta["quote_clock_invalid"] = quote_clock_invalid
    quote_invalid = bad_print or quote_clock_invalid
    data_meta["quote_state"] = ("invalid" if quote_invalid else
                                "missing" if not quote or quote.get("price") is None else
                                "stale" if stale["stale"] else "current")
    invalid_baseline = health and health["state"] in {"missing", "invalid", "unverified"}
    is_stale = (stale["stale"] or bad_print or not has_history or frozen
                or invalid_baseline or history_bad)

    if is_stale:
        if bad_print:
            reason, flag = "bad print (limit-move guard)", "bad_print"
        elif quote_invalid:
            reason, flag = stale["reason"], "invalid_quote"
        elif invalid_baseline:
            reason, flag = "baseline " + health["state"], "baseline_stale"
        elif history_bad:
            reason, flag = "price history " + history["state"], "history_stale"
        elif frozen:
            reason = ("market holiday" if session["state"] == "holiday" else "market closed")
            reason += " — retained completed session"
            if baseline_stale:
                reason += "; baseline missing expected sessions"
            flag = "baseline_stale" if baseline_stale else "market_closed"
        else:
            reason, flag = stale["reason"], "no_quote"
        return {
            "ticker": ticker, "region": region, "session_open": session["open"],
            "price": base_close,
            "source": (quote or {}).get("source"), "quote_ts": (quote or {}).get("quote_ts"),
            "price_basis": (quote or {}).get("price_basis"),
            "stale": True, "age_min": stale["age_min"], "stale_reason": reason,
            "baseline_asof": baseline.get("asof"), **data_meta,
            "tech": base_tech,
            "divergence": {"flag": flag, "severity": "info", "detail": reason,
                           "chg_pct": None},
        }

    price = float(quote["price"])
    # Exchange-local date, without mutating the persisted nightly history.
    splice_at = (datetime.combine(market_local_date(cash_market, now), datetime.min.time())
                 if cash_market else now)
    tech = live_tech(close, price, splice_at)
    div = divergence(baseline, price, tech)
    if baseline_stale and div.get("severity") == "alert":
        div = {**div, "severity": "info", "flag": "baseline_stale",
               "detail": f"baseline {age_days} trading days old — move spans multiple "
                         f"sessions, breach not trustworthy ({div.get('detail')})"}

    return {
        "ticker": ticker, "region": region, "session_open": session["open"],
        "price": round(price, 4), "source": quote.get("source"),
        "quote_ts": quote.get("quote_ts"), "price_basis": quote.get("price_basis"),
        "delay_min": quote.get("delay_min"), "currency": quote.get("currency"),
        "stale": False, "age_min": stale["age_min"],
        "baseline_asof": baseline.get("asof"), **data_meta,
        "prev_close": base_close, "chg_pct": div.get("chg_pct"),
        "tech": tech, "divergence": div,
    }


# ----------------------------------------------- bot-facing reconciliation ----

# What a confirmed, fresh divergence suggests to the bot. Policy stays with the
# bot; this is a coarse routing hint, not an order.
_ROUTE = {"band_breach_up": "review_new_entry",
          "band_breach_down": "reduce_or_review",
          "rsi_cross": "watch", "macd_flip": "watch"}


def merge_baseline(baseline: dict, overlay: dict) -> dict:
    """The reconciliation a consumer (Mastermind) applies: nightly scores are the
    decision SPINE; the live overlay refreshes timing leaves and surfaces an
    invalidation signal. The slow-brain conviction/verdict pass through untouched.

    Honesty split (the fix to the old perverse logic): ``act_on_live`` reflects
    DATA TRUST only (is the quote fresh?) — a STALE quote means defer to baseline.
    A FRESH cone breach is NOT suppressed; it surfaces as ``invalidated`` so the
    bot can act on exactly the moment the nightly assumption broke.
    """
    conv = baseline.get("conviction") or {}
    div = overlay.get("divergence", {}) or {}
    stale = overlay.get("stale", True)
    sev = div.get("severity")
    return {
        "ticker": baseline.get("ticker") or overlay.get("ticker"),
        "as_of_baseline": baseline.get("asof"),
        # --- slow brain (authoritative, nightly) ---
        "conviction": conv.get("score"),
        "verdict": conv.get("verdict"),
        "size": (conv.get("size") or {}).get("pct"),
        # --- fast layer (live, advisory) ---
        "live_price": overlay.get("price"),
        "chg_pct": overlay.get("chg_pct"),
        "stale": stale, "age_min": overlay.get("age_min"),
        "session_open": overlay.get("session_open"),
        "session_state": overlay.get("session_state"),
        "data_frozen": overlay.get("data_frozen", False),
        "data_state": overlay.get("data_state"),
        "quote_state": overlay.get("quote_state"),
        "data_through": overlay.get("data_through"),
        "expected_session": overlay.get("expected_session"),
        "divergence": div.get("flag"),
        "divergence_severity": sev,
        "divergence_detail": div.get("detail"),
        # data trust: a fresh quote's timing is usable; a stale one is not.
        "act_on_live": not stale,
        # the invalidation the bot should heed: a FRESH alert (not suppressed).
        "invalidated": (not stale) and sev == "alert",
        "route_hint": _ROUTE.get(div.get("flag")) if not stale else None,
    }
