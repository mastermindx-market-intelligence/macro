"""Original-available stock exchange reference admission, no collection.

Massive /v3/reference/exchanges defines venue type as exchange, SIP or TRF.
The numeric exchange ID on a trade is not by itself proof of a lit venue.
This leaf parses one immutable reference response from the incumbent owner
and qualifies one provisional trade's exchange context at a decision cutoff.

Never use a later-fetched reference to rewrite an earlier live decision.
No vendor socket, orders, participant identity, ATS naming or score authority.
https://massive.com/docs/rest/stocks/market-operations/exchanges
"""

from __future__ import annotations

import hashlib
import json

from engine.tick_plane.stream_events import (
    SCHEMA as STREAM_SCHEMA, FrameContractError, _integer, _text,
    _NON_LIT_EXCHANGE_IDS, _KNOWN_TRF_IDS,
)

REFERENCE_SCHEMA = "equity.tick_plane.exchange_reference/v0"
VERDICT_SCHEMA = "equity.tick_plane.venue_admission/v0"
MAX_BYTES = 2 * 1024 * 1024
MAX_ENTRIES = 512
TYPES = frozenset({"exchange", "SIP", "TRF"})


def parse_exchange_reference(*, raw_response_bytes, available_ns,
                             source_receipt_id):
    _integer(available_ns, "exchange reference available time", minimum=1)
    _text(source_receipt_id, "source_receipt_id")
    if type(raw_response_bytes) is not bytes or not 0 < len(raw_response_bytes) <= MAX_BYTES:
        raise FrameContractError("missing or oversized exchange reference bytes")
    try:
        response = json.loads(raw_response_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise FrameContractError("malformed exchange reference response") from exc
    if (not isinstance(response, dict) or response.get("status") != "OK"
            or not isinstance(response.get("request_id"), str)
            or not response["request_id"].strip()
            or type(response.get("results")) is not list
            or not 0 < len(response["results"]) <= MAX_ENTRIES):
        raise FrameContractError("exchange reference is not a qualified response")
    if response.get("next_url"):
        raise FrameContractError("exchange reference is not fully paginated")
    codes = {}
    for row in response["results"]:
        if not isinstance(row, dict):
            raise FrameContractError("malformed exchange reference record")
        if row.get("asset_class") != "stocks":
            continue
        code = _integer(row.get("id"), "exchange ID")
        venue_type = row.get("type")
        if venue_type not in TYPES:
            raise FrameContractError("unknown reference venue type")
        old = codes.get(code)
        if old is not None and old != venue_type:
            raise FrameContractError("conflicting exchange reference identity")
        codes[code] = venue_type
    if not codes:
        raise FrameContractError("stock exchange reference has no records")
    return {
        "schema": REFERENCE_SCHEMA,
        "reference_available_ns": available_ns,
        "original_reference_receipt": source_receipt_id,
        "source_request_id": response["request_id"],
        "reference_sha256": hashlib.sha256(raw_response_bytes).hexdigest(),
        "source_types": codes,
        "source_vintage": "AS_RECEIVED_NOT_RETROACTIVE",
        "authority": "SOURCE_REFERENCE_ONLY",
    }


def classify_trade_venue(*, trade, reference, decision_ns,
                         original_reference_custody_attested):
    """Produce a source-bound classification; not a standalone trading signal."""
    trade_id = trade.get("dedup_key") if isinstance(trade, dict) else None
    exchange = trade.get("exchange") if isinstance(trade, dict) else None
    trf = trade.get("trf_id") if isinstance(trade, dict) else None

    def result(venue, reason):
        return {
            "schema": VERDICT_SCHEMA, "venue_class": venue,
            "reason": reason, "lit_eligible": venue == "LIT",
            "trade_dedup_key": trade_id,
            "native_exchange_id": exchange, "native_trf_id": trf,
            "trade_original_available_ns": (
                trade.get("original_frame_received_ns")
                if isinstance(trade, dict) else None
            ),
            "decision_ns": decision_ns,
            "exchange_reference_sha256": (
                reference.get("reference_sha256") if isinstance(reference, dict) else None
            ),
            "exchange_reference_received_ns": (
                reference.get("reference_available_ns") if isinstance(reference, dict) else None
            ),
            "authority": "VENUE_OBSERVATION_ONLY",
        }

    if (not isinstance(trade, dict) or trade.get("schema") != STREAM_SCHEMA
            or trade.get("event_type") != "T" or not isinstance(trade_id, str)
            or not trade_id):
        return result("UNKNOWN", "UNQUALIFIED_TRADE_IDENTITY")
    if (not isinstance(reference, dict)
            or reference.get("schema") != REFERENCE_SCHEMA
            or reference.get("source_vintage") != "AS_RECEIVED_NOT_RETROACTIVE"
            or reference.get("authority") != "SOURCE_REFERENCE_ONLY"
            or not isinstance(reference.get("reference_sha256"), str)
            or len(reference["reference_sha256"]) != 64):
        return result("UNKNOWN", "UNQUALIFIED_EXCHANGE_REFERENCE")
    if original_reference_custody_attested is not True:
        return result("UNKNOWN", "UNATTESTED_REFERENCE_CUSTODY")
    clocks = (
        decision_ns, reference.get("reference_available_ns"),
        trade.get("original_frame_received_ns"),
    )
    if any(type(v) is not int or v < 0 for v in clocks):
        return result("UNKNOWN", "INVALID_SOURCE_OR_DECISION_CLOCK")
    if reference["reference_available_ns"] > decision_ns or trade["original_frame_received_ns"] > decision_ns:
        return result("UNKNOWN", "REFERENCE_OR_TRADE_NOT_KNOWN_AT_DECISION")
    if type(exchange) is not int or exchange < 0:
        return result("UNKNOWN", "INVALID_NATIVE_EXCHANGE")
    native_type = reference.get("source_types", {}).get(exchange)
    if native_type not in TYPES:
        return result("UNKNOWN", "EXCHANGE_MISSING_IN_REFERENCE")
    if exchange in (5, 13, 62) and native_type == "exchange":
        return result("UNKNOWN", "NONLIT_SOURCE_TYPE_CONFLICT")
    if native_type == "exchange" and exchange not in _NON_LIT_EXCHANGE_IDS:
        return result("LIT", "SOURCE_REFERENCE_EXCHANGE_CANDIDATE")
    if (exchange == 4 and native_type == "TRF"
            and trf in _KNOWN_TRF_IDS):
        return result("TRF", "FINRA_REPORTING_FACILITY_NOT_NAMED_ATS")
    return result("UNKNOWN", "NONLIT_OR_UNRECOGNIZED_REPORTING_ROUTE")
