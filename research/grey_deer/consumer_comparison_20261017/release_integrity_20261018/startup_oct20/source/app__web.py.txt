"""Dashboard web routes — GET / serves the static dashboard; /api/* expose
the data contracts the page JS fetches at runtime.
"""
from __future__ import annotations

import json
import logging
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from portfolio import registry as _portfolio_registry

_PRODUCT_DEFAULT_ID = _portfolio_registry.DASHBOARD_DEFAULT_ID
_log = logging.getLogger(__name__)

# Lazy import so the module loads even if brain/ isn't fully initialised yet
def _cached_zh(text: str):
    """Safe wrapper: returns None if brain.translate isn't available."""
    try:
        from brain.translate import cached_zh
        return cached_zh(text)
    except Exception:
        return None

router = APIRouter()

_STATIC = Path(__file__).parent / "static"

# The Mastermind project root is two levels up from app/web.py
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _data() -> Path:
    """Return the Mastermind-local data/ directory (not the macro vendor data/)."""
    return _PROJECT_ROOT / "data"


def _macro_data() -> Path:
    """Return the vendored macro engine's data/ directory (read-only)."""
    return _PROJECT_ROOT / "vendor" / "macro" / "data"


def _portfolio_dir(portfolio_id: str | None = None) -> Path:
    """The per-portfolio state directory (flagship → legacy data/portfolio/)."""
    try:
        from portfolio import registry
        return registry.data_dir(portfolio_id)
    except Exception:
        return _data() / "portfolio"


def _product_portfolio_id(portfolio_id: str | None) -> str:
    """Resolve an API-facing book id, REJECTING an explicit unknown id.

    Three distinct cases, deliberately kept apart:
      * omitted / blank  -> the dashboard default (``autonomous``). A caller that named no book
        is asking for the default book.
      * a known registry id -> itself, archived books included (they keep serving frozen history).
      * an explicit UNKNOWN id -> HTTP 404. It must NOT silently become the default.

    That last case used to fall through to ``DASHBOARD_DEFAULT_ID``, so a typo, a stale bookmark,
    or malformed client state answered with a valid-looking Autonomous/US-Brain payload labelled
    with the caller's own bogus id. For a portfolio surface, wrong data is worse than no data:
    fail closed, exactly as ``registry.canonical_id`` already does before any filesystem use.
    """
    if not portfolio_id:
        return _PRODUCT_DEFAULT_ID
    if _portfolio_registry.is_known(portfolio_id):
        return portfolio_id
    raise HTTPException(status_code=404, detail={
        "error": "unknown_portfolio",
        "portfolio_id": portfolio_id,
        "known": _portfolio_registry.ids(),
    })


def _read_json_object(path: Path) -> dict[str, Any]:
    """Best-effort local artifact read used by the frozen archive path."""
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _read_json_list(path: Path) -> list[Any]:
    """Best-effort local JSON-list read used by archived pending history."""
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, list) else []
    except Exception:
        return []


def _read_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    """Read valid object rows without importing a live valuation/feed module."""
    try:
        rows = []
        for line in path.read_text().splitlines():
            try:
                value = json.loads(line)
            except Exception:
                continue
            if isinstance(value, dict):
                rows.append(value)
        return rows
    except Exception:
        return []


