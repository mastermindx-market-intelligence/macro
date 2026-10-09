"""Pure source-owner captured-frame → provisional minute composer (TP-1).

This is NOT a websocket client, receiver daemon, R2 publisher, source identity
owner, completeness generator, scheduler, or a second event lifecycle. The
caller must supply ORIGINAL private frame bytes and real source-receipt clocks
from the incumbent Massive singleton. An external source owner attests stream
continuity, subscription universe, correct session, reference vintages,
current production lease and receipt custody. A boolean cannot prove these.

No outcome labels, trade sizing, rank, alerts or order-level replenishment.
"""

from __future__ import annotations

from hashlib import sha256
import json

from engine.tick_plane.stream_events import (
    normalize_ws_frame, FrameContractError, _integer, _text,
)
from engine.tick_plane.asof_nbbo import InFlightNBBO
from engine.tick_plane.condition_policy import evaluate_trade_conditions
from engine.tick_plane.exchange_reference import classify_trade_venue
from engine.tick_plane.quote_condition_policy import evaluate_quote_condition
from engine.tick_plane.print_observations import observe_provisional_trade
from engine.tick_plane.minute_projection import (
    project_provisional_minute, MINUTE_NS,
)

SCHEMA = "equity.tick_plane.captured_minute/v0"
MAX_BATCH_FRAMES = 500
MAX_BATCH_BYTES = 12 * 1024 * 1024
MAX_BATCH_EVENTS = 12000


class CapturedMinuteRefusal(ValueError):
    pass


