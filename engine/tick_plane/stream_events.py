"""Decode a captured Massive Stocks T/Q WebSocket frame, without opening a socket.

TP-1 owns this source interface; it is not a feed, publisher, clock authority, or
replacement for the Terminal Quote Hub. Raw bytes are private and supplied by an
already authorized incumbent stream owner, with an ORIGINAL receipt timestamp.

Vendor WebSocket SIP/participant/TRF clocks are in MILLISECONDS. Conversion to
Unix ns is exact arithmetic but DOES NOT increase timestamp precision.
WebSocket T does NOT include corrections/cancellations. Every trade is therefore
STREAM_PROVISIONAL until independently reconciled with the original-available
REST/flat-file correction records. No actor intent or rank authority.

Official field references:
https://massive.com/docs/websocket/stocks/trades
https://massive.com/docs/websocket/stocks/quotes
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

SCHEMA = "equity.tick_plane.stream_event/v0"
# Vendor exchange reference names these non-exchange reporting/SIP codes.
# This is a conservative exclusion, NOT an authoritative map of every venue.
# Later source qualification must bind the versioned /v3/reference/exchanges table.
_NON_LIT_EXCHANGE_IDS = frozenset({4, 5, 13, 62})
_KNOWN_TRF_IDS = frozenset({201, 202, 203})


def _coarse_venue_class(exchange, trf_id):
    """Exclude known reporting/SIP routes from lit quote-rule classification."""
    if exchange == 4:
        return "TRF" if trf_id in _KNOWN_TRF_IDS else "UNKNOWN"
    return "UNKNOWN" if exchange in _NON_LIT_EXCHANGE_IDS else "LIT"

MAX_FRAME_BYTES = 2 * 1024 * 1024
MAX_UNIVERSE = 600
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_SESSION = re.compile(r"^(\d{4}-\d{2}-\d{2}):(RTH|PRE|POST)$")
_NS_PER_MS = 1_000_000


class FrameContractError(ValueError):
    """Malformed input, source ambiguity, or invalid frame admission."""


def _integer(value, field, *, minimum=0, optional=False):
    if optional and value is None:
        return None
    if type(value) is not int or value < minimum:
        raise FrameContractError(f"{field} requires an integer >= {minimum}")
    return value


def _decimal(value, field, *, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (Decimal, str, int, float)):
        raise FrameContractError(f"{field} requires a decimal")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise FrameContractError(f"{field} invalid decimal") from exc
    if not number.is_finite() or (number < 0 if allow_zero else number <= 0):
        raise FrameContractError(f"{field} invalid nonpositive price/size")
    return format(number, "f")


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise FrameContractError(f"{field} missing or invalid")
    return value


def _millis(value, field, *, optional=False):
    milliseconds = _integer(value, field, minimum=1, optional=optional)
    return milliseconds * _NS_PER_MS if milliseconds is not None else None


def _condition_codes(raw, *, field="conditions"):
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > 32:
        raise FrameContractError(f"{field} must be a bounded integer array")
    return [_integer(x, field) for x in raw]


def _quote_side(event, price_key, size_key, exchange_key):
    p = event.get(price_key)
    size = event.get(size_key)
    venue = event.get(exchange_key)
    if p is None and size is None:
        if venue is not None:
            raise FrameContractError("quote exchange without its price and size")
        return {"price": None, "size": None, "exchange": None}
    if p is None or size is None:
        raise FrameContractError("one quote side has mismatched price/size")
    return {"price": _decimal(p, price_key, allow_zero=True),
            "size": _integer(size, size_key),
            "exchange": _integer(venue, exchange_key, optional=True)}


def normalize_ws_event(
    raw_frame_bytes: bytes, *, event_index: int,
    frame_received_ns: int, source_receipt_id: str,
    session: str, allowed_symbols,
):
    """Return one immutable-ready event record and its exact raw-frame digest.

    The caller proves that raw bytes, frame receipt time and source subscription
    genuinely came from the canonical singleton. They are not authenticated here.
    The returned receipt is a HASH pointer, not an invitation to publish raw tape.
    No quote/trade ordering, correction resolution or source completeness is
    inferred from a single event's SIP sequence number.
    """
    if type(raw_frame_bytes) is not bytes or not raw_frame_bytes:
        raise FrameContractError("raw frame bytes are required")
    if len(raw_frame_bytes) > MAX_FRAME_BYTES:
        raise FrameContractError("raw frame exceeds the bounded pilot budget")
    _integer(frame_received_ns, "frame_received_ns", minimum=1)
    _text(source_receipt_id, "source_receipt_id")
    m = _SESSION.fullmatch(session) if isinstance(session, str) else None
    if m is None:
        raise FrameContractError("invalid explicit session")
    try:
        date.fromisoformat(m.group(1))
    except ValueError as exc:
        raise FrameContractError("invalid session date") from exc
    if not isinstance(allowed_symbols, (set, frozenset, tuple, list)):
        raise FrameContractError("explicit pilot symbol set is required")
    universe = set(allowed_symbols)
    if not universe or len(universe) > MAX_UNIVERSE or any(
        not isinstance(x, str) or _SYMBOL.fullmatch(x) is None for x in universe
    ):
        raise FrameContractError("invalid or unbounded pilot symbol set")
    try:
        frame = json.loads(raw_frame_bytes.decode("utf-8"),
                           parse_float=Decimal, parse_int=int)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameContractError("invalid original UTF-8 JSON frame") from exc
    if type(frame) is not list or not frame:
        raise FrameContractError("expected a nonempty vendor event array")
    if type(event_index) is not int or event_index < 0 or event_index >= len(frame):
        raise FrameContractError("invalid frame event index")
    event = frame[event_index]
    if not isinstance(event, dict) or event.get("ev") not in ("T", "Q"):
        raise FrameContractError("status/control/unknown event is not T or Q")
    symbol = event.get("sym")
    if symbol not in universe:
        raise FrameContractError("event outside the frozen pilot universe")
    sip_ns = _millis(event.get("t"), "sip timestamp")
    if frame_received_ns < sip_ns:
        raise FrameContractError("ingest receipt precedes vendor SIP time")
    sequence = _integer(event.get("q"), "native sequence")
    participant_ns = _millis(event.get("pt"), "participant timestamp", optional=True)
    digest = hashlib.sha256(raw_frame_bytes).hexdigest()
    common = {
        "schema": SCHEMA, "ticker": symbol, "session": session,
        "source": "MASSIVE_STOCKS_SIP_WS", "event_type": event["ev"],
        "native_sequence": sequence, "sip_timestamp_ns": sip_ns,
        "participant_timestamp_ns": participant_ns,
        "source_timestamp_precision": "MILLISECONDS",
        "original_frame_received_ns": frame_received_ns,
        "source_receipt_id": source_receipt_id,
        "source_frame_sha256": digest, "frame_event_index": event_index,
        "source_status": "RECEIPT_UNQUALIFIED_UNTIL_OWNER_ATTESTS",
        "correction_status": "STREAM_PROVISIONAL_UNRECONCILED",
        "eligible_for_pressure": None, "conditions_rules_ref": None,
        "market_tape": _integer(event.get("z"), "market tape", optional=True),
    }
    if event["ev"] == "Q":
        bid = _quote_side(event, "bp", "bs", "bx")
        ask = _quote_side(event, "ap", "as", "ax")
        condition = _integer(event.get("c"), "quote condition", optional=True)
        indicators = _condition_codes(event.get("i"), field="quote indicators")
        valid = (bid["price"] is not None and ask["price"] is not None
                 and Decimal(bid["price"]) > 0
                 and Decimal(ask["price"]) > Decimal(bid["price"])
                 and bid["size"] > 0 and ask["size"] > 0
                 and bid["exchange"] is not None
                 and ask["exchange"] is not None)
        common.update({
            "quote_id": f"{session}:{symbol}:Q:{sequence}:{sip_ns}",
            "bid": bid["price"], "bid_size": bid["size"],
            "bid_exchange": bid["exchange"],
            "ask": ask["price"], "ask_size": ask["size"],
            "ask_exchange": ask["exchange"],
            "quote_condition": condition, "quote_indicators": indicators,
            "valid_firm_nbbo": bool(valid),
            "invalid_nbbo_is_state_not_absent_event": not valid,
        })
    else:
        trade_id = _text(event.get("i"), "trade ID")
        size = _integer(event.get("s"), "trade size")
        fractional = event.get("ds")
        size_exact = _decimal(fractional, "decimal trade size") if fractional is not None else str(size)
        if fractional is not None and int(Decimal(size_exact)) != size:
            raise FrameContractError("fractional decimal_size disagrees with integer size")
        if Decimal(size_exact) <= 0:
            raise FrameContractError("trade is zero-size without qualified fractional size")
        price = _decimal(event.get("p"), "trade price")
        conditions = _condition_codes(event.get("c"))
        exchange = _integer(event.get("x"), "trade exchange")
        trf_id = _integer(event.get("trfi"), "TRF pipe", optional=True)
        trf_ns = _millis(event.get("trft"), "TRF timestamp", optional=True)
        common.update({
            "trade_id": trade_id,
            "dedup_key": f"{session}:{symbol}:{exchange}:{trf_id if trf_id is not None else '-'}:{trade_id}:{sip_ns}",
            "price": price, "size_integer_shares": size,
            "decimal_size_shares": size_exact, "trade_conditions": conditions,
            "exchange": exchange, "trf_id": trf_id,
            "trf_timestamp_ns": trf_ns,
            "venue_class": _coarse_venue_class(exchange, trf_id),
            "trade_action": "UNRESOLVED_STREAM_ORIGINAL",
        })
    return common