def _number(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _first_number(*values: Any, default: float = 0.0) -> float:
    for value in values:
        parsed = _number(value)
        if parsed is not None:
            return parsed
    return default


def _archived_performance(portfolio_id: str) -> dict[str, Any]:
    """Build performance solely from the retired book's final persisted artifacts.

    In particular this does not call ``paper_account.performance``: that active-book helper reads
    the current benchmark store and can append today's live mark to the served curve. Archived
    headlines and charts must stay on the same last recorded row forever.
    """
    meta = _portfolio_registry.get(portfolio_id)
    base = _portfolio_dir(portfolio_id)
    snapshot = _read_json_object(base / "latest.json")
    account = _read_json_object(base / "account.json")
    history = [row for row in _read_jsonl_objects(base / "nav_history.jsonl")
               if row.get("date") and _number(row.get("nav")) is not None]

    starting_nav = _first_number(account.get("starting_nav"), meta.get("starting_nav"),
                                 default=1_000_000.0)
    final = history[-1] if history else {}
    current_nav = _first_number(final.get("nav"), snapshot.get("nav"), default=starting_nav)
    cash = _first_number(final.get("cash"), snapshot.get("cash_usd"), account.get("cash"))
    invested = _number(final.get("invested"))
    if invested is None:
        invested = max(0.0, current_nav - cash)

    benchmark = _portfolio_registry.benchmark(portfolio_id)

    def _benchmark_matches(row: dict[str, Any]) -> bool:
        persisted = row.get("benchmark")
        return persisted == benchmark or (persisted is None and benchmark == "SPY")

    series = []
    for row in history:
        spy_nav = _number(row.get("spy_nav")) if _benchmark_matches(row) else None
        series.append({
            "date": row["date"],
            "nav": _number(row.get("nav")),
            "spy_nav": spy_nav,
            "kind": "realized",
        })

    navs = [row["nav"] for row in series if row.get("nav") is not None]
    max_drawdown_pct = 0.0
    if navs:
        peak = navs[0]
        for value in navs:
            peak = max(peak, value)
            if peak > 0:
                max_drawdown_pct = min(max_drawdown_pct, (value / peak - 1.0) * 100.0)

    total_return_pct = ((current_nav / starting_nav - 1.0) * 100.0
                        if starting_nav > 0 else 0.0)
    day_change_pct = 0.0
    if len(navs) >= 2 and navs[-2] > 0:
        day_change_pct = (navs[-1] / navs[-2] - 1.0) * 100.0

    final_spy_nav = (_number(final.get("spy_nav")) if _benchmark_matches(final) else None)
    vs_benchmark_pct = None
    if final_spy_nav and starting_nav > 0:
        benchmark_return_pct = (final_spy_nav / starting_nav - 1.0) * 100.0
        vs_benchmark_pct = round(total_return_pct - benchmark_return_pct, 4)

    frozen_as_of = final.get("date") or snapshot.get("as_of") or account.get("as_of")
    inception_date = (account.get("inception_date") or
                      (history[0].get("date") if history else None) or
                      snapshot.get("as_of"))
    return {
        "inception_date": inception_date,
        "starting_nav": round(starting_nav, 2),
        "current_nav": round(current_nav, 2),
        "cash": round(cash, 2),
        "invested": round(invested, 2),
        "total_return_pct": round(total_return_pct, 4),
        "vs_benchmark_pct": vs_benchmark_pct,
        "vs_spy_pct": vs_benchmark_pct,
        "benchmark": benchmark,
        "benchmark_name": _portfolio_registry.benchmark_name(portfolio_id),
        "benchmark_name_zh": _portfolio_registry.benchmark_name_zh(portfolio_id),
        "benchmark_as_of": final.get("date") if final_spy_nav is not None else None,
        "day_change_pct": round(day_change_pct, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "realized_since": history[0].get("date") if history else inception_date,
        "series": series,
        "archived": True,
        "lifecycle": "archived",
        "frozen_as_of": frozen_as_of,
        "note": "Archived portfolio: values are frozen at the final persisted mark.",
    }


def _archived_live_marks(portfolio_id: str) -> dict[str, Any]:
    """Live-marks-shaped frozen snapshot for a retired portfolio; local reads only."""
    snapshot = _read_json_object(_portfolio_dir(portfolio_id) / "latest.json")
    performance = _archived_performance(portfolio_id)
    frozen_as_of = performance.get("frozen_as_of") or snapshot.get("as_of")
    positions = []
    for persisted in snapshot.get("positions") or []:
        if not isinstance(persisted, dict):
            continue
        row = dict(persisted)
        row.update({
            "quote_source": "archived_snapshot",
            "quote_as_of": frozen_as_of,
            "quote_time_kind": "final_persisted_mark",
            "quote_is_live": False,
        })
        positions.append(row)
    _attach_security_names(positions)
    priced = sum(1 for row in positions if row.get("current_price") is not None)
    return {
        "schema_version": "live_marks.v1",
        "portfolio": portfolio_id,
        "currency": _portfolio_registry.currency(portfolio_id),
        "generated_at": frozen_as_of,
        "archived": True,
        "lifecycle": "archived",
        "frozen_as_of": frozen_as_of,
        "session": {
            "venue": None, "market": "ARCHIVED", "timezone": "UTC", "is_open": False,
            "state": "archived", "trading_day": False, "holiday": False,
            "as_of": frozen_as_of, "next_open": None, "poll_after_seconds": None,
        },
        "poll_after_seconds": None,
        "positions": positions,
        "performance": performance,
        "pricing": {
            "priced_positions": priced,
            "total_positions": len(positions),
            "complete": priced == len(positions),
            "source": "final_persisted_snapshot",
        },
    }


def _persisted_held_days(opened_at: Any, ended_at: Any) -> int | None:
    """Elapsed calendar days between two persisted timestamps; never consults today's clock."""
    try:
        opened = date.fromisoformat(str(opened_at)[:10])
        ended = date.fromisoformat(str(ended_at)[:10])
        return max(0, (ended - opened).days)
    except (TypeError, ValueError):
        return None


def _archived_position_rows(portfolio_id: str, frozen_as_of: Any) -> tuple[list[dict], list[dict]]:
    """Shape the persisted position ledger without its active reader's moving held-day clock."""
    ledger = _read_json_object(_portfolio_dir(portfolio_id) / "positions_ledger.json")
    opened_rows: list[dict] = []
    closed_rows: list[dict] = []
    for entry in ledger.values():
        if not isinstance(entry, dict) or not entry.get("ticker"):
            continue
        if entry.get("still_open"):
            opened_rows.append({
                "ticker": entry["ticker"], "sleeve": entry.get("sleeve"),
                "opened_at": entry.get("opened_at"),
                "held_days": _persisted_held_days(entry.get("opened_at"), frozen_as_of),
                "entry_weight": entry.get("entry_weight"),
                "current_weight": entry.get("current_weight"),
                "entry_price": entry.get("entry_price"),
                "time_stop_by": entry.get("time_stop_by"),
                "thesis_id": entry.get("thesis_id"),
                "published_stop": entry.get("published_stop"),
                "buy_zone": entry.get("buy_zone"),
            })
            continue
        close_event = next(
            (event for event in reversed(entry.get("history") or [])
             if isinstance(event, dict) and event.get("event") == "close"),
            {},
        )
        closed_rows.append({
            "ticker": entry["ticker"], "sleeve": entry.get("sleeve"),
            "opened_at": entry.get("opened_at"), "closed_at": entry.get("closed_at"),
            "held_days": _persisted_held_days(entry.get("opened_at"), entry.get("closed_at")),
            "exit_reason": close_event.get("reason") or "removed from book",
            "reason_code": close_event.get("reason_code") or "unspecified",
        })
    opened_rows.sort(key=lambda row: row.get("opened_at") or "", reverse=True)
    closed_rows.sort(key=lambda row: row.get("closed_at") or "", reverse=True)
    return opened_rows, closed_rows


def _attach_security_names(rows) -> None:
    """Attach canonical display names to ticker-bearing API rows in place.

    The Macro security master covers US stocks/ETFs plus the China/HK books.
    Resolve on every read so historical payloads written before names were
    captured are repaired without requiring a trading run or state rewrite.
    Missing artifacts remain fail-soft and never replace a valid name with a
    duplicate raw ticker.
    """
    try:
        from brain import china_intake
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            ticker = (row.get("ticker") or "").upper().strip()
            if not ticker:
                continue
            name = china_intake.display_name(ticker)
            if name and name.upper() != ticker:
                row["name"] = name
            if ticker.endswith(".HK"):
                name_zh = china_intake.display_name_zh(ticker)
                if name_zh and name_zh.upper() != ticker:
                    row["name_zh"] = name_zh
    except Exception:  # noqa: BLE001 — display enrichment must never sink an API response
        pass


# Mastermind Portfolio books backed by a module exposing load_decisions(). Archived modules stay
# mapped so their historical journals remain browseable; mapping never grants run authority.
_BRAIN_BOOK_MODULES = {"autonomous": "bot.autonomous", "heavyweight": "bot.heavyweight",
                       "china": "bot.china", "hk": "bot.hk", "etf": "bot.etf"}


def _brain_book_module(portfolio: str):
    """Import the bot module backing a Brain book's decision log, or None for non-Brain books."""
    import importlib
    name = _BRAIN_BOOK_MODULES.get(portfolio)
    return importlib.import_module(name) if name else None


def _sha256_identity(value: Any) -> bool:
    """True only for the lowercase digest form persisted by the paper ledger."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _decision_execution_receipt_verified(row: Any) -> bool:
    """Require complete receipt/fill identity before an API row may claim FILLED.

    Historical decision rows stored display summaries in ``executed`` without immutable fill ids.
    They remain useful audit records, but only the settlement reconciler's transaction id, receipt
    hash, and exact fill-id vector prove that those summaries came from the durable fill ledger.
    An empty, receipt-bound vector is valid evidence of a settled target that required no trade.
    """
    if not isinstance(row, dict) or row.get("target_status") != "executed":
        return False
    decision_id = str(row.get("decision_id") or "")
    decision_suffix = decision_id.removeprefix("decision.v1.")
    try:
        accepted_asof = date.fromisoformat(str(row.get("accepted_asof") or ""))
        settled_asof = date.fromisoformat(str(row.get("settled_asof") or ""))
    except (TypeError, ValueError):
        return False
    if (
        settled_asof < accepted_asof
        or not _sha256_identity(row.get("submission_sha256"))
        or not _sha256_identity(row.get("target_sha256"))
        or not decision_id.startswith("decision.v1.")
        or len(decision_suffix) != 24
        or any(char not in "0123456789abcdef" for char in decision_suffix)
    ):
        return False
    transaction_id = row.get("settlement_transaction_id")
    if not _sha256_identity(transaction_id) or not _sha256_identity(
        row.get("settlement_receipt_sha256")
    ):
        return False
    fill_ids = row.get("settlement_fill_ids")
    executed = row.get("executed")
    if not isinstance(fill_ids, list) or not isinstance(executed, list):
        return False
    if len(fill_ids) != len(executed) or any(not _sha256_identity(value) for value in fill_ids):
        return False
    if len(set(fill_ids)) != len(fill_ids):
        return False
    for index, fill in enumerate(executed):
        if (
            not isinstance(fill, dict)
            or fill.get("transaction_id") != transaction_id
            or fill.get("fill_id") != fill_ids[index]
            or fill.get("side") not in {"buy", "sell"}
            or not str(fill.get("ticker") or "").strip()
        ):
            return False
    return True


def _account_tickers(portfolio_id: str | None = None) -> list[str]:
    """Tickers currently held in a paper account (for live marks)."""
    try:
        acct = json.loads((_portfolio_dir(portfolio_id) / "account.json").read_text())
        return list((acct.get("positions") or {}).keys())
    except Exception:
        return []


def _dash_mark_usd(t: str) -> float | None:
    """Best-available USD mark for a ticker on the DASHBOARD READ path — NEVER blocks on the network.

    Order: the hot in-process live cache (kept warm by the ``prewarm_marks`` scheduler job) → the
    Terminal (Macro Dashboard) per-ticker snapshot, an instant local file read. The authoritative NAV
    is still marked from the LIVE feeds by the scheduler; this fast path only feeds the dashboard's
    live-preview so switching books paints immediately instead of stalling ~5s on a synchronous
    yfinance download."""
    tt = (t or "").upper().strip()
    if not tt:
        return None
    try:
        from data_layer import yahoo_feed, terminal_prices
    except Exception:
        return None
    cached = yahoo_feed.price_cached(tt)   # LOCAL currency: USD / HKD / CNY by venue suffix
    if cached is not None and cached > 0:
        if tt.endswith((".HK", ".SS", ".SZ")):
            try:
                from portfolio import fx
                usd = fx.to_usd(cached, tt)
                return float(usd) if usd and usd > 0 else None
            except Exception:
                return None
        return float(cached)               # US: the cache already holds USD
    return terminal_prices.price_usd(tt)   # cold miss → instant Terminal snapshot (→ USD)


def _live_prices(tickers: list[str], *, refresh: bool | None = None) -> dict[str, float]:
    """USD marks for the bare-US names in `tickers`, for the DASHBOARD read path — {} when none.

    NON-BLOCKING: kicks a background refresh of the live Yahoo cache (so it never blocks the response)
    and reads the cache, falling back to the Terminal snapshot on a cold miss. This REPLACED the old
    synchronous ``warm() → yf.download`` that made switching to a cold book stall ~5s while three
    parallel endpoints (/api/portfolio, /api/performance, /api/trades) stampeded the same fetch. The
    authoritative NAV is unaffected (the scheduler marks off the live feeds directly). Only bare US
    symbols route here; venue-suffixed names are marked on their own path in ``_book_marks``."""
    us = [t for t in (tickers or []) if t and "." not in t]
    if not us:
        return {}
    try:
        from portfolio import market_sessions
        market_open = market_sessions.status_for_portfolio("self_directed")["is_open"]
    except Exception:
        market_open = False
    if market_open and refresh is not False:
        try:
            from data_layer import yahoo_feed
            yahoo_feed.warm(us, background=(refresh is None))
        except Exception:
            pass
    out: dict[str, float] = {}
    for t in us:
        v = _dash_mark_usd(t)
        if v and v > 0:
            out[t] = float(v)
    return out


def _book_marks(
    portfolio_id: str | None = None,
    *,
    refresh: bool | None = None,
    tickers: list[str] | None = None,
) -> dict[str, float]:
    """Current marks for a book's held names, in the book's BASE currency — the dashboard's live
    valuation preview for NAV / per-position P&L.

    NON-BLOCKING (dashboard read path): pre-warms the live caches in the BACKGROUND and marks each
    name off the hot cache or the instant Terminal snapshot — never a synchronous per-name network
    fetch (the old HK path fired one yf.download PER NAME, ~5-12s). USD books mark in USD;
    single-currency non-US books (hk=HKD / china=CNY) convert the USD mark to base via ``portfolio.fx``
    exactly as before. Returns {} only when neither a current source nor a bounded persisted mark is
    available; callers then render an honest unpriced state. The book of record's NAV is still marked from the LIVE feeds
    by the scheduler's daily_mark/build jobs — this fast path never writes NAV.  If both hot paths
    miss, a bounded read of the book's own last persisted mark supplies the prior EOD/base-currency
    value with provenance through ``_book_quote_provenance``; that display carry is never exposed to
    settlement or rebalance code.
    """
    tickers = list(tickers) if tickers is not None else _account_tickers(portfolio_id)
    if not tickers:
        return {}
    resolved_pid = portfolio_id
    try:
        from portfolio import registry
        resolved_pid = registry.canonical_id(portfolio_id)
        ccy = registry.currency(portfolio_id)
    except Exception:
        ccy = "USD"
    # Only touch the live feed during this book's actual cash session. The default dashboard read
    # warms off-thread; the dedicated live-marks endpoint pre-warms synchronously and then calls
    # this helper with refresh=False. China A-shares are included — their CNY marks are converted
    # to USD by _dash_mark_usd before conversion into the book's base currency below.
    session: dict[str, Any] = {}
    try:
        from portfolio import market_sessions
        session = market_sessions.status_for_portfolio(portfolio_id)
        market_open = session["is_open"]
    except Exception:
        market_open = False
    if market_open and refresh is not False:
        try:
            from data_layer import yahoo_feed
            yahoo_feed.warm(tickers, background=(refresh is None))
        except Exception:
            pass
    persisted = _persisted_book_quotes(
        resolved_pid or _portfolio_registry.DEFAULT_ID,
        tickers,
        asof=session.get("as_of"),
    )
    current_quotes = _quote_provenance(tickers)
    out: dict[str, float] = {}
    for t in tickers:
        persisted_quote = persisted.get(t)
        current_quote = current_quotes.get(t)
        selected_quote = _select_dashboard_quote(
            current_quote,
            persisted_quote,
            asof=session.get("as_of"),
        )
        if selected_quote is persisted_quote and persisted_quote is not None:
            px = persisted_quote.get("price_local")
            if px and px > 0:
                out[t] = float(px)
            continue
        usd = _dash_mark_usd(t)
        # A dated non-live quote that failed the freshness selector is not rescued by its bare
        # price.  (A source-less injected quote remains supported for legacy/tests only.)
        if current_quote is not None and selected_quote is None:
            continue
        if not (usd and usd > 0):
            continue
        if ccy == "USD":
            out[t] = float(usd)
        else:
            try:
                from portfolio import fx
                base = fx.usd_to(usd, ccy)
            except Exception:
                base = None
            if base and base > 0:
                out[t] = float(base)
    return out


def _quote_provenance(tickers: list[str]) -> dict[str, dict[str, Any]]:
    """Cache-only source/as-of metadata for marks; never triggers a quote request."""
    try:
        from data_layer import terminal_prices, yahoo_feed
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        t = (ticker or "").upper().strip()
        if not t:
            continue
        quote = yahoo_feed.quote_cached(t) or terminal_prices.quote_local(t)
        if quote:
            out[t] = quote
    return out


_PERSISTED_MARK_MAX_AGE_DAYS = 30


def _date_part(value: Any) -> date | None:
    """Parse a contract date/timestamp without guessing a timezone or accepting malformed input."""
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _snapshot_is_completed_eod(
    portfolio_id: str,
    snapshot: dict[str, Any],
    snapshot_date: date | None,
) -> bool:
    """Conservatively identify a portfolio snapshot written after that venue's regular close."""
    status = snapshot.get("market_status") or {}
    if (
        snapshot_date is None
        or status.get("open") is not False
        or status.get("trading_day") is False
    ):
        return False
    if status.get("state") in {"post_close", "early_close"}:
        return True
    raw_asof = status.get("asof") or status.get("asof_cst") or status.get("asof_et")
    try:
        marked_at = datetime.fromisoformat(str(raw_asof).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    if marked_at.date() != snapshot_date:
        return False
    close_hour = 15 if portfolio_id == "china" else 16
    return (marked_at.hour, marked_at.minute) >= (close_hour, 0)


def _persisted_book_quotes(
    portfolio_id: str,
    tickers: list[str],
    *,
    asof: Any = None,
) -> dict[str, dict[str, Any]]:
    """Last valid per-position marks for the dashboard's *display-only* fallback.

    This is deliberately separate from every fill/rebalance price path.  It reads only the book's
    persisted account and published portfolio snapshot, rejects future-dated or >30-calendar-day
    marks, and returns the book's BASE-currency price with explicit provenance.  The published
    snapshot wins ties because it also records whether the strategy published after the cash market
    had closed.  Legacy account ``current_price`` fields without an as-of are never trusted on their
    own; an existing close snapshot can still attest the same holding during the upgrade cutover.
    """
    wanted = {(ticker or "").upper().strip() for ticker in (tickers or [])} - {""}
    if not wanted:
        return {}
    target_date = _date_part(asof) or date.today()
    base = _portfolio_dir(portfolio_id)
    snapshot = _read_json_object(base / "latest.json")
    if portfolio_id == "self_directed":
        try:
            from portfolio import self_directed
            account = self_directed._load_account()
        except Exception:
            account = {}
    else:
        account = _read_json_object(base / "account.json")

    candidates: dict[str, list[tuple[date, int, float, dict[str, Any]]]] = {
        ticker: [] for ticker in wanted
    }

    snapshot_date = _date_part(snapshot.get("as_of"))
    snapshot_is_eod = _snapshot_is_completed_eod(portfolio_id, snapshot, snapshot_date)
    if snapshot_date is not None:
        for raw in snapshot.get("positions") or []:
            if not isinstance(raw, dict):
                continue
            ticker = str(raw.get("ticker") or "").upper().strip()
            if ticker not in candidates:
                continue
            px = _number(raw.get("current_price"))
            if px is None or not math.isfinite(px) or px <= 0:
                continue
            source = "portfolio_eod" if snapshot_is_eod else "portfolio_snapshot"
            candidates[ticker].append((
                snapshot_date,
                2,
                px,
                {
                    "source": source,
                    "as_of": str(snapshot.get("as_of"))[:10],
                    "time_kind": (
                        "completed_session_close" if snapshot_is_eod
                        else "portfolio_snapshot_date"
                    ),
                    "origin_source": raw.get("quote_source"),
                },
            ))

    for ticker, raw in (account.get("positions") or {}).items():
        ticker = str(ticker or "").upper().strip()
        if ticker not in candidates or not isinstance(raw, dict):
            continue
        px = _number(raw.get("current_price"))
        mark_date = _date_part(raw.get("current_price_asof"))
        if px is None or not math.isfinite(px) or px <= 0 or mark_date is None:
            continue
        candidates[ticker].append((
            mark_date,
            1,
            px,
            {
                "source": "persisted_portfolio_mark",
                "as_of": str(raw.get("current_price_asof"))[:10],
                "time_kind": raw.get("current_price_time_kind") or "portfolio_mark_date",
                "origin_source": raw.get("current_price_source"),
            },
        ))

    out: dict[str, dict[str, Any]] = {}
    for ticker, rows in candidates.items():
        eligible = []
        for mark_date, priority, px, meta in rows:
            age_days = (target_date - mark_date).days
            if age_days < 0 or age_days > _PERSISTED_MARK_MAX_AGE_DAYS:
                continue
            eligible.append((mark_date, priority, px, meta, age_days))
        if not eligible:
            continue
        mark_date, _priority, px, meta, age_days = max(
            eligible, key=lambda row: (row[0], row[1])
        )
        out[ticker] = {
            "ticker": ticker,
            "price_local": float(px),
            **meta,
            "age_seconds": float(age_days * 86_400),
            "stale_days": age_days,
            "fresh": False,
            "is_live": False,
        }
    return out


def _select_dashboard_quote(
    current: dict[str, Any] | None,
    persisted: dict[str, Any] | None,
    *,
    asof: Any = None,
) -> dict[str, Any] | None:
    """Choose the display quote by evidence time, not accessor order.

    A real intraday quote always wins.  Terminal is a non-live daily snapshot: it must be dated,
    point-in-time valid, and strictly newer than the book's persisted close before it can replace
    that close.  File-mtime-only Terminal provenance cannot outrank a market-dated portfolio mark.
    """
    if current and current.get("source") == "yahoo_intraday":
        return current
    target_date = _date_part(asof) or date.today()
    if current:
        current_date = _date_part(current.get("as_of"))
        current_age = (target_date - current_date).days if current_date is not None else None
        current_is_bounded = (
            current_age is not None
            and 0 <= current_age <= _PERSISTED_MARK_MAX_AGE_DAYS
        )
        if not current_is_bounded:
            current = None
        elif persisted:
            persisted_date = _date_part(persisted.get("as_of"))
            if (
                current.get("time_kind") == "snapshot_file_mtime"
                or persisted_date is None
                or current_date is None
                or current_date <= persisted_date
            ):
                current = None
    return current or persisted


def _book_quote_provenance(
    portfolio_id: str,
    tickers: list[str],
) -> dict[str, dict[str, Any]]:
    """Provenance matching ``_book_marks``: hot/Terminal first, bounded persisted mark second."""
    current = _quote_provenance(tickers)
    try:
        from portfolio import market_sessions
        asof = market_sessions.status_for_portfolio(portfolio_id).get("as_of")
    except Exception:
        asof = None
    carried = _persisted_book_quotes(portfolio_id, tickers, asof=asof)
    out: dict[str, dict[str, Any]] = {}
    for raw_ticker in tickers:
        ticker = (raw_ticker or "").upper().strip()
        selected = _select_dashboard_quote(
            current.get(ticker), carried.get(ticker), asof=asof
        )
        if selected is not None:
            out[ticker] = selected
    return out


def _parse_note(path: Path) -> dict[str, Any] | None:
    """Parse a research note markdown file into {title, tickers, date, body_md}."""
    try:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines:
            return None

        # title from first # heading
        title = lines[0].lstrip("# ").strip() if lines[0].startswith("#") else path.stem

        # find the *tickers: ... · ISO-date* line
        ticker_line_idx = None
        tickers: list[str] = []
        date: str = ""
        for i, ln in enumerate(lines[1:], 1):
            m = re.match(r"\*tickers:\s*(.*?)\s*·\s*([\d\-T:.+Z]+)\*", ln)
            if m:
                raw_tickers = m.group(1)
                tickers = [t.strip() for t in raw_tickers.split(",") if t.strip()]
                date = m.group(2)
                ticker_line_idx = i
                break

        # body = everything after title + ticker line
        body_start = (ticker_line_idx + 1) if ticker_line_idx is not None else 1
        body_lines = lines[body_start:]
        body_md = "\n".join(body_lines).strip()

        # fall back to mtime for sort key if no date parsed
        sort_key = date or path.stat().st_mtime_ns.__str__()

        return {
            "title": title,
            "tickers": tickers,
            "date": date,
            "body_md": body_md,
            "_sort_key": sort_key,
        }
    except Exception:
        return None


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------

# The HTML files are application shells; every market/portfolio value is fetched from /api/*
# after paint.  Keeping a shell for two minutes makes cross-page navigation instant through the
# edge/browser cache without making investment data stale.  stale-while-revalidate lets an open
# session keep moving while the edge checks for a newly deployed shell in the background.
_PAGE_CACHE = {"Cache-Control": "public, max-age=120, stale-while-revalidate=600"}

# Shared CSS/JS changes only on deploy.  A five-minute fresh window removes four edge round-trips
# from every page transition, while the short max-age bounds how long an unversioned asset can lag
# a release.  FileResponse still supplies ETag and Last-Modified for revalidation.
_ASSET_CACHE = {"Cache-Control": "public, max-age=300, stale-while-revalidate=3600"}

# Stateful downloads and data artifacts keep their existing revalidation semantics.
_NOCACHE = {"Cache-Control": "no-cache"}


@router.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(_STATIC / "index.html", media_type="text/html", headers=_PAGE_CACHE)


@router.get("/research", include_in_schema=False)
def research_page() -> FileResponse:
    """The Research page — same SPA; the client opens the Research view from this path."""
    return FileResponse(_STATIC / "index.html", media_type="text/html", headers=_PAGE_CACHE)


@router.get("/self", include_in_schema=False)
def self_directed_page() -> FileResponse:
    """The Self-Directed book — same SPA; the client opens that view from this path."""
    return FileResponse(_STATIC / "index.html", media_type="text/html", headers=_PAGE_CACHE)


@router.get("/desk", include_in_schema=False)
def desk_page() -> FileResponse:
    """The Desk observability page — same SPA; the client opens the Desk view from this path."""
    return FileResponse(_STATIC / "index.html", media_type="text/html", headers=_PAGE_CACHE)


@router.get("/market_view", include_in_schema=False)
def market_view_page() -> FileResponse:
    """The Market View mirror (W-E.1 task E1.2) — a read-only render of the perception
    artifact (data/market_view/latest.json): the planes table, the label-vs-planes banner,
    the deterministic brief, and the top rotation pairs. Its own standalone static page
    (not the SPA) so it can be shared/bookmarked; fetches /api/market_view client-side."""
    return FileResponse(_STATIC / "market_view.html", media_type="text/html", headers=_PAGE_CACHE)


@router.get("/agenda", include_in_schema=False)
def agenda_page() -> FileResponse:
    """The Improvement Agenda mirror (W-L / L3) — a read-only render of the weekly self-critique
    artifact (data/agenda/<date>.json): the ranked items, each with its evidence, suggested fix,
    fix_type, owner, explicit Agent OS reference, and Agent OS readiness annotation. Its own
    standalone static page (not the SPA) so a maintenance session can bookmark it; fetches
    /api/agenda client-side. Readiness is visible but never reorders the queue, and this view
    sizes/changes nothing — advisory only."""
    return FileResponse(_STATIC / "agenda.html", media_type="text/html", headers=_PAGE_CACHE)


@router.get("/theme.css", include_in_schema=False)
def theme_css() -> FileResponse:
    """Serve the macro design-system stylesheet the dashboard links."""
    return FileResponse(_STATIC / "theme.css", media_type="text/css", headers=_ASSET_CACHE)


@router.get("/theme.js", include_in_schema=False)
def theme_js() -> FileResponse:
    """Serve the macro theme toggle script (optional; dark renders without it)."""
    return FileResponse(_STATIC / "theme.js", media_type="application/javascript",
                        headers=_ASSET_CACHE)


@router.get("/chat.js", include_in_schema=False)
def chat_js() -> FileResponse:
    """Serve the live advisor chat widget (the floating Brain popup).
    """
    return FileResponse(_STATIC / "chat.js", media_type="application/javascript",
                        headers=_ASSET_CACHE)


@router.get("/account.js", include_in_schema=False)
def account_js() -> FileResponse:
    """Serve the shared account/profile panel loaded by the dashboard shell."""
    return FileResponse(_STATIC / "account.js", media_type="application/javascript",
                        headers=_ASSET_CACHE)


def _company_meta(ticker: str) -> dict:
    """Company name / sector / current price / fundamentals for the research PDF, merged from
    the vendored macro stockdata (fundamentals) + Polygon (live price, optional description /
    market cap). Every field is best-effort; missing ones are simply omitted."""
    t = (ticker or "").upper().strip()
    meta: dict[str, Any] = {}
    sd: dict = {}
    try:
        p = _PROJECT_ROOT / "vendor" / "macro" / "site" / "stockdata" / f"{t}.json"
        if p.exists():
            sd = json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        sd = {}
    fin = sd.get("financials") or {}
    an = sd.get("analyst") or {}
    ear = sd.get("earnings") or {}
    tech = sd.get("tech") or {}
    fac = sd.get("factors") or {}
    # macro stockdata stores margins/growth/yields in PERCENT units (e.g. 85.2 = +85.2%);
    # the PDF formatter expects fractions, so normalise here (÷100, None-safe).
    def _frac(v):
        try:
            return float(v) / 100.0
        except (TypeError, ValueError):
            return None

    meta["name"] = sd.get("name")
    meta["sector"] = fac.get("sector")
    meta["rev_growth"] = _frac(fin.get("rev_growth"))
    meta["gross_margin"] = _frac(fin.get("gross_margin"))
    meta["net_margin"] = _frac(fin.get("net_margin"))
    meta["roe"] = _frac(fin.get("roe") if fin.get("roe") is not None else an.get("roe"))
    meta["fwd_pe"] = an.get("forward_pe") if an.get("forward_pe") is not None else an.get("pe_yf")
    meta["div_yield"] = _frac(an.get("div_yield"))
    meta["analyst_target"] = an.get("target")
    meta["rating"] = an.get("rating")
    meta["next_earnings"] = ear.get("next_date")
    # live (delayed) price; fall back to the stockdata snapshot price
    price = None
    try:
        from data_layer import polygon
        price = polygon.quote(t)
    except Exception:  # noqa: BLE001
        price = None
    meta["price"] = price if price else tech.get("price")
    # optional richer reference: company description + market cap (Polygon, best-effort)
    try:
        from data_layer import polygon
        det = polygon.ticker_details(t)
        if det:
            meta["name"] = meta.get("name") or det.get("name")
            meta["sector"] = meta.get("sector") or det.get("sector")
            meta["description"] = det.get("description")
            meta["market_cap"] = det.get("market_cap")
    except Exception:  # noqa: BLE001
        pass
    return {k: v for k, v in meta.items() if v is not None}


@router.get("/research_paper.pdf", include_in_schema=False)
def research_paper_pdf(id: str = "", ticker: str = "") -> Response:
    """Generate a beautifully formatted research-paper PDF on the spot (deterministic, no AI).
    `id` selects the exact saved paper; `ticker` falls back to that name's latest paper."""
    try:
        from brain import research_paper
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"research store unavailable: {exc}"}, status_code=503)

    paper = None
    try:
        papers = research_paper.load_papers()
        if id:
            paper = next((p for p in papers if p.get("id") == id), None)
        if paper is None and ticker:
            paper = research_paper.latest_for(ticker)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"could not load paper: {exc}"}, status_code=500)
    if paper is None:
        return JSONResponse({"error": "research paper not found"}, status_code=404)

    try:
        from app import research_pdf
    except Exception as exc:  # noqa: BLE001 — reportlab missing, etc.
        return JSONResponse({"error": f"PDF engine unavailable (is reportlab installed?): {exc}"},
                            status_code=503)

    meta = {}
    try:
        meta = _company_meta(paper.get("ticker") or "")
    except Exception:  # noqa: BLE001 — metadata is enrichment; render without it on failure
        meta = {}
    try:
        pdf = research_pdf.build(paper, meta)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": f"PDF generation failed: {exc}"}, status_code=500)

    tkr = (paper.get("ticker") or "research").upper()
    datestr = str(paper.get("asof") or paper.get("generated_at") or "")[:10]
    # allowlist-sanitise: ticker/asof come from the paper JSON; a stray CR/LF/quote would
    # otherwise produce an illegal Content-Disposition header (and 500 the response)
    fname = re.sub(r"[^A-Za-z0-9._-]", "_",
                   f"Mastermind_{tkr}{('_' + datestr) if datestr else ''}.pdf")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"',
                             "Cache-Control": "no-cache"})