def compose_captured_minute(
    *, original_frames, ticker, session, start_ns, decision_ns,
    source_complete_through_ns, watermark_available_ns,
    watermark_receipt_id, source_completeness_attested,
    max_quote_age_ns, trade_condition_reference,
    exchange_reference, quote_condition_policy,
    original_reference_custody_attested,
):
    """Compose one research-only minute using ONE TP-1 source classification.

    `original_frames`: bounded private list of
      {"raw_bytes": bytes, "frame_received_ns": int,
       "source_receipt_id": str}.
    Frames containing status/control events must be filtered separately by
    the incumbent source owner; market batches are atomic and fail closed.

    Raw WebSocket Q updates are *returned only in a private-memory result* so
    the caller can calculate contemporaneous TP-1/R0 context. Never persist
    those Q arrays: only permitted, derived minute summaries are suitable
    for a future authorized private publisher.
    """
    _text(ticker,"ticker")
    _text(session,"session")
    for key,value in (
        ("start_ns",start_ns),("decision_ns",decision_ns),
        ("source_complete_through_ns",source_complete_through_ns),
        ("watermark_available_ns",watermark_available_ns),
        ("max_quote_age_ns",max_quote_age_ns),
    ):
        _integer(value,key)
    _text(watermark_receipt_id,"watermark_receipt_id")
    if start_ns % MINUTE_NS:
        raise CapturedMinuteRefusal("expected UTC minute-aligned start")
    if not isinstance(original_frames,(list,tuple)) or len(original_frames)>MAX_BATCH_FRAMES:
        raise CapturedMinuteRefusal("bounded original frame cohort required")
    if original_reference_custody_attested is not True:
        return {"schema":SCHEMA,"state":"SOURCE_NOT_QUALIFIED",
                "reason":"REFERENCE_CUSTODY_UNATTESTED",
                "authority":"CAPTURED_SOURCE_RESEARCH_ONLY"}
    if source_completeness_attested is not True:
        return {"schema":SCHEMA,"state":"SOURCE_NOT_QUALIFIED",
                "reason":"ORIGINAL_TQ_COMPLETENESS_UNATTESTED",
                "authority":"CAPTURED_SOURCE_RESEARCH_ONLY"}
    if (source_complete_through_ns < start_ns+MINUTE_NS
            or watermark_available_ns<source_complete_through_ns
            or watermark_available_ns>decision_ns
            or decision_ns<start_ns+MINUTE_NS):
        return {"schema":SCHEMA,"state":"NOT_MATURE",
                "reason":"COMPLETED_SOURCE_WINDOW_NOT_ORIGINALLY_AVAILABLE",
                "authority":"CAPTURED_SOURCE_RESEARCH_ONLY"}

    ring=InFlightNBBO(session=session,symbols={ticker},
                      per_symbol_cap=8192,total_cap=8192)
    quotes=[]
    trades=[]
    frame_digests=[]
    n_events=0
    n_bytes=0
    for f in original_frames:
        if not isinstance(f,dict) or set(f)!={
            "raw_bytes","frame_received_ns","source_receipt_id"}:
            raise CapturedMinuteRefusal("original captured frame has wrong contract")
        raw=f["raw_bytes"]
        if type(raw) is not bytes:
            raise CapturedMinuteRefusal("original source frame must be exact bytes")
        n_bytes+=len(raw)
        if n_bytes>MAX_BATCH_BYTES:
            raise CapturedMinuteRefusal("original source byte budget exhausted")
        seen=_integer(f["frame_received_ns"],"frame_received_ns",minimum=1)
        _text(f["source_receipt_id"],"source_receipt_id")
        # Future frames may appear in the physical input batch, but cannot
        # change a prior as-seen observation. They are not source evidence.
        if seen>decision_ns:
            continue
        batch=normalize_ws_frame(
            raw_frame_bytes=raw,frame_received_ns=seen,
            source_receipt_id=f["source_receipt_id"],
            session=session,allowed_symbols={ticker})
        n_events+=len(batch)
        if n_events>MAX_BATCH_EVENTS:
            raise CapturedMinuteRefusal("original source event budget exhausted")
        frame_digests.append(sha256(raw).hexdigest())
        for event in batch:
            if event["event_type"]=="Q":
                # Keep a warmup quote before minute start, provided it is
                # still recent enough to make a qualified start midpoint.
                if event["sip_timestamp_ns"]<start_ns-max_quote_age_ns:
                    continue
                if event["sip_timestamp_ns"]>=start_ns+MINUTE_NS:
                    continue
                ring.ingest_quote(event)
                quotes.append(event)
            elif start_ns<=event["sip_timestamp_ns"]<start_ns+MINUTE_NS:
                trades.append(event)
    if ring._gaps or ring._evicted[ticker]:
        return {"schema":SCHEMA,"state":"SOURCE_NOT_QUALIFIED",
                "reason":"QUOTE_RING_GAP_OR_EVICTION",
                "authority":"CAPTURED_SOURCE_RESEARCH_ONLY"}
    observations=[]
    for trade in trades:
        trade_verdict=evaluate_trade_conditions(
            trade_conditions=trade["trade_conditions"],
            reference=trade_condition_reference,
            decision_ns=decision_ns,
            original_reference_custody_attested=True)
        venue_verdict=classify_trade_venue(
            trade=trade,reference=exchange_reference,
            decision_ns=decision_ns,
            original_reference_custody_attested=True)
        obs=observe_provisional_trade(
            trade,ring,decision_ns=decision_ns,
            source_complete_through_ns=source_complete_through_ns,
            watermark_available_ns=watermark_available_ns,
            watermark_receipt_id=watermark_receipt_id,
            source_completeness_attested=True,
            max_quote_age_ns=max_quote_age_ns,
            trade_condition_verdict=trade_verdict,
            venue_reference_verdict=venue_verdict,
            quote_condition_policy=quote_condition_policy,
            original_quote_policy_custody_attested=True)
        observations.append(obs)
    minute=project_provisional_minute(
        ticker=ticker,session=session,start_ns=start_ns,decision_ns=decision_ns,
        source_complete_through_ns=source_complete_through_ns,
        watermark_available_ns=watermark_available_ns,
        watermark_receipt_id=watermark_receipt_id,
        source_completeness_attested=True,
        observations=observations)
    quote_verdicts={
        q["quote_id"]:evaluate_quote_condition(
            quote=q,policy=quote_condition_policy,decision_ns=decision_ns,
            original_policy_custody_attested=True)
        for q in quotes
    }
    if len(quote_verdicts)!=len(quotes):
        raise CapturedMinuteRefusal("duplicate captured quote identity")
    return {
        "schema":SCHEMA,"state":"PRIVATE_SOURCE_CONTEXT_ONLY",
        "authority":"CAPTURED_SOURCE_RESEARCH_ONLY",
        "ticker":ticker,"session":session,"start_ns":start_ns,
        "end_ns":start_ns+MINUTE_NS,
        "decision_ns":decision_ns,
        "original_watermark_receipt":watermark_receipt_id,
        "source_frame_count":len(frame_digests),
        "source_event_count":n_events,
        "original_source_bytes":n_bytes,
        "raw_frame_digest_set_sha256":sha256(json.dumps(
            sorted(frame_digests),separators=(",",":")).encode()).hexdigest(),
        "minute_private_only":minute,
        "quotes_private_memory_only":quotes,
        "quote_verdicts_private_memory_only":quote_verdicts,
        "source_capture_authenticity":"REQUIRES_ORIGINAL_OWNER_PROOF",
        "publication_authority":False,
    }
