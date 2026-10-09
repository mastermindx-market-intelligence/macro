"""Research-only RTH volume reference from ORIGINAL existing Massive REST minute bars.

This pure adapter performs no REST calls, no pagination, no source auth, no
source storage, no clock scheduling and no market-calendar inference. It only
consumes original already-received single-ticker Aggregate Bars (minute)
response bytes supplied by the incumbent data owner.

Crucial inherited source fact: Massive daily aggregate OHLC is RTH-based but
daily volume/transaction activity includes the FULL market day. Therefore a
FULL_DAY grouped-daily `v` cannot be compared to TP-1's RTH tick shares.
The source owner must independently qualify exact requested RTH minute scope,
native minute volume update rules, response paging and market calendar.

Accepted discovery: DSC-SPY-DAILY-AGG-IS-RTH-PRICE-FULLDAY-ACTIVITY
Source vendor: https://massive.com/docs/rest/stocks/aggregates/custom-bars

Never treat a post-session reference as available to an intraday signal.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from datetime import date

from engine.tick_plane.minute_projection import MINUTE_NS
from engine.tick_plane.stream_events import FrameContractError

SCHEMA = "equity.tick_plane.rth_aggregate_volume_reference/v0"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_RTH_MINUTES = 390
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _int(x, label, *, positive=False):
    if type(x) is not int or x < (1 if positive else 0):
        raise FrameContractError(f"{label} must be a native integer")
    return x


def _id(x, label):
    if not isinstance(x, str) or not x.strip() or len(x) > 400:
        raise FrameContractError(f"{label} requires a bounded original reference")
    return x


def _vol(value):
    if isinstance(value, bool) or not isinstance(value, (int, str, Decimal)):
        raise FrameContractError("REST minute volume must be an exact decimal")
    try:
        result=Decimal(str(value))
    except InvalidOperation as exc:
        raise FrameContractError("REST minute volume is invalid decimal") from exc
    if not result.is_finite() or result < 0:
        raise FrameContractError("REST minute volume must be nonnegative and finite")
    return result


def normalize_rth_minute_volume_reference(
    *, original_response_bytes, ticker, session,
    rth_start_ns, rth_end_ns, expected_rth_minutes,
    source_received_ns, source_receipt_id, source_query_receipt,
    calendar_receipt, volume_semantics_receipt,
    calendar_scope_reviewed, exact_query_range_reviewed,
    complete_pagination_reviewed, minute_volume_semantics_reviewed,
):
    """Produce a bounded, *externally admitted* comparable RTH volume candidate.

    External reviewer flags and receipt strings do not authenticate themselves.
    If any critical proof is absent, return only a typed unqualified profile;
    no volume reference may be fed to the TP-1 2% numerical checker.
    """
    _id(ticker, "ticker")
    if _SYMBOL.fullmatch(ticker) is None:
        raise FrameContractError("invalid stock ticker")
    _id(session,"session")
    if not session.endswith(":RTH"):
        raise FrameContractError("RTH reference requires explicit RTH session")
    try:
        date.fromisoformat(session.split(":",1)[0])
    except ValueError as exc:
        raise FrameContractError("invalid source session date") from exc
    start=_int(rth_start_ns,"rth_start_ns",positive=True)
    end=_int(rth_end_ns,"rth_end_ns",positive=True)
    minutes=_int(expected_rth_minutes,"expected_rth_minutes",positive=True)
    got=_int(source_received_ns,"source_received_ns",positive=True)
    if (minutes>MAX_RTH_MINUTES or start%MINUTE_NS or end%MINUTE_NS
            or end-start != minutes*MINUTE_NS or got<end):
        raise FrameContractError("RTH window and independently supplied calendar disagree")
    for label,val in (
        ("source_receipt_id",source_receipt_id),
        ("source_query_receipt",source_query_receipt),
        ("calendar_receipt",calendar_receipt),
        ("volume_semantics_receipt",volume_semantics_receipt),
    ):
        _id(val,label)
    if (type(original_response_bytes) is not bytes
            or not 0<len(original_response_bytes)<=MAX_RESPONSE_BYTES):
        raise FrameContractError("missing or oversized original minute REST page")
    try:
        native=json.loads(original_response_bytes.decode("utf-8"),
                          parse_float=Decimal,parse_int=int)
    except (ValueError,UnicodeDecodeError) as exc:
        raise FrameContractError("malformed original REST minute response") from exc
    if (not isinstance(native,dict) or native.get("status")!="OK"
            or type(native.get("results")) is not list
            or len(native["results"])>MAX_RTH_MINUTES):
        raise FrameContractError("unqualified vendor aggregate envelope")
    if native.get("ticker") not in (None,ticker):
        raise FrameContractError("aggregate ticker differs from frozen source query")
    if native.get("next_url"):
        raise FrameContractError("source pagination incomplete")
    if native.get("adjusted") is True:
        raise FrameContractError("adjusted aggregate volume not admitted")
    native_count=native.get("resultsCount")
    if native_count is not None and _int(native_count,"resultsCount")!=len(native["results"]):
        raise FrameContractError("vendor returned-count differs from original page")
    rows={}
    for obj in native["results"]:
        if not isinstance(obj,dict):
            raise FrameContractError("malformed native source minute")
        stamp_ms=_int(obj.get("t"),"source minute UTC milliseconds",positive=True)
        ns=stamp_ms*1_000_000
        if (ns%MINUTE_NS or not start<=ns<end):
            raise FrameContractError("source bar does not match exact RTH minute query")
        if ns in rows:
            raise FrameContractError("duplicate source minute; revision needs adjudication")
        rows[ns]=_vol(obj.get("v"))
    # A valid source response can have no activity for some minutes. Sparse
    # records are retained without manufacturing missing bars as trade=0;
    # complete-range coverage must come from the upstream query/paging owner.
    total=sum(rows.values(),Decimal(0))
    receipts=[calendar_scope_reviewed,exact_query_range_reviewed,
              complete_pagination_reviewed,minute_volume_semantics_reviewed]
    if any(type(x) is not bool for x in receipts):
        raise FrameContractError("reference admission flags must be explicit booleans")
    qualified=all(receipts)
    fingerprint=hashlib.sha256(original_response_bytes).hexdigest()
    return {
        "schema":SCHEMA,
        "ticker":ticker,"session":session,
        "reference_scope":"RTH",
        "native_source":"MASSIVE_REST_STOCK_MINUTE_AGGS",
        "rth_start_ns":start,"rth_end_ns":end,
        "expected_rth_minutes":minutes,
        "actual_minute_records":len(rows),
        "missing_minute_rows":minutes-len(rows),
        "reference_volume_shares":format(total,"f") if qualified else None,
        "observed_unadmitted_volume_shares_private_only":format(total,"f"),
        "source_received_ns":got,
        "source_response_sha256":fingerprint,
        "source_receipt_id":source_receipt_id,
        "query_receipt":source_query_receipt,
        "calendar_receipt":calendar_receipt,
        "volume_semantics_receipt":volume_semantics_receipt,
        "source_request_id":native.get("request_id")
        if isinstance(native.get("request_id"),str) else None,
        "calendar_scope_reviewed":calendar_scope_reviewed,
        "exact_query_range_reviewed":exact_query_range_reviewed,
        "complete_pagination_reviewed":complete_pagination_reviewed,
        "minute_volume_semantics_reviewed":minute_volume_semantics_reviewed,
        "reference_state":("CANDIDATE_SAME_SCOPE_EXTERNAL_PROOF_REQUIRED"
                           if qualified else "UNQUALIFIED_MISSING_SOURCE_REVIEW"),
        "reference_source_available_at_original_decision":False,
        "native_volume_eligibility_automatically_validated":False,
        "original_vendor_receipt_authenticity":"REQUIRES_INCUMBENT_OWNER_VERIFICATION",
        "acceptance_authority":None,
        "signal":None,
    }