@router.get("/api/performance")
def api_performance(portfolio: str = _PRODUCT_DEFAULT_ID) -> JSONResponse:
    """Equity curve for an active book, or final persisted history for an archived one."""
    portfolio = _product_portfolio_id(portfolio)
    if _portfolio_registry.is_archived(portfolio):
        return JSONResponse(_archived_performance(portfolio))
    try:
        from portfolio import paper_account
        payload = paper_account.performance(portfolio_id=portfolio,
                                            prices=_book_marks(portfolio))
        return JSONResponse(payload)
    except Exception as exc:
        # never 500 — return a safe minimal payload
        return JSONResponse({
            "inception_date": None,
            "starting_nav": 1_000_000,
            "current_nav": 1_000_000,
            "cash": 1_000_000,
            "invested": 0.0,
            "total_return_pct": 0.0,
            "vs_spy_pct": 0.0,
            "day_change_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "realized_since": None,
            "series": [],
            "note": f"Performance unavailable: {exc}",
        })


@router.get("/api/live_marks")
def api_live_marks(portfolio: str = _PRODUCT_DEFAULT_ID) -> JSONResponse:
    """Active-book intraday prices, unrealized P&L, and calculated NAV.

    The endpoint is deliberately narrow and read-only. It performs a batched live
    refresh only while the selected book's own exchange is open. At all other
    times it serves explicitly labelled cache/snapshot marks and tells the client
    to wake once at the next valid open instead of polling overnight or through
    holidays. Archived books bypass the exchange clock and quote layer entirely.
    """
    pid = _product_portfolio_id(portfolio)
    if _portfolio_registry.is_archived(pid):
        return JSONResponse(_archived_live_marks(pid), headers={"Cache-Control": "no-store"})

    from portfolio import market_sessions, registry

    session = market_sessions.status_for_portfolio(pid)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        if pid == "self_directed":
            from data_layer import yahoo_feed
            from portfolio import self_directed

            held = sorted((self_directed._load_account().get("positions") or {}).keys())
            if session["is_open"] and held:
                yahoo_feed.warm(held)  # one blocking batch; only on a valid US session
            prices = _live_prices(held, refresh=False)
            persisted_quotes = _persisted_book_quotes(
                pid, held, asof=session.get("as_of")
            )
            current_quotes = _quote_provenance(held)
            for ticker in held:
                current_quote = current_quotes.get(ticker)
                persisted_quote = persisted_quotes.get(ticker)
                selected_quote = _select_dashboard_quote(
                    current_quote, persisted_quote, asof=session.get("as_of")
                )
                if selected_quote is persisted_quote and persisted_quote is not None:
                    px = persisted_quote.get("price_local")
                    if px and px > 0:
                        prices[ticker] = float(px)
                elif current_quote is not None and selected_quote is None:
                    prices.pop(ticker, None)
            book = self_directed.book(
                prices=prices,
                read_only=True,
                resolve_missing_prices=False,
            )
            _attach_security_names(book.get("positions"))
            provenance = _book_quote_provenance(pid, held)
            for row in book.get("positions") or []:
                quote = provenance.get((row.get("ticker") or "").upper()) or {}
                row.update({
                    "quote_source": quote.get("source"),
                    "quote_as_of": quote.get("as_of"),
                    "quote_time_kind": quote.get("time_kind"),
                    "quote_age_seconds": quote.get("age_seconds"),
                    "quote_stale_days": quote.get("stale_days"),
                    "quote_origin_source": quote.get("origin_source"),
                    "quote_is_live": bool(
                        quote.get("is_live") or quote.get("source") == "yahoo_intraday"
                    ),
                })
            priced = sum(1 for row in book.get("positions") or []
                         if row.get("current_price") is not None)
            performance = {
                "current_nav": book.get("nav"),
                "cash": book.get("cash"),
                "invested": book.get("invested"),
                "total_return_pct": (book.get("allocation") or {}).get("total_return_pct"),
            }
            payload = {
                "schema_version": "live_marks.v1",
                "portfolio": pid,
                "currency": registry.currency(pid),
                "generated_at": generated_at,
                "session": session,
                "poll_after_seconds": (
                    300 if session["is_open"] and not held else session["poll_after_seconds"]),
                "positions": book.get("positions") or [],
                "performance": performance,
                "book": book,
                "pricing": {
                    "priced_positions": priced,
                    "total_positions": len(held),
                    "complete": priced == len(held),
                },
            }
        else:
            from data_layer import yahoo_feed
            from portfolio import paper_account

            held = _account_tickers(pid)
            if session["is_open"] and held:
                yahoo_feed.warm(held)  # all names in one request; no per-ticker stampede
            prices = _book_marks(pid, refresh=False)
            pnl = paper_account.positions_pnl(prices, portfolio_id=pid)
            provenance = _book_quote_provenance(pid, held)
            positions = []
            for ticker, row in pnl.items():
                quote = provenance.get((ticker or "").upper()) or {}
                positions.append({
                    "ticker": ticker,
                    **row,
                    # UI and historical book rows use ``cost_basis``; retain ``avg_cost`` in the
                    # live contract too, but expose the shared name so an account-only holding
                    # renders its true entry instead of a misleading dash.
                    "cost_basis": row.get("avg_cost"),
                    "quote_source": quote.get("source"),
                    "quote_as_of": quote.get("as_of"),
                    "quote_time_kind": quote.get("time_kind"),
                    "quote_age_seconds": quote.get("age_seconds"),
                    "quote_stale_days": quote.get("stale_days"),
                    "quote_origin_source": quote.get("origin_source"),
                    "quote_is_live": bool(
                        quote.get("is_live") or quote.get("source") == "yahoo_intraday"
                    ),
                })
            performance_full = paper_account.performance(portfolio_id=pid, prices=prices)
            performance = {
                key: performance_full.get(key)
                for key in (
                    "inception_date", "starting_nav", "current_nav", "cash", "invested",
                    "total_return_pct", "vs_benchmark_pct", "vs_spy_pct", "benchmark",
                    "benchmark_name", "benchmark_name_zh", "benchmark_as_of", "day_change_pct",
                    "max_drawdown_pct", "realized_since",
                )
            }
            current_nav = performance.get("current_nav")
            if current_nav and current_nav > 0:
                for row in positions:
                    market_value = row.get("market_value")
                    if market_value is not None:
                        row["weight"] = round(float(market_value) / float(current_nav), 6)
            priced = sum(1 for row in positions if row.get("current_price") is not None)
            payload = {
                "schema_version": "live_marks.v1",
                "portfolio": pid,
                "currency": registry.currency(pid),
                "generated_at": generated_at,
                "session": session,
                "poll_after_seconds": (
                    300 if session["is_open"] and not held else session["poll_after_seconds"]),
                "positions": positions,
                "performance": performance,
                "pricing": {
                    "priced_positions": priced,
                    "total_positions": len(held),
                    "complete": priced == len(held),
                },
            }
        return JSONResponse(payload, headers={"Cache-Control": "no-store"})
    except Exception as exc:  # noqa: BLE001 — live preview must degrade, never sink the dashboard
        return JSONResponse({
            "schema_version": "live_marks.v1",
            "portfolio": pid,
            "currency": registry.currency(pid),
            "generated_at": generated_at,
            "session": session,
            "poll_after_seconds": 60 if session["is_open"] else session["poll_after_seconds"],
            "positions": [],
            "performance": {},
            "pricing": {"priced_positions": 0, "total_positions": 0, "complete": False},
            "error": str(exc),
        }, headers={"Cache-Control": "no-store"})


@router.get("/api/risk")
def api_risk(portfolio: str = _PRODUCT_DEFAULT_ID, recompute: bool = False) -> JSONResponse:
    """Portfolio safety scorecard: a static-weight historical risk backtest of the live book
    (max drawdown · diversification · ticker correlations · beta · vol/VaR/CVaR + a 0-100
    safety score). Serves the nightly-persisted snapshot; pass ?recompute=true to rebuild now
    (skips the heavier bootstrap CI for a snappy response). Archived books always serve their final
    snapshot and ignore recompute. Never 500 — read-only, never an order.
    """
    portfolio = _product_portfolio_id(portfolio)
    try:
        from portfolio import safety
        if _portfolio_registry.is_archived(portfolio):
            rep = safety.load_safety(portfolio)
            if rep is None:
                rep = {
                    "portfolio_id": portfolio, "safety_score": None, "grade": "—",
                    "verdict": "Archived safety snapshot unavailable.", "metrics": {},
                    "subscores": {}, "breaches": [], "caveats": [],
                }
            rep = {**rep, "portfolio_id": portfolio, "archived": True,
                   "lifecycle": "archived", "snapshot_only": True}
            return JSONResponse(rep)
        rep = None if recompute else safety.load_safety(portfolio)
        if rep is None:
            rep = safety.compute_safety(portfolio, bootstrap=not recompute)
            # a fresh (not bot-built) read isn't consumed, so show the INDICATED de-gross
            if "overlay" not in rep:
                rep["overlay"] = {**safety.gross_overlay(rep), "applied": False}
            try:
                safety.persist(rep, portfolio)
            except Exception:
                pass
        return JSONResponse(rep)
    except Exception as exc:
        return JSONResponse({
            "portfolio_id": portfolio, "safety_score": None, "grade": "—",
            "verdict": "Safety report unavailable.", "metrics": {}, "subscores": {},
            "breaches": [], "caveats": [], "note": f"Safety unavailable: {exc}",
        })


@router.get("/api/portfolio")
def api_portfolio(portfolio: str = _PRODUCT_DEFAULT_ID) -> JSONResponse:
    portfolio = _product_portfolio_id(portfolio)
    path = _portfolio_dir(portfolio) / "latest.json"
    if not path.exists():
        return JSONResponse({"error": "no book yet", "portfolio_id": portfolio}, status_code=404)
    try:
        payload = json.loads(path.read_text())
        from portfolio import registry
        # Runtime registry is authoritative: persisted book contracts may predate a benchmark
        # migration and must never make CSI 300 / Hang Seng appear as FXI or SPY in the UI.
        payload["benchmark"] = registry.benchmark(portfolio)
        payload["benchmark_name"] = registry.benchmark_name(portfolio)
        payload["benchmark_name_zh"] = registry.benchmark_name_zh(portfolio)
        archived = registry.is_archived(portfolio)
        payload["archived"] = archived
        payload["lifecycle"] = "archived" if archived else "active"
        if archived:
            frozen = _archived_performance(portfolio)
            payload["frozen_as_of"] = frozen.get("frozen_as_of")
            payload["account_preview"] = {
                key: value for key, value in frozen.items()
                if key not in {"series", "note"}
            }

        # ------------------------------------------------------------------
        # Live marks: attach current price + unrealized P&L to each position
        # (Polygon delayed quotes via the account's avg-cost lots). Degrades to
        # nulls offline so the client always renders an honest dash.
        # ------------------------------------------------------------------
        if not archived:
            try:
                from portfolio import paper_account
                prices = _book_marks(portfolio)
                # positions_pnl({}) still returns every actual account lot with honest null marks.
                # This matters when the daily strategy snapshot has zero rows but the paper account
                # still owns positions: the first critical response must not pretend it is empty.
                pnl = paper_account.positions_pnl(prices, portfolio_id=portfolio)
                provenance = _book_quote_provenance(portfolio, list(pnl))
                account_nav = paper_account.nav(prices, portfolio_id=portfolio)
                account = paper_account._load_account(portfolio)
                cash = float(account.get("cash") or 0.0)
                starting_nav = float(account.get("starting_nav") or 1_000_000.0)
                payload["account_preview"] = {
                    "inception_date": account.get("inception_date"),
                    "starting_nav": starting_nav,
                    "current_nav": round(float(account_nav), 2),
                    "cash": round(cash, 2),
                    "invested": round(max(0.0, float(account_nav) - cash), 2),
                    "total_return_pct": round(
                        (float(account_nav) / starting_nav - 1.0) * 100, 4
                    ) if starting_nav > 0 else None,
                    "benchmark": registry.benchmark(portfolio),
                    "benchmark_name": registry.benchmark_name(portfolio),
                    "benchmark_name_zh": registry.benchmark_name_zh(portfolio),
                }
                published_tickers: set[str] = set()
                for pos in payload.get("positions", []):
                    ticker = pos.get("ticker")
                    if ticker:
                        published_tickers.add(ticker)
                    rec = pnl.get(ticker)
                    if rec:
                        quote = provenance.get((ticker or "").upper()) or {}
                        pos["cost_basis"] = rec.get("avg_cost")
                        pos["current_price"] = rec.get("current_price")
                        pos["market_value"] = rec.get("market_value")
                        pos["unrealized_pnl"] = rec.get("unrealized_pnl")
                        pos["unrealized_pct"] = rec.get("unrealized_pct")
                        if quote:
                            pos["quote_source"] = quote.get("source")
                            pos["quote_as_of"] = quote.get("as_of")
                            pos["quote_time_kind"] = quote.get("time_kind")
                            pos["quote_age_seconds"] = quote.get("age_seconds")
                            pos["quote_stale_days"] = quote.get("stale_days")
                            pos["quote_origin_source"] = quote.get("origin_source")
                            pos["quote_is_live"] = bool(
                                quote.get("is_live") or quote.get("source") == "yahoo_intraday"
                            )
                        if rec.get("market_value") is not None and account_nav > 0:
                            pos["weight"] = round(float(rec["market_value"]) / account_nav, 6)
                for ticker, rec in pnl.items():
                    if ticker in published_tickers:
                        continue
                    quote = provenance.get((ticker or "").upper()) or {}
                    account_row = {
                        "ticker": ticker,
                        "sleeve": "account",
                        "verdict": "hold",
                        "stage": None,
                        "live_only": True,
                        "shares": rec.get("shares"),
                        "cost_basis": rec.get("avg_cost"),
                        "current_price": rec.get("current_price"),
                        "market_value": rec.get("market_value"),
                        "unrealized_pnl": rec.get("unrealized_pnl"),
                        "unrealized_pct": rec.get("unrealized_pct"),
                        "weight": (
                            round(float(rec["market_value"]) / account_nav, 6)
                            if rec.get("market_value") is not None and account_nav > 0 else None
                        ),
                    }
                    if quote:
                        account_row.update({
                            "quote_source": quote.get("source"),
                            "quote_as_of": quote.get("as_of"),
                            "quote_time_kind": quote.get("time_kind"),
                            "quote_age_seconds": quote.get("age_seconds"),
                            "quote_stale_days": quote.get("stale_days"),
                            "quote_origin_source": quote.get("origin_source"),
                            "quote_is_live": bool(
                                quote.get("is_live") or quote.get("source") == "yahoo_intraday"
                            ),
                        })
                    payload.setdefault("positions", []).append(account_row)
            except Exception:
                pass

        # Every book gets canonical human-readable security names on read. This
        # repairs historical US/China/HK payloads without mutating runtime state.
        _attach_security_names(payload.get("positions"))

        # ------------------------------------------------------------------
        # Inject zh fields from the cache (read-only — no LLM in this path)
        # ------------------------------------------------------------------

        # disclaimer_zh
        disclaimer = payload.get("disclaimer")
        if disclaimer:
            zh_d = _cached_zh(disclaimer)
            if zh_d:
                payload["disclaimer_zh"] = zh_d

        # positions[].research.summary_zh (the Research Desk gate block)
        for pos in payload.get("positions", []):
            rb = pos.get("research")
            if rb and rb.get("summary"):
                zh_s = _cached_zh(rb["summary"])
                if zh_s:
                    rb["summary_zh"] = zh_s

        # positions[].thesis_full._zh
        for pos in payload.get("positions", []):
            tf = pos.get("thesis_full")
            if not tf:
                continue
            zh_tf: dict[str, Any] = {}
            for field in ("summary", "why_now", "sizing_rationale", "what_would_prove_wrong"):
                v = tf.get(field)
                if v:
                    zh = _cached_zh(v)
                    if zh:
                        zh_tf[field] = zh
            bull_zh = [_cached_zh(b) for b in (tf.get("bull") or [])]
            if any(zh for zh in bull_zh):
                zh_tf["bull"] = [zh if zh else b for zh, b in zip(bull_zh, tf.get("bull", []))]
            bear_zh = [_cached_zh(b) for b in (tf.get("bear") or [])]
            if any(zh for zh in bear_zh):
                zh_tf["bear"] = [zh if zh else b for zh, b in zip(bear_zh, tf.get("bear", []))]
            if zh_tf:
                tf["_zh"] = zh_tf

        # rejected[]._zh
        for rej in payload.get("rejected", []):
            zh_rej: dict[str, Any] = {}
            reason = rej.get("reason")
            if reason:
                zh_r = _cached_zh(reason)
                if zh_r:
                    zh_rej["reason"] = zh_r
            bear_zh = [_cached_zh(b) for b in (rej.get("bear") or [])]
            if any(zh for zh in bear_zh):
                zh_rej["bear"] = [zh if zh else b for zh, b in zip(bear_zh, rej.get("bear", []))]
            if zh_rej:
                rej["_zh"] = zh_rej

        # Banner write-up (top-of-page one-paragraph summary). It's published from the live
        # submission, which is CLEARED at the start of every run — so a run that carries the book
        # unchanged (feed gate, off-hours, skipped Brain) nulls it even though the last decision's
        # rationale still holds. For the Brain books, fall back to the most recent decision-log
        # summary so the banner never goes blank when the book hasn't changed.
        if not payload.get("summary"):
            src = _brain_book_module(portfolio)
            if src is not None:
                try:
                    # walk newest→oldest to the last decision that actually CARRIES a summary —
                    # a skipped/feed-gated run appends a summary-less entry, which shouldn't blank
                    # the banner when an earlier rationale (the still-current book) holds.
                    for rec in src.load_decisions(60):
                        if rec.get("summary"):
                            payload["summary"] = rec["summary"]
                            if not payload.get("sold_note"):
                                payload["sold_note"] = rec.get("sold_note")
                            break
                except Exception:  # noqa: BLE001
                    pass
        # zh for the banner summary (cache lookup; client falls back to English when cold)
        _sum = payload.get("summary")
        if _sum and not payload.get("summary_zh"):
            zh_sum = _cached_zh(_sum)
            if zh_sum:
                payload["summary_zh"] = zh_sum

        return JSONResponse(payload)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


