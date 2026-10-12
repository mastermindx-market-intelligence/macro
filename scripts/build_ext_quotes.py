"""Bounded BOATS archive-to-display publisher through the incumbent R2 key.

The public publication boundary accepts only flow.ext_quotes/v2 from
Tiingo BOATS, with an exact envelope/row allowlist. It rejects legacy or mixed
providers before constructing a storage client. The retained Yahoo builder is
an unpublished local diagnostic; --publish requires --boats.

BOATS prints qualify by documented trade-condition slots and exact event,
arrival and publication clocks. Quotes never substitute for trades. Breaks,
gaps, disconnects and final shutdown publish an empty full replacement.
A quote expires at the earlier event/publication 30-second deadline; the display
is the latest qualifying BOATS trade, single ATS, never NBBO or a canonical candle.

Use python -m scripts.build_ext_quotes --boats [--publish] for one bounded
capture (default 600 seconds / 20,000 messages). Reconnects start fresh state.
Raw frames must be successfully archived before display reduction/publication.
No persistent runner or schedule is installed by this source module.
R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY and R2_BUCKET are used only
by the existing storage client when explicitly publishing the approved object.
All output remains display-tier and carries no signal or execution authority.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import re
import uuid
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, date, time as dtime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ── repo path ─────────────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from lib.nyse_calendar import is_session, ET

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ext_quotes] %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schema / R2 constants
# ---------------------------------------------------------------------------

SCHEMA = "flow.ext_quotes/v1"
R2_KEY = "live_flow/ext_quotes.json"
SOURCE_LABEL = "yahoo-chart (grey)"

# Yahoo v8 chart endpoint (grey / undocumented — same as lib/yahoo.py).
# query1 is more permissive than query2 on residential IPs.
_YAHOO_CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
    "?interval=1m&range=1d&includePrePost=true"
)
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
_ACCEPT = "application/json"
_ACCEPT_LANG = "en-US,en;q=0.9"

# Pacing: 0.8 req/s → 1.25 s between requests.
_PACE_S = 1.25
# HTTP timeout per request.
_TIMEOUT_S = 10

# ---------------------------------------------------------------------------
# Symbol universe
# ---------------------------------------------------------------------------
# Static curated ~100 US liquid names covering:
#   - Macro Dashboard DEFAULT watchlist symbols (SPY, QQQ, BTC-USD excluded —
#     BTC has no Yahoo ext-hours bar; index ETFs covered via separate entries)
#   - Top ~100 US names by market-cap / flow-desk importance
#   - Core sector ETFs used throughout the engine
# Update this list in-place as the universe evolves.

DEFAULT_SYMBOLS: list[str] = [
    # Index ETFs + sector ETFs
    "SPY", "QQQ", "IWM", "DIA", "RSP",
    "XLK", "XLF", "XLV", "XLE", "XLY", "XLP", "XLI", "XLB", "XLU", "XLRE", "XLC",
    "SMH", "SOXX", "XBI", "KRE", "GLD", "SLV", "TLT", "HYG", "LQD",
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "AVGO",
    # Large-cap tech
    "AMD", "INTC", "QCOM", "ORCL", "CRM", "ADBE", "AMAT", "LRCX", "KLAC",
    "NOW", "SNOW", "PANW", "CRWD", "NET",
    # Financials
    "JPM", "BAC", "GS", "MS", "WFC", "C", "BLK", "SCHW", "AXP", "V", "MA",
    # Healthcare
    "JNJ", "UNH", "LLY", "PFE", "MRK", "ABBV", "BMY", "AMGN", "GILD",
    # Consumer
    "AMZN", "COST", "WMT", "HD", "TGT", "NKE", "MCD", "SBUX", "DIS", "NFLX",
    # Energy
    "XOM", "CVX", "COP", "EOG", "SLB",
    # Industrials / Materials
    "CAT", "DE", "HON", "BA", "GE", "RTX", "LMT", "NOC",
    # Communication
    "T", "VZ", "TMUS",
    # Other high-volume names
    "BABA", "TSM", "ASML", "ARM", "MRVL", "MU", "WDC",
    "PLTR", "RBLX", "RIVN", "LCID", "COIN",
    "BRK-B", "UBER", "LYFT", "ABNB", "SHOP",
    "ZM", "DOCU", "TWLO", "OKTA", "DDOG",
]
# De-duplicate while preserving order (e.g. AMZN appears twice in draft above).
DEFAULT_SYMBOLS = list(dict.fromkeys(DEFAULT_SYMBOLS))

# ---------------------------------------------------------------------------
# Window classification
# ---------------------------------------------------------------------------

# Extended hours windows (half-open intervals in ET).
_EXT_PRE_OPEN  = dtime(4, 0, 0)
_EXT_PRE_CLOSE = dtime(9, 30, 0)
_EXT_POST_OPEN = dtime(16, 0, 0)
_EXT_POST_CLOSE = dtime(20, 0, 0)


def is_ext_window_now(now_et: Optional[datetime] = None) -> bool:
    """Return True if current ET time is in the pre-market or post-market window."""
    if now_et is None:
        now_et = datetime.now(tz=ET)
    if not is_session(now_et.date()):
        return False
    t = now_et.time()
    return (_EXT_PRE_OPEN <= t < _EXT_PRE_CLOSE) or (_EXT_POST_OPEN <= t < _EXT_POST_CLOSE)


def classify_ext_session(now_et: Optional[datetime] = None) -> str:
    """Return 'pre', 'post', or 'none' based on current ET time."""
    if now_et is None:
        now_et = datetime.now(tz=ET)
    t = now_et.time()
    if _EXT_PRE_OPEN <= t < _EXT_PRE_CLOSE:
        return "pre"
    if _EXT_POST_OPEN <= t < _EXT_POST_CLOSE:
        return "post"
    return "none"


# ---------------------------------------------------------------------------
# Yahoo chart fetch
# ---------------------------------------------------------------------------

def _fetch_yahoo_chart(sym: str) -> Optional[dict]:
    """
    Fetch Yahoo v8/finance/chart for sym.
    Returns the raw JSON dict, or None on error / 429.
    Grey source — ToS-grey risk noted in module docstring.
    """
    url = _YAHOO_CHART_URL.format(sym=sym)
    req = urllib.request.Request(url, headers={
        "User-Agent": _UA,
        "Accept": _ACCEPT,
        "Accept-Language": _ACCEPT_LANG,
    })
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            log.warning("yahoo 429 for %s — rate-limited, skipping", sym)
        else:
            log.debug("yahoo HTTP %d for %s", exc.code, sym)
        return None
    except Exception as exc:  # noqa: BLE001
        log.debug("yahoo fetch error for %s: %s", sym, exc)
        return None


def extract_ext_print(
    sym: str,
    chart_json: dict,
    session: str,
) -> Optional[dict[str, object]]:
    """
    Extract the latest extended-hours print from a Yahoo chart response.

    Returns {"extPrice": float, "extTs": int, "close": float} or None.
    Only emits when the ext print timestamp is NEWER than the regular-session
    close timestamp (i.e. a real ext print exists, not just the close bar).

    session: 'pre' | 'post'
    """
    try:
        result = (chart_json.get("chart") or {}).get("result") or []
        if not result:
            return None
        r = result[0]
        meta = r.get("meta") or {}
        timestamps = r.get("timestamp") or []
        quote_block = (r.get("indicators") or {}).get("quote") or [{}]
        closes = (quote_block[0] if quote_block else {}).get("close") or []

        if not timestamps:
            return None

        # Determine session boundaries.
        ctp = meta.get("currentTradingPeriod") or {}
        if session == "pre":
            sess_info = ctp.get("pre") or {}
        else:
            sess_info = ctp.get("post") or {}

        sess_start = sess_info.get("start")
        sess_end = sess_info.get("end")

        if not sess_start or not sess_end:
            return None

        # Regular session close timestamp (used to confirm ext print is newer).
        rth_info = ctp.get("regular") or {}
        rth_end_ts = rth_info.get("end")  # Unix seconds

        # Official regular-session close price from meta (most reliable).
        official_close = meta.get("regularMarketPrice") or meta.get("chartPreviousClose")
        if official_close is None:
            return None
        try:
            official_close = float(official_close)
        except (TypeError, ValueError):
            return None

        # Find last bar in the ext session window with a non-null close.
        last_ts: Optional[int] = None
        last_price: Optional[float] = None
        for i in range(len(timestamps) - 1, -1, -1):
            ts = timestamps[i]
            c = closes[i] if i < len(closes) else None
            if ts is None or c is None:
                continue
            try:
                ts = int(ts)
                c = float(c)
            except (TypeError, ValueError):
                continue
            if not (sess_start <= ts < sess_end):
                continue
            if not (c > 0):
                continue
            last_ts = ts
            last_price = c
            break

        if last_ts is None or last_price is None:
            return None

        # Guard: ext print must be newer than regular-session close.
        # This ensures we emit only real ext prints, not the closing bar.
        if rth_end_ts is not None:
            try:
                rth_end_ts = int(rth_end_ts)
                if last_ts <= rth_end_ts:
                    return None
            except (TypeError, ValueError):
                pass

        return {
            "extPrice": round(last_price, 4),
            "extTs": last_ts,
            "close": round(official_close, 4),
        }
    except Exception as exc:  # noqa: BLE001
        log.debug("extract_ext_print error for %s: %s", sym, exc)
        return None


# ---------------------------------------------------------------------------
# R2 client
# ---------------------------------------------------------------------------

def _r2_client():
    """Build a boto3 S3 client for R2, or None if creds are absent."""
    ep = os.environ.get("R2_ENDPOINT")
    ak = os.environ.get("R2_ACCESS_KEY_ID")
    sk = os.environ.get("R2_SECRET_ACCESS_KEY")
    if not (ep and ak and sk):
        return None
    try:
        import boto3
        from botocore.config import Config
        kw = dict(
            region_name="auto",
            signature_version="s3v4",
            max_pool_connections=4,
            retries={"max_attempts": 3, "mode": "standard"},
        )
        try:
            cfg = Config(
                **kw,
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
            )
        except TypeError:
            cfg = Config(**kw)
        return boto3.client(
            "s3",
            endpoint_url=ep,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            config=cfg,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("ext_quotes: R2 client build failed: %s", exc)
        return None


def _publish_r2(payload_json: str) -> bool:
    """Publish only the approved BOATS allowlist to the existing relay key."""
    try:
        payload_json = json.dumps(public_boats_payload(json.loads(payload_json)),
                                  separators=(",", ":"), allow_nan=False)
    except (ValueError, TypeError, KeyError, OverflowError):
        log.warning("ext_quotes: payload refused by BOATS public allowlist")
        return False
    s3 = _r2_client()
    if s3 is None:
        log.warning("ext_quotes: R2 client unavailable — skipping publish")
        return False
    bucket = os.environ.get("R2_BUCKET", "mastermindx")
    try:
        s3.put_object(
            Bucket=bucket,
            Key=R2_KEY,
            Body=payload_json.encode("utf-8"),
            ContentType="application/json",
            CacheControl="no-store, max-age=0",
        )
        log.info("ext_quotes: published → R2 %s/%s", bucket, R2_KEY)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("ext_quotes: R2 publish failed: %s", exc)
        return False


# BOATS display projection shares the existing relay object and stream owner.
# This is a last-trade display, never an NBBO, close, or executable quote.
BOATS_MAX_AGE_S = 30
BOATS_PUBLISH_S = 5


def boats_session_date(now: datetime) -> str | None:
    """Conservative overnight session tied to the following US cash session."""
    local = now.astimezone(ET)
    if local.hour >= 20:
        day = local.date() + timedelta(days=1)
    elif local.hour < 4:
        day = local.date()
    else:
        return None
    return day.isoformat() if is_session(day) else None


def _utc_stamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return stamp.astimezone(timezone.utc)


def public_boats_payload(payload: dict, now: datetime | None = None) -> dict:
    """Construct the complete public object; reject legacy/mixed/raw fields.

    Chairman-attested BOATS redistribution does not clear other upstreams.
    The legacy Yahoo builder remains a private diagnostic. This gate runs before
    credentials/client construction and is independent of any CLI caller.
    """
    now = now or datetime.now(timezone.utc)
    top = ("schema", "snapshot_mode", "asof_utc", "expires_at_utc", "session_date",
           "source", "capture_id", "connection_generation", "stream_status",
           "max_event_age_seconds", "coverage_symbols", "quotes")
    row_keys = ("extPrice", "extTs", "extSession", "extSource", "extVenue",
                "extPriceKind", "extBasis", "extReceivedAt", "extEventAt",
                "venue_scope", "nbbo")
    if not isinstance(payload, dict) or set(payload) != set(top):
        raise ValueError("unknown public envelope fields")
    if (payload["schema"] != "flow.ext_quotes/v2" or payload["source"] != "tiingo_boats"
            or payload["snapshot_mode"] != "full_replace"
            or type(payload["max_event_age_seconds"]) is not int
            or payload["max_event_age_seconds"] != BOATS_MAX_AGE_S):
        raise ValueError("unapproved public source or contract")
    if not isinstance(payload["capture_id"], str) or str(uuid.UUID(payload["capture_id"])) != payload["capture_id"]:
        raise ValueError("invalid capture identity")
    generation = payload["connection_generation"]
    status = payload["stream_status"]
    if (type(generation) is not int or generation < 0 or status not in
            {"connected", "gap", "error", "disconnected", "ended"}
            or (status == "connected" and generation < 1)):
        raise ValueError("invalid stream state")
    published, expires = _utc_stamp(payload["asof_utc"]), _utc_stamp(payload["expires_at_utc"])
    if (published > now or now >= expires or expires - published != timedelta(seconds=BOATS_MAX_AGE_S)
            or payload["session_date"] != boats_session_date(published)):
        raise ValueError("invalid publication clock or session")
    symbols = payload["coverage_symbols"]
    if (not isinstance(symbols, list) or not 1 <= len(symbols) <= 500
            or any(not isinstance(s, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.:-]{0,31}", s) for s in symbols)
            or len(set(symbols)) != len(symbols)):
        raise ValueError("invalid coverage identity")
    rows = payload["quotes"]
    if not isinstance(rows, dict) or (status != "connected" and rows):
        raise ValueError("inactive stream cannot publish trades")
    approved = {}
    for symbol, row in rows.items():
        if symbol not in symbols or not isinstance(row, dict) or set(row) != set(row_keys):
            raise ValueError("unapproved row fields or symbol")
        if (row["extSource"] != "tiingo_boats" or row["extVenue"] != "BOATS"
                or row["extPriceKind"] != "LAST_TRADE" or row["extBasis"] != "LIVE"
                or row["extSession"] != "overnight" or row["venue_scope"] != "single_ats"
                or row["nbbo"] is not False):
            raise ValueError("unapproved row provenance")
        if (type(row["extPrice"]) not in {int, float} or not math.isfinite(row["extPrice"])
                or row["extPrice"] <= 0 or type(row["extTs"]) not in {int, float}
                or not math.isfinite(row["extTs"])):
            raise ValueError("invalid price or event clock")
        event, received = _utc_stamp(row["extEventAt"]), _utc_stamp(row["extReceivedAt"])
        if (abs(event.timestamp() - row["extTs"]) > 0.000001
                or not event <= received <= published or now.timestamp() - row["extTs"] > BOATS_MAX_AGE_S
                or row["extTs"] > now.timestamp() or boats_session_date(event) is None
                or boats_session_date(event) != payload["session_date"]):
            raise ValueError("invalid event/arrival/publication clock chain")
        approved[symbol] = {key: row[key] for key in row_keys}
    return {key: (approved if key == "quotes" else payload[key]) for key in top}


class BoatsLastTrade:
    """Reduce successfully archived frames; breaks and gaps invalidate state.

    No trade identifier is available. A break conservatively clears the symbol;
    only a subsequently received trade newer than its watermark restores it.
    Unknown conditions remain in the raw archive but do not qualify for display.
    """

    def __init__(self, symbols: list[str], capture_id: str):
        from collectors.tiingo_archive import symbol_path
        if not symbols or len(symbols) > 500 or len(set(symbols)) != len(symbols):
            raise ValueError("bounded unique symbol coverage required")
        for symbol in symbols:
            symbol_path(symbol)
            if symbol != symbol.upper():
                raise ValueError("exact uppercase vendor symbols required")
        self.symbols = tuple(symbols)
        self.capture_id = capture_id
        self.connection = 0
        self.status = "disconnected"
        self.quotes: dict[str, dict] = {}
        self.watermarks: dict[str, int] = {}

    def reset(self, status: str, connection: int | None = None) -> None:
        self.quotes.clear()
        self.watermarks.clear()
        self.status = status
        if connection is not None:
            self.connection = connection

    def consume(self, raw: str, received_at: str) -> None:
        from collectors.tiingo_archive import decode_boats, TiingoArchiveError
        try:
            message = json.loads(raw)
        except (ValueError, TypeError):
            self.quotes.clear()
            return
        if not isinstance(message, dict) or message.get("service") != "boats":
            return
        data = message.get("data")
        if not isinstance(data, list) or not data:
            return
        if not isinstance(data[0], str):
            self.quotes.clear()
            return
        if data[0] not in {"Q", "T", "B"}:
            return
        # Do not accept the research decoder's string/int coercion as identity proof.
        symbol = data[3] if len(data) > 3 else None
        if not isinstance(symbol, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9.:-]{0,31}", symbol):
            self.quotes.clear()
            return
        if symbol not in self.symbols:
            return
        try:
            event = decode_boats(message, received_at)
            if event is None or type(data[2]) is not int or data[2] <= 0:
                raise ValueError("invalid event clock")
            stamp = _utc_stamp(data[1])
            arrival = _utc_stamp(received_at)
            delta = stamp - datetime(1970, 1, 1, tzinfo=timezone.utc)
            stamp_ns = ((delta.days * 86400 + delta.seconds) * 1_000_000 + delta.microseconds) * 1000
            if not 0 <= data[2] - stamp_ns < 1000:
                raise ValueError("event clocks disagree")
            arrival_delta = arrival - datetime(1970, 1, 1, tzinfo=timezone.utc)
            arrival_ns = ((arrival_delta.days * 86400 + arrival_delta.seconds) * 1_000_000 + arrival_delta.microseconds) * 1000
            if not 0 <= arrival_ns - data[2] <= BOATS_MAX_AGE_S * 1_000_000_000:
                raise ValueError("event clock outside receive-age budget")
            age = (arrival - stamp).total_seconds()
            if not 0 <= age <= BOATS_MAX_AGE_S or boats_session_date(stamp) != boats_session_date(arrival) or boats_session_date(stamp) is None:
                raise ValueError("outside current overnight session or age budget")
        except (ValueError, TypeError, OverflowError, TiingoArchiveError):
            self.quotes.pop(symbol, None)
            return
        if event["kind"] == "Q":
            return  # A quote cannot advance or refresh a last-trade clock.
        epoch_ns = data[2]
        prior = self.watermarks.get(symbol, 0)
        if event["kind"] == "B":
            self.quotes.pop(symbol, None)
            self.watermarks[symbol] = max(prior, epoch_ns)
            return
        if epoch_ns <= prior:
            return
        self.watermarks[symbol] = epoch_ns
        price, size = data[4:6]
        if (type(price) not in {int, float} or not math.isfinite(price) or price <= 0
                or type(size) not in {int, float} or not math.isfinite(size) or size <= 0
                or int(size) != size):
            self.quotes.pop(symbol, None)
            return
        # Tiingo documents @ regular sale, F ISO, T extended hours by position.
        # Excluded conditions do not rejuvenate the prior qualifying trade.
        if any(type(value) is not str or value not in allowed for value, allowed in zip(
                data[6:10], ({"", "@"}, {"", "F"}, {"", "T"}, {""}))):
            return
        self.quotes[symbol] = {
            "extPrice": price, "extTs": epoch_ns / 1_000_000_000,
            "extSession": "overnight", "extSource": "tiingo_boats",
            "extVenue": "BOATS", "extPriceKind": "LAST_TRADE", "extBasis": "LIVE",
            "extReceivedAt": arrival.isoformat(), "extEventAt": stamp.isoformat(),
            "venue_scope": "single_ats", "nbbo": False,
        }

    def snapshot(self, now: datetime) -> dict:
        if now.tzinfo is None:
            raise ValueError("aware publication clock required")
        now = now.astimezone(timezone.utc)
        quotes = {}
        if self.status == "connected" and boats_session_date(now):
            for symbol, entry in self.quotes.items():
                age = now.timestamp() - entry["extTs"]
                if 0 <= age <= BOATS_MAX_AGE_S and boats_session_date(_utc_stamp(entry["extEventAt"])) == boats_session_date(now):
                    quotes[symbol] = dict(entry)
        return {
            "schema": "flow.ext_quotes/v2", "snapshot_mode": "full_replace",
            "asof_utc": now.isoformat(),
            "expires_at_utc": (now + timedelta(seconds=BOATS_MAX_AGE_S)).isoformat(),
            "session_date": boats_session_date(now), "source": "tiingo_boats",
            "capture_id": self.capture_id, "connection_generation": self.connection,
            "stream_status": self.status, "max_event_age_seconds": BOATS_MAX_AGE_S,
            "coverage_symbols": list(self.symbols), "quotes": quotes,
        }


def publish_boats_stream(*, max_seconds: int = 600, max_messages: int = 20000,
                         symbols: list[str] | None = None, publish: bool = False,
                         archive=None) -> dict:
    """One bounded segment of the existing stream in the incumbent publisher.

    Each invocation is bounded. Reconnects never inherit state;
    publication is downstream of successful archive writes and carries expiry.
    """
    from scripts.tiingo_ingest import boats_stream
    reducer = BoatsLastTrade(symbols or DEFAULT_SYMBOLS, str(uuid.uuid4()))
    last_publish = -math.inf
    publication = {"requested": publish, "attempted": 0, "succeeded": 0,
                   "failed": 0, "final_invalidation_delivered": None}

    def emit(force=False):
        nonlocal last_publish
        tick = time.monotonic()
        if force or tick - last_publish >= BOATS_PUBLISH_S:
            payload = reducer.snapshot(datetime.now(timezone.utc))
            if publish:
                publication["attempted"] += 1
                delivered = _publish_r2(json.dumps(payload, separators=(",", ":")))
                publication["succeeded" if delivered else "failed"] += 1
                if reducer.status == "ended":
                    publication["final_invalidation_delivered"] = delivered
                if delivered:
                    last_publish = tick
            else:
                last_publish = tick

    def observe(kind, payload):
        if kind == "connected":
            reducer.reset("connected", payload["connection"])
            emit(True)
        elif kind == "archived":
            if payload["active"] and payload["connection"] == reducer.connection:
                for received_at, raw in payload["frames"]:
                    reducer.consume(raw, received_at)
            emit()
        elif kind == "tick":
            emit()
        else:
            reducer.reset(kind)
            emit(True)

    counts = boats_stream(max_seconds=max_seconds, max_messages=max_messages,
                          batch_messages=1000, flush_seconds=5, archive=archive,
                          observer=observe)
    publication_ok = (publication["failed"] == 0 and publication["final_invalidation_delivered"] is True) if publish else None
    return {"capture_id": reducer.capture_id, **counts,
            "publication": publication, "publication_ok": publication_ok}


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_ext_quotes(
    symbols: Optional[list[str]] = None,
    publish: bool = False,
    smoke: bool = False,
) -> Optional[dict]:
    """
    Poll Yahoo for each symbol and build the ext_quotes payload.

    Returns the payload dict on success, None on global failure.
    Never raises — all errors are logged.

    Args:
        symbols: Override symbol list (default: DEFAULT_SYMBOLS).
        publish: If True, write to R2.
        smoke:   If True, only process first 3 symbols and return without publishing.
    """
    now_et = datetime.now(tz=ET)
    now_utc = datetime.now(tz=timezone.utc)
    session_date = now_et.date().isoformat()

    # Window guard.
    if not smoke and not is_ext_window_now(now_et):
        log.info(
            "ext_quotes: outside ext window (%s ET, session=%s) — exiting cleanly",
            now_et.strftime("%H:%M"),
            classify_ext_session(now_et),
        )
        return None

    session = classify_ext_session(now_et)
    if smoke:
        # In smoke mode we always attempt fetches regardless of window.
        session = session if session != "none" else "post"

    syms = symbols if symbols is not None else DEFAULT_SYMBOLS
    if smoke:
        syms = syms[:3]

    log.info(
        "ext_quotes: starting cycle session=%s syms=%d publish=%s smoke=%s",
        session, len(syms), publish, smoke,
    )

    quotes: dict[str, dict] = {}
    fetched = 0
    emitted = 0
    errors = 0

    for sym in syms:
        raw = _fetch_yahoo_chart(sym)
        fetched += 1
        if raw is None:
            errors += 1
        else:
            entry = extract_ext_print(sym, raw, session)
            if entry is not None:
                quotes[sym] = entry
                emitted += 1
                if smoke:
                    log.info("smoke [%s]: extPrice=%.4f extTs=%d close=%.4f",
                             sym, entry["extPrice"], entry["extTs"], entry["close"])
            else:
                log.debug("ext_quotes: %s — no ext print in %s session", sym, session)

        # Pacing: 0.8 req/s.
        if fetched < len(syms):
            time.sleep(_PACE_S)

    asof_utc = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema": SCHEMA,
        "asof_utc": asof_utc,
        "session_date": session_date,
        "source": SOURCE_LABEL,
        "quotes": quotes,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))

    log.info(
        "ext_quotes: cycle done — fetched=%d emitted=%d errors=%d asof=%s",
        fetched, emitted, errors, asof_utc,
    )

    if smoke:
        print(payload_json)
        return payload

    if publish:
        _publish_r2(payload_json)
    else:
        # Dry-run: write to /tmp for inspection.
        out = Path("/tmp/ext_quotes_debug.json")
        out.write_text(payload_json)
        log.info("ext_quotes: dry-run written to %s", out)
        print(payload_json)

    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Extended-hours quote publisher.")
    parser.add_argument("--publish", action="store_true",
                        help="Publish to R2 (requires R2_* env vars).")
    parser.add_argument("--smoke", action="store_true",
                        help="Fetch first 3 symbols, print, exit (no publish).")
    parser.add_argument("--boats", action="store_true", help="One bounded BOATS archive and display segment.")
    parser.add_argument("--max-seconds", type=int, default=600)
    parser.add_argument("--max-messages", type=int, default=20000)
    parser.add_argument("--session", action="store_true", help="Print the current ET session for the existing runner.")
    args = parser.parse_args()
    if args.publish and not args.boats and not args.smoke:
        parser.error("public relay publication requires --boats; legacy diagnostics are private")
    if args.session:
        now = datetime.now(timezone.utc)
        print("overnight" if boats_session_date(now) else classify_ext_session(now.astimezone(ET)) if is_ext_window_now(now.astimezone(ET)) else "none")
        return
    if args.boats:
        if args.smoke:
            parser.error("--boats and --smoke are incompatible; smoke cannot open or publish a live stream")
        now = datetime.now(timezone.utc)
        if boats_session_date(now) is None:
            log.info("BOATS outside conservative overnight window")
            return
        local = now.astimezone(ET)
        boundary = datetime.combine(local.date() + timedelta(days=1 if local.hour >= 20 else 0), dtime(4), tzinfo=ET)
        seconds = min(args.max_seconds, max(1, int((boundary - local).total_seconds())))
        result = publish_boats_stream(max_seconds=seconds, max_messages=args.max_messages, publish=args.publish)
        log.info("BOATS bounded segment settled %s", json.dumps(result))
        if args.publish and result["publication_ok"] is not True:
            raise SystemExit(1)
        return

    result = build_ext_quotes(publish=args.publish, smoke=args.smoke)
    sys.exit(0 if result is not None or (not args.publish and not args.smoke) else 0)


if __name__ == "__main__":
    main()
