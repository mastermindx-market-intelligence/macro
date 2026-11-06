#!/usr/bin/env python3
"""Pure research prototype for the EXISTING entry/outcome owners.

No database, collector, runtime, network access, or production integration.
Missing evidence yields an explicit unavailable result. Original publication
records and subsequent corrections remain separate append-only events.
"""
from __future__ import annotations
import copy, datetime as dt, hashlib, json, math, re

class EvidenceError(ValueError):
    pass

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def clock(value):
    if not isinstance(value,str):raise EvidenceError("CLOCK_UNAVAILABLE")
    try:t=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError:raise EvidenceError("CLOCK_INVALID")
    if t.tzinfo is None:raise EvidenceError("CLOCK_TIMEZONE_MISSING")
    return t.astimezone(dt.timezone.utc)

def mark_from_bar(*,ticker,session,anchor,bar,source,basis_id):
    """An observed market mark is never an actual execution receipt."""
    if anchor not in ("session_open","session_close","hl2_proxy"):raise EvidenceError("UNKNOWN_ANCHOR")
    field={"session_open":"open","session_close":"close"}.get(anchor)
    if anchor=="hl2_proxy":
        price=(bar["high"]+bar["low"])/2 if bar.get("high") is not None and bar.get("low") is not None else None
    else:price=bar.get(field)
    if price is None:raise EvidenceError("PRICE_FIELD_UNAVAILABLE:"+str(field or "high_low"))
    if not isinstance(price,(int,float)) or isinstance(price,bool) or not math.isfinite(price) or price<=0:raise EvidenceError("PRICE_INVALID")
    return {"ticker":ticker,"session":session,"anchor":anchor,"price":price,"basis_id":basis_id,"source":copy.deepcopy(source),"bar_row_sha256":digest({"ticker":ticker,"session":session,"bar":bar}),"execution_status":"MARK_ONLY"}

def legacy_snapshot(row):
    """Preserve original bytes represented by the seven existing latch fields."""
    fields=("date","ticker","entry","basis_used","t1_date","corrupt_bar","latched_asof")
    original={k:row.get(k) for k in fields}
    return {"legacy_row_id":digest(original),"original":original,"qualification":"LEGACY_SOURCE_VINTAGE_UNVERIFIED","reason":"The latch has no immutable price-source identity, vendor availability clock, or execution receipt. Numeric equality cannot fill those fields."}

def validate_mark(mark,asof):
    if mark.get("execution_status")!="MARK_ONLY":raise EvidenceError("EXECUTION_RECEIPT_NOT_IMPLEMENTED")
    if not isinstance(mark.get("basis_id"),str) or not mark["basis_id"]:raise EvidenceError("PRICE_BASIS_UNAVAILABLE")
    source=mark.get("source",{})
    if not re.fullmatch(r"[0-9a-f]{64}",source.get("sha256", "")):raise EvidenceError("SOURCE_IDENTITY_UNAVAILABLE")
    if source.get("clock_kind")!="producer_available_at":raise EvidenceError("SOURCE_AVAILABILITY_UNVERIFIED")
    if clock(source.get("available_at"))>clock(asof):raise EvidenceError("FUTURE_SOURCE_AT_GRADING")
    if mark.get("anchor")=="hl2_proxy":raise EvidenceError("HL2_EXACT_TIME_UNAVAILABLE")
    if mark.get("anchor") not in ("session_open","session_close"):raise EvidenceError("UNKNOWN_ANCHOR")
    price=mark.get("price")
    if not isinstance(price,(int,float)) or isinstance(price,bool) or not math.isfinite(price) or price<=0:raise EvidenceError("PRICE_INVALID")