# The tab-switcher status payload is just NAV/return chips — re-pricing every book on every poll or
# tab click is wasteful, so cache the assembled payload for a short window. A live trade or reprice
# shows up within _PORTFOLIOS_TTL; the per-book live marks underneath have their own (shorter) caches.
_PORTFOLIOS_TTL = 45.0  # seconds
_portfolios_cache: dict[str, Any] = {}  # {"payload": dict, "ts": float}


def _portfolio_status(meta: dict) -> dict:
    """Assemble one book's tab-switcher row (metadata + quick status). I/O-bound (live marks +
    benchmark history), so callers run these concurrently across books."""
    from portfolio import registry
    pid = meta["id"]
    status: dict[str, Any] = {"nav": None, "total_return_pct": None,
                              "vs_benchmark_pct": None, "vs_spy_pct": None,
                              "day_change_pct": None, "holdings": 0, "cash_pct": None, "as_of": None}
    if registry.is_archived(pid):
        perf = _archived_performance(pid)
        nav = perf.get("current_nav") or 0
        status.update({
            "nav": perf.get("current_nav"),
            "total_return_pct": perf.get("total_return_pct"),
            "vs_benchmark_pct": perf.get("vs_benchmark_pct"),
            "vs_spy_pct": perf.get("vs_spy_pct"),
            "day_change_pct": perf.get("day_change_pct"),
            "cash_pct": round((perf.get("cash") or 0) / nav * 100, 1) if nav else None,
            "as_of": perf.get("frozen_as_of"),
        })
        snapshot = _read_json_object(registry.data_dir(pid) / "latest.json")
        status["holdings"] = len(snapshot.get("positions") or [])
        return {**{k: meta.get(k) for k in (
                    "id", "name", "tagline", "kind", "manager", "benchmark",
                    "benchmark_name", "benchmark_name_zh", "currency")},
                "active": False, "lifecycle": "archived",
                "superseded_by": meta.get("superseded_by"),
                "archived_reason": meta.get("archived_reason"),
                "status": status}

    # the self-directed book has its own engine (not paper_account) — read its NAV/return directly
    if pid == "self_directed":
        try:
            from portfolio import self_directed
            held = list((self_directed._load_account().get("positions") or {}).keys())
            bk = self_directed.book(
                prices=_live_prices(held, refresh=False),
                read_only=True,
                resolve_missing_prices=False,
            )  # tab badges are snapshot-only; the active-book live endpoint refreshes quotes
            alloc = bk.get("allocation") or {}
            status.update({
                "nav": bk.get("nav"),
                "total_return_pct": alloc.get("total_return_pct"),
                "cash_pct": round((alloc.get("cash_pct") or 0) * 100, 1),
                "holdings": alloc.get("n_positions") or 0,
                "as_of": bk.get("inception_date"),
            })
        except Exception:
            pass
        # vs_spy and vs_defensive: benchmark_ledger already computes these bogey returns; wire the
        # read here so the leaderboard row for self_directed carries the same performance columns
        # as the other books. Best-effort: skip cleanly if the ledger hasn't been built yet.
        try:
            from brain import benchmark_ledger
            ledger = benchmark_ledger.latest()
            bogeys = ledger.get("bogeys") or {}
            spy_ret = (bogeys.get("spy") or {}).get("return_pct")
            def_ret = (bogeys.get("defensive") or {}).get("return_pct")
            own_ret = status.get("total_return_pct")
            if own_ret is not None and spy_ret is not None:
                status["vs_spy_pct"] = round(own_ret - spy_ret, 4)
                status["vs_benchmark_pct"] = status["vs_spy_pct"]
            if own_ret is not None and def_ret is not None:
                status["vs_defensive_pct"] = round(own_ret - def_ret, 4)
        except Exception:  # noqa: BLE001
            pass
        return {**{k: meta.get(k) for k in (
                    "id", "name", "tagline", "kind", "manager", "benchmark",
                    "benchmark_name", "benchmark_name_zh", "currency")},
                "status": status}
    from portfolio import paper_account
    try:
        # The switcher is navigation metadata, not a reason to live-fetch every book at once.
        # Use cache/snapshot marks here; /api/live_marks updates the active tab during its session.
        perf = paper_account.performance(portfolio_id=pid, prices=_book_marks(pid, refresh=False))
        nav = perf.get("current_nav") or 0
        status.update({
            "nav": perf.get("current_nav"),
            "total_return_pct": perf.get("total_return_pct"),
            "vs_benchmark_pct": perf.get("vs_benchmark_pct"),
            "vs_spy_pct": perf.get("vs_spy_pct"),
            "day_change_pct": perf.get("day_change_pct"),
            "cash_pct": round((perf.get("cash") or 0) / nav * 100, 1) if nav else None,
            "as_of": perf.get("realized_since"),
        })
    except Exception:
        pass
    try:
        latest = registry.data_dir(pid) / "latest.json"
        if latest.exists():
            d = json.loads(latest.read_text())
            status["holdings"] = len(d.get("positions") or [])
            status["as_of"] = d.get("as_of") or status["as_of"]
    except Exception:
        pass
    return {**{k: meta.get(k) for k in (
                "id", "name", "tagline", "kind", "manager", "benchmark",
                "benchmark_name", "benchmark_name_zh", "currency")},
            "active": bool(meta.get("active", True)),
            "lifecycle": meta.get("status") or ("active" if meta.get("active", True) else "archived"),
            "superseded_by": meta.get("superseded_by"),
            "archived_reason": meta.get("archived_reason"),
            "status": status}


@router.get("/api/portfolios")
def api_portfolios() -> JSONResponse:
    """The set of portfolios the dashboard switches between, each with a quick status
    (NAV, return, versus-book-benchmark, holdings) for the tab labels. US Brain is the active US
    Mastermind Portfolio; Flagship, Heavyweight, and ETF remain read-only archived history.

    Each book's status is I/O-bound (live marks + benchmark history); we price them concurrently
    and cache the assembled payload for ``_PORTFOLIOS_TTL`` so a tab click / poll doesn't re-price."""
    from portfolio import registry
    now = time.time()
    cached = _portfolios_cache.get("payload")
    if cached is not None and (now - _portfolios_cache.get("ts", 0.0)) < _PORTFOLIOS_TTL:
        return JSONResponse(cached)

    metas = registry.all_portfolios()
    # Price the books concurrently — each row is independent and network-bound, so wall-clock
    # collapses to roughly the slowest single book instead of the sum across all of them.
    with ThreadPoolExecutor(max_workers=max(1, len(metas))) as ex:
        out = list(ex.map(_portfolio_status, metas))

    payload = {"portfolios": out, "default": registry.DASHBOARD_DEFAULT_ID,
               "scope": "mastermind_portfolio"}
    _portfolios_cache["payload"] = payload
    _portfolios_cache["ts"] = now
    return JSONResponse(payload)


@router.get("/api/forward-evaluation")
def api_forward_evaluation(portfolio: str | None = None,
                           asof: str | None = None) -> JSONResponse:
    """Compact read-only evidence status for the three active regional portfolio brains.

    This route only serves already-materialised runtime artifacts.  It never computes a metric,
    takes a book lock, calls a feed/model, or writes the evaluation cohort/snapshots.
    """
    from portfolio import forward_evaluation, registry

    if portfolio is not None and not registry.is_known(portfolio):
        return JSONResponse({
            "schema": forward_evaluation.STATUS_SCHEMA,
            "book": portfolio,
            "status": "unknown_book",
            "write_permitted": False,
        }, status_code=404)
    try:
        return JSONResponse(forward_evaluation.status(portfolio, asof))
    except ValueError:
        _log.warning("Rejected invalid forward-evaluation request", exc_info=True)
        return JSONResponse({
            "schema": forward_evaluation.STATUS_SCHEMA,
            "book": portfolio,
            "status": "invalid_request",
            "write_permitted": False,
            "error": "asof must be a valid ISO date (YYYY-MM-DD)",
        }, status_code=400)


@router.get("/api/decisions")
def api_decisions(portfolio: str = "autonomous", limit: int = 60) -> JSONResponse:
    """Mastermind Portfolio's structured daily decision journal for an active or archived Brain."""
    try:
        _src = _brain_book_module(portfolio)
        if _src is None:
            return JSONResponse({"decisions": [], "note": "decision log is Brain-book-only (autonomous/heavyweight/china/hk/etf)"})
        decisions = _src.load_decisions(limit)
        today_iso = date.today().isoformat()
        # Resolve names for every Brain book on read so historical US and venue-
        # book decisions render like the Positions and Trade History panels.
        # A dollar figure alone doesn't say how much of a position a SELL trimmed or whether it
        # made money. Enrich each executed sell with the fraction of the position sold (pct_sold;
        # 1.0 = full exit) and the realized P&L + %, sourced from the SAME FIFO blotter the Trade
        # History panel uses so the two agree. Derived from fills on every read, so historical
        # decision-log entries (which stored only ticker/side/value) backfill too.
        try:
            from portfolio import trade_history
            _sell = trade_history.sell_realized(portfolio)
        except Exception:  # noqa: BLE001
            _sell = {}
        # Attach cached Chinese for the AI write-ups so the Daily Decision Log renders in
        # Chinese when zh is toggled. cached_zh() is a pure cache lookup (None -> client
        # falls back to English) — warmed by brain.translate.translate_decisions() on the
        # daily run; English never regresses if the cache is cold.
        for d in decisions:
            # flag a decision logged today so the UI can highlight + tag it "new"
            d["today"] = str(d.get("asof") or "")[:10] == today_iso
            _attach_security_names(d.get("executed"))
            _attach_security_names(d.get("holdings"))
            _attach_security_names(d.get("effective_holdings"))
            receipt_verified = _decision_execution_receipt_verified(d)
            if receipt_verified:
                d["execution_evidence_status"] = "receipt_verified"
            elif d.get("target_status") == "executed" or d.get("executed"):
                # Older rows may contain plausible-looking trade summaries, but no immutable
                # receipt/fill lineage.  Preserve them for audit without upgrading them to fills.
                d["execution_evidence_status"] = "legacy_unverified"
            else:
                # Never trust a persisted display classification; derive it on every read.
                d["execution_evidence_status"] = "none"
            sell_asof = str(d.get("settled_asof") or d.get("asof") or "")[:10]
            for rec in (d.get("executed") or []):
                if rec.get("side") == "sell":
                    # A queued decision can settle on a later session.  FIFO P&L belongs to the
                    # actual settlement day, never the proposal/acceptance day.
                    det = _sell.get((sell_asof, (rec.get("ticker") or "").upper()))
                    if det:
                        for k in ("pct_of_position", "realized_pnl", "realized_pct"):
                            if det.get(k) is not None and rec.get(k) is None:
                                rec[k] = det[k]
            for fld in ("summary", "sold_note", "brain_text"):
                v = d.get(fld)
                if v:
                    zh = _cached_zh(v)
                    if zh:
                        d[fld + "_zh"] = zh
            for h in (d.get("holdings") or []) + (d.get("effective_holdings") or []):
                r = h.get("rationale")
                if r:
                    zh = _cached_zh(r)
                    if zh:
                        h["rationale_zh"] = zh
        from portfolio import registry
        meta = registry.get(portfolio)
        return JSONResponse({"decisions": decisions, "portfolio": portfolio,
                             "lifecycle": meta.get("status"),
                             "archived": registry.is_archived(portfolio),
                             "scope": "mastermind_portfolio"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"decisions": [], "error": str(exc)})


@router.get("/api/posture")
def api_posture(book: str = _PRODUCT_DEFAULT_ID) -> JSONResponse:
    """The book's STRATEGY-LABEL signal — a glance-able posture on top of the free-form rationale:
    {book, posture_label, posture_label_zh, posture_tone, sub_strategy, favored[], avoided[],
    driver, detail, cash_pct, invested_pct, available}.

    Derived deterministically from the book's structured state (cash / gross / net trade flow /
    macro regime) and enriched with a keyword scan over the Brain's own write-up. Read-only,
    offline (no LLM), and graceful: an absent / malformed book degrades to ``available: False``
    rather than raising. The `book` id is any registry portfolio (flagship / autonomous /
    heavyweight / china / hk / etf)."""
    book = _product_portfolio_id(book)
    try:
        from brain import posture as _posture
        return JSONResponse(_posture.posture(book))
    except Exception as exc:  # noqa: BLE001 — never raise; degrade to an honest stub
        return JSONResponse({"book": book, "available": False, "posture_label": "—",
                             "posture_label_zh": "—", "posture_tone": "muted", "sub_strategy": None,
                             "favored": [], "avoided": [], "driver": None, "detail": None,
                             "cash_pct": None, "invested_pct": None, "error": str(exc)})


def _enrich_rotation_pairs(view: dict) -> None:
    """Read-only display enrichment: attach the rotation_tensor's ``top_pairs`` extract to the
    served view so the E1.2 mirror can render the top rotation pairs. The market_view artifact's
    rotation_tensor plane carries only ``headline_episode`` in its ``raw``; the pairs live at
    ``rs_velocity.top_pairs`` of the tensor artifact. This mutates only the SERVED copy (never the
    on-disk artifact, never any sizing path) and no-ops silently when the organ is absent."""
    try:
        planes = view.get("planes")
        rt = planes.get("rotation_tensor") if isinstance(planes, dict) else None
        if not isinstance(rt, dict):
            return
        raw = rt.get("raw")
        if not isinstance(raw, dict) or raw.get("present") is False:
            return
        tpath = _data() / "market_view" / "rotation_tensor.json"
        if not tpath.exists():
            return
        tensor = json.loads(tpath.read_text())
        pairs = ((tensor.get("rs_velocity") or {}).get("top_pairs")
                 if isinstance(tensor, dict) else None)
        if isinstance(pairs, list):
            raw["top_pairs"] = pairs
    except Exception:  # noqa: BLE001 — enrichment is best-effort; never break the response
        pass


@router.get("/api/market_view")
def api_market_view() -> JSONResponse:
    """The perception artifact (W-E.1 task E1.2) — the one deterministic, freshness+confidence
    stamped market view (schema market_view.v1): planes{}, net_posture_tilt, label_vs_planes,
    disagreements[], coherence, brief, budget_ref, and the rotation_tensor plane's top_pairs.

    Read-only: serves data/market_view/latest.json verbatim. No behavior change — this is the
    E1.2 HTML mirror's data source, not a sizing path. Degrades to an honest ``available:false``
    stub when the artifact is absent/unreadable (the organ built-but-not-running protects nothing
    but breaks nothing) rather than raising."""
    path = _data() / "market_view" / "latest.json"
    try:
        if not path.exists():
            return JSONResponse(
                {"available": False, "note": "market_view artifact not built yet "
                 "(brain.market_view.build has not run)"},
                status_code=404, headers=_NOCACHE)
        view = json.loads(path.read_text())
        if not isinstance(view, dict):
            raise ValueError("artifact is not a JSON object")
        _enrich_rotation_pairs(view)
        return JSONResponse(view, headers=_NOCACHE)
    except Exception as exc:  # noqa: BLE001 — never raise; degrade to an honest stub
        return JSONResponse(
            {"available": False, "error": str(exc)}, status_code=500, headers=_NOCACHE)


@router.get("/api/agenda")
def api_agenda() -> JSONResponse:
    """The Improvement Agenda artifact (W-L / L3) — the weekly self-critique fusing every
    accountability artifact into a ranked list of {evidence, suggested_fix, fix_type, expected_impact,
    owner, agentos_ref, readiness}. ``readiness_input`` carries a display-safe Macro root label plus
    SHA/resolver provenance for the optional Agent OS readiness input. Serves the latest
    data/agenda/<date>.json verbatim (schema improvement_agenda.v1); missing or malformed readiness
    fails open and never changes rank.

    Read-only + advisory: this artifact ranks and reports — it never trades, flips a flag, or mutates
    a seat. Degrades to an honest ``available:false`` stub when no agenda has been built yet (the
    weekly CIO job writes it) rather than raising."""
    try:
        from brain import improvement_agenda
        agenda = improvement_agenda.latest()
        if not agenda:
            return JSONResponse(
                {"available": False, "note": "no agenda built yet "
                 "(brain.improvement_agenda.write runs in the weekly CIO job)"},
                status_code=404, headers=_NOCACHE)
        return JSONResponse(agenda, headers=_NOCACHE)
    except Exception as exc:  # noqa: BLE001 — never raise; degrade to an honest stub
        return JSONResponse(
            {"available": False, "error": str(exc)}, status_code=500, headers=_NOCACHE)


