"""Qualified provisional trade context from a canonical T/Q source and NBBO ring.

This pure leaf is the TP-1 consumer bridge, NOT a new source, actor classifier,
event lifecycle, rank, trade recommendation, order-book detector or publisher.
Native stream trades remain correction-provisional until REST/flat-file review.
An invalid or absent quote/condition can never be filled from the later market.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from engine.flow_signing import classify_print
from engine.tick_plane.asof_nbbo import InFlightNBBO, MATCH_SCHEMA
from engine.tick_plane.stream_events import SCHEMA as STREAM_SCHEMA

SCHEMA = "equity.tick_plane.provisional_print_observation/v0"


def _money(trade):
    try:
        price = Decimal(str(trade["price"]))
        shares = Decimal(str(trade["decimal_size_shares"]))
    except (KeyError, InvalidOperation, TypeError, ValueError):
        return None
    if not price.is_finite() or not shares.is_finite() or price <= 0 or shares <= 0:
        return None
    return format(price * shares, "f")


def observe_provisional_trade(
    trade, ring: InFlightNBBO, *, decision_ns, source_complete_through_ns,
    watermark_available_ns, watermark_receipt_id,
    source_completeness_attested, max_quote_age_ns,
    trade_condition_eligible, trade_condition_rules_ref,
    quote_condition_eligible, quote_condition_rules_ref,
):
    """Return measured quote-location context with strict as-seen abstention.

    Coverage denominator and correction status remain explicit; signed notional
    is unavailable when trade-side or quote-side eligibility is unknown. A
    quantity printed at the ask is not proof of institutional buying.
    """
    def output(state, reason, *, bucket="unclassified", matched=None,
               quote_receipt=None, age=None):
        return {
            "schema": SCHEMA, "state": state, "reason": reason,
            "ticker": trade.get("ticker") if isinstance(trade, dict) else None,
            "session": trade.get("session") if isinstance(trade, dict) else None,
            "trade_id": trade.get("trade_id") if isinstance(trade, dict) else None,
            "dedup_key": trade.get("dedup_key") if isinstance(trade, dict) else None,
            "original_available_ns": trade.get("original_frame_received_ns") if isinstance(trade, dict) else None,
            "decision_ns": decision_ns, "source_watermark_receipt": watermark_receipt_id,
            "trade_conditions_rules_ref": trade_condition_rules_ref,
            "quote_conditions_rules_ref": quote_condition_rules_ref,
            "quote_source_receipt_id": quote_receipt,
            "matched_quote_id": matched, "quote_age_ns": age,
            "source_trade_conditions": trade.get("trade_conditions") if isinstance(trade, dict) else None,
            "venue_class": trade.get("venue_class") if isinstance(trade, dict) else None,
            "correction_status": trade.get("correction_status") if isinstance(trade, dict) else None,
            "gross_observed_notional_usd": _money(trade) if isinstance(trade, dict) else None,
            "side_proxy": bucket,
            "signed_notional_usd": (
                _money(trade) if bucket == "buy" else
                "-" + _money(trade) if bucket == "sell" else None
            ),
            "authority": "OBSERVATIONAL_PROVISIONAL_ONLY",
            "forward_response_label": None,
            "absorption_signal": None,
        }

    if not isinstance(ring, InFlightNBBO):
        return output("UNKNOWN", "MISSING_CANONICAL_QUOTE_RING")
    if not isinstance(trade, dict) or trade.get("schema") != STREAM_SCHEMA or trade.get("event_type") != "T":
        return output("UNKNOWN", "INVALID_STREAM_TRADE")
    if trade.get("correction_status") != "STREAM_PROVISIONAL_UNRECONCILED":
        return output("UNKNOWN", "UNQUALIFIED_CORRECTION_STATE")
    if _money(trade) is None:
        return output("UNKNOWN", "INVALID_TRADE_NOTIONAL")
    if type(trade_condition_eligible) is not bool or not isinstance(trade_condition_rules_ref, str) or not trade_condition_rules_ref.strip():
        return output("UNKNOWN", "TRADE_CONDITION_POLICY_UNQUALIFIED")
    if not trade_condition_eligible:
        return output("INELIGIBLE", "TRADE_CONDITION_EXCLUDED")
    if trade.get("venue_class") != "LIT":
        return output("UNKNOWN", "TRF_OR_VENUE_CLOCK_UNQUALIFIED")
    matched = ring.match(
        trade, decision_ns=decision_ns,
        source_complete_through_ns=source_complete_through_ns,
        watermark_available_ns=watermark_available_ns,
        watermark_receipt_id=watermark_receipt_id,
        source_completeness_attested=source_completeness_attested,
        max_quote_age_ns=max_quote_age_ns,
        quote_condition_eligible=quote_condition_eligible,
        quote_condition_rules_ref=quote_condition_rules_ref,
    )
    if matched.get("schema") != MATCH_SCHEMA or matched.get("state") != "MATCHED_SOURCE_CONTEXT":
        return output("UNKNOWN", matched.get("reason", "QUOTE_NOT_QUALIFIED"))
    quote = matched["quote"]
    trade_receipt = trade["source_frame_sha256"] + ":" + str(trade["frame_event_index"])
    quote_receipt = quote["source_frame_sha256"] + ":" + str(quote["frame_event_index"])
    location = classify_print(
        ticker=trade["ticker"], quote_ticker=quote["ticker"],
        session=trade["session"], quote_session=quote["session"],
        trade_price=trade["price"], bid=quote["bid"], ask=quote["ask"],
        bid_size=quote["bid_size"], ask_size=quote["ask_size"],
        trade_sip_ns=trade["sip_timestamp_ns"],
        quote_sip_ns=quote["sip_timestamp_ns"],
        trade_received_ns=trade["original_frame_received_ns"],
        quote_received_ns=quote["original_frame_received_ns"],
        decision_ns=decision_ns, max_quote_age_ns=max_quote_age_ns,
        trade_source_receipt=trade_receipt, quote_source_receipt=quote_receipt,
        eligible_for_pressure=trade_condition_eligible,
        condition_rules_ref=trade_condition_rules_ref,
        venue_class=trade["venue_class"],
    )
    if location["bucket"] == "unclassified":
        return output("UNKNOWN", location["reason"], quote_receipt=quote_receipt,
                      matched=quote["quote_id"], age=matched["quote_age_ns"])
    return output("MEASURED_SOURCE_PROXY", None, bucket=location["bucket"],
                  quote_receipt=quote_receipt, matched=quote["quote_id"],
                  age=matched["quote_age_ns"])
