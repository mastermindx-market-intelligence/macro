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
from engine.tick_plane.condition_policy import POLICY_SCHEMA
from engine.tick_plane.exchange_reference import VERDICT_SCHEMA as VENUE_SCHEMA
from engine.tick_plane.quote_condition_policy import evaluate_quote_condition, POLICY_SCHEMA as QUOTE_POLICY_SCHEMA
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
    trade_condition_verdict, venue_reference_verdict,
    quote_condition_policy, original_quote_policy_custody_attested,
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
            "trade_sip_timestamp_ns": trade.get("sip_timestamp_ns") if isinstance(trade, dict) else None,
            "decision_ns": decision_ns, "source_watermark_receipt": watermark_receipt_id,
            "trade_conditions_rules_ref": (
                trade_condition_verdict.get("conditions_rules_ref")
                if isinstance(trade_condition_verdict, dict) else None
            ),
            "trade_condition_policy_reason": (
                trade_condition_verdict.get("reason")
                if isinstance(trade_condition_verdict, dict) else None
            ),
            "quote_conditions_rules_ref": (
                quote_condition_policy.get("policy_sha256")
                if isinstance(quote_condition_policy, dict) else None
            ),
            "quote_source_receipt_id": quote_receipt,
            "matched_quote_id": matched, "quote_age_ns": age,
            "quote_age_limit_ns": max_quote_age_ns,
            "source_trade_conditions": trade.get("trade_conditions") if isinstance(trade, dict) else None,
            "venue_class": trade.get("venue_class") if isinstance(trade, dict) else None,
            "venue_reference_sha256": (
                venue_reference_verdict.get("exchange_reference_sha256")
                if isinstance(venue_reference_verdict, dict) else None
            ),
            "venue_admission_reason": (
                venue_reference_verdict.get("reason")
                if isinstance(venue_reference_verdict, dict) else None
            ),
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
    if (type(decision_ns) is not int or decision_ns < 0
            or type(trade.get("original_frame_received_ns")) is not int):
        return output("UNKNOWN", "TRADE_CLOCK_UNQUALIFIED")
    if trade["original_frame_received_ns"] > decision_ns:
        return output("UNKNOWN", "TRADE_NOT_AVAILABLE_AT_DECISION")
    if (not isinstance(trade_condition_verdict, dict)
            or trade_condition_verdict.get("schema") != POLICY_SCHEMA
            or trade_condition_verdict.get("authority") != "OBSERVATIONAL_ONLY"
            or trade_condition_verdict.get("method") != "CONSOLIDATED_UPDATES_V0_CONSERVATIVE_PROXY"
            or trade_condition_verdict.get("decision_ns") != decision_ns
            or trade_condition_verdict.get("reference_vintage") != "RECEIVED_AT_ONLY_NOT_HISTORICAL_VALIDITY"
            or type(trade_condition_verdict.get("reference_received_ns")) is not int
            or trade_condition_verdict["reference_received_ns"] > decision_ns
            or not isinstance(trade_condition_verdict.get("reference_source_receipt_id"), str)
            or not trade_condition_verdict["reference_source_receipt_id"]
            or not isinstance(trade_condition_verdict.get("conditions_rules_ref"), str)
            or len(trade_condition_verdict["conditions_rules_ref"]) != 64
            or trade_condition_verdict.get("native_trade_conditions") != trade.get("trade_conditions")):
        return output("UNKNOWN", "TRADE_CONDITION_POLICY_UNQUALIFIED")
    trade_condition_eligible = trade_condition_verdict.get("eligible_for_pressure")
    trade_condition_rules_ref = trade_condition_verdict["conditions_rules_ref"]
    if type(trade_condition_eligible) is not bool:
        return output("UNKNOWN", "TRADE_CONDITION_POLICY_UNQUALIFIED")
    if not trade_condition_eligible:
        return output("INELIGIBLE", "TRADE_CONDITION_EXCLUDED")
    v = venue_reference_verdict
    if (not isinstance(v, dict) or v.get("schema") != VENUE_SCHEMA
            or v.get("authority") != "VENUE_OBSERVATION_ONLY"
            or v.get("trade_dedup_key") != trade.get("dedup_key")
            or v.get("native_exchange_id") != trade.get("exchange")
            or v.get("native_trf_id") != trade.get("trf_id")
            or v.get("trade_original_available_ns") != trade.get("original_frame_received_ns")
            or v.get("decision_ns") != decision_ns
            or not isinstance(v.get("exchange_reference_sha256"), str)
            or len(v["exchange_reference_sha256"]) != 64
            or type(v.get("exchange_reference_received_ns")) is not int
            or v["exchange_reference_received_ns"] > decision_ns):
        return output("UNKNOWN", "VENUE_REFERENCE_UNQUALIFIED")
    if (v.get("venue_class") != "LIT" or v.get("lit_eligible") is not True
            or trade.get("venue_class") != "LIT"):
        return output("UNKNOWN", "TRF_OR_VENUE_CLOCK_UNQUALIFIED")
    # The ring resolves ORIGINAL-AS-OF quote state; its legacy quote-condition
    # args only permit lookup, NEVER authorize trade-side classification.
    # A validated and source-bound typed quote verdict is required afterward.
    if (not isinstance(quote_condition_policy, dict)
            or quote_condition_policy.get("schema") != QUOTE_POLICY_SCHEMA
            or quote_condition_policy.get("authority") != "SOURCE_POLICY_CANDIDATE_REQUIRES_CUSTODY"
            or original_quote_policy_custody_attested is not True):
        return output("UNKNOWN", "QUOTE_CONDITION_POLICY_UNQUALIFIED")
    matched = ring.match(
        trade, decision_ns=decision_ns,
        source_complete_through_ns=source_complete_through_ns,
        watermark_available_ns=watermark_available_ns,
        watermark_receipt_id=watermark_receipt_id,
        source_completeness_attested=source_completeness_attested,
        max_quote_age_ns=max_quote_age_ns,
        quote_condition_eligible=True,  # lookup-only; source admission below
        quote_condition_rules_ref="LOOKUP_ONLY_SOURCE_QUOTE_CONDITION_PENDING",
    )
    if matched.get("schema") != MATCH_SCHEMA or matched.get("state") != "MATCHED_SOURCE_CONTEXT":
        return output("UNKNOWN", matched.get("reason", "QUOTE_NOT_QUALIFIED"))
    quote = matched["quote"]
    quote_verdict = evaluate_quote_condition(
        quote=quote, policy=quote_condition_policy, decision_ns=decision_ns,
        original_policy_custody_attested=original_quote_policy_custody_attested,
    )
    if quote_verdict.get("eligible") is not True:
        return output("UNKNOWN", quote_verdict.get("reason") or "QUOTE_CONDITION_UNQUALIFIED",
                      matched=quote["quote_id"], age=matched["quote_age_ns"])
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
