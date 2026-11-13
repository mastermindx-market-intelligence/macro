"""Private historical Massive stock trade/quote page normalization.

Consume ORIGINAL bytes supplied by incumbent TP-1 REST owner. This module
does not fetch a page, create a data store, infer pagination completeness,
reconstruct a correction chain, or pretend today's archive was historically
available. REST source times are nanoseconds (NOT websocket milliseconds).

Vendor schemas:
https://massive.com/docs/rest/stocks/trades-quotes/trades
https://massive.com/docs/rest/stocks/trades-quotes/quotes
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from engine.tick_plane.stream_events import (
    FrameContractError, _SESSION, _SYMBOL, _integer, _text, _coarse_venue_class,
    _bounded_fixed_decimal,
)

SCHEMA = "equity.tick_plane.historical_rest_page/v0"
MAX_PAGE_BYTES = 16 * 1024 * 1024
MAX_PAGE_ROWS = 50000


def _dec(value, field, zero_ok=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise FrameContractError(field + " invalid decimal")
    try:
        d = Decimal(str(value))
    except InvalidOperation as exc:
        raise FrameContractError(field + " invalid decimal") from exc
    if not d.is_finite() or (d < 0 if zero_ok else d <= 0):
        raise FrameContractError(field + " invalid decimal")
    return _bounded_fixed_decimal(d, field)


def _opt_int(row, field):
    if field not in row or row[field] is None:
        return None
    return _integer(row[field], field)


def _codes(row, field):
    if field not in row or row[field] is None:
        return None
    val = row[field]
    if not isinstance(val, list) or len(val) > 32:
        raise FrameContractError(field + " must be a bounded list")
    return [_integer(x, field) for x in val]


def _quote(row, symbol, stamp):
    seq = _integer(row.get("sequence_number"), "quote sequence")
    bp = _dec(row.get("bid_price", 0), "bid", True)
    ap = _dec(row.get("ask_price", 0), "ask", True)
    bs = _dec(row.get("bid_size", 0), "bid size", True)
    asks = _dec(row.get("ask_size", 0), "ask size", True)
    bx, ax = _opt_int(row, "bid_exchange"), _opt_int(row, "ask_exchange")
    valid = (bp > 0 and ap > bp and bs > 0 and asks > 0
             and bs == int(bs) and asks == int(asks)
             and bx is not None and ax is not None)
    return {
        "native_key": f"{symbol}:Q:{seq}:{stamp}",
        "source_kind": "Q", "sequence_number": seq,
        "bid": format(bp, "f"), "ask": format(ap, "f"),
        "bid_size": format(bs, "f"), "ask_size": format(asks, "f"),
        "bid_exchange": bx, "ask_exchange": ax,
        "conditions": _codes(row, "conditions"),
        "indicators": _codes(row, "indicators"),
        "valid_firm_nbbo_candidate": bool(valid),
        "quote_condition_eligibility": None,
    }


def _trade(row, symbol):
    trade_id = _text(row.get("id"), "trade ID")
    exchange = _integer(row.get("exchange"), "exchange")
    trf = _opt_int(row, "trf_id")
    seq = _integer(row.get("sequence_number"), "trade sequence")
    price = _dec(row.get("price"), "trade price")
    shares = _dec(row.get("decimal_size", row.get("size")), "shares")
    if row.get("size") is not None:
        size = _dec(row["size"], "size", True)
        if size != int(size) or int(size) != int(shares):
            raise FrameContractError("decimal and integer trade size disagree")
    correction = _opt_int(row, "correction")
    return {
        "native_key": f"{symbol}:{exchange}:{trf if trf is not None else '-'}:{trade_id}",
        "source_kind": "T", "trade_id": trade_id,
        "exchange": exchange, "trf_id": trf, "sequence_number": seq,
        "price": format(price, "f"), "decimal_size_shares": format(shares, "f"),
        "conditions": _codes(row, "conditions"),
        "correction_code": correction,
        "correction_status": ("CORRECTION_PRESENT_UNLINKED" if correction not in (None, 0)
                              else "CURRENT_VINTAGE_NOT_HISTORICALLY_FINAL"),
        "venue_class": _coarse_venue_class(exchange, trf),
        "eligible_for_pressure": None,
    }


def normalize_rest_page(*, raw_bytes, endpoint_kind, ticker, session,
                        window_start_ns, window_end_ns, page_received_ns,
                        original_page_receipt):
    """Return one private FINAL_VINTAGE page and explicit incomplete-range state."""
    if endpoint_kind not in ("trades", "quotes"):
        raise FrameContractError("unrecognized REST endpoint kind")
    if not isinstance(ticker, str) or _SYMBOL.fullmatch(ticker) is None:
        raise FrameContractError("invalid symbol")
    m = _SESSION.fullmatch(session) if isinstance(session, str) else None
    if m is None:
        raise FrameContractError("invalid declared session")
    try:
        date.fromisoformat(m.group(1))
    except ValueError as exc:
        raise FrameContractError("invalid session date") from exc
    start = _integer(window_start_ns, "window_start_ns", minimum=1)
    end = _integer(window_end_ns, "window_end_ns", minimum=1)
    received = _integer(page_received_ns, "page_received_ns", minimum=1)
    if start >= end or received < end:
        raise FrameContractError("invalid window or real availability timestamp")
    _text(original_page_receipt, "original_page_receipt")
    if type(raw_bytes) is not bytes or not 0 < len(raw_bytes) <= MAX_PAGE_BYTES:
        raise FrameContractError("missing or oversized raw REST page")
    try:
        body = json.loads(raw_bytes.decode("utf-8"), parse_float=Decimal, parse_int=int)
    except (UnicodeDecodeError, ValueError, InvalidOperation) as exc:
        raise FrameContractError("malformed source REST JSON") from exc
    if (not isinstance(body, dict) or body.get("status") != "OK"
            or not isinstance(body.get("request_id"), str)
            or not body["request_id"].strip()
            or type(body.get("results")) is not list
            or len(body["results"]) > MAX_PAGE_ROWS):
        raise FrameContractError("unqualified response envelope")
    next_url = body.get("next_url")
    if next_url is not None and (not isinstance(next_url, str)
                                  or not next_url.startswith("https://")):
        raise FrameContractError("invalid pagination metadata")
    rows, identities = [], set()
    for index, item in enumerate(body["results"]):
        if not isinstance(item, dict):
            raise FrameContractError("malformed vendor record")
        stamp = _integer(item.get("sip_timestamp"), "sip_timestamp", minimum=1)
        if not start <= stamp < end:
            raise FrameContractError("source record outside requested time window")
        if stamp > received:
            raise FrameContractError("REST receipt before event time")
        parsed = (_quote(item, ticker, stamp) if endpoint_kind == "quotes"
                  else _trade(item, ticker))
        if parsed["native_key"] in identities:
            raise FrameContractError("duplicate native identity needs correction adjudication")
        identities.add(parsed["native_key"])
        parsed.update({
            "ticker": ticker, "session": session, "sip_timestamp_ns": stamp,
            "participant_timestamp_ns": _opt_int(item, "participant_timestamp"),
            "trf_timestamp_ns": _opt_int(item, "trf_timestamp"),
            "original_available_ns": received,
            "mode": "FINAL_VINTAGE_NOT_AS_SEEN",
            "source_page_index": index, "source_page_receipt": original_page_receipt,
        })
        rows.append(parsed)
    return {
        "schema": SCHEMA, "kind": endpoint_kind, "ticker": ticker,
        "session": session, "start_ns": start, "end_ns": end,
        "source_available_ns": received,
        "source_receipt": original_page_receipt,
        "source_request_id": body["request_id"],
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "row_count": len(rows),
        "pagination": ("MORE_PAGES_REQUIRED" if next_url
                       else "TERMINAL_PAGE_NOT_COVERAGE_PROOF"),
        "total_range_complete": None,
        "market_capture_coverage": None,
        "evidence_mode": "FINAL_VINTAGE",
        "source_receipt_authenticated": False,
        "private_rows": rows,
        "authority": "OFFLINE_EXPLORATORY_ONLY",
    }
