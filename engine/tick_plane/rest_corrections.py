"""Source-cited REST correction context for provisional T.* trade prints.

A WebSocket trade has no correction/cancel field. The vendor's historical REST
response may include `correction`, but today's REST vintage is NOT what was
knowable when an earlier SIP trade arrived. Never overwrite an as-seen print
or equate an absent REST record with cancellation. Multiple correction rows
require native lineage adjudication; do not choose one by sorted timestamp.

This pure module parses an owner-supplied complete, privately held REST page
(no network or credentials), preserves its original byte digest and actual
fetch availability, and returns ONLY a typed comparison receipt.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal

from engine.tick_plane.stream_events import (
    SCHEMA as WS_SCHEMA, FrameContractError, _decimal, _integer, _text,
)

SCHEMA = "equity.tick_plane.rest_correction_comparison/v0"
MAX_REST_BYTES = 16 * 1024 * 1024


def compare_rest_trade(*, stream_trade, raw_rest_bytes, fetched_at_ns,
                       source_receipt_id, requested_ticker):
    """Return conservative REST-vs-WS comparison, not a finalized trade.

    Source owner MUST independently prove endpoint, entitlement, full paginated
    query coverage and receipt custody. Never assign REST receipt time to the
    earlier WebSocket decision, even when both records appear to match.
    """
    if not isinstance(stream_trade, dict) or stream_trade.get("schema") != WS_SCHEMA or stream_trade.get("event_type") != "T":
        raise FrameContractError("only normalized provisional WS trades can be compared")
    if stream_trade.get("correction_status") != "STREAM_PROVISIONAL_UNRECONCILED":
        raise FrameContractError("unexpected WebSocket correction status")
    if requested_ticker != stream_trade["ticker"]:
        raise FrameContractError("REST query ticker does not match source trade")
    _text(source_receipt_id, "REST source receipt")
    _integer(fetched_at_ns, "REST fetched_at_ns", minimum=1)
    if fetched_at_ns < stream_trade["original_frame_received_ns"]:
        raise FrameContractError("REST snapshot predates stream receipt")
    if type(raw_rest_bytes) is not bytes or len(raw_rest_bytes) == 0 or len(raw_rest_bytes) > MAX_REST_BYTES:
        raise FrameContractError("missing or oversized original REST response")
    try:
        response = json.loads(raw_rest_bytes.decode("utf-8"),
                              parse_float=Decimal, parse_int=int)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameContractError("malformed REST response bytes") from exc
    if (not isinstance(response, dict) or response.get("status") != "OK"
            or not isinstance(response.get("results"), list)
            or not isinstance(response.get("request_id"), str)
            or not response["request_id"].strip()):
        raise FrameContractError("REST response lacks required provenance shape")
    receipt = {
        "schema": SCHEMA, "ticker": requested_ticker,
        "stream_dedup_key": stream_trade["dedup_key"],
        "stream_original_available_ns": stream_trade["original_frame_received_ns"],
        "stream_reconciliation_state": "PROVISIONAL_UNCHANGED",
        "rest_available_ns": fetched_at_ns,
        "rest_source_receipt_id": source_receipt_id,
        "rest_response_sha256": hashlib.sha256(raw_rest_bytes).hexdigest(),
        "rest_request_id": response["request_id"],
        "authority": "RESEARCH_CONTEXT_ONLY",
        "rest_correction_code": None,
        "rest_sip_timestamp_ns": None,
        "state": None,
    }
    if response.get("next_url"):
        receipt["state"] = "PAGINATION_INCOMPLETE"
        return receipt
    candidates = []
    for row in response["results"]:
        if not isinstance(row, dict):
            raise FrameContractError("malformed REST row")
        native_id = row.get("id")
        if native_id != stream_trade["trade_id"]:
            continue
        ex = _integer(row.get("exchange"), "REST.exchange")
        trf = _integer(row.get("trf_id"), "REST.trf_id", optional=True)
        if ex == stream_trade["exchange"] and trf == stream_trade["trf_id"]:
            candidates.append(row)
    if not candidates:
        receipt["state"] = "NOT_IN_REST_SAMPLE_UNKNOWN"
        return receipt
    if len(candidates) > 1:
        receipt["state"] = "MULTIPLE_NATIVE_REST_GENERATIONS_NEED_LINEAGE"
        return receipt
    r = candidates[0]
    rest_clock = _integer(r.get("sip_timestamp"), "REST.sip_timestamp", minimum=1)
    receipt["rest_sip_timestamp_ns"] = rest_clock
    correction = _integer(r.get("correction"), "REST.correction", optional=True)
    receipt["rest_correction_code"] = correction
    if rest_clock // 1_000_000 != stream_trade["sip_timestamp_ns"] // 1_000_000:
        receipt["state"] = "SIP_TIME_SCOPE_DISAGREEMENT"
        return receipt
    if correction not in (None, 0):
        receipt["state"] = "CORRECTION_FLAG_PRESENT_NEEDS_NATIVE_LINEAGE"
        return receipt
    if _decimal(r.get("price"), "REST.price") != stream_trade["price"]:
        receipt["state"] = "REST_PRICE_RESTATED_UNLINKED"
        return receipt
    if (r.get("decimal_size") is not None and
            _decimal(r["decimal_size"], "REST.decimal_size") !=
            stream_trade["decimal_size_shares"]):
        receipt["state"] = "REST_SIZE_RESTATED_UNLINKED"
        return receipt
    receipt["state"] = "MATCHED_CURRENT_REST_VINTAGE_NOT_AS_SEEN"
    return receipt