@router.get("/api/etf/outcomes")
def api_etf_outcomes() -> JSONResponse:
    """The ETF book's accountability scorecard — every past pick forward-graded vs SPY (21d
    rel-return), with hit-rate, per-conviction calibration, weight-IC, and the book-edge (Newey-West
    t over independent windows). 'building' until enough resolves. Backs the ETF track-record panel."""
    try:
        from portfolio import etf_outcomes
        return JSONResponse(etf_outcomes.summary())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"scorecard": {"status": "building"}, "error": str(exc)})


@router.get("/api/overnight-tape")
def api_overnight_tape() -> JSONResponse:
    """The LIVE overnight cross-asset tape — US index futures, international indices, FX/rates, vol,
    commodities and crypto, each with its overnight % change, plus a distilled risk read
    (calm/elevated/stressed). What's moving while the cash market is shut — the thing the EOD macro
    dashboard can't see. Polled by the dashboard's Overnight Tape panel; cached ~5 min server-side."""
    try:
        from data_layer import overnight
        return JSONResponse(overnight.tape())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"groups": {}, "risk": {"state": "calm", "reasons": ["unavailable"]},
                             "live": False, "error": str(exc)})


@router.get("/api/research")
def api_research() -> JSONResponse:
    notes_dir = _data() / "research" / "notes"
    if not notes_dir.exists():
        return JSONResponse([])
    try:
        parsed: list[dict[str, Any]] = []
        for p in notes_dir.glob("*.md"):
            note = _parse_note(p)
            if note:
                parsed.append(note)
        # sort newest first
        parsed.sort(key=lambda n: n["_sort_key"], reverse=True)
        # collapse identical notes (same title + body) — keep the newest of each;
        # earlier test runs wrote duplicate note files, which would otherwise spam the feed
        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for n in parsed:
            key = (n["title"], n["body_md"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(n)
        # strip internal sort key, cap at 30; inject zh fields from cache
        out = []
        for n in deduped[:30]:
            note = {k: v for k, v in n.items() if k != "_sort_key"}
            # keys are always present (null when uncached) so the client can rely on them
            note["title_zh"] = _cached_zh(note.get("title") or "")
            note["body_md_zh"] = _cached_zh(note.get("body_md") or "")
            out.append(note)
        return JSONResponse(out)
    except Exception:
        return JSONResponse([])


@router.get("/api/research_papers")
def api_research_papers() -> JSONResponse:
    """The Research page contract — one row per gated buy decision, newest first.

    Each row is a holistic research paper joined with the live book's gate result: the
    engine buy-score, the research score, the combined Conviction Index, the viability, the
    action (buy_confirmed / research_held / evaluated), the decision time, and the full
    report (markdown + sections) for the 'view thesis' panel.
    """
    try:
        from brain import research_paper
        papers = research_paper.load_papers()
    except Exception as exc:
        return JSONResponse({"papers": [], "error": str(exc)})

    # join with the latest book: ticker -> (research_block, action, trade_time, weight)
    gate: dict[str, dict] = {}
    try:
        book = json.loads((_data() / "portfolio" / "latest.json").read_text())
        for pos in book.get("positions", []):
            rb = pos.get("research")
            if rb and pos.get("sleeve") == "conviction":
                gate[(pos.get("ticker") or "").upper()] = {
                    "block": rb, "action": "buy_confirmed",
                    "trade_time": pos.get("opened_at"), "weight": pos.get("weight"),
                }
        for held in book.get("research_held", []):
            t = (held.get("ticker") or "").upper()
            gate.setdefault(t, {"block": held, "action": "research_held",
                                "trade_time": None, "weight": 0.0})
    except Exception:
        pass

    out: list[dict[str, Any]] = []
    for p in papers:
        t = (p.get("ticker") or "").upper()
        g = gate.get(t, {})
        rb = g.get("block") or {}
        summary = p.get("summary") or ""
        out.append({
            "id": p.get("id"),
            "ticker": t,
            "asof": p.get("asof"),
            "reviewed_at": p.get("generated_at"),
            "trade_time": g.get("trade_time"),
            "action": g.get("action", "evaluated"),
            "mode": p.get("mode"),
            # prefer the live book's gate result; fall back to the gate the paper stamped on
            # itself at review time (so a reviewed-but-not-traded name still shows its scores)
            "engine_score": rb.get("engine_score", p.get("engine_score")),
            "research_score": p.get("research_score"),
            "combined": rb.get("combined", p.get("combined")),
            "confirmed": rb.get("confirmed", p.get("confirmed")),
            "viability": p.get("viability"),
            "recommend": p.get("recommend"),
            "confidence": p.get("confidence"),
            "fair_value": p.get("fair_value"),
            "price_at_review": p.get("price_at_review"),
            "price_assessment": p.get("price_assessment"),
            "weight": g.get("weight"),
            "summary": summary,
            "summary_zh": _cached_zh(summary) if summary else None,
            "report_md": p.get("report_md"),
            "report_md_zh": _cached_zh(p.get("report_md") or "") if p.get("report_md") else None,
            "key_risks": p.get("key_risks") or [],
        })
    return JSONResponse({"papers": out})


@router.get("/api/outcome_ledger")
def api_outcome_ledger() -> JSONResponse:
    """The Calibration page contract — the engine's accountability scorecard (brain.outcome_ledger).

    On every RESOLVED thesis it joins what the engine PREDICTED (prob_correct) with what HAPPENED
    (realized rel-return + hit/miss) and what it SAW (the point-in-time lens snapshot). Returns:
      - summary           : n / status / Brier / hit-rate / calibration_error
      - reliability_curve : per predicted-probability bucket, mean predicted vs realized hit-rate
                            (is the engine's stated 60% actually 60%?)
      - lens_edge         : per (lens, direction) realized hit-rate (which lenses actually predicted)
      - lens_weights      : the reliability multiplier the self-calibrating gate now applies per lens
      - records           : the resolved theses log (newest first, capped)
    status='building' (n=0) until the first cohort matures (~2026-07-17). Evergreen — the page polls it.
    """
    try:
        from brain import outcome_ledger
        summary = outcome_ledger.summary()
        curve = outcome_ledger.reliability_curve()
        edge = outcome_ledger.lens_edge(min_n=1)
        weights = outcome_ledger.lens_weights()
        records = outcome_ledger.load()
    except Exception as exc:
        return JSONResponse({"summary": {"n": 0, "status": "building", "brier": None,
                                         "hit_rate": None, "calibration_error": None},
                             "reliability_curve": [], "lens_edge": [], "lens_weights": {},
                             "records": [], "error": str(exc)})
    records = sorted(records, key=lambda r: r.get("asof_resolved") or "", reverse=True)[:200]
    rec_out = [{
        "thesis_id": r.get("thesis_id"), "subject": r.get("subject"), "sleeve": r.get("sleeve"),
        "asof_decided": r.get("asof_decided"), "asof_resolved": r.get("asof_resolved"),
        "prob_correct": r.get("prob_correct"), "realized_rel": r.get("realized_rel"),
        "outcome": r.get("outcome"), "quad_at_entry": r.get("quad_at_entry"),
        "confluence_at_entry": r.get("confluence_at_entry"), "lens_dirs": r.get("lens_dirs") or {},
    } for r in records]
    return JSONResponse({"summary": summary, "reliability_curve": curve, "lens_edge": edge,
                         "lens_weights": weights, "records": rec_out})


def _pending_target_projection(
    portfolio: str,
    *,
    prices: dict[str, float],
    market_status: dict[str, Any],
    account_state: dict[str, Any] | None,
    pending_read: tuple[str, dict[str, Any] | None] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Project one valid full-target queue into receipt-honest dashboard intent.

    A Brain ``pending_target.json`` is a complete desired book, not a fill ledger and not a
    share-sized order list.  The dashboard therefore exposes every target/current comparison in a
    dedicated audit object, while returning only actionable rows for the legacy Pending Orders
    panel.  In particular, an unchanged carried holding remains auditable but is not presented as
    an order.

    This helper is deliberately read-only.  ``load_pending_target`` validates without quarantine,
    and its account view was loaded by the route through ``_load_account_file`` (bypassing
    transaction recovery).  A GET must never recover a WAL, quarantine a queue, or otherwise
    change executable state.
    """
    from portfolio import paper_account, registry

    empty = {"portfolio": portfolio, "status": "none", "rows": []}
    if registry.is_archived(portfolio) or not registry.is_active(portfolio):
        return empty, []
    meta = registry.get(portfolio)
    if meta.get("manager") != "brain":
        return empty, []

    if pending_read is None:
        try:
            pending = paper_account.load_pending_target(portfolio)
        except Exception:  # noqa: BLE001 - a read failure is not executable intent
            return {"portfolio": portfolio, "status": "unavailable", "rows": []}, []
        if pending is None:
            # Presence plus a failed validating read means malformed/incompatible executable state.
            # Report that fail-closed condition without invoking quarantine/preflight; those paths
            # belong solely to settlement/startup.
            try:
                target_exists = paper_account.pending_target_file_exists(portfolio)
            except Exception:  # noqa: BLE001 - path/read uncertainty fails closed
                return {"portfolio": portfolio, "status": "unavailable", "rows": []}, []
            pending_status = "invalid" if target_exists else "none"
        else:
            pending_status = "queued"
    else:
        pending_status, pending = pending_read

    if pending_status != "queued" or not isinstance(pending, dict):
        if pending_status == "none":
            return empty, []
        return {"portfolio": portfolio, "status": pending_status, "rows": []}, []

    projection: dict[str, Any] = {
        "portfolio": portfolio,
        "status": "queued",
        "rows": [],
    }
    for source_key in ("asof", "queued_at", "schema_version", "engine_version"):
        value = pending.get(source_key)
        if value is not None:
            projection[source_key] = value
    fill_after = market_status.get("next_open")
    if isinstance(fill_after, str) and fill_after.strip():
        projection["fill_after"] = fill_after

    targets = pending["target"]  # canonical and validated by load_pending_target()
    try:
        if account_state is None:
            raise ValueError("account unavailable")
        account = account_state
        positions = paper_account.canonical_positive_positions(account.get("positions"))
    except Exception:  # noqa: BLE001 - fail closed; never leak account/runtime details
        projection["comparison_status"] = "account_unavailable"
        projection["rows"] = [
            {
                "ticker": ticker,
                "action": "comparison_unavailable",
                "target_weight": float(weight),
                "status": "queued",
                "source": "pending_target",
            }
            for ticker, weight in sorted(targets.items())
        ]
        return projection, []

    normalized_prices = {
        str(ticker).upper(): float(price)
        for ticker, price in (prices or {}).items()
        if (
            isinstance(ticker, str)
            and isinstance(price, (int, float))
            and not isinstance(price, bool)
            and math.isfinite(float(price))
            and float(price) > 0.0
        )
    }
    raw_cash = account.get("cash")
    cash_valid = (
        isinstance(raw_cash, (int, float))
        and not isinstance(raw_cash, bool)
        and math.isfinite(float(raw_cash))
        and float(raw_cash) >= 0.0
    )
    all_relevant_priced = all(
        ticker in normalized_prices for ticker in (set(positions) | set(targets))
    )
    current_weights: dict[str, float] | None = None
    nav: float | None = None
    if cash_valid and all_relevant_priced:
        nav = float(raw_cash) + math.fsum(
            lot["shares"] * normalized_prices[ticker]
            for ticker, lot in positions.items()
        )
        if math.isfinite(nav) and nav > 0.0:
            current_weights = {
                ticker: (lot["shares"] * normalized_prices[ticker]) / nav
                for ticker, lot in positions.items()
            }
    projection["comparison_status"] = (
        "current_weights_available" if current_weights is not None else "prices_unavailable"
    )
    no_trade_band_frac = paper_account._no_trade_band_frac()
    min_position_frac = paper_account._min_position_frac()
    constraints = pending.get("execution_constraints")
    preserved: set[str] = set()
    if isinstance(constraints, dict):
        preserved = set(constraints.get("tickers") or [])
        try:
            positions_match = (
                paper_account.positions_sha256(account.get("positions"))
                == constraints.get("positions_sha256")
            )
        except Exception:  # noqa: BLE001 - invalid comparison cannot grant actionability
            positions_match = False
        if not positions_match:
            projection["comparison_status"] = "constraint_snapshot_mismatch"

    audit_rows: list[dict[str, Any]] = []
    actionable_rows: list[dict[str, Any]] = []
    for ticker in sorted(set(targets) | set(positions)):
        target_weight = float(targets.get(ticker, 0.0))
        is_held = ticker in positions
        current_weight = current_weights.get(ticker) if current_weights is not None else None
        px = normalized_prices.get(ticker)
        suppressed_by: str | None = None

        if projection["comparison_status"] == "constraint_snapshot_mismatch":
            action, side = "blocked", None
            suppressed_by = "execution_constraint_snapshot"
        elif ticker in preserved:
            # The one privileged migration constraint pins the exact existing lot even when its
            # target weight and live mark imply a resize.  It is a carry, never a pending order.
            action, side = "hold", "hold"
            suppressed_by = "preserve_existing_shares"
        elif current_weights is None or nav is None:
            action, side = "comparison_unavailable", None
            suppressed_by = "prices_unavailable"
        elif not is_held:
            if target_weight < min_position_frac - 1e-9:
                action, side = "filtered", None
                suppressed_by = "minimum_position"
            elif px is None:
                action, side = "unpriceable", None
                suppressed_by = "missing_price"
            else:
                desired_shares = (target_weight * nav) / px
                if paper_account._buyable_shares(desired_shares, px, nav) <= 1e-9:
                    action, side = "filtered", None
                    suppressed_by = "buy_dust"
                else:
                    action, side = "buy", "buy"
        elif target_weight <= 0.0:
            if px is None:
                action, side = "unpriceable", None
                suppressed_by = "missing_exit_price"
            else:
                action, side = "exit", "sell"
        elif px is None:
            action, side = "unpriceable", None
            suppressed_by = "missing_price"
        else:
            held_shares = positions[ticker]["shares"]
            target_shares = (target_weight * nav) / px
            share_delta = target_shares - held_shares
            delta_value = abs(share_delta) * px
            if abs(share_delta) <= 1e-9 or delta_value < no_trade_band_frac * nav:
                action, side = "hold", "hold"
                suppressed_by = "no_trade_band" if abs(share_delta) > 1e-9 else None
            elif share_delta > 0.0:
                if paper_account._buyable_shares(share_delta, px, nav) <= 1e-9:
                    action, side = "hold", "hold"
                    suppressed_by = "buy_dust"
                else:
                    action, side = "add", "buy"
            else:
                # Sells are never dust-filtered; a trim at the band boundary is executable.
                action, side = "trim", "sell"

        row: dict[str, Any] = {
            "ticker": ticker,
            "action": action,
            "target_weight": target_weight,
            "status": "queued",
            "source": "pending_target",
        }
        if side is not None:
            row["side"] = side
        if suppressed_by is not None:
            row["suppressed_by"] = suppressed_by
        if current_weight is not None:
            row["current_weight"] = round(current_weight, 8)
        if pending.get("asof") is not None:
            row["placed_asof"] = pending["asof"]
        if pending.get("queued_at") is not None:
            row["queued_at"] = pending["queued_at"]
        if "fill_after" in projection:
            row["fill_after"] = projection["fill_after"]
        audit_rows.append(row)
        if side in {"buy", "sell"}:
            actionable_rows.append(dict(row))

    projection["rows"] = audit_rows
    return projection, actionable_rows


@router.get("/api/trades")
def api_trades(portfolio: str = _PRODUCT_DEFAULT_ID) -> JSONResponse:
    """Open/closed position summaries PLUS a complete per-fill blotter (`history`):
    every individual buy/sell, with realized P&L on sells and live unrealized P&L
    on still-open buy remainders. Archived books use only their final persisted marks and ledgers.
    Scoped to a portfolio (default: active US Brain)."""
    portfolio = _product_portfolio_id(portfolio)
    try:
        from portfolio import registry, trade_history
        if registry.is_archived(portfolio):
            archived_dir = registry.data_dir(portfolio)
            snapshot = _read_json_object(archived_dir / "latest.json")
            account = _read_json_object(archived_dir / "account.json")
            frozen_as_of = (_archived_performance(portfolio).get("frozen_as_of")
                            or snapshot.get("as_of"))
            persisted_marks = {
                str(row.get("ticker") or "").upper(): float(row["current_price"])
                for row in (snapshot.get("positions") or [])
                if isinstance(row, dict) and row.get("ticker") and _number(row.get("current_price"))
            }
            history = trade_history.history(
                persisted_marks,
                portfolio_id=portfolio,
                account_state=account,
            )
            pending = _read_json_list(archived_dir / "pending_orders.json")
            open_positions, closed_positions = _archived_position_rows(portfolio, frozen_as_of)
            _attach_security_names([*open_positions, *closed_positions, *history, *pending])
            return JSONResponse({
                "open": open_positions, "closed": closed_positions, "history": history,
                "pending": pending,
                "market": {"is_open": False, "session": "archived", "as_of": frozen_as_of,
                           "next_open": None},
                "portfolio": portfolio, "archived": True, "lifecycle": "archived",
                "frozen_as_of": frozen_as_of,
            })

        from portfolio import market_calendar, paper_account, position_log
        # Account, fills, and executable queue state form one paper transaction.  Hold the same
        # per-book lock as the writer while reading that snapshot, but never invoke WAL recovery
        # from a GET.  An outstanding WAL is an explicit transient-unavailable state: mixing its
        # partially applied account/fills would be more misleading than temporarily showing none.
        venue_book = bool(registry.venues(portfolio))
        with paper_account._paper_transaction_lock(portfolio):
            if paper_account._transaction_path(portfolio).exists():
                if venue_book:
                    from portfolio import china_calendar
                    market_status = china_calendar.status(
                        venue="HK" if portfolio == "hk" else "CN"
                    )
                else:
                    market_status = market_calendar.status()
                return JSONResponse({
                    "open": [],
                    "closed": [],
                    "history": [],
                    "pending": [],
                    "pending_target": {
                        "portfolio": portfolio,
                        "status": "unavailable",
                        "comparison_status": "transaction_pending",
                        "rows": [],
                    },
                    "market": market_status,
                    "snapshot_status": "transaction_pending",
                })

            try:
                history_account: dict[str, Any] | None = paper_account._load_account_file(
                    portfolio,
                    strict=True,
                )
                account_status = "coherent"
            except Exception:  # noqa: BLE001 - a GET never repairs or replaces account state
                history_account = None
                account_status = "account_unavailable"

            try:
                target_payload = paper_account.load_pending_target(portfolio)
                if target_payload is not None:
                    pending_read = ("queued", target_payload)
                elif paper_account.pending_target_file_exists(portfolio):
                    pending_read = ("invalid", None)
                else:
                    pending_read = ("none", None)
            except Exception:  # noqa: BLE001 - fail closed without quarantine/mutation
                target_payload = None
                pending_read = ("unavailable", None)

            held_tickers = sorted(
                (history_account.get("positions") or {})
                if isinstance(history_account, dict)
                and isinstance(history_account.get("positions"), dict)
                else []
            )
            target_tickers = sorted(
                (target_payload.get("target") or {})
                if isinstance(target_payload, dict)
                and isinstance(target_payload.get("target"), dict)
                else []
            )
            wanted_tickers = sorted(set(held_tickers) | set(target_tickers))

            # Venue-restricted books mark in base currency.  US books include pending-target names,
            # not only existing holdings, so min-position/whole-share/dust classification follows
            # the allocator instead of blindly calling every positive target a BUY.
            prices = (
                _book_marks(portfolio, tickers=wanted_tickers)
                if venue_book
                else _live_prices(wanted_tickers)
            )
            history = trade_history.history(
                prices,
                portfolio_id=portfolio,
                # ``positions=None`` deliberately tells the FIFO reader that authoritative open
                # shares are unknown.  Passing {} would incorrectly close every historical BUY;
                # passing None would invoke recovery-capable account loading.
                account_state=(
                    history_account
                    if history_account is not None
                    else {"positions": None}
                ),
            )
            pending = paper_account.load_pending(portfolio)
            open_positions = position_log.open_positions(portfolio_id=portfolio)
            closed_positions = position_log.closed_positions(portfolio_id=portfolio)
            # Market-status strip: venue books report their own exchange, not NYSE.
            if venue_book:
                from portfolio import china_calendar
                market_status = china_calendar.status(
                    venue="HK" if portfolio == "hk" else "CN"
                )
            else:
                market_status = market_calendar.status()
            pending_target, target_actions = _pending_target_projection(
                portfolio,
                prices=prices,
                market_status=market_status,
                account_state=history_account,
                pending_read=pending_read,
            )

        _attach_security_names([*open_positions, *closed_positions, *history, *pending])
        _attach_security_names(target_actions)
        _attach_security_names(pending_target.get("rows"))
        pending = [*pending, *target_actions]
        return JSONResponse({
            "open": open_positions,
            "closed": closed_positions,
            "history": history,
            "pending": pending,
            # Complete Brain target intent.  ``rows`` also includes unchanged carries, while the
            # legacy list above contains only allocator-actionable directions and never fills.
            "pending_target": pending_target,
            "market": market_status,
            "snapshot_status": account_status,
        })
    except Exception as exc:
        return JSONResponse({"open": [], "closed": [], "history": [],
                             "pending": [], "market": {}, "error": str(exc)})


# ---------------------------------------------------------------------------
# Self-Directed book (the third portfolio) — user-driven manual paper trading.
# Read-only marks come from the same delayed Polygon feed as the rest of the dashboard;
# orders/theses are written by the user. PAPER ONLY — long-only, no leverage.
# ---------------------------------------------------------------------------

class _OrderReq(BaseModel):
    ticker: str
    side: str                          # "buy" | "sell"
    shares: float | None = None        # share-sized order
    notional: float | None = None      # OR dollar-sized order ($ → shares at the fill price)


class _ThesisReq(BaseModel):
    ticker: str
    note: str = ""


@router.get("/api/self_directed")
def api_self_directed() -> JSONResponse:
    """The Self-Directed book: positions (live marks + weights), allocation scorecard,
    market state, pending orders. Settles any due pending orders on read."""
    try:
        from portfolio import self_directed
        # one batched live-price fetch for all held + pending names, then build the book
        held = list((self_directed._load_account().get("positions") or {}).keys())
        pend = [o.get("ticker") for o in self_directed._load_pending()]
        prices = _live_prices(sorted({*held, *[t for t in pend if t]}))
        payload = self_directed.book(
            prices=prices, read_only=True, resolve_missing_prices=False)
        _attach_security_names(payload.get("positions"))
        _attach_security_names(payload.get("pending"))
        return JSONResponse(payload)
    except Exception as exc:  # noqa: BLE001 — never 500 the dashboard
        return JSONResponse({"nav": 1_000_000.0, "cash": 1_000_000.0, "invested": 0.0,
                             "positions": [], "pending": [],
                             "allocation": {"cash_pct": 1.0, "gross": 0.0, "n_positions": 0,
                                            "largest_weight": 0.0, "total_unrealized_pnl": 0.0,
                                            "total_return_pct": 0.0},
                             "market": {"is_open": False, "session": "closed"},
                             "error": str(exc)})


@router.get("/api/self_directed/history")
def api_self_directed_history() -> JSONResponse:
    """Trade History blotter for the Self-Directed book (every fill + the pending queue)."""
    try:
        from portfolio import self_directed
        held = list((self_directed._load_account().get("positions") or {}).keys())
        prices = _live_prices(held)
        payload = self_directed.history(prices=prices)
        _attach_security_names(payload.get("history"))
        _attach_security_names(payload.get("pending"))
        return JSONResponse(payload)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"history": [], "pending": [], "realized_total": 0.0,
                             "n_closed": 0, "n_buys": 0, "win_rate": None, "error": str(exc)})


@router.get("/api/self_directed/search")
def api_self_directed_search(q: str = "") -> JSONResponse:
    """Live US-stock search (ticker or company name) for the order ticket."""
    try:
        from data_layer import polygon
        return JSONResponse({"results": polygon.search_tickers(q)})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"results": [], "error": str(exc)})


@router.get("/api/self_directed/quote")
def api_self_directed_quote(ticker: str = "") -> JSONResponse:
    """Live price + company name + market state for one ticker (order-ticket display)."""
    try:
        from portfolio import self_directed
        return JSONResponse(self_directed.quote_info(ticker))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ticker": (ticker or "").upper(), "price": None, "error": str(exc)})


@router.post("/api/self_directed/order")
def api_self_directed_order(req: _OrderReq) -> JSONResponse:
    """Place a buy/sell. Fills now at market if open; otherwise queues to the next open."""
    try:
        from portfolio import self_directed
        return JSONResponse(self_directed.place_order(
            req.ticker, req.side, req.shares, notional=req.notional))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/self_directed/thesis")
def api_self_directed_thesis(req: _ThesisReq) -> JSONResponse:
    """Save (or clear) the user's conviction thesis note for a position."""
    try:
        from portfolio import self_directed
        saved = self_directed.set_thesis(req.ticker, req.note)
        return JSONResponse({"ok": True, "ticker": (req.ticker or "").upper(), "thesis": saved})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/self_directed/cancel")
def api_self_directed_cancel(order_id: str = "") -> JSONResponse:
    """Cancel a still-pending (unfilled) order."""
    try:
        from portfolio import self_directed
        return JSONResponse({"ok": self_directed.cancel_order(order_id)})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.get("/api/outcomes")
def api_outcomes() -> JSONResponse:
    """Realized thesis outcomes — triple-barrier + rel-return vs SPY (the learning signal that
    feeds the Brier track record). `labels` per thesis, `summary` stats, and the graded
    `track_record`. Best-effort: returns empty-but-valid on any failure."""
    try:
        import bot  # noqa: F401 — bootstraps vendor/macro for the price accessor
        from datetime import date as _date
        from brain import calibration, outcomes, scorer
        asof = _date.today()
        realized = outcomes.realized_returns(asof)
        try:
            cal = calibration.load() or calibration.compute(asof)
        except Exception:  # noqa: BLE001
            cal = {}
        return JSONResponse({
            "labels": outcomes.all_labels(asof),
            "summary": outcomes.summary(asof),
            "track_record": scorer.track_record(asof, realized=realized),
            "calibration": cal,
        })
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"labels": [], "summary": {}, "track_record": {},
                             "calibration": {}, "error": str(exc)})


@router.get("/api/shadow_books")
def api_shadow_books() -> JSONResponse:
    """Parallel forward shadow books — the leakage-free A/B of decision policies (prod vs
    no-committee vs no-calibration vs engine-only). Returns the persisted leaderboard
    (per-policy forward NAV return, hit rate, Brier, holdings divergence vs prod). Best-effort:
    falls back to a live recompute if the file is absent, then to empty-but-valid."""
    try:
        import bot  # noqa: F401 — bootstraps vendor/macro for the price accessor
        from portfolio import shadow_books
        data = shadow_books.load_leaderboard()
        if not data:
            from datetime import date as _date
            data = shadow_books.run(_date.today().isoformat())
        return JSONResponse({
            "as_of": data.get("as_of"),
            "leaderboard": data.get("leaderboard", []),
            "books": data.get("books", {}),
            "policies": [{"id": p["id"], "label": p["label"], "label_zh": p.get("label_zh"),
                          "desc": p.get("desc"), "desc_zh": p.get("desc_zh")}
                         for p in shadow_books.POLICIES],
        })
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"leaderboard": [], "books": {}, "policies": [], "error": str(exc)})


