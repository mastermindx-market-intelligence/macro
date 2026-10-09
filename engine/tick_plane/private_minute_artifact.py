"""Strict PRIVATE_SERVICE handoff projection from ONE canonical TP-1 minute.

No vendor T/Q, credentials, native trade IDs, per-quote records, publisher,
bucket selection, endpoint, queue, R2 client or alternative source lifecycle.

This is an allowlist view of an already-built TP-1 minute. It is NOT an
automatically distributable product; rights, source receipt custody, original
feed completeness, consumer authz and the actual PRIVATE R2 bucket remain
separate admission gates owned by their incumbent operators.

The payload is deterministic canonical JSON, byte-addressed for a later
authorized private writer/reader. The byte digest proves representation
integrity, not vendor authenticity or source entitlement.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation

SCHEMA = "equity.tick_plane.private_minute_artifact/v0"
SOURCE_SCHEMA = "equity.tick_plane.minute_observation/v0"
MINUTE_NS = 60_000_000_000
MAX_PAYLOAD_BYTES = 32 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_SESSION = re.compile(r"^\d{4}-\d{2}-\d{2}:(RTH|PRE|POST)$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]{0,79}$")

_SOURCE_KEYS = frozenset((
    "schema","authority","ticker","session","start_ns","end_ns",
    "decision_ns","source_watermark_receipt","source_complete_through_ns",
    "watermark_available_ns","correction_status","source_mode",
    "rank_or_trade_authority","state","reason","n_sampled_prints",
    "n_lit","n_trf","n_unknown_venue","n_unclassified",
    "n_condition_ineligible","n_buy_proxy","n_sell_proxy","n_midpoint",
    "n_lit_eligible_prints","n_lit_classified_quote_le5s_prints",
    "n_lit_classified_quote_gt5s_prints","n_lit_unclassified_prints",
    "n_lit_source_unqualified_prints","lit_unknown_reason_counts",
    "gross_sampled_notional_usd","buy_proxy_notional_usd",
    "sell_proxy_notional_usd","midpoint_notional_usd",
    "unknown_notional_usd","ineligible_notional_usd",
    "source_all_printed_shares","source_volume_included_shares",
    "source_volume_excluded_shares","source_volume_unknown_shares",
    "n_source_volume_included_prints","n_source_volume_excluded_prints",
    "n_source_volume_unknown_prints","trf_gross_notional_usd",
    "lit_quoted_notional_coverage","reason_counts",
    "condition_rules_ref","exchange_reference_sha256",
    "quote_condition_rules_sha256","max_quote_age_ns",
    "original_latest_available_ns","source_observation_sha256",
    "absorption_signal","forward_return_label","price_response_label",
    "market_capture_coverage",
))
_COUNTER_KEYS = (
    "n_sampled_prints","n_lit","n_trf","n_unknown_venue","n_unclassified",
    "n_condition_ineligible","n_buy_proxy","n_sell_proxy","n_midpoint",
    "n_lit_eligible_prints","n_lit_classified_quote_le5s_prints",
    "n_lit_classified_quote_gt5s_prints","n_lit_unclassified_prints",
    "n_lit_source_unqualified_prints",
    "n_source_volume_included_prints","n_source_volume_excluded_prints",
    "n_source_volume_unknown_prints",
)
_NOTIONAL_KEYS = (
    "gross_sampled_notional_usd","buy_proxy_notional_usd",
    "sell_proxy_notional_usd","midpoint_notional_usd",
    "unknown_notional_usd","ineligible_notional_usd",
    "trf_gross_notional_usd",
)
_SHARE_KEYS = (
    "source_all_printed_shares","source_volume_included_shares",
    "source_volume_excluded_shares","source_volume_unknown_shares",
)


class PrivateMinuteRefusal(ValueError):
    """No private artifact may be emitted on an invalid source minute."""


def _nonnegative_int(value, field):
    if type(value) is not int or value < 0:
        raise PrivateMinuteRefusal(f"{field} needs original nonnegative integer")
    return value


def _source_decimal(value, field):
    if not isinstance(value,str):
        raise PrivateMinuteRefusal(f"{field} requires source exact decimal text")
    try:
        amount=Decimal(value)
    except InvalidOperation as exc:
        raise PrivateMinuteRefusal(f"{field} malformed source amount") from exc
    if not amount.is_finite() or amount < 0:
        raise PrivateMinuteRefusal(f"{field} invalid source amount")
    return amount


def _digest(value, field, *, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value,str) or _SHA256.fullmatch(value) is None:
        raise PrivateMinuteRefusal(f"{field} is not a source SHA-256")
    return value


def _reasons(value, field):
    if not isinstance(value,dict) or len(value)>96:
        raise PrivateMinuteRefusal(f"{field} must be bounded typed reasons")
    for key,n in value.items():
        if not isinstance(key,str) or _REASON.fullmatch(key) is None:
            raise PrivateMinuteRefusal(f"{field} contains free text / unknown reason")
        _nonnegative_int(n,field+"."+key)
    return dict(sorted(value.items()))


def project_private_minute(*, source_minute, source_manifest_sha256):
    """Return *private-only* canonical JSON bytes + hash for an existing writer.

    In particular, never return raw source_watermark_receipt text: its digest
    suffices to link to the original owner custody plane without leaking
    host-specific references, URLs or token-bearing source metadata.
    """
    if not isinstance(source_minute,dict) or set(source_minute)!=_SOURCE_KEYS:
        raise PrivateMinuteRefusal("source minute fields do not match strict source contract")
    m=source_minute
    if (m["schema"]!=SOURCE_SCHEMA
            or m["authority"]!="OBSERVATIONAL_PROVISIONAL_ONLY"
            or m["state"]!="PROVISIONAL_MEASURED_CONTEXT"
            or m["reason"] is not None
            or m["correction_status"]!="STREAM_PROVISIONAL_UNRECONCILED"
            or m["source_mode"]!="ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS"
            or m["rank_or_trade_authority"] is not False):
        raise PrivateMinuteRefusal("source state or market/trade authority is not qualified")
    if any(m[key] is not None for key in (
        "absorption_signal","forward_return_label","price_response_label",
        "market_capture_coverage",
    )):
        raise PrivateMinuteRefusal("future, speculative or captured-completeness data cannot be promoted")
    symbol=m["ticker"]
    session=m["session"]
    if not isinstance(symbol,str) or _TICKER.fullmatch(symbol) is None:
        raise PrivateMinuteRefusal("invalid source ticker")
    if not isinstance(session,str) or _SESSION.fullmatch(session) is None:
        raise PrivateMinuteRefusal("invalid source session")
    from datetime import date
    try:
        date.fromisoformat(session.split(":",1)[0])
    except ValueError as exc:
        raise PrivateMinuteRefusal("invalid source session date") from exc
    clocks={key:_nonnegative_int(m[key],key) for key in (
        "start_ns","end_ns","decision_ns","source_complete_through_ns",
        "watermark_available_ns","original_latest_available_ns","max_quote_age_ns",
    )}
    if (clocks["start_ns"]%MINUTE_NS!=0
            or clocks["end_ns"]-clocks["start_ns"]!=MINUTE_NS
            or clocks["source_complete_through_ns"]<clocks["end_ns"]
            or clocks["watermark_available_ns"]<clocks["source_complete_through_ns"]
            or clocks["watermark_available_ns"]>clocks["decision_ns"]
            or clocks["original_latest_available_ns"]>clocks["decision_ns"]
            or clocks["original_latest_available_ns"]<clocks["start_ns"]):
        raise PrivateMinuteRefusal("minute original time/receipt custody is contradictory")
    receipt=m["source_watermark_receipt"]
    if not isinstance(receipt,str) or not receipt.strip() or len(receipt)>2048:
        raise PrivateMinuteRefusal("missing or oversized original watermark receipt")
    counters={key:_nonnegative_int(m[key],key) for key in _COUNTER_KEYS}
    notional={key:_source_decimal(m[key],key) for key in _NOTIONAL_KEYS}
    shares={key:_source_decimal(m[key],key) for key in _SHARE_KEYS}
    if (counters["n_sampled_prints"]<=0
            or counters["n_lit"]+counters["n_trf"]+counters["n_unknown_venue"]!=counters["n_sampled_prints"]
            or counters["n_source_volume_included_prints"]
               +counters["n_source_volume_excluded_prints"]
               +counters["n_source_volume_unknown_prints"]!=counters["n_sampled_prints"]
            or counters["n_buy_proxy"]+counters["n_sell_proxy"]+counters["n_midpoint"]
               +counters["n_unclassified"]+counters["n_condition_ineligible"]!=counters["n_sampled_prints"]
            or counters["n_lit_classified_quote_le5s_prints"]
               +counters["n_lit_classified_quote_gt5s_prints"]
               +counters["n_lit_unclassified_prints"]!=counters["n_lit_eligible_prints"]):
        raise PrivateMinuteRefusal("source minute contradictory print denominators")
    if (notional["buy_proxy_notional_usd"]+notional["sell_proxy_notional_usd"]
            +notional["midpoint_notional_usd"]+notional["unknown_notional_usd"]
            +notional["ineligible_notional_usd"]!=notional["gross_sampled_notional_usd"]
            or sum((shares[key] for key in (
                "source_volume_included_shares","source_volume_excluded_shares",
                "source_volume_unknown_shares")),Decimal(0))!=shares["source_all_printed_shares"]):
        raise PrivateMinuteRefusal("source notional/volume conservation failed")
    reasons=_reasons(m["reason_counts"],"reason_counts")
    age_reasons=_reasons(m["lit_unknown_reason_counts"],"lit_unknown_reason_counts")
    if (sum(reasons.values())!=counters["n_unclassified"]+counters["n_condition_ineligible"]
            or sum(age_reasons.values())!=counters["n_lit_unclassified_prints"]):
        raise PrivateMinuteRefusal("source exception reasons missing denominator entries")
    for key in ("condition_rules_ref","exchange_reference_sha256",
                "quote_condition_rules_sha256"):
        _digest(m[key],key,optional=True)
    _digest(m["source_observation_sha256"],"source_observation_sha256")
    _digest(source_manifest_sha256,"source_manifest_sha256")
    coverage=m["lit_quoted_notional_coverage"]
    if coverage is not None:
        valid=_source_decimal(coverage,"lit_quoted_notional_coverage")
        if valid>1:
            raise PrivateMinuteRefusal("lit notional coverage exceeds one")
    body={
        "schema":SCHEMA,
        "source_schema":SOURCE_SCHEMA,
        "distribution_class":"PRIVATE_SERVICE_HOLD_PENDING_LICENSE_AND_CONSUMER_REVIEW",
        "public_delivery_allowed":False,
        "rank_trade_alert_authority":False,
        "source_authenticity":"EXTERNAL_INCUMBENT_PROOF_REQUIRED",
        "live_capture_completeness":"UNVERIFIED_BY_PROJECTION",
        "source_mode":"ACTUAL_AS_SEEN_ONLY_WHEN_OWNER_PROVES_RECEIPTS",
        "correction_status":m["correction_status"],
        "ticker":symbol,"session":session,
        "start_ns":clocks["start_ns"],"end_ns":clocks["end_ns"],
        "source_complete_through_ns":clocks["source_complete_through_ns"],
        "decision_ns":clocks["decision_ns"],
        "source_watermark_available_ns":clocks["watermark_available_ns"],
        "source_latest_print_available_ns":clocks["original_latest_available_ns"],
        "max_quote_age_ns":clocks["max_quote_age_ns"],
        "source_watermark_receipt_sha256":hashlib.sha256(receipt.encode("utf-8")).hexdigest(),
        "source_manifest_sha256":source_manifest_sha256,
        "source_observation_sha256":m["source_observation_sha256"],
        "condition_policy_sha256":m["condition_rules_ref"],
        "exchange_policy_sha256":m["exchange_reference_sha256"],
        "quote_policy_sha256":m["quote_condition_rules_sha256"],
        "counts":counters,
        "notional_usd":{k:notional[k].to_eng_string() for k in _NOTIONAL_KEYS},
        "volume_shares":{k:shares[k].to_eng_string() for k in _SHARE_KEYS},
        "lit_quoted_notional_coverage":coverage,
        "unknown_reason_counts":reasons,
        "lit_unknown_reason_counts":age_reasons,
        "price_response_bps":None,
        "absorption_signal":None,
    }
    packed=(json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False)
            +"\n").encode("utf-8")
    if len(packed)>MAX_PAYLOAD_BYTES:
        raise PrivateMinuteRefusal("derived private artifact exceeds byte budget")
    return {
        "schema":"equity.tick_plane.private_artifact_receipt/v0",
        "state":"NOT_PUBLISHED",
        "authority":"PRIVATE_DERIVED_HANDOFF_ONLY",
        "content_type":"application/json",
        "sha256":hashlib.sha256(packed).hexdigest(),
        "byte_length":len(packed),
        "bytes_private_only":packed,
        "is_public_delivery_authorized":False,
        "source_custody_proven":False,
    }


def verify_private_minute_bytes(*, expected_sha256, expected_byte_length, blob):
    """Strict bounded local readback. Does not retrieve, publish or grant access."""
    _digest(expected_sha256,"expected_sha256")
    _nonnegative_int(expected_byte_length,"expected_byte_length")
    if type(blob) is not bytes or len(blob)!=expected_byte_length or len(blob)>MAX_PAYLOAD_BYTES:
        raise PrivateMinuteRefusal("artifact readback byte length invalid")
    if hashlib.sha256(blob).hexdigest()!=expected_sha256:
        raise PrivateMinuteRefusal("artifact content digest mismatch")
    try:
        record=json.loads(blob.decode("utf-8"))
    except (ValueError,UnicodeDecodeError) as exc:
        raise PrivateMinuteRefusal("artifact JSON invalid") from exc
    if (not isinstance(record,dict) or record.get("schema")!=SCHEMA
            or record.get("public_delivery_allowed") is not False
            or record.get("rank_trade_alert_authority") is not False
            or record.get("absorption_signal") is not None
            or record.get("source_authenticity")!="EXTERNAL_INCUMBENT_PROOF_REQUIRED"
            or record.get("distribution_class")!="PRIVATE_SERVICE_HOLD_PENDING_LICENSE_AND_CONSUMER_REVIEW"):
        raise PrivateMinuteRefusal("artifact distribution/authority not permitted")
    if (json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)
            +"\n").encode("utf-8")!=blob:
        raise PrivateMinuteRefusal("artifact canonical bytes mismatched")
    return record