def aligned_excess(stock_entry,stock_exit,benchmark_entry,benchmark_exit,*,published_at,entry_anchor_at,graded_at):
    """Strict same-anchor diagnostic, not an executable/trading P&L claim.

The existing calendar owner supplies entry_anchor_at. A missing benchmark open
must be handled when constructing that mark; it cannot be replaced by close.
"""
    if published_at is None:raise EvidenceError("PUBLICATION_CLOCK_UNVERIFIED")
    if clock(published_at)>clock(entry_anchor_at):raise EvidenceError("PUBLICATION_AFTER_ENTRY_ANCHOR")
    for mark in (stock_entry,stock_exit,benchmark_entry,benchmark_exit):validate_mark(mark,graded_at)
    if (stock_entry["session"],stock_entry["anchor"])!=(benchmark_entry["session"],benchmark_entry["anchor"]):raise EvidenceError("ENTRY_ANCHOR_MISMATCH")
    if (stock_exit["session"],stock_exit["anchor"])!=(benchmark_exit["session"],benchmark_exit["anchor"]):raise EvidenceError("EXIT_ANCHOR_MISMATCH")
    if stock_entry["session"]>=stock_exit["session"]:raise EvidenceError("NONPOSITIVE_SESSION_WINDOW")
    for entry,exit in ((stock_entry,stock_exit),(benchmark_entry,benchmark_exit)):
        if entry["ticker"]!=exit["ticker"]:raise EvidenceError("INSTRUMENT_MISMATCH")
        if entry["basis_id"]!=exit["basis_id"]:raise EvidenceError("BASIS_ID_MISMATCH")
        if entry["source"]["sha256"]!=exit["source"]["sha256"]:raise EvidenceError("WITHIN_INSTRUMENT_VINTAGE_MISMATCH")
    stock_return=(stock_exit["price"]/stock_entry["price"]-1)*100
    benchmark_return=(benchmark_exit["price"]/benchmark_entry["price"]-1)*100
    return {"status":"ALIGNED_MARK_DIAGNOSTIC","stock_return_pct":stock_return,"benchmark_return_pct":benchmark_return,"excess_pp":stock_return-benchmark_return,"execution_status":"MARK_ONLY","accounting":"Price marks on each instrument's declared consistent basis; total-return certification and execution costs require separate evidence."}

def seal_event(event):
    if "event_id" in event:raise EvidenceError("EVENT_ALREADY_SEALED")
    result=copy.deepcopy(event);result["event_id"]=digest(event);return result

def append_event(ledger,event):
    """In-memory falsifier of append-only semantics; storage remains incumbent."""
    body={k:v for k,v in event.items() if k!="event_id"}
    if event.get("event_id")!=digest(body):raise EvidenceError("EVENT_HASH_MISMATCH")
    key=tuple(event.get(k) for k in ("decision_id","ticker","entry_session"))
    if not all(key):raise EvidenceError("DECISION_LINK_UNAVAILABLE")
    prior={x["event_id"]:x for x in ledger}
    if event["event_id"] in prior:return copy.deepcopy(ledger)
    if event.get("kind")=="original_entry":
        if any(x.get("kind")=="original_entry" and tuple(x.get(k) for k in ("decision_id","ticker","entry_session"))==key for x in ledger):raise EvidenceError("ORIGINAL_ENTRY_IMMUTABLE")
    elif event.get("kind")=="entry_correction":
        original=prior.get(event.get("correction_of"))
        if not original or original.get("kind")!="original_entry":raise EvidenceError("CORRECTION_TARGET_UNAVAILABLE")
        if tuple(original.get(k) for k in ("decision_id","ticker","entry_session"))!=key:raise EvidenceError("CORRECTION_IDENTITY_MISMATCH")
        if not event.get("reason"):raise EvidenceError("CORRECTION_REASON_UNAVAILABLE")
        if clock(event.get("recorded_at"))<clock(original.get("recorded_at")):raise EvidenceError("CORRECTION_PRECEDES_ORIGINAL")
    else:raise EvidenceError("EVENT_KIND_UNSUPPORTED")
    return [*copy.deepcopy(ledger),copy.deepcopy(event)]