@router.get("/api/predictions")
def api_predictions() -> JSONResponse:
    """Universe-wide forward prediction log — a falsifiable rel-return thesis on EVERY name the
    engine has a directional opinion on (~1,600), forward-labeled. Returns coverage + a
    date-CLUSTERED cross-sectional scorecard (rank-IC of ladder.score vs forward rel-return,
    directional hit-rate + Brier, 'up' edge), each with a CI + effective-n so small samples never
    overclaim. This is the statistical-power unlock — n grows with breadth, not portfolio turnover."""
    try:
        import bot  # noqa: F401 — bootstraps vendor/macro for the price panel
        from datetime import date as _date
        from portfolio import predictions
        return JSONResponse(predictions.summary(_date.today().isoformat()))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"coverage": {}, "scorecard": {}, "error": str(exc)})


@router.get("/api/rejections")
def api_rejections() -> JSONResponse:
    """Off-policy REJECTION log — every name the gate rejected (conviction veto / research hold /
    committee drop / timing withhold), forward-graded vs SPY. Returns coverage + the veto-regret
    scorecard ('did the gate veto winners?', split by reject stage). Read-only; best-effort."""
    try:
        import bot  # noqa: F401 — bootstraps vendor/macro for the price labeler
        from datetime import date as _date
        from portfolio import rejections
        return JSONResponse(rejections.summary(_date.today().isoformat()))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"coverage": {}, "scorecard": {}, "error": str(exc)})


@router.get("/api/shadow_bandit")
def api_shadow_bandit() -> JSONResponse:
    """Discounted Thompson Sampling over the shadow policies — each arm's discounted forward hit-rate
    posterior + P(arm is best). A faster, regime-adaptive read of which policy is winning than the raw
    cumulative-return leaderboard. Read-only (never switches the live policy); best-effort."""
    try:
        import bot  # noqa: F401 — bootstraps vendor/macro for the shadow ledgers
        from portfolio import bandit
        return JSONResponse(bandit.rank_shadow_books())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "building", "arms": [], "error": str(exc)})


@router.get("/api/student")
def api_student() -> JSONResponse:
    """The fast statistical STUDENT (#3, CatBoost) — its latest training metrics (OOS rank-IC, hit-rate,
    feature importances) + the current top predicted-edge names. 'unavailable' without catboost,
    'building' until the universe log accrues resolved rows. Read-only; best-effort."""
    try:
        import bot  # noqa: F401 — bootstraps vendor/macro for the price panel
        from brain import student
        out = student.summary()
        out["top_predicted"] = student.predict(top=12)
        return JSONResponse(out)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "building", "top_predicted": [], "error": str(exc)})


@router.get("/api/distill")
def api_distill() -> JSONResponse:
    """The DISTILLED-OPUS model (#3 v2) — its latest metrics (OOS AUC mimicking Opus's buys) + the names
    it predicts Opus would most likely buy. 'building' until Opus accrues months of decisions. Read-only."""
    try:
        import bot  # noqa: F401
        from brain import distill
        out = distill.summary()
        out["top_predicted"] = distill.predict(top=12)
        return JSONResponse(out)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "building", "top_predicted": [], "error": str(exc)})


@router.get("/api/interim_marks")
def api_interim_marks() -> JSONResponse:
    """Interim trajectory checkpoints (#11) — day-5/day-10 rel-return per open conviction thesis, a
    per-checkpoint hit-rate, and the live early-warning list (held names underwater at their latest
    checkpoint). Evidence only, never the 21-bday label. Read-only; best-effort."""
    try:
        import bot  # noqa: F401 — bootstraps vendor/macro for the price labeler
        from brain import interim_marks
        return JSONResponse(interim_marks.summary())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"scorecard": {}, "error": str(exc)})


@router.get("/api/engine_backtest")
def api_engine_backtest() -> JSONResponse:
    """Historical engine-backtest verdict — the HIGH-statistical-power, leakage-free read on the
    deterministic engine (DSR / PBO / BH-FDR / one-shot holdout over the survivorship-safe S&P-1500
    panel). Read-only: surfaces the persisted artifact (generated on demand by
    scripts/run_engine_backtest.py); honest 'unavailable' until a run is recorded."""
    try:
        import bot  # noqa: F401
        from loop import engine_backtest
        return JSONResponse(engine_backtest.load())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "unavailable", "error": str(exc)})


@router.get("/api/factor_zoo")
def api_factor_zoo() -> JSONResponse:
    """Advanced factor-alpha lab — a broad price-factor library + IC term-structure + a
    holdout-validated COMPOSITE, scored under the frozen multiple-testing gauntlet (DSR re-deflated
    at effective-N over the whole pool, PBO/CSCV, BH-FDR, one-shot 2022+ holdout). Read-only:
    surfaces the persisted artifact (generated on demand by scripts/run_factor_zoo.py)."""
    try:
        import bot  # noqa: F401
        from loop import factor_zoo
        return JSONResponse(factor_zoo.load())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "unavailable", "error": str(exc)})


@router.get("/api/fundamentals")
def api_fundamentals() -> JSONResponse:
    """PIT fundamental factors (value + quality) from SEC EDGAR — point-in-time (asof_date-gated, no
    look-ahead), scored through the frozen gauntlet, with regime-conditional IC. Read-only: surfaces
    the persisted artifact (generated on demand by scripts/run_fundamentals.py)."""
    try:
        import bot  # noqa: F401
        from loop import fundamentals
        return JSONResponse(fundamentals.load())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "unavailable", "error": str(exc)})


# ─────────────────────────────────────────────────────────────────────────────────────────────
# MASTERMIND PORTFOLIO LOOP (legacy route prefix: /api/mastermind_ai).
# This is NOT the public Mastermind AI market copilot served by Macro Dashboard.
# GETs are read-only snapshots; the POSTs are non-LLM operator paths registered in
# app/auth.py _NON_LLM_OPERATOR_PATHS (blocked on the serve-only mirror) and the whole
# /api/mastermind_ai prefix is denied in app/response_cache.py (always-fresh admin data).
# ─────────────────────────────────────────────────────────────────────────────────────────────

@router.get("/api/mastermind_ai")
def api_mastermind_ai() -> JSONResponse:
    """One-call status snapshot for the admin 'Mastermind Portfolio Loop' section: settings, flags, last
    loops, latest review, the current NW reflection (nudges/drift/coverage/quality), journal
    counts, and the operator directive queue."""
    try:
        import bot  # noqa: F401
        from brain import mastermind_ai
        payload = mastermind_ai.status()
        payload["product_scope"] = "mastermind_portfolio_loop"
        payload["public_chatbot_separate"] = True
        payload["legacy_route_prefix"] = "/api/mastermind_ai"
        return JSONResponse(payload)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"schema": "mastermind_ai_status.v1", "error": str(exc)})


@router.get("/api/mastermind_ai/loop_log")
def api_mastermind_ai_loop_log(n: int = 50) -> JSONResponse:
    """The self-improvement loop log (one row per nightly cycle) + the every-N-loop reviews."""
    try:
        import bot  # noqa: F401
        from brain import mastermind_ai
        n = max(1, min(int(n), 500))
        return JSONResponse({"loop_log": mastermind_ai.loop_log(limit=n),
                             "reviews": mastermind_ai.reviews(limit=12)})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"loop_log": [], "reviews": [], "error": str(exc)})


@router.get("/api/mastermind_ai/improvements")
def api_mastermind_ai_improvements() -> JSONResponse:
    """What has actually improved: pinned rules (+ their falsifier state), self_tune events,
    lesson taxonomy counts, and the agenda's current top items."""
    try:
        import bot  # noqa: F401
        from brain import mastermind_ai
        return JSONResponse(mastermind_ai.improvements())
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"pins": [], "agenda_top": [], "lessons_by_taxonomy": {},
                             "error": str(exc)})


