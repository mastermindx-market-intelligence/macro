"""Only already-matured, PIT-eligible future NBBO markouts for R0 research.

This produces an EVALUATION LABEL, never a contemporaneous signal, trading
action, entry condition or an extension of TP-1's event/episode lifecycle.
An original decision may only use quotes available then; the later endpoint
is evaluated separately after the horizon, source watermark and receipt mature.

The source owner must separately prove actual quote completeness, market status
and any historical receivability claim. FINAL_VINTAGE is research-only.
"""

from __future__ import annotations

from decimal import Decimal
from engine.market_microstructure.pressure_response import (
    _quote, _int, _name, _prior_quote, _fmt, _midpoint,
    _midpoint_change_bps, MODES,
)

SCHEMA = "equity.price_response_evaluation_label/v0"
_HEALTH = frozenset({"NORMAL", "HALTED", "UNKNOWN"})


def measure_matured_response(*, ticker, session, original_decision_ns,
                             anchor_ns, label_end_ns, evaluation_cutoff_ns,
                             source_watermark_ns, watermark_received_ns,
                             watermark_receipt, source_manifest,
                             source_mode, max_quote_age_ns, market_health,
                             market_health_receipt, quotes):
    """Calculate a positive/negative midpoint response only after maturity.

    The anchor midpoint must have been known no later than original_decision.
    Label-end midpoint and source watermark may arrive later but must be
    knowable by evaluation_cutoff_ns. This cannot retroactively authorize the
    anchor decision. No trade fills or execution costs are asserted.
    """
    _name(ticker, "ticker")
    _name(session, "session")
    _name(watermark_receipt, "watermark_receipt")
    _name(source_manifest, "source_manifest")
    _name(market_health_receipt, "market_health_receipt")
    for key,value in (
        ("original_decision_ns",original_decision_ns),("anchor_ns",anchor_ns),
        ("label_end_ns",label_end_ns),("evaluation_cutoff_ns",evaluation_cutoff_ns),
        ("source_watermark_ns",source_watermark_ns),
        ("watermark_received_ns",watermark_received_ns),
        ("max_quote_age_ns",max_quote_age_ns)):
        _int(value,key)
    if original_decision_ns < anchor_ns or label_end_ns <= anchor_ns:
        raise ValueError("invalid original decision or forward-horizon clocks")
    if source_mode not in MODES:
        raise ValueError("unrecognized source mode")
    if market_health not in _HEALTH:
        raise ValueError("market status is not qualified")
    identity={
        "schema":SCHEMA, "authority":"RESEARCH_OUTCOME_LABEL_ONLY",
        "ticker":ticker, "session":session,
        "original_decision_ns":original_decision_ns,
        "anchor_ns":anchor_ns, "label_end_ns":label_end_ns,
        "evaluation_cutoff_ns":evaluation_cutoff_ns,
        "source_watermark_receipt":watermark_receipt,
        "source_manifest":source_manifest, "source_mode":source_mode,
        "market_health_receipt":market_health_receipt,
        "forward_label_not_available_to_original_decision":True,
        "signal":None, "absorption_signal":None, "trade_fill":None,
    }
    if (evaluation_cutoff_ns < label_end_ns
            or source_watermark_ns < label_end_ns
            or watermark_received_ns < source_watermark_ns
            or watermark_received_ns > evaluation_cutoff_ns):
        return {**identity,"state":"NOT_MATURE","reason":"FUTURE_HORIZON_OR_SOURCE_NOT_KNOWN"}
    if market_health != "NORMAL":
        return {**identity,"state":"CENSORED","reason":"HALT_OR_UNKNOWN_MARKET_STATUS"}
    if not isinstance(quotes,(tuple,list)):
        raise ValueError("source quotes must be a bounded sequence")
    if len(quotes)>100000:
        raise ValueError("source quote window exceeds the bounded research budget")
    normalized=[]
    for quote in quotes:
        if not isinstance(quote,dict):
            raise ValueError("invalid source quote")
        stamp=_int(quote.get("available_ns"),"quote.available_ns")
        if stamp>evaluation_cutoff_ns:
            # An amended/future record may exist in the supplied archive but
            # must not affect the earlier evidence state or its validation.
            continue
        normalized.append(_quote(quote,ticker,session))
    anchor=[q for q in normalized if q["available_ns"]<=original_decision_ns]
    anchor.sort(key=lambda x:(x["sip_ns"],x["id"]))
    end=sorted(normalized,key=lambda x:(x["sip_ns"],x["id"]))
    a,ar=_prior_quote(anchor,[q["sip_ns"] for q in anchor],anchor_ns,
                      max_age_ns=max_quote_age_ns,require_exact_order=True)
    b,br=_prior_quote(end,[q["sip_ns"] for q in end],label_end_ns,
                      max_age_ns=max_quote_age_ns,require_exact_order=True)
    if a is None or b is None:
        return {**identity,"state":"UNOBSERVABLE",
                "reason":{"anchor":ar,"forward":br}}
    first=_midpoint(a)
    last=_midpoint(b)
    pct_bps=_midpoint_change_bps(first,last)
    availability=max(watermark_received_ns,b["available_ns"])
    return {**identity,"state":"MATURED_EVALUATION_LABEL","reason":None,
            "midpoint_response_bps":_fmt(pct_bps),
            "label_first_knowable_ns":availability,
            "anchor_quote_age_ns":anchor_ns-a["sip_ns"],
            "label_quote_age_ns":label_end_ns-b["sip_ns"],
            "quote_receipts_private_only":{
                "anchor":a["source_receipt"],"label":b["source_receipt"]},
            "market_capture_completeness":None,
            "source_quality":"REQUIRES_ORIGINAL_SOURCE_OWNER_PROOF",
            "execution_adjusted_return":None}
