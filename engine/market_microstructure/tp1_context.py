"""R0 research-only consumption of qualified TP-1 minute evidence + NBBO.

A compatibility adapter, NOT a second trade signer, raw tape store, collector,
market clock, signal, or event lifecycle. Never translate provisional WebSocket
trades into R0's finalized-looking revision=0/action=ORIGINAL records.
TP-1 owns trade signing, condition/venue decisions and original receipt custody.

This leaf uses ONLY minute-observation totals and quote context, with exact
source schemas. As-seen eligibility and full T/Q capture completeness require
independent incumbent-owner proof; booleans here are necessary, not sufficient.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re

from engine.market_microstructure.pressure_response import (
    _prior_quote, _quote, _recovery, _fmt,
)

SCHEMA = "equity.pressure_response.tp1_context/v0"
TP1_MINUTE_SCHEMA = "equity.tick_plane.minute_observation/v0"
TP1_QUOTE_SCHEMA = "equity.tick_plane.stream_event/v0"
_QUOTE_VERDICT_KEYS = frozenset({
    "schema", "authority", "eligible", "reason", "quote_id",
    "source_frame_sha256", "original_frame_received_ns",
    "quote_condition", "quote_indicators", "decision_ns",
    "policy_available_ns", "policy_rules_sha256", "source_reference_sha256",
})
MINUTE_NS = 60_000_000_000
MAX_MINUTES = 5
MAX_QUOTES = 20000
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class TP1ContextRefusal(ValueError):
    """Source incompatibility or integrity breach; must not become zero flow."""


def _int(x, field):
    if type(x) is not int or x < 0:
        raise TP1ContextRefusal(f"{field} requires nonnegative integer nanoseconds")
    return x


def _id(x, field):
    if not isinstance(x, str) or not x.strip() or len(x) > 300:
        raise TP1ContextRefusal(f"{field} missing or malformed")
    return x


def _sha(x, field):
    if not isinstance(x, str) or _SHA256.fullmatch(x) is None:
        raise TP1ContextRefusal(f"{field} requires source SHA-256")
    return x


def _money(x, field):
    if not isinstance(x, str):
        raise TP1ContextRefusal(f"{field} must be an exact decimal string")
    try:
        n = Decimal(x)
    except InvalidOperation as exc:
        raise TP1ContextRefusal(f"{field} malformed decimal") from exc
    if not n.is_finite() or n < 0:
        raise TP1ContextRefusal(f"{field} invalid notional")
    return n


def _head(ticker, session, start_ns, end_ns, decision_ns, source_manifest,
          watermark_receipt):
    return {
        "schema": SCHEMA, "authority": "RESEARCH_CONTEXT_ONLY",
        "ticker": ticker, "session": session, "start_ns": start_ns,
        "end_ns": end_ns, "decision_ns": decision_ns,
        "source_manifest": source_manifest,
        "source_watermark_receipt": watermark_receipt,
        "correction_status": "STREAM_PROVISIONAL_UNRECONCILED",
        "source_mode": "AS_SEEN_REQUIRES_ORIGINAL_OWNER_PROOF",
        "capture_completeness_proven_by_this_function": False,
        "absorption_signal": None, "rank_authority": False,
        "forward_outcome_label": None, "execution_adjusted_return": None,
    }


def project_tp1_pressure_context(
    *, ticker, session, start_ns, end_ns, decision_ns, watermark_ns,
    watermark_received_ns, watermark_receipt, source_manifest,
    source_completeness_attested, max_quote_age_ns,
    minute_observations, source_quotes, quote_condition_receipts,
):
    """Compute descriptive TP-1 pressure vs NBBO, never future prediction.

    Original quote eligibility is a source-specific per-quote receipt. If a
    previously seen quote condition is unknown or non-eligible, the quote must
    remain in the as-of chain as an INVALID update (rather than reviving a
    stale older valid quote). No quote-condition receipt, no classified context.
    """
    _id(ticker, "ticker")
    _id(session, "session")
    _id(source_manifest, "source_manifest")
    _id(watermark_receipt, "watermark_receipt")
    for field, value in (
        ("start_ns", start_ns), ("end_ns", end_ns),
        ("decision_ns", decision_ns), ("watermark_ns", watermark_ns),
        ("watermark_received_ns", watermark_received_ns),
        ("max_quote_age_ns", max_quote_age_ns),
    ):
        _int(value, field)
    if end_ns <= start_ns or start_ns % MINUTE_NS or end_ns % MINUTE_NS:
        raise TP1ContextRefusal("TP-1 pressure study requires aligned, ordered whole minutes")
    n_minutes = (end_ns - start_ns) // MINUTE_NS
    if not 1 <= n_minutes <= MAX_MINUTES:
        raise TP1ContextRefusal("TP-1 bounded study supports one through five minutes")
    head = _head(ticker, session, start_ns, end_ns, decision_ns,
                 source_manifest, watermark_receipt)
    if source_completeness_attested is not True:
        return {**head, "state": "SOURCE_NOT_QUALIFIED",
                "reason": "ORIGINAL_SOURCE_COMPLETENESS_UNATTESTED"}
    if (decision_ns < end_ns or watermark_ns < end_ns
            or watermark_received_ns < watermark_ns
            or watermark_received_ns > decision_ns):
        return {**head, "state": "NOT_MATURE",
                "reason": "WINDOW_OR_ORIGINAL_RECEIPT_NOT_AVAILABLE"}
    if (not isinstance(minute_observations, (tuple, list))
            or len(minute_observations) != n_minutes):
        raise TP1ContextRefusal("one already-qualified TP-1 minute per whole minute required")
    if (not isinstance(source_quotes, (tuple, list))
            or len(source_quotes) > MAX_QUOTES):
        raise TP1ContextRefusal("bounded TP-1 quote event sample required")
    if not isinstance(quote_condition_receipts, dict):
        raise TP1ContextRefusal("original quote-condition receipt map required")

    amounts = {name: Decimal(0) for name in (
        "gross", "buy", "sell", "mid", "unknown", "ineligible", "trf"
    )}
    minute_refs, condition_refs, exchange_refs, minute_quote_refs = [], set(), set(), set()
    minute_age_limits = set()
    count_prints = count_unknown = 0
    for i, minute in enumerate(sorted(minute_observations, key=lambda m: m.get("start_ns", -1))):
        if not isinstance(minute, dict) or minute.get("schema") != TP1_MINUTE_SCHEMA:
            raise TP1ContextRefusal("source minute missing canonical TP-1 schema")
        if (minute.get("ticker") != ticker or minute.get("session") != session
                or minute.get("start_ns") != start_ns + i*MINUTE_NS
                or minute.get("end_ns") != start_ns + (i+1)*MINUTE_NS):
            raise TP1ContextRefusal("minute gap, duplicate or symbol/session mismatch")
        if (minute.get("authority") != "OBSERVATIONAL_PROVISIONAL_ONLY"
                or minute.get("state") != "PROVISIONAL_MEASURED_CONTEXT"
                or minute.get("correction_status") != "STREAM_PROVISIONAL_UNRECONCILED"
                or minute.get("source_mode") != "ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS"
                or minute.get("absorption_signal") is not None
                or minute.get("rank_or_trade_authority") is not False
                or minute.get("market_capture_coverage") is not None):
            return {**head, "state": "MINUTE_NOT_QUALIFIED",
                    "reason": "SOURCE_AUTHORITY_OR_CAPTURE_UNRESOLVED"}
        for clock in ("decision_ns", "source_complete_through_ns",
                      "watermark_available_ns", "original_latest_available_ns"):
            _int(minute.get(clock), f"minute.{clock}")
        source_quote_age = _int(minute.get("max_quote_age_ns"),
                                "minute.max_quote_age_ns")
        minute_age_limits.add(source_quote_age)
        if source_quote_age > max_quote_age_ns:
            return {**head, "state": "MINUTE_NOT_QUALIFIED",
                    "reason": "SOURCE_QUOTE_AGE_POLICY_TOO_LENIENT"}
        if (minute["decision_ns"] > decision_ns
                or minute["source_complete_through_ns"] < minute["end_ns"]
                or minute["watermark_available_ns"] < minute["source_complete_through_ns"]
                or minute["watermark_available_ns"] > minute["decision_ns"]
                or minute["original_latest_available_ns"] > minute["decision_ns"]):
            return {**head, "state": "MINUTE_NOT_KNOWABLE",
                    "reason": "ORIGINAL_MINUTE_SOURCE_RECEIPT_LATE"}
        _id(minute.get("source_watermark_receipt"), "minute.watermark_receipt")
        condition_refs.add(_sha(minute.get("condition_rules_ref"), "condition_rules_ref"))
        exchange_refs.add(_sha(minute.get("exchange_reference_sha256"), "exchange_reference"))
        minute_quote_refs.add(_sha(minute.get("quote_condition_rules_sha256"),
                                   "minute.quote_condition_rules_sha256"))
        source_observation_sha = _sha(
            minute.get("source_observation_sha256"), "source_observation_sha256")
        # Bind every *individual minute's* measured original source generation,
        # not just a de-duplicated set of watermark strings.
        minute_refs.append((
            minute["start_ns"], minute["end_ns"], minute["decision_ns"],
            minute["source_complete_through_ns"], minute["source_watermark_receipt"],
            source_observation_sha,
        ))
        for target, key in (
            ("gross", "gross_sampled_notional_usd"),
            ("buy", "buy_proxy_notional_usd"),
            ("sell", "sell_proxy_notional_usd"),
            ("mid", "midpoint_notional_usd"),
            ("unknown", "unknown_notional_usd"),
            ("ineligible", "ineligible_notional_usd"),
            ("trf", "trf_gross_notional_usd"),
        ):
            amounts[target] += _money(minute.get(key), key)
        _int(minute.get("n_sampled_prints"), "minute.n_sampled_prints")
        _int(minute.get("n_unclassified"), "minute.n_unclassified")
        if minute["n_sampled_prints"] == 0 or minute["n_unclassified"] > minute["n_sampled_prints"]:
            raise TP1ContextRefusal("source minute contains contradictory print counts")
        # The canonical TP-1 minute defines one venue and one classification
        # bucket for each retained print. Detect counter substitution.
        venue_total = 0
        class_total = 0
        for key in ("n_lit", "n_trf", "n_unknown_venue"):
            venue_total += _int(minute.get(key), key)
        for key in ("n_buy_proxy", "n_sell_proxy", "n_midpoint",
                    "n_unclassified", "n_condition_ineligible"):
            class_total += _int(minute.get(key), key)
        if venue_total != minute["n_sampled_prints"] or class_total != minute["n_sampled_prints"]:
            raise TP1ContextRefusal("source minute print denominators inconsistent")
        count_prints += minute["n_sampled_prints"]
        count_unknown += minute["n_unclassified"]
    if (len(condition_refs) != 1 or len(exchange_refs) != 1
            or len(minute_quote_refs) != 1 or len(minute_age_limits) != 1):
        raise TP1ContextRefusal("mixed condition or exchange source vintages")
    if amounts["trf"] > amounts["unknown"] or sum(amounts[k] for k in (
        "buy", "sell", "mid", "unknown", "ineligible"
    )) != amounts["gross"]:
        raise TP1ContextRefusal("TP-1 minute notional denominators inconsistent")

    normalized = []
    quote_refs = set()
    unqualified_quote_events = 0
    for q in source_quotes:
        if (not isinstance(q, dict) or q.get("schema") != TP1_QUOTE_SCHEMA
                or q.get("event_type") != "Q"
                or q.get("ticker") != ticker or q.get("session") != session):
            raise TP1ContextRefusal("source Q update has wrong original identity")
        if q.get("source") != "MASSIVE_STOCKS_SIP_WS":
            raise TP1ContextRefusal("quote is not a canonical TP-1 stream record")
        stamp = _int(q.get("sip_timestamp_ns"), "quote.sip_timestamp_ns")
        available = _int(q.get("original_frame_received_ns"),
                         "quote.original_frame_received_ns")
        if available < stamp:
            raise TP1ContextRefusal("quote original receipt precedes SIP event")
        if available > decision_ns:
            continue  # A later assertion cannot poison an earlier decision.
        key = _id(q.get("quote_id"), "quote_id")
        frame = _sha(q.get("source_frame_sha256"), "source_frame_sha256")
        _id(q.get("source_receipt_id"), "source_receipt_id")
        slot = _int(q.get("frame_event_index"), "frame_event_index")
        policy = quote_condition_receipts.get(key)
        # Consume the exact typed TP-1 quote verdict. Its quote/indicator
        # content, original frame identity, policy vintage and decision cutoff
        # must agree with the source quote; an old generic eligible=True is
        # never a valid research receipt.
        if (not isinstance(policy, dict)
                or set(policy) != _QUOTE_VERDICT_KEYS
                or policy.get("schema") != "equity.tick_plane.quote_condition_admission/v0"
                or policy.get("authority") != "ORIGINAL_QUOTE_POLICY_CONTEXT_ONLY"
                or policy.get("quote_id") != key
                or policy.get("source_frame_sha256") != frame
                or policy.get("original_frame_received_ns") != available
                or policy.get("quote_condition") != q.get("quote_condition")
                or policy.get("quote_indicators") != q.get("quote_indicators")):
            return {**head, "state": "QUOTE_REFERENCE_UNQUALIFIED",
                    "reason": "MISSING_OR_MISMATCHED_QUOTE_CONDITION_RECEIPT"}
        policy_available = _int(policy.get("policy_available_ns"),
                                "policy_available_ns")
        policy_cutoff = _int(policy.get("decision_ns"), "policy.decision_ns")
        if (policy_available > policy_cutoff or policy_cutoff < available
                or policy_cutoff > decision_ns):
            return {**head, "state": "QUOTE_REFERENCE_UNQUALIFIED",
                    "reason": "QUOTE_CONDITION_POLICY_NOT_AVAILABLE_AT_DECISION"}
        quote_refs.add(_sha(policy.get("policy_rules_sha256"), "quote condition policy"))
        _sha(policy.get("source_reference_sha256"), "native quote condition reference")
        if type(policy.get("eligible")) is not bool:
            return {**head, "state": "QUOTE_REFERENCE_UNQUALIFIED",
                    "reason": "QUOTE_CONDITION_ELIGIBILITY_UNKNOWN"}
        # Preserve invalid or unknown quote updates as *invalid* at their
        # time; never drop them and silently revive a preceding valid quote.
        firm = q.get("valid_firm_nbbo") is True and policy["eligible"]
        if not firm:
            unqualified_quote_events += 1
        bx, ax = q.get("bid_exchange"), q.get("ask_exchange")
        if bx is not None and (type(bx) is not int or bx < 0):
            raise TP1ContextRefusal("invalid native bid exchange ID")
        if ax is not None and (type(ax) is not int or ax < 0):
            raise TP1ContextRefusal("invalid native ask exchange ID")
        native_bid, native_ask = q.get("bid"), q.get("ask")
        if native_bid is None or native_ask is None:
            # The source had an absent quote side. Encoding an invalid zero
            # solely for the legacy R0 arithmetic does NOT invent firm size.
            native_bid, native_ask = "0", "0"
            firm = False
        record = {
            "id": key, "ticker": ticker, "session": session,
            "sip_ns": stamp, "available_ns": available,
            "bid": str(native_bid), "ask": str(native_ask),
            "bid_size": q.get("bid_size") if firm else 0,
            "ask_size": q.get("ask_size") if firm else 0,
            "bid_exchange": str(bx) if bx is not None else None,
            "ask_exchange": str(ax) if ax is not None else None,
            "source_receipt": f"{frame}:{slot}",
        }
        normalized.append(_quote(record, ticker, session))
    if len(quote_refs) != 1:
        return {**head, "state": "QUOTE_REFERENCE_UNQUALIFIED",
                "reason": "MIXED_OR_MISSING_QUOTE_CONDITION_POLICY"}
    if quote_refs != minute_quote_refs:
        return {**head, "state": "QUOTE_REFERENCE_UNQUALIFIED",
                "reason": "MINUTE_AND_QUOTE_POLICY_GENERATION_DISAGREEMENT"}
    if not normalized:
        return {**head, "state": "QUOTE_REFERENCE_UNQUALIFIED",
                "reason": "NO_ELIGIBLE_SOURCE_QUOTE_UPDATES"}
    normalized.sort(key=lambda x: (x["sip_ns"], x["id"]))
    ids = set()
    for q in normalized:
        if q["id"] in ids:
            raise TP1ContextRefusal("duplicate source quote identity")
        ids.add(q["id"])
    timestamps = [q["sip_ns"] for q in normalized]
    start_quote, start_reason = _prior_quote(
        normalized, timestamps, start_ns, max_age_ns=max_quote_age_ns,
        require_exact_order=True,
    )
    end_quote, end_reason = _prior_quote(
        normalized, timestamps, end_ns, max_age_ns=max_quote_age_ns,
        require_exact_order=True,
    )
    if start_quote is None or end_quote is None:
        return {**head, "state": "PRICE_CONTEXT_UNOBSERVABLE",
                "reason": {"start": start_reason, "end": end_reason},
                "n_source_minute_packets": n_minutes,
                "n_quote_updates": len(normalized)}
    start_mid = (start_quote["bid"] + start_quote["ask"])/2
    end_mid = (end_quote["bid"] + end_quote["ask"])/2
    price_response_bps = (end_mid/start_mid-1)*Decimal(10000)
    classified = amounts["buy"] + amounts["sell"]
    gross = amounts["gross"]
    receipt_digest = sha256(json.dumps(sorted(minute_refs),
                          separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    # The quote context has a DIFFERENT source dependency from the signed minute
    # totals. Preserve its digest separately to prevent opaque output changes.
    quoted_source = [
        (q["id"], q["sip_ns"], q["available_ns"], q["source_receipt"],
         _fmt(q["bid"]), _fmt(q["ask"]), q["bid_size"], q["ask_size"],
         q.get("bid_exchange"), q.get("ask_exchange"))
        for q in normalized
    ]
    quote_digest = sha256(json.dumps(quoted_source, sort_keys=True,
                           separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    return {
        **head, "state": "PROVISIONAL_RESEARCH_CONTEXT", "reason": None,
        "source_minutes_receipt_sha256": receipt_digest,
        "source_quote_observations_sha256": quote_digest,
        "source_condition_rules_sha256": next(iter(condition_refs)),
        "source_exchange_rules_sha256": next(iter(exchange_refs)),
        "source_quote_condition_rules_sha256": next(iter(quote_refs)),
        "source_quote_age_limit_ns": next(iter(minute_age_limits)),
        "n_source_minute_packets": n_minutes, "n_sampled_prints": count_prints,
        "n_unclassified": count_unknown, "n_quote_updates": len(normalized),
        "n_quote_condition_unqualified": unqualified_quote_events,
        "gross_sampled_notional_usd": _fmt(gross),
        "buy_proxy_notional_usd": _fmt(amounts["buy"]),
        "sell_proxy_notional_usd": _fmt(amounts["sell"]),
        "midpoint_notional_usd": _fmt(amounts["mid"]),
        "unknown_notional_usd": _fmt(amounts["unknown"]),
        "ineligible_notional_usd": _fmt(amounts["ineligible"]),
        "trf_gross_notional_usd": _fmt(amounts["trf"]),
        "classified_notional_coverage": _fmt(classified/gross) if gross else None,
        "pressure_balance": _fmt((amounts["buy"]-amounts["sell"])/classified)
            if classified else None,
        "midpoint_response_bps": _fmt(price_response_bps),
        "bid_size_recovery": _recovery(normalized, start_quote, start_ns,
                                      end_ns, "bid", max_age_ns=max_quote_age_ns),
        "ask_size_recovery": _recovery(normalized, start_quote, start_ns,
                                      end_ns, "ask", max_age_ns=max_quote_age_ns),
        "absorption_signal": None,
        "impact_relative_to_control": None,
        "source_qualification": "EXTERNAL_OWNER_RECEIPTS_REQUIRED",
    }
