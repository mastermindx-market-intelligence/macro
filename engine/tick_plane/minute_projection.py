"""Deterministic private minute projection of source-qualified TP-1 observations.

This is a leaf of the incumbent Massive TP-1 source, not another market-data
source, signal/scoring model, event store, publisher, or public API. Data are
provisional until native corrections have been adjudicated. Never treat an
empty capture, missing watermark or incomplete sample as zero pressure.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

SCHEMA = "equity.tick_plane.minute_observation/v0"
SOURCE_SCHEMA = "equity.tick_plane.provisional_print_observation/v0"
MINUTE_NS = 60_000_000_000
MAX_OBSERVATIONS = 10000
_OBS_KEYS = frozenset({
    "schema", "state", "reason", "ticker", "session", "trade_id",
    "dedup_key", "original_available_ns", "trade_sip_timestamp_ns",
    "decision_ns", "source_watermark_receipt", "trade_conditions_rules_ref",
    "trade_condition_policy_reason", "quote_conditions_rules_ref",
    "quote_source_receipt_id", "matched_quote_id", "quote_age_ns",
    "source_trade_conditions", "venue_class", "correction_status",
    "gross_observed_notional_usd", "side_proxy", "signed_notional_usd",
    "authority", "forward_response_label", "absorption_signal",
})


class MinuteProjectionRefusal(ValueError):
    """Source, timing, or identity failure that must not become neutral volume."""


def _integer(value, label):
    if type(value) is not int or value < 0:
        raise MinuteProjectionRefusal(f"{label} must be nonnegative integer")
    return value


def _decimal(value, label):
    if type(value) is not str:
        raise MinuteProjectionRefusal(f"{label} must be exact decimal string")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise MinuteProjectionRefusal(f"{label} malformed decimal") from exc
    if not d.is_finite() or d <= 0:
        raise MinuteProjectionRefusal(f"{label} must be positive and finite")
    return d


def _money(d):
    return format(d, "f")


def project_provisional_minute(
    *, ticker, session, start_ns, decision_ns,
    source_complete_through_ns, watermark_available_ns,
    watermark_receipt_id, source_completeness_attested, observations,
):
    """Return a nullable, source-bound private observation window.

    Inputs are existing TP-1 `observe_provisional_trade` outputs, not raw
    vendor quote/trade payloads. The incumbent source owner independently
    establishes completeness and the original availability receipt. The
    external attestation flag is not self-verifying and NEVER opens a live
    service or predictive authority.
    """
    for label,value in (
        ("start_ns",start_ns),("decision_ns",decision_ns),
        ("source_complete_through_ns",source_complete_through_ns),
        ("watermark_available_ns",watermark_available_ns),
    ):
        _integer(value,label)
    if start_ns % MINUTE_NS:
        raise MinuteProjectionRefusal("minute window must align to UTC minute")
    if not isinstance(ticker,str) or not ticker or not isinstance(session,str) or not session:
        raise MinuteProjectionRefusal("ticker and session are required")
    if not isinstance(watermark_receipt_id,str) or not watermark_receipt_id.strip():
        raise MinuteProjectionRefusal("original watermark receipt required")
    if not isinstance(observations,(tuple,list)) or len(observations)>MAX_OBSERVATIONS:
        raise MinuteProjectionRefusal("bounded observation cohort required")
    end_ns=start_ns+MINUTE_NS
    head={
        "schema":SCHEMA, "authority":"OBSERVATIONAL_PROVISIONAL_ONLY",
        "ticker":ticker, "session":session, "start_ns":start_ns,
        "end_ns":end_ns, "decision_ns":decision_ns,
        "source_watermark_receipt":watermark_receipt_id,
        "source_complete_through_ns":source_complete_through_ns,
        "watermark_available_ns":watermark_available_ns,
        "correction_status":"STREAM_PROVISIONAL_UNRECONCILED",
        "source_mode":"ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS",
        "rank_or_trade_authority":False,
    }
    if source_completeness_attested is not True:
        return {**head,"state":"SOURCE_NOT_QUALIFIED",
                "reason":"SOURCE_COMPLETENESS_UNATTESTED"}
    if (end_ns>decision_ns or source_complete_through_ns<end_ns
            or watermark_available_ns<source_complete_through_ns
            or watermark_available_ns>decision_ns):
        return {**head,"state":"NOT_MATURE",
                "reason":"ORIGINAL_WINDOW_OR_WATERMARK_NOT_KNOWABLE"}
    dedup={}
    latest=None
    for obs in observations:
        if not isinstance(obs,dict) or set(obs)!=_OBS_KEYS:
            raise MinuteProjectionRefusal("observation is not exact incumbent source shape")
        if (obs["schema"]!=SOURCE_SCHEMA
                or obs["authority"]!="OBSERVATIONAL_PROVISIONAL_ONLY"
                or obs["ticker"]!=ticker or obs["session"]!=session
                or obs["source_watermark_receipt"]!=watermark_receipt_id
                or obs["decision_ns"]!=decision_ns):
            raise MinuteProjectionRefusal("source identity or cutoff mismatch")
        if obs["correction_status"]!="STREAM_PROVISIONAL_UNRECONCILED":
            raise MinuteProjectionRefusal("live source correction finality is not proven")
        if obs["forward_response_label"] is not None or obs["absorption_signal"] is not None:
            raise MinuteProjectionRefusal("predictive fields must remain null")
        ts=_integer(obs["trade_sip_timestamp_ns"],"trade SIP time")
        seen=_integer(obs["original_available_ns"],"original receipt")
        if ts<start_ns or ts>=end_ns:
            raise MinuteProjectionRefusal("trade outside minute cohort")
        if seen>decision_ns or seen<ts:
            raise MinuteProjectionRefusal("unavailable or impossible trade clock")
        if not isinstance(obs["dedup_key"],str) or not obs["dedup_key"]:
            raise MinuteProjectionRefusal("native print identity missing")
        prior=dedup.get(obs["dedup_key"])
        if prior is not None:
            if obs!=prior:
                raise MinuteProjectionRefusal("conflicting duplicate provisional trade")
            continue
        dedup[obs["dedup_key"]]=obs
        latest=seen if latest is None else max(latest,seen)
    if not dedup:
        return {**head,"state":"NO_SAMPLED_PRINTS",
                "reason":"NO_OBSERVED_ROWS_IS_NOT_PROOF_OF_ZERO_MARKET_VOLUME",
                "n_sampled_prints":0}
    sums=Counter()
    counts=Counter()
    problems=Counter()
    policy_refs=set()
    for o in dedup.values():
        gross=_decimal(o["gross_observed_notional_usd"],"gross notional")
        side=o["side_proxy"]
        state=o["state"]
        venue=o["venue_class"]
        if venue not in ("LIT","TRF","UNKNOWN"):
            raise MinuteProjectionRefusal("invalid native venue classification")
        sums["observed"]+=gross
        counts["total"]+=1
        counts[venue]+=1
        if state=="INELIGIBLE":
            if side!="unclassified" or o["signed_notional_usd"] is not None:
                raise MinuteProjectionRefusal("ineligible print has signed quantity")
            sums["ineligible"]+=gross
            counts["ineligible"]+=1
        elif state=="UNKNOWN":
            if side!="unclassified" or o["signed_notional_usd"] is not None:
                raise MinuteProjectionRefusal("unqualified print has signed quantity")
            sums["unknown"]+=gross
            counts["unknown"]+=1
        elif state=="MEASURED_SOURCE_PROXY":
            if venue!="LIT" or side not in ("buy","sell","mid"):
                raise MinuteProjectionRefusal("signed off-exchange/unknown or invalid side")
            if o["reason"] is not None:
                raise MinuteProjectionRefusal("measured source has failure reason")
            signed=o["signed_notional_usd"]
            if side=="mid":
                if signed is not None:
                    raise MinuteProjectionRefusal("midpoint may not carry signed amount")
                sums["mid"]+=gross
            else:
                if not isinstance(signed,str):
                    raise MinuteProjectionRefusal("signed notional disagrees with exact gross")
                try:
                    signed_decimal=Decimal(signed)
                except InvalidOperation as exc:
                    raise MinuteProjectionRefusal("malformed signed notional") from exc
                if (not signed_decimal.is_finite()
                        or signed_decimal != (gross if side=="buy" else -gross)):
                    raise MinuteProjectionRefusal("signed notional disagrees with exact gross")
                sums[side]+=gross
            counts[side]+=1
        else:
            raise MinuteProjectionRefusal("unrecognized source observation state")
        if state in ("UNKNOWN","INELIGIBLE"):
            reason=o["reason"]
            if not isinstance(reason,str) or not reason:
                raise MinuteProjectionRefusal("unqualified row missing typed reason")
            problems[reason]+=1
        if venue=="LIT" and state!="INELIGIBLE":
            sums["lit_observed"]+=gross
        if venue=="TRF":
            sums["trf"]+=gross
        ref=o["trade_conditions_rules_ref"]
        if ref is not None:
            if not isinstance(ref,str) or len(ref)!=64:
                raise MinuteProjectionRefusal("unqualified condition rule digest")
            policy_refs.add(ref)
    if len(policy_refs)>1:
        raise MinuteProjectionRefusal("mixed condition rule generations in one minute")
    known_lit=sums["buy"]+sums["sell"]+sums["mid"]
    lit_total=sums["lit_observed"]
    ordered=sorted(dedup.values(),key=lambda o:(o["trade_sip_timestamp_ns"],o["dedup_key"]))
    digest=sha256(json.dumps(ordered,sort_keys=True,separators=(",",":"),
                            ensure_ascii=True).encode()).hexdigest()
    return {**head, "state":"PROVISIONAL_MEASURED_CONTEXT",
            "reason":None, "n_sampled_prints":counts["total"],
            "n_lit":counts["LIT"],"n_trf":counts["TRF"],
            "n_unknown_venue":counts["UNKNOWN"],
            "n_unclassified":counts["unknown"],
            "n_condition_ineligible":counts["ineligible"],
            "n_buy_proxy":counts["buy"],"n_sell_proxy":counts["sell"],
            "n_midpoint":counts["mid"],
            "gross_sampled_notional_usd":_money(sums["observed"]),
            "buy_proxy_notional_usd":_money(sums["buy"]),
            "sell_proxy_notional_usd":_money(sums["sell"]),
            "midpoint_notional_usd":_money(sums["mid"]),
            "unknown_notional_usd":_money(sums["unknown"]),
            "ineligible_notional_usd":_money(sums["ineligible"]),
            "trf_gross_notional_usd":_money(sums["trf"]),
            "lit_quoted_notional_coverage":_money(known_lit/lit_total) if lit_total else None,
            "reason_counts":dict(sorted(problems.items())),
            "condition_rules_ref":next(iter(policy_refs),None),
            "original_latest_available_ns":latest,
            "source_observation_sha256":digest,
            "absorption_signal":None,
            "forward_return_label":None,
            "price_response_label":None,
            "market_capture_coverage":None,
    }