@router.get("/api/mastermind_ai/reflection")
def api_mastermind_ai_reflection() -> JSONResponse:
    """The full latest nw_reflection.v1 report (contract drift, coverage, attribution,
    context quality, nudges)."""
    try:
        import bot  # noqa: F401
        from brain import nw_reflection
        return JSONResponse(nw_reflection.latest() or {"schema": nw_reflection.SCHEMA,
                                                       "state": "absent"})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"state": "absent", "error": str(exc)})


class _MMAISettingsReq(BaseModel):
    settings: dict


class _MMAIDirectiveReq(BaseModel):
    text: str


class _MMAIActNudgesReq(BaseModel):
    codes: list[str] | None = None    # missing/empty = all currently open nudges


@router.post("/api/mastermind_ai/settings")
def api_mastermind_ai_settings(req: _MMAISettingsReq) -> JSONResponse:
    """Operator settings patch — bounded to the known mastermind_ai keys (unknown/out-of-range
    keys are rejected, never applied)."""
    try:
        import bot  # noqa: F401
        from brain import mastermind_ai
        return JSONResponse(mastermind_ai.update_settings(req.settings or {}))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/mastermind_ai/directive")
def api_mastermind_ai_directive(req: _MMAIDirectiveReq) -> JSONResponse:
    """Queue an operator directive for the NW orchestrator (published on the next macro
    snapshot push, ingested by the next nightly macro build). Intake-scrubbed: secrets,
    env names, and $-amounts are refused — this text lands on a public artifact."""
    try:
        import bot  # noqa: F401
        from brain import mastermind_ai
        return JSONResponse(mastermind_ai.add_directive(req.text))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/mastermind_ai/act_on_nudges")
def api_mastermind_ai_act_on_nudges(req: _MMAIActNudgesReq) -> JSONResponse:
    """Bulk-draft directives from the currently open reflection nudges (all of them when
    codes is empty/omitted). Authority is operator-granted: per-click via this endpoint, or
    as a standing grant via the auto_act_on_findings setting (in which case run_cycle drafts
    them automatically). Every drafted text passes the same intake scrub as a typed one."""
    try:
        import bot  # noqa: F401
        from brain import mastermind_ai
        return JSONResponse(mastermind_ai.draft_directives_from_nudges(req.codes))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.post("/api/mastermind_ai/run")
def api_mastermind_ai_run() -> JSONResponse:
    """Run one self-improvement cycle now (non-LLM, observational; same code path as the
    nightly loop_maintenance step)."""
    try:
        import bot  # noqa: F401
        from brain import mastermind_ai
        return JSONResponse(mastermind_ai.run_cycle(trigger="manual"))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@router.get("/api/readiness")
def api_readiness() -> JSONResponse:
    """Forward-proof readiness — which thresholds have crossed (calibration left cold-start,
    cross-sectional IC now statistically honest, shadow books first resolved) + the persistent
    alerts the daily build records. Drives the dashboard's 'go look now' banner."""
    try:
        import bot  # noqa: F401
        from portfolio import readiness
        return JSONResponse({"status": readiness.status(), "alerts": readiness.alerts()})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": {}, "alerts": [], "error": str(exc)})


@router.get("/api/portfolio_learning")
def api_portfolio_learning() -> JSONResponse:
    """Post-sell opportunity-cost ledger, measured lessons and context requests for the three
    active regional portfolios. Read-only; separate from the public Mastermind AI chatbot."""
    try:
        from brain import portfolio_learning
        return JSONResponse(portfolio_learning.status())
    except Exception:  # noqa: BLE001
        _log.exception("Portfolio learning status read failed")
        return JSONResponse({
            "schema": "mastermind_portfolio_learning.v1",
            "error": "portfolio learning unavailable",
        })


@router.get("/api/macro")
def api_macro() -> JSONResponse:
    """Key macro reads for the current regime: yield-curve regime, real 10y yield,
    DXY, VIX. Curve/real-yield come from the macro engine's rate-transmission state
    (calibrated, EN/ZH labelled); DXY/VIX levels + 1d change from the engine price
    store. Levels are EOD-grade (indices aren't on the delayed equity-snapshot key)."""
    out: dict[str, Any] = {"as_of": None, "yield_curve": None, "real_yield": None,
                           "dxy": None, "vix": None}
    # --- engine rate-transmission state (curve + real yields) ---
    try:
        regime = json.loads((_macro_data() / "regime" / "latest.json").read_text())
        out["as_of"] = regime.get("date")
        rates = (((regime.get("rate_inflation_transmission") or {}).get("state") or {})
                 .get("rates") or {})
        if rates:
            out["yield_curve"] = {
                "regime": rates.get("regime"),
                "direction": rates.get("direction"),
                "curve_2s10s": rates.get("curve_2s10s"),
                "nominal_10y": rates.get("nominal_10y"),
                "policy_gap": rates.get("policy_gap"),
                "label_en": (rates.get("label") or {}).get("en"),
                "label_zh": (rates.get("label") or {}).get("zh"),
            }
            out["real_yield"] = {
                "real_10y": rates.get("real_10y"),
                "pctile": rates.get("real_10y_pctile"),
                "chg_63d_bp": rates.get("real_10y_chg_63d_bp"),
                "regime": rates.get("regime"),
                "direction": rates.get("direction"),
            }
    except Exception:
        pass

    # --- DXY + VIX levels + 1d change from the engine yahoo store ---
    def _level_chg(ticker: str) -> dict | None:
        try:
            import bot  # noqa: F401  -> vendor/macro on sys.path
            from lib import store
            df = store.read("yahoo", ticker)
            if df is None or "close" not in getattr(df, "columns", []):
                return None
            s = df["close"].astype(float).dropna()
            if len(s) == 0:
                return None
            last = float(s.iloc[-1])
            prev = float(s.iloc[-2]) if len(s) > 1 else last
            return {"value": round(last, 2),
                    "chg": round(last - prev, 2),
                    "chg_pct": round((last / prev - 1) * 100, 2) if prev else 0.0}
        except Exception:
            return None

    dxy = _level_chg("DX-Y.NYB")
    vix = _level_chg("^VIX")
    if dxy:
        out["dxy"] = dxy
    if vix:
        # plain-English vol regime band
        v = vix["value"]
        band = ("calm" if v < 15 else "normal" if v < 20
                else "elevated" if v < 30 else "stress")
        vix["band"] = band
        out["vix"] = vix
    return JSONResponse(out)


# ---------------------------------------------------------------------------
# Brain Log (activity) localisation
# ---------------------------------------------------------------------------
# The activity feed assembles its English strings by interpolating tickers,
# weights and free-text theses, so a pure translation cache can't cover them.
# Instead each event carries a parallel zh title/detail: the STRUCTURED parts
# (verbs, sleeves, quadrant names, scaffolding) are mapped deterministically here
# while tickers/numbers stay verbatim; the FREE-TEXT parts (decision thesis,
# research note title/body) fall back to cached_zh(). The client picks the _zh
# variant only when zh is toggled, so English never regresses.
_TRADE_VERB_ZH = {
    "buy": "买入", "sell": "卖出", "add": "加仓", "trim": "减仓",
    "open": "开仓", "close": "平仓", "reduce": "减仓", "increase": "加仓",
    "exit": "退出", "hold": "持有", "rebalance": "再平衡", "cover": "回补",
}
_SLEEVE_ZH = {
    "conviction": "信念", "mechanical": "机械", "tactical": "战术",
    "hedge": "对冲", "core": "核心", "satellite": "卫星", "liquidity": "流动性",
}
_DECISION_LEAN_ZH = {
    "buy": "买入", "sell": "卖出", "add": "加仓", "trim": "减仓",
    "watch": "观察", "hold": "持有", "avoid": "回避", "exit": "退出",
    "reduce": "减仓", "increase": "加仓",
}
_QUAD_ZH = {
    "Goldilocks": "黄金区间", "Reflation": "再通胀", "Stagflation": "滞胀",
    "Growth-Scare": "增长恐慌", "Growth Scare": "增长恐慌", "Deflation": "通缩",
}


@router.get("/api/activity")
def api_activity() -> JSONResponse:
    """Reverse-chronological activity timeline (cap 60).

    Assembles events from:
      - positions_ledger history entries  (kind "trade")
      - decisions[] in latest.json        (kind "decision")
      - research note files               (kind "research")
      - runs table via latest.json as_of  (kind "run")

    Each event also carries title_zh / detail_zh so the Brain Log renders in
    Chinese when zh is toggled (see the localisation maps above).
    """
    events: list[dict] = []

    # --- trades from ledger history ---
    try:
        ledger_path = _data() / "portfolio" / "positions_ledger.json"
        if ledger_path.exists():
            ledger = json.loads(ledger_path.read_text())
            for key, entry in ledger.items():
                for h in entry.get("history", []):
                    ts = h.get("ts") or ""
                    ev = h.get("event", "")
                    ticker = entry.get("ticker", key.split(":")[-1])
                    weight = h.get("weight")
                    w_str = f" ({round((weight or 0)*100, 1)}%)" if weight is not None else ""
                    sleeve = entry.get("sleeve", "")
                    still_open = entry.get("still_open")
                    verb_zh = _TRADE_VERB_ZH.get(ev.lower(), ev.upper())
                    sleeve_zh = _SLEEVE_ZH.get(sleeve.lower(), sleeve)
                    events.append({
                        "ts": ts,
                        "kind": "trade",
                        "title": f"{ev.upper()} {ticker}{w_str}",
                        "title_zh": f"{verb_zh} {ticker}{w_str}",
                        "detail": (
                            f"{sleeve} sleeve | "
                            f"{'open' if still_open else 'closed'}"
                        ),
                        "detail_zh": (
                            f"{sleeve_zh}组合 | "
                            f"{'持有中' if still_open else '已平仓'}"
                        ),
                    })
    except Exception:
        pass

    # --- decisions from latest.json ---
    try:
        portfolio_path = _data() / "portfolio" / "latest.json"
        if portfolio_path.exists():
            portfolio = json.loads(portfolio_path.read_text())
            asof = portfolio.get("as_of", "")
            for d in portfolio.get("decisions", []):
                lean = d.get("lean", "watch")
                subject = d.get("subject", "?")
                thesis = d.get("thesis") or ""
                lean_zh = _DECISION_LEAN_ZH.get(lean.lower(), lean.upper())
                thesis_zh = _cached_zh(thesis) or thesis
                events.append({
                    "ts": d.get("logged_at") or asof or "",
                    "kind": "decision",
                    "title": f"Decision: {lean.upper()} {subject}",
                    "title_zh": f"决策：{lean_zh} {subject}",
                    "detail": thesis[:200],
                    "detail_zh": thesis_zh[:200],
                })
            # top-level run event
            if asof:
                regime = (portfolio.get("regime") or {})
                quad = regime.get("quad_name") or regime.get("quad")
                quad_zh = _QUAD_ZH.get(quad, quad)
                gross_pct = portfolio.get("gross", 0) * 100
                cash_pct = portfolio.get("cash", 0) * 100
                events.append({
                    "ts": asof,
                    "kind": "run",
                    "title": f"Book rebuilt — {asof}",
                    "title_zh": f"组合重建 — {asof}",
                    "detail": (
                        f"Quad: {quad} | "
                        f"gross={gross_pct:.1f}% cash={cash_pct:.1f}%"
                    ),
                    "detail_zh": (
                        f"象限：{quad_zh} | "
                        f"总敞口={gross_pct:.1f}% 现金={cash_pct:.1f}%"
                    ),
                })
    except Exception:
        pass

    # --- research notes (deduped on title+body, newest kept) ---
    try:
        notes_dir = _data() / "research" / "notes"
        if notes_dir.exists():
            parsed = [n for n in (_parse_note(p) for p in notes_dir.glob("*.md"))
                      if n and n.get("date")]
            parsed.sort(key=lambda n: n["_sort_key"], reverse=True)
            seen: set[tuple[str, str]] = set()
            for note in parsed:
                key = (note["title"], note["body_md"])
                if key in seen:
                    continue
                seen.add(key)
                tickers_str = (", ".join(note["tickers"]) if note.get("tickers") else "")
                title = note["title"]
                body_md = note.get("body_md") or ""
                title_zh = _cached_zh(title) or title
                body_zh = _cached_zh(body_md) or body_md
                events.append({
                    "ts": note["date"],
                    "kind": "research",
                    "title": title,
                    "title_zh": title_zh,
                    "detail": (
                        (f"Tickers: {tickers_str} | " if tickers_str else "")
                        + body_md[:160]
                    ),
                    "detail_zh": (
                        (f"标的：{tickers_str} | " if tickers_str else "")
                        + body_zh[:160]
                    ),
                })
    except Exception:
        pass

    # flag actions logged today so the Brain Log can highlight + tag them "new".
    # Wall-clock date is the trading-day source of truth here (matches the data's as_of).
    today_iso = date.today().isoformat()
    for e in events:
        e["today"] = (e.get("ts") or "")[:10] == today_iso

    # sort newest first, cap at 60
    events.sort(key=lambda e: e.get("ts") or "", reverse=True)
    return JSONResponse(events[:60])




@router.get("/api/runs")
def api_runs() -> JSONResponse:
    """List all run-log entries, newest first.
    Each entry: {run_id, ts, kind, title, n_steps, cost_usd, summary}.

    title_zh / summary_zh carry the cached Chinese translation of the run's AI write-up so
    the Brain Activity ("Full Trace") log renders in Chinese when zh is toggled. cached_zh()
    is a pure cache lookup (returns None -> client falls back to English) until
    brain.translate.translate_runs() warms the cache on the daily run; English never regresses.
    """
    try:
        from brain import runlog
        runs = runlog.list_runs()
        for r in runs:
            tz = _cached_zh(r.get("title") or "")
            if tz:
                r["title_zh"] = tz
            sz = _cached_zh(r.get("summary") or "")
            if sz:
                r["summary_zh"] = sz
        return JSONResponse(runs)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/runlog")
def api_runlog(run_id: str | None = None) -> JSONResponse:
    """Return the complete granular step-trace for a run.
    Pass ?run_id=ID or omit for the most recent run.
    Returns {run_id, ts, kind, title, steps: [{ts, type, title, detail, ...}]}."""
    try:
        from brain import runlog
        return JSONResponse(runlog.read_run(run_id or None))
    except Exception as exc:
        return JSONResponse({"run_id": run_id, "steps": [], "error": str(exc)}, status_code=500)


# ---------------------------------------------------------------------------
# DESK observability — surface the multi-seat Flagship "desk" artifacts the
# committee/gate/risk machinery already writes to disk. STRICTLY READ-ONLY and
# ADDITIVE: every endpoint is wrapped try/except → JSONResponse, never raises,
# and degrades to {"status": "building"} / [] when an artifact is absent.
#
# Artifact tree (relative to the project data/ dir):
#   committee/<asof>/_FLAGSHIP/strategist.json   — the macro strategist verdict
#   committee/<asof>/<TICKER>/{forge,sentinel,nexus}.json — per-name committee
#   gate_officer/<asof>/decisions.json           — portfolio gate decisions
#   risk_officer/<asof>/decisions.json           — portfolio risk decisions
#   portfolios/flagship/watchlist.jsonl          — parked (withheld) names
#   brain/{calibration,reputation}.json,
#   brain/attribution/_rollup.json, brain/cio/<week>.{json,md} — per-seat scorecard
# ---------------------------------------------------------------------------

def _committee_dir() -> Path:
    return _data() / "committee"


def _gate_officer_dir() -> Path:
    return _data() / "gate_officer"


def _risk_officer_dir() -> Path:
    return _data() / "risk_officer"


def _macro_risk_dir() -> Path:
    return _data() / "macro_risk"


def _is_date_dir(name: str) -> bool:
    """A committee/<asof> dir name is an ISO date (YYYY-MM-DD)."""
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", name or ""))


def _latest_asof(*roots: Path) -> str | None:
    """The most-recent ISO-date subdir name across one or more artifact roots ({} → None)."""
    dates: set[str] = set()
    for root in roots:
        try:
            for p in root.iterdir():
                if p.is_dir() and _is_date_dir(p.name):
                    dates.add(p.name)
        except Exception:  # noqa: BLE001
            continue
    return max(dates) if dates else None


def _read_json(path: Path) -> dict[str, Any]:
    """Parse a JSON file → dict; {} on any failure (missing / malformed)."""
    try:
        if path.exists():
            d = json.loads(path.read_text())
            return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001
        return {}
    return {}


@router.get("/api/desk/strategist")
def api_desk_strategist(asof: str = "") -> JSONResponse:
    """The macro STRATEGIST verdict for `asof` (default: most-recent available) — the confirmed
    themes (with member names + why), the backdrop stance, the crowding flags, the emerging
    watch-list and the rationale. 'building' until the desk has written a strategist artifact."""
    try:
        asof = (asof or "")[:10]
        if not (asof and _is_date_dir(asof)):
            asof = _latest_asof(_committee_dir())
        if not asof:
            return JSONResponse({"status": "building", "asof": None})
        j = _read_json(_committee_dir() / asof / "_FLAGSHIP" / "strategist.json")
        verdict = j.get("verdict") or {}
        if not verdict:
            return JSONResponse({"status": "building", "asof": asof})
        inp = j.get("input") or {}
        # bound payloads: cap the per-theme member list + the emerging/crowding arrays
        themes = []
        for t in (verdict.get("confirmed_themes") or [])[:20]:
            themes.append({
                "theme": t.get("theme"),
                "stage": t.get("stage"),
                "leadership": t.get("leadership"),
                "names": (t.get("names") or [])[:12],
                "why": (t.get("why") or "")[:600],
            })
        return JSONResponse({
            "status": "scoring",
            "asof": asof,
            "regime": {k: (inp.get("regime") or {}).get(k) for k in
                       ("quad", "quad_name", "liquidity_overlay", "cycle_tag")},
            "confirmed_themes": themes,
            "backdrop_stance": verdict.get("backdrop_stance"),
            "supportive": verdict.get("supportive"),
            "watch_emerging": (verdict.get("watch_emerging") or [])[:12],
            "crowding_flags": (verdict.get("crowding_flags") or [])[:12],
            "rationale": (verdict.get("rationale") or "")[:1600],
            "calibration_multiplier": verdict.get("calibration_multiplier"),
        })
    except Exception as exc:  # noqa: BLE001 — never raise; degrade to building
        return JSONResponse({"status": "building", "asof": None, "error": str(exc)})


