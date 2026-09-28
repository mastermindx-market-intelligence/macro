"""Pure contract helpers for the live China A-share heatmap overlay.

The daily heatmap remains the canonical membership/history owner. This module
normalizes current-session observations into a display-only contract and
performs no network or disk I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
from datetime import date, datetime, timezone
import math
import re
from typing import Any, Mapping
from zoneinfo import ZoneInfo

import pandas as pd

from engine.prophet_live import cn_clock

SCHEMA = "china_heatmap_live.v1"
MIN_COVERAGE = 0.95
MAX_SOURCE_LAG_SECONDS = 45.0
MAX_FUTURE_SKEW_SECONDS = 5.0
BREADTH_EPSILON = 0.05
CST = ZoneInfo("Asia/Shanghai")
_CANONICAL_TICKER = re.compile(r"^\d{6}\.(?:SS|SZ)$")


class LiveContractError(ValueError):
    """Raised when a baseline or live projection is internally incoherent."""


@dataclass(frozen=True)
class BaselineHeatmap:
    asof: str
    tickers: tuple[str, ...]

    @property
    def ticker_set(self) -> frozenset[str]:
        return frozenset(self.tickers)


def _is_record(value: Any) -> bool:
    return isinstance(value, Mapping)


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def _positive(value: Any) -> float | None:
    out = _finite(value)
    return out if out is not None and out > 0 else None


def _nonnegative(value: Any) -> float | None:
    out = _finite(value)
    return out if out is not None and out >= 0 else None


def _valid_day(value: Any) -> bool:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _canonical_ticker(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    ticker = value.strip().upper()
    if ticker.endswith(".SH"):
        ticker = ticker[:-3] + ".SS"
    return ticker if _CANONICAL_TICKER.fullmatch(ticker) else None


def validate_baseline(payload: Mapping[str, Any]) -> BaselineHeatmap:
    """Validate the daily China heatmap identity and freeze ticker order."""
    if not _is_record(payload):
        raise LiveContractError("baseline identity is not an object")
    if (
        payload.get("market") != "china"
        or payload.get("map_type") != "stocks"
        or payload.get("source") != "daily-close"
    ):
        raise LiveContractError("baseline identity mismatch")
    asof = payload.get("asof")
    if not _valid_day(asof):
        raise LiveContractError("baseline date is invalid")
    tiles = payload.get("tiles")
    n_tiles = payload.get("n_tiles")
    if (
        not isinstance(tiles, list)
        or not tiles
        or isinstance(n_tiles, bool)
        or not isinstance(n_tiles, int)
        or n_tiles != len(tiles)
    ):
        raise LiveContractError("baseline tile count mismatch")

    tickers: list[str] = []
    seen: set[str] = set()
    for tile in tiles:
        if not _is_record(tile):
            raise LiveContractError("baseline tile identity is invalid")
        raw = tile.get("t")
        ticker = _canonical_ticker(raw)
        if ticker is None:
            raise LiveContractError("baseline ticker is not a mainland .SS/.SZ identity")
        if ticker != raw:
            raise LiveContractError("baseline ticker is not canonical")
        if ticker in seen:
            raise LiveContractError("baseline contains duplicate ticker")
        seen.add(ticker)
        tickers.append(ticker)
    return BaselineHeatmap(asof=str(asof), tickers=tuple(tickers))


def parse_market_time(value: Any) -> datetime | None:
    """Parse a provider market clock and return an aware UTC datetime."""
    parsed: datetime | None = None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        raw = _finite(value)
        if raw is None:
            return None
        if abs(raw) > 10_000_000_000:
            raw /= 1000.0
        try:
            parsed = datetime.fromtimestamp(raw, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        iso = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(iso)
        except ValueError:
            parsed = None
        if parsed is None:
            for fmt in ("%Y%m%d%H%M%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    parsed = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=CST)
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        return None


def _make_quote(
    *,
    price: Any,
    prev_close: Any,
    market_time: Any,
    open_price: Any = None,
    high: Any = None,
    low: Any = None,
    volume: Any = None,
    amount: Any = None,
) -> dict[str, Any] | None:
    px = _positive(price)
    prev = _positive(prev_close)
    observed = parse_market_time(market_time)
    if px is None or prev is None or observed is None:
        return None

    op = _positive(open_price)
    hi = _positive(high)
    lo = _positive(low)
    vol = _nonnegative(volume)
    amt = _nonnegative(amount)
    same_close = math.isclose(px, prev, rel_tol=1e-10, abs_tol=1e-8)
    no_market_shape = op is None and hi is None and lo is None
    no_activity = (vol is None or vol <= 0) and (amt is None or amt <= 0)
    if same_close and no_market_shape and no_activity:
        return None

    return {
        "price": px,
        "prevClose": prev,
        "changePct": (px / prev - 1.0) * 100.0,
        "ts": int(observed.timestamp() * 1000),
        "open": op,
        "high": hi,
        "low": lo,
        "vol": int(vol) if vol is not None else None,
        "amount": amt,
    }


def normalize_tushare_rows(
    frame: pd.DataFrame,
    baseline: BaselineHeatmap,
) -> dict[str, dict[str, Any]]:
    """Normalize a Tushare ``rt_k`` frame to the public quote sub-contract."""
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return {}
    allowed = baseline.ticker_set
    out: dict[str, dict[str, Any]] = {}
    for row in frame.to_dict(orient="records"):
        ticker = _canonical_ticker(row.get("ts_code"))
        if ticker is None or ticker not in allowed:
            continue
        if ticker in out:
            raise LiveContractError(f"duplicate normalized ticker: {ticker}")
        quote = _make_quote(
            price=row.get("close"),
            prev_close=row.get("pre_close"),
            market_time=row.get("trade_time"),
            open_price=row.get("open"),
            high=row.get("high"),
            low=row.get("low"),
            volume=row.get("vol"),
            amount=row.get("amount"),
        )
        if quote is not None:
            out[ticker] = quote
    return out


def normalize_tencent_quotes(
    raw: Mapping[str, Mapping[str, Any]],
    baseline: BaselineHeatmap,
) -> dict[str, dict[str, Any]]:
    """Normalize the existing ``engine.live_quotes`` Tencent contract."""
    if not _is_record(raw):
        return {}
    allowed = baseline.ticker_set
    out: dict[str, dict[str, Any]] = {}
    for raw_ticker, row in raw.items():
        ticker = _canonical_ticker(raw_ticker)
        if ticker is None or ticker not in allowed or not _is_record(row):
            continue
        if ticker in out:
            raise LiveContractError(f"duplicate normalized ticker: {ticker}")
        quote = _make_quote(
            price=row.get("price"),
            prev_close=row.get("prev_close"),
            market_time=row.get("quote_ts"),
            open_price=row.get("day_open"),
            high=row.get("day_high"),
            low=row.get("day_low"),
            volume=row.get("day_volume"),
            amount=row.get("day_amount"),
        )
        if quote is not None:
            out[ticker] = quote
    return out


_PHASE_STATUS = {
    "pre_open": "pre_open",
    "morning": "live",
    "session_break": "break",
    "afternoon": "live",
    "closing_auction": "auction",
    "post_close": "closed",
    "closed": "closed",
    "holiday": "holiday",
    "weekend": "weekend",
}
_ALLOWED_SOURCES = {None, "tushare-rt-k", "tencent"}
_PUBLIC_KEYS = frozenset({
    "schema", "market", "map_type", "baseline_asof", "session_date",
    "phase", "status", "source", "generated_at", "source_observed_at",
    "requested", "resolved", "coverage", "usable", "fallback",
    "quotes", "breadth",
})
_QUOTE_KEYS = frozenset({
    "price", "prevClose", "changePct", "ts", "open", "high", "low",
    "vol", "amount",
})


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _normalize_public_quote(value: Mapping[str, Any]) -> dict[str, Any]:
    if not _is_record(value) or set(value) != _QUOTE_KEYS:
        raise LiveContractError("live quote shape mismatch")
    price = _positive(value.get("price"))
    prev = _positive(value.get("prevClose"))
    change = _finite(value.get("changePct"))
    stamp = value.get("ts")
    if price is None or prev is None or change is None:
        raise LiveContractError("live quote price contract invalid")
    if isinstance(stamp, bool) or not isinstance(stamp, int) or stamp <= 0:
        raise LiveContractError("live quote timestamp invalid")
    expected_change = (price / prev - 1.0) * 100.0
    if not math.isclose(change, expected_change, rel_tol=1e-10, abs_tol=1e-10):
        raise LiveContractError("live quote percentage disagrees with price")

    optional_positive: dict[str, float | None] = {}
    for key in ("open", "high", "low"):
        raw = value.get(key)
        parsed = None if raw is None else _positive(raw)
        if raw is not None and parsed is None:
            raise LiveContractError(f"live quote {key} invalid")
        optional_positive[key] = parsed
    optional_nonnegative: dict[str, float | None] = {}
    for key in ("vol", "amount"):
        raw = value.get(key)
        parsed = None if raw is None else _nonnegative(raw)
        if raw is not None and parsed is None:
            raise LiveContractError(f"live quote {key} invalid")
        optional_nonnegative[key] = parsed
    hi, lo = optional_positive["high"], optional_positive["low"]
    if hi is not None and lo is not None and hi < lo:
        raise LiveContractError("live quote range invalid")
    return {
        "price": price,
        "prevClose": prev,
        "changePct": expected_change,
        "ts": stamp,
        "open": optional_positive["open"],
        "high": hi,
        "low": lo,
        "vol": int(optional_nonnegative["vol"]) if optional_nonnegative["vol"] is not None else None,
        "amount": optional_nonnegative["amount"],
    }


def _normalize_quote_map(
    quotes: Mapping[str, Mapping[str, Any]],
    baseline: BaselineHeatmap,
) -> dict[str, dict[str, Any]]:
    if not _is_record(quotes):
        raise LiveContractError("live quotes must be an object")
    allowed = baseline.ticker_set
    staged: dict[str, dict[str, Any]] = {}
    for raw_ticker, row in quotes.items():
        ticker = _canonical_ticker(raw_ticker)
        if ticker is None or ticker != raw_ticker or ticker not in allowed:
            raise LiveContractError("live quote key is outside the baseline universe")
        if ticker in staged:
            raise LiveContractError("live quote key is duplicated")
        staged[ticker] = _normalize_public_quote(row)
    return {ticker: staged[ticker] for ticker in baseline.tickers if ticker in staged}


def _breadth(quotes: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    adv = dec = flat = 0
    for quote in quotes.values():
        change = float(quote["changePct"])
        if change > BREADTH_EPSILON:
            adv += 1
        elif change < -BREADTH_EPSILON:
            dec += 1
        else:
            flat += 1
    n = adv + dec + flat
    return {
        "n": n,
        "adv": adv,
        "dec": dec,
        "flat": flat,
        "pctUp": 100.0 * adv / n if n else 0.0,
    }


def _source_observation(quotes: Mapping[str, Mapping[str, Any]]) -> datetime | None:
    if not quotes:
        return None
    stamp = max(int(quote["ts"]) for quote in quotes.values())
    return datetime.fromtimestamp(stamp / 1000.0, tz=timezone.utc)


def _phase_allows_live(phase: str, now: datetime) -> bool:
    if phase in {"morning", "session_break", "afternoon", "closing_auction", "post_close"}:
        return True
    if phase == "closed":
        return _utc(now).astimezone(CST).time() >= cn_clock.SESSION_CLOSE
    return False


def _source_is_fresh(observed: datetime | None, *, now: datetime) -> bool:
    if observed is None:
        return False
    expected = _utc(cn_clock.expected_latest_quote_time(now))
    lag = (expected - _utc(observed)).total_seconds()
    return -MAX_FUTURE_SKEW_SECONDS <= lag <= MAX_SOURCE_LAG_SECONDS


def _source_contract(source: str | None, fallback: bool, quote_count: int) -> None:
    if source not in _ALLOWED_SOURCES or not isinstance(fallback, bool):
        raise LiveContractError("live source contract invalid")
    if source is None:
        if fallback or quote_count:
            raise LiveContractError("unavailable source cannot carry quotes")
    elif source == "tushare-rt-k" and fallback:
        raise LiveContractError("primary source cannot be labelled fallback")
    elif source == "tencent" and not fallback:
        raise LiveContractError("Tencent source must disclose fallback")


def build_live_payload(
    baseline: BaselineHeatmap,
    quotes: Mapping[str, Mapping[str, Any]],
    *,
    source: str | None,
    fallback: bool,
    phase: str,
    now: datetime,
) -> dict[str, Any]:
    """Build one coherent, display-only live overlay payload."""
    if phase not in _PHASE_STATUS:
        raise LiveContractError("unknown mainland phase")
    now_utc = _utc(now)
    completed = cn_clock.last_completed_session(now_utc)
    if baseline.asof != completed:
        raise LiveContractError("daily heatmap is not the completed-session baseline")
    session = cn_clock.session_date(now_utc).isoformat()
    if baseline.asof > session:
        raise LiveContractError("baseline date is after the live session")

    normalized = _normalize_quote_map(quotes, baseline)
    # A fresh maximum timestamp proves only ONE stock is current. Account only
    # for individually source-current observations, against the same canonical
    # segment clock (fixed at 11:30 during lunch and 15:00 after the close).
    expected_ms = int(_utc(cn_clock.expected_latest_quote_time(now_utc)).timestamp() * 1000)
    normalized = {
        ticker: quote for ticker, quote in normalized.items()
        if -MAX_FUTURE_SKEW_SECONDS * 1000
        <= expected_ms - quote["ts"] <= MAX_SOURCE_LAG_SECONDS * 1000
    }
    _source_contract(source, fallback, len(normalized))
    requested = len(baseline.tickers)
    resolved = len(normalized)
    coverage = resolved / requested if requested else 0.0
    observed = _source_observation(normalized)
    status = "unavailable" if source is None else _PHASE_STATUS[phase]
    usable = bool(
        source is not None
        and coverage >= MIN_COVERAGE
        and _phase_allows_live(phase, now_utc)
        and _source_is_fresh(observed, now=now_utc)
    )
    payload = {
        "schema": SCHEMA,
        "market": "china",
        "map_type": "stocks",
        "baseline_asof": baseline.asof,
        "session_date": session,
        "phase": phase,
        "status": status,
        "source": source,
        "generated_at": now_utc.isoformat(),
        "source_observed_at": observed.isoformat() if observed else None,
        "requested": requested,
        "resolved": resolved,
        "coverage": coverage,
        "usable": usable,
        "fallback": fallback,
        "quotes": normalized,
        "breadth": _breadth(normalized),
    }
    return payload


def _parse_aware_iso(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise LiveContractError(f"{label} is not an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise LiveContractError(f"{label} is not an ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise LiveContractError(f"{label} is not timezone-aware")
    return parsed.astimezone(timezone.utc)


def validate_live_payload(
    payload: Mapping[str, Any],
    baseline: BaselineHeatmap,
    *,
    now: datetime,
) -> dict[str, Any]:
    """Independently recompute identity, accounting, freshness, and usability."""
    if not _is_record(payload) or set(payload) != _PUBLIC_KEYS:
        raise LiveContractError("live payload field allowlist mismatch")
    if payload.get("schema") != SCHEMA or payload.get("market") != "china" or payload.get("map_type") != "stocks":
        raise LiveContractError("live payload identity mismatch")
    generated = _parse_aware_iso(payload.get("generated_at"), "generated_at")
    now_utc = _utc(now)
    if (generated - now_utc).total_seconds() > MAX_FUTURE_SKEW_SECONDS:
        raise LiveContractError("live payload generation is in the future")
    phase = payload.get("phase")
    source = payload.get("source")
    fallback = payload.get("fallback")
    expected = build_live_payload(
        baseline,
        payload.get("quotes"),
        source=source,
        fallback=fallback,
        phase=phase,
        now=now_utc,
    )
    for key in _PUBLIC_KEYS - {"generated_at"}:
        if payload.get(key) != expected.get(key):
            raise LiveContractError(f"live payload {key} disagrees with recomputed contract")
    return copy.deepcopy(dict(payload))