@router.get("/api/desk/decisions")
def api_desk_decisions(asof: str = "") -> JSONResponse:
    """The per-name desk decision log for `asof` (default: most-recent) — one readable row per name:
    what FORGE confirmed, SENTINEL's stance, NEXUS's action, the Gate Officer's action, and the
    realized risk action, each joined from the committee + gate + risk artifacts. 'building' when no
    committee dir exists for the date."""
    try:
        asof = (asof or "")[:10]
        if not (asof and _is_date_dir(asof)):
            asof = _latest_asof(_committee_dir(), _gate_officer_dir(), _risk_officer_dir())
        if not asof:
            return JSONResponse({"status": "building", "asof": None, "decisions": []})

        # Gate + Risk per-name decisions (keyed by ticker) for the date
        def _by_ticker(root: Path) -> dict[str, dict]:
            j = _read_json(root / asof / "decisions.json")
            out: dict[str, dict] = {}
            for dec in ((j.get("result") or {}).get("decisions") or []):
                tk = str(dec.get("ticker") or "").upper().strip()
                if tk:
                    out[tk] = {"action": str(dec.get("action") or "").lower(),
                               "scale": dec.get("scale"),
                               "reason": (dec.get("reason") or "")[:400]}
            return out

        gate = _by_ticker(_gate_officer_dir())
        risk = _by_ticker(_risk_officer_dir())

        cdir = _committee_dir() / asof
        rows: list[dict[str, Any]] = []
        tickers: list[str] = []
        try:
            if cdir.exists():
                tickers = sorted(p.name for p in cdir.iterdir()
                                 if p.is_dir() and p.name != "_FLAGSHIP")
        except Exception:  # noqa: BLE001
            tickers = []
        # also surface gate/risk-only names (e.g. a withheld name with no committee folder)
        for tk in sorted(set(gate) | set(risk)):
            if tk not in tickers:
                tickers.append(tk)

        for tk in tickers[:120]:
            forge = _read_json(cdir / tk / "forge.json")
            sentinel = _read_json(cdir / tk / "sentinel.json")
            nexus = _read_json(cdir / tk / "nexus.json")
            g = gate.get(tk) or {}
            r = risk.get(tk) or {}
            rows.append({
                "ticker": tk,
                "forge": ({"confirmed": forge.get("confirmed"),
                           "combined": forge.get("combined"),
                           "viability": forge.get("viability"),
                           "size_mult": forge.get("size_mult")} if forge else None),
                "sentinel": ({"stance": sentinel.get("stance"),
                              "confidence": sentinel.get("confidence"),
                              "strongest_bear": (sentinel.get("strongest_bear") or "")[:400]}
                             if sentinel else None),
                "nexus": ({"action": nexus.get("action"), "scale": nexus.get("scale"),
                           "lean": nexus.get("lean"),
                           "rationale": (nexus.get("rationale") or "")[:400]} if nexus else None),
                "gate": (g or None),
                "risk": (r or None),
            })
        return JSONResponse({"status": "scoring" if rows else "building",
                             "asof": asof, "decisions": rows})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"status": "building", "asof": None, "decisions": [], "error": str(exc)})


@router.get("/api/desk/watchlist")
def api_desk_watchlist(book: str = "flagship") -> JSONResponse:
    """The parked (withheld) names for a book — the daily re-review queue. Dedups to the latest
    record per ticker, each with its reason + asof. [] when the watchlist is empty/absent. The
    module is flagship-scoped today; `book` is accepted for forward-compatibility."""
    try:
        from portfolio import watchlist
        # the re-review state machine (state + days-in-state) is the source of truth when present;
        # fall back to the append-log latest() for any parked name not yet in the snapshot so the
        # surface is never thinner than before (back-compatible).
        state_by_ticker = {}
        try:
            for s in (watchlist.state_rows() or []):
                t = (s.get("ticker") or "").upper()
                if t:
                    state_by_ticker[t] = s
        except Exception:  # noqa: BLE001
            state_by_ticker = {}
        rows = []
        for r in (watchlist.latest() or []):
            t = (r.get("ticker") or "").upper()
            s = state_by_ticker.get(t) or {}
            rows.append({"ticker": t,
                         "asof": str(r.get("asof") or "")[:10],
                         "reason": (s.get("reason") or r.get("reason") or "")[:400],
                         "combined": r.get("combined"),
                         "state": s.get("state") or "watch",
                         "days_in_state": s.get("days_in_state"),
                         "last_review": str(s.get("last_review") or "")[:10] or None})
        # surface EXPIRED names from the snapshot too (they've left the append-log's active view).
        for t, s in state_by_ticker.items():
            if s.get("state") == "expired" and not any(x["ticker"] == t for x in rows):
                rows.append({"ticker": t,
                             "asof": str(s.get("asof") or "")[:10],
                             "reason": (s.get("expire_reason") or s.get("reason") or "")[:400],
                             "combined": s.get("combined"),
                             "state": "expired",
                             "days_in_state": s.get("days_in_state"),
                             "last_review": str(s.get("last_review") or "")[:10] or None})
        return JSONResponse({"book": book, "watchlist": rows[:120]})
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"book": book, "watchlist": [], "error": str(exc)})


@router.get("/api/desk/scorecard")
def api_desk_scorecard() -> JSONResponse:
    """The per-seat accountability scorecard: each seat's calibration (multiplier / reliability /
    n / status), its cumulative attributed bps (the Brinson credit rollup), and its reputation
    label — plus the latest CIO weekly note. Every input degrades independently to empty/None, so
    the payload is always valid even before any seat has cleared cold-start."""
    out: dict[str, Any] = {"seats": [], "cio": None, "status": "building"}
    # --- per-agent calibration (the spine of the table) ---
    agents: dict[str, Any] = {}
    try:
        from brain import calibration
        agents = (calibration.load() or {}).get("agents") or {}
    except Exception:  # noqa: BLE001
        agents = {}
    # --- cumulative attributed bps per seat (Brinson rollup) ---
    attr_seats: dict[str, Any] = {}
    try:
        from brain import attribution
        attr_seats = (attribution.rollup() or {}).get("seats") or {}
    except Exception:  # noqa: BLE001
        attr_seats = {}
    # --- CIO weekly review: structured per-seat reputation + the note (md + week) ---
    # Prefer the PERSISTED weekly artifact (data/brain/cio/<week>.json, written by cio.write() on the
    # daily/weekly build) — it's a single bounded file read, so the live endpoint stays snappy. Fall
    # back to a fresh, LLM-free cio.review() only when nothing has been persisted yet (which does the
    # heavier KPI scan). Either way the per-seat reputation labels + the note (md + week) are surfaced.
    rep_by_seat: dict[str, str] = {}
    cio_block: dict[str, Any] | None = None
    try:
        rep = None
        cio_dir = _data() / "brain" / "cio"
        try:
            files = sorted(cio_dir.glob("*.json"), reverse=True) if cio_dir.exists() else []
            if files:
                rep = json.loads(files[0].read_text())
        except Exception:  # noqa: BLE001
            rep = None
        if not rep:
            from brain import cio
            rep = cio.review()  # LLM-free; deterministic fallback note
        for s in (rep.get("per_seat") or []):
            if s.get("seat"):
                rep_by_seat[s["seat"]] = s.get("reputation")
        cio_block = {"week": rep.get("iso_week"),
                     "note_md": (rep.get("note_md") or "")[:8000],
                     "whats_working": rep.get("whats_working") or [],
                     "whats_broken": rep.get("whats_broken") or [],
                     "tuning_recommendations": (rep.get("tuning_recommendations") or [])[:12]}
    except Exception:  # noqa: BLE001
        cio_block = None

    # the seats we surface, in desk reading order (calibration keys); only emit those that exist
    # in at least one source so the table stays honest, but always include the core six.
    _order = ["strategist", "forge", "sentinel", "nexus", "gate", "risk",
              "pm", "timing", "autonomous", "heavyweight", "china", "hk"]
    seats: list[dict[str, Any]] = []
    try:
        keys = [k for k in _order if k in agents or k in attr_seats or k in rep_by_seat]
        # append any unexpected calibration agents not in our order list (forward-compatible)
        for k in agents:
            if k not in keys:
                keys.append(k)
        for k in keys:
            cal = agents.get(k) or {}
            ab = attr_seats.get(k) or {}
            seats.append({
                "seat": k,
                "status": cal.get("status"),
                "multiplier": cal.get("multiplier"),
                "reliability": cal.get("reliability"),
                "n": cal.get("n"),
                "attributed_bps": ab.get("attributed_bps"),
                "attributed_n": ab.get("n"),
                "reputation": rep_by_seat.get(k),
            })
    except Exception:  # noqa: BLE001
        seats = []
    out["seats"] = seats
    out["cio"] = cio_block
    out["status"] = "scoring" if seats else "building"
    # --- nightly per-book Opus-cost spend vs the tripwire cap (OFF/unlimited by default) ---
    try:
        from brain import cost_guard
        out["cost"] = cost_guard.summary()
    except Exception:  # noqa: BLE001 — additive; never break the scorecard
        out["cost"] = None
    return JSONResponse(out)


@router.get("/api/desk/macro-risk")
def api_desk_macro_risk(asof: str = "") -> JSONResponse:
    """The MACRO RISK OFFICER read for `asof` (default: most-recent, else computed LIVE). The top-down
    DEFENSE state the desk lacked on 2026-06-23: the deterministic RISK STATE (risk_on/caution/risk_off)
    + per-axis fragility (vol / credit-USD / liquidity / crowding / dealer-gamma), the leading-edge
    fragile DRIVER chains, the hard gross cap + add-block (the teeth), the driver-aware defensive tilt,
    and the falsifier. Reads the persisted artifact; falls back to a fresh deterministic compute (no
    LLM) so the card is never blank. Never 500s."""
    def _shape(st: dict) -> dict:
        st = st or {}
        return {
            "asof": st.get("asof"),
            "state": st.get("state"),
            "fragility": st.get("fragility"),
            "gross_cap": st.get("gross_cap"),
            "allow_adds": st.get("allow_adds"),
            "axes": st.get("axes") or {},
            "signals": (st.get("signals") or [])[:10],
            "drivers": (st.get("drivers") or [])[:8],
            "hot_tickers": (st.get("hot_tickers") or [])[:12],
            "defensive_tilt": st.get("defensive_tilt") or {},
            "falsifier": (st.get("falsifier") or "")[:600],
            "check_by": st.get("check_by"),
            "rationale": (st.get("rationale") or "")[:1600],
            "lead_driver": (st.get("lead_driver") or "")[:300],
        }
    try:
        asof = (asof or "")[:10]
        if not (asof and _is_date_dir(asof)):
            asof = _latest_asof(_macro_risk_dir())
        if asof:
            j = _read_json(_macro_risk_dir() / asof / "state.json")
            st = j.get("state") or {}
            if st:
                return JSONResponse({"status": "scoring", **_shape(st)})
        # nothing persisted yet — compute the deterministic state LIVE (no LLM) so the card renders
        from brain import macro_risk
        reg = _read_json(Path(_data().parent / "vendor" / "macro" / "data" / "regime" / "latest.json")) \
            if (_data().parent / "vendor" / "macro" / "data" / "regime" / "latest.json").exists() else {}
        st = macro_risk.risk_state(reg.get("date") or "", reg or None)
        return JSONResponse({"status": "scoring" if st.get("state") else "building", **_shape(st)})
    except Exception as exc:  # noqa: BLE001 — never raise; degrade to building
        return JSONResponse({"status": "building", "state": None, "error": str(exc)})


@router.get("/api/desk/firm-exposure")
def api_desk_firm_exposure() -> JSONResponse:
    """READ-ONLY firm-level cross-book exposure monitor — where the independent books (flagship,
    heavyweight, US/CN/HK/ETF Brains) have piled into the SAME names / sectors. Surfaces the flagged
    concentrations + the top firm-wide exposures + a sector rollup. A MONITOR only: it never changes
    any allocation or trades. Degrades to an honest empty payload; never 500s."""
    try:
        from portfolio import firm_exposure
        return JSONResponse(firm_exposure.summary())
    except Exception as exc:  # noqa: BLE001 — never raise; degrade to an honest stub
        return JSONResponse({"as_of": None, "books": [], "n_books": 0, "top_exposures": [],
                             "flags": [], "by_sector": {}, "by_chain": {}, "thresholds": {},
                             "currency_clean": False, "note": f"Firm exposure unavailable: {exc}"})


@router.get("/api/firm_allocator")
def api_firm_allocator(rebuild: bool = False) -> JSONResponse:
    """Shadow Firm Allocator — MW5 Lane A (docket M3).

    DISPLAY-ONLY.  Returns the latest persisted allocator artifact, or computes a
    fresh one if rebuild=true or no artifact exists yet.  Auth-gated via the standard
    session cookie / bearer token (app.auth middleware applies to all /api/* routes).

    The allocator is ADVISORY ONLY and has NO effect on any book's sizing.  See
    portfolio/firm_allocator.py for the pre-committed formula.

    Integration point for the weekly CIO path (lane B owns the scheduler wire):
        from portfolio.firm_allocator import build_latest
        artifact = build_latest()
    """
    try:
        from portfolio import firm_allocator as _fa
        if rebuild:
            artifact = _fa.build_latest()
        else:
            artifact = _fa.latest_artifact()
            if artifact is None:
                artifact = _fa.build_latest()
        return JSONResponse(artifact or {"advisory_only": True, "computed": False,
                                         "reason": "no artifact available"})
    except Exception as exc:  # noqa: BLE001 — never 500
        return JSONResponse({"advisory_only": True, "computed": False,
                             "reason": f"firm_allocator endpoint error: {exc}"})


@router.get("/api/desk/experiments")
def api_desk_experiments() -> JSONResponse:
    """Experiment registry — W-L / L6 + MW2 Lane B tri-state maturity.

    Every accruing experiment tracked with its come-back date, gate language, current status, owner,
    and artifact paths.  Surfaces matured-but-unjudged experiments at the top (these are the
    highest-priority agenda items).  The improvement agenda consumes this endpoint; so does the
    dashboard's accountability page.

    MW2 addition: each open experiment now carries an ``evaluation`` sub-dict with fields:
      state               — not_old_enough | blocked_missing_evidence | ready_for_review
      reason              — human-readable explanation
      evidence_n          — current count when computable (null otherwise)
      required_n          — threshold when computable (null otherwise)
      expected_ready_date — ISO date estimate when computable (null otherwise)
      stuck               — true if blocked >14 days with no comeback_date

    open_tristate is sorted: ready_for_review → stuck → blocked → not_old_enough.

    Returns {as_of, total, open, matured, judged, cancelled, matured_items: [...],
             open_tristate: [...], all_items: [...]}.
    Never 500s — degrades to an empty registry on any failure."""
    try:
        from brain import experiment_registry
        s = experiment_registry.summary()
        all_items = experiment_registry.load()
        s["all_items"] = all_items
        return JSONResponse(s)
    except Exception as exc:  # noqa: BLE001 — additive; never break the desk
        return JSONResponse({"as_of": None, "total": 0, "open": 0, "matured": 0,
                             "judged": 0, "cancelled": 0, "matured_items": [], "all_items": [],
                             "open_tristate": [],
                             "note": f"Experiment registry unavailable: {exc}"})


@router.get("/api/scheduler")
def api_scheduler() -> JSONResponse:
    """Operator-only scheduler health.

    Returns per-job records: id, next_run_time, last_started, last_finished, last_skipped,
    last_status, last_severity.  Reads the run_events JSONL tail and the live APScheduler
    instance.  Auth-gated via the same app-level middleware as all other /api/* routes.
    Never 500s — degrades to an empty list on any failure.
    """
    try:
        from app.scheduler import scheduler_health
        return JSONResponse({"jobs": scheduler_health()})
    except Exception as exc:  # noqa: BLE001 — operator endpoint; must never raise
        return JSONResponse({"jobs": [], "note": f"Scheduler health unavailable: {exc}"})


@router.get("/api/provenance")
def api_provenance() -> JSONResponse:
    """MW6 provenance banner — git short-SHA, data-snapshot date, and PAPER TRADING label.

    Served by every page's topbar so the operator always knows which version and
    data snapshot they are viewing.  Read-only; best-effort; never 500s.
    """
    import subprocess
    import shlex as _shlex

    # git short SHA — resolved at request time (cheaper than startup import; cached by OS)
    sha: str | None = None
    try:
        sha = subprocess.check_output(
            _shlex.split("git rev-parse --short HEAD"),
            stderr=subprocess.DEVNULL, text=True,
            cwd=_PROJECT_ROOT,
        ).strip() or None
    except Exception:
        sha = None

    # data snapshot date — cheapest readable proxy: regime/latest.json's date field
    snapshot_date: str | None = None
    try:
        import json as _json
        reg_path = _macro_data() / "regime" / "latest.json"
        if reg_path.exists():
            reg = _json.loads(reg_path.read_text())
            snapshot_date = str(reg.get("date") or "")[:10] or None
    except Exception:
        snapshot_date = None

    return JSONResponse({
        "sha": sha,
        "snapshot_date": snapshot_date,
        "paper_trading": True,
        "label": "PAPER TRADING",
    })


@router.get("/portfolio_desk", include_in_schema=False)
def portfolio_desk_page() -> FileResponse:
    """The Portfolio Risk Desk — operator's held-position ledger with live quotes and
    evidence-lane risk context (W1 base; risk grid added by W2). Standalone static page;
    session-auth-gated by the same middleware as the rest of the app."""
    return FileResponse(_STATIC / "portfolio.html", media_type="text/html", headers=_PAGE_CACHE)
