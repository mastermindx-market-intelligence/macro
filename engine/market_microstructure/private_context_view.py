"""Serialize canonical TP-1/R0 observational context for a private service reader.

R0 owns measurement semantics. This pure function neither stores source frames,
publishes anything, grants data redistribution rights, nor creates a second
source/signing, auth, runtime, retry, background worker, or event lifecycle.

The allowed output is an observational VIEW of already-produced R0 context,
never new alpha, an order-level replenishment measurement, or a trade signal.
Python Decimal precision in quote-size recovery is preserved as strings.
"""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal, InvalidOperation

from engine.market_microstructure.tp1_context import SCHEMA as SOURCE_SCHEMA, MINUTE_NS

SCHEMA = "equity.pressure_response.private_context_view/v0"
MAX_BYTES = 24 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASONS = re.compile(r"^[A-Z][A-Z0-9_]{0,79}$")
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_SOURCE_FIELDS = frozenset((
    "schema","authority","ticker","session","start_ns","end_ns",
    "decision_ns","source_manifest","source_watermark_receipt",
    "correction_status","source_mode",
    "capture_completeness_proven_by_this_function",
    "absorption_signal","rank_authority","forward_outcome_label",
    "execution_adjusted_return",
    "state","reason","source_minutes_receipt_sha256",
    "source_quote_observations_sha256",
    "source_condition_rules_sha256","source_exchange_rules_sha256",
    "source_quote_condition_rules_sha256","source_quote_age_limit_ns",
    "n_source_minute_packets","n_sampled_prints","n_unclassified",
    "n_quote_updates","n_quote_condition_unqualified",
    "gross_sampled_notional_usd","buy_proxy_notional_usd",
    "sell_proxy_notional_usd","midpoint_notional_usd",
    "unknown_notional_usd","ineligible_notional_usd",
    "trf_gross_notional_usd","classified_notional_coverage",
    "pressure_balance","midpoint_response_bps",
    "bid_size_recovery","ask_size_recovery",
    "impact_relative_to_control","source_qualification",
))
_MONEY_FIELDS = (
    "gross_sampled_notional_usd","buy_proxy_notional_usd",
    "sell_proxy_notional_usd","midpoint_notional_usd",
    "unknown_notional_usd","ineligible_notional_usd",
    "trf_gross_notional_usd",
)
_RECV_FIELDS = frozenset((
    "state","depletion_shares","recovered_shares",
    "original_shares","final_shares","best_exchange","price",
))


class PrivateContextRefusal(ValueError):
    """Research context cannot be safely projected into the private reader."""


def _str(x,name):
    if not isinstance(x,str) or not x.strip() or len(x)>2048:
        raise PrivateContextRefusal(f"{name} requires original bounded text")
    return x


def _int(x,name):
    if type(x) is not int or x<0:
        raise PrivateContextRefusal(f"{name} must be nonnegative integer")
    return x


def _decimal(x,name,*,positive=False):
    if isinstance(x,bool) or not isinstance(x,(Decimal,int,str)):
        raise PrivateContextRefusal(f"{name} missing exact decimal quantity")
    try:
        d=Decimal(str(x))
    except InvalidOperation as exc:
        raise PrivateContextRefusal(f"{name} malformed decimal") from exc
    if not d.is_finite() or d<0 or (positive and d==0):
        raise PrivateContextRefusal(f"{name} invalid value")
    return format(d,"f")


def _signed(x,name):
    if not isinstance(x,str):
        raise PrivateContextRefusal(f"{name} requires signed decimal source string")
    try:
        d=Decimal(x)
    except InvalidOperation as exc:
        raise PrivateContextRefusal(f"{name} malformed signed decimal") from exc
    if not d.is_finite():
        raise PrivateContextRefusal(f"{name} nonfinite response")
    return format(d,"f")


def _sha(x,name):
    if not isinstance(x,str) or _SHA256.fullmatch(x) is None:
        raise PrivateContextRefusal(f"{name} requires exact source SHA256")
    return x


def _recovery(value,side):
    if not isinstance(value,dict):
        raise PrivateContextRefusal(f"{side} best-quote recovery not an object")
    state=value.get("state")
    if state=="UNKNOWN":
        if set(value)!={"state","reason"}:
            raise PrivateContextRefusal(f"{side} unclassified recovery shape invalid")
        reason=_str(value["reason"],side+".reason")
        if _REASONS.fullmatch(reason) is None:
            raise PrivateContextRefusal(f"{side} recovery reason untyped")
        return {"state":"UNKNOWN","reason":reason}
    if state!="MEASURED_PROXY" or set(value)!=_RECV_FIELDS:
        raise PrivateContextRefusal(f"{side} recovery has unauthorized state or fields")
    quantities={key:_decimal(value[key],side+"."+key) for key in (
        "depletion_shares","recovered_shares","original_shares","final_shares")}
    depleted=Decimal(quantities["depletion_shares"])
    recovered=Decimal(quantities["recovered_shares"])
    initial=Decimal(quantities["original_shares"])
    final=Decimal(quantities["final_shares"])
    if (depleted<=0 or initial<=0 or final<=0 or depleted>initial
            or final!=initial-depleted+recovered):
        raise PrivateContextRefusal(f"{side} recovery impossible observed depletion")
    price=_decimal(value["price"],side+".price",positive=True)
    venue=_str(value["best_exchange"],side+".best_exchange")
    if len(venue)>32:
        raise PrivateContextRefusal("source venue code too long for derived proxy")
    return {
        "state":"MEASURED_NBBO_SIZE_PROXY_NOT_ORDER_REPLENISHMENT",
        "depletion_shares":quantities["depletion_shares"],
        "recovered_shares":quantities["recovered_shares"],
        "original_shares":quantities["original_shares"],
        "final_shares":quantities["final_shares"],
        "source_best_exchange":venue,
        "source_best_price":price,
    }


def project_private_research_context(*, research_context, source_manifest_sha256):
    if not isinstance(research_context,dict) or set(research_context)!=_SOURCE_FIELDS:
        raise PrivateContextRefusal("unexpected raw/new research context fields")
    m=research_context
    if (m["schema"]!=SOURCE_SCHEMA
            or m["authority"]!="RESEARCH_CONTEXT_ONLY"
            or m["state"]!="PROVISIONAL_RESEARCH_CONTEXT"
            or m["reason"] is not None
            or m["correction_status"]!="STREAM_PROVISIONAL_UNRECONCILED"
            or m["source_mode"]!="AS_SEEN_REQUIRES_ORIGINAL_OWNER_PROOF"
            or m["source_qualification"]!="EXTERNAL_OWNER_RECEIPTS_REQUIRED"
            or m["capture_completeness_proven_by_this_function"] is not False
            or m["rank_authority"] is not False
            or any(m[k] is not None for k in (
                "absorption_signal","forward_outcome_label",
                "execution_adjusted_return","impact_relative_to_control",
            ))):
        raise PrivateContextRefusal("R0 source correction or trading authority invalid")
    ticker=_str(m["ticker"],"ticker")
    if _SYMBOL.fullmatch(ticker) is None:
        raise PrivateContextRefusal("invalid source ticker")
    session=_str(m["session"],"session")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}:RTH",session) is None:
        raise PrivateContextRefusal("private R0 pilot requires exact day and RTH session")
    from datetime import date
    try:
        date.fromisoformat(session.split(":",1)[0])
    except ValueError as exc:
        raise PrivateContextRefusal("R0 session date invalid") from exc
    start=_int(m["start_ns"],"start_ns")
    end=_int(m["end_ns"],"end_ns")
    decision=_int(m["decision_ns"],"decision_ns")
    if (start%MINUTE_NS or not start<end<=decision
            or (end-start)%MINUTE_NS or (end-start)>5*MINUTE_NS):
        raise PrivateContextRefusal("R0 window/cutoff does not match completed minutes")
    age=_int(m["source_quote_age_limit_ns"],"source_quote_age_limit_ns")
    counts={}
    for key in ("n_source_minute_packets","n_sampled_prints","n_unclassified",
                "n_quote_updates","n_quote_condition_unqualified"):
        counts[key]=_int(m[key],key)
    if (counts["n_source_minute_packets"]!=(end-start)//MINUTE_NS
            or counts["n_sampled_prints"]==0
            or counts["n_unclassified"]>counts["n_sampled_prints"]
            or counts["n_quote_condition_unqualified"]>counts["n_quote_updates"]):
        raise PrivateContextRefusal("R0 sampled/quote denominators conflict")
    notional={key:_decimal(m[key],key) for key in _MONEY_FIELDS}
    if sum((Decimal(notional[key]) for key in (
        "buy_proxy_notional_usd","sell_proxy_notional_usd",
        "midpoint_notional_usd","unknown_notional_usd",
        "ineligible_notional_usd")),Decimal(0)) != Decimal(notional["gross_sampled_notional_usd"]):
        raise PrivateContextRefusal("R0 source notional conservation failure")
    pressure=m["pressure_balance"]
    if pressure is not None:
        pressure=_signed(pressure,"pressure_balance")
        if Decimal(pressure)<-1 or Decimal(pressure)>1:
            raise PrivateContextRefusal("pressure outside bounded normalized range")
    coverage=m["classified_notional_coverage"]
    if coverage is not None:
        coverage=_decimal(coverage,"classified_notional_coverage")
        if Decimal(coverage)>1:
            raise PrivateContextRefusal("classified notional coverage exceeds one")
    response=_signed(m["midpoint_response_bps"],"midpoint_response_bps")
    for key in ("source_minutes_receipt_sha256","source_quote_observations_sha256",
                "source_condition_rules_sha256","source_exchange_rules_sha256",
                "source_quote_condition_rules_sha256"):
        _sha(m[key],key)
    _sha(source_manifest_sha256,"source_manifest_sha256")
    manifest=_str(m["source_manifest"],"source_manifest")
    watermark=_str(m["source_watermark_receipt"],"source_watermark_receipt")
    bid=_recovery(m["bid_size_recovery"],"bid")
    ask=_recovery(m["ask_size_recovery"],"ask")
    body={
        "schema":SCHEMA,"source_schema":SOURCE_SCHEMA,
        "distribution_class":"PRIVATE_SERVICE_HOLD_PENDING_LICENSE_REVIEW",
        "public_delivery_allowed":False,
        "rank_trade_alert_authority":False,
        "source_authenticity":"ORIGINAL_TQ_RECEIPTS_REQUIRE_EXTERNAL_OWNER_PROOF",
        "market_capture_completeness":"NOT_PROVEN_BY_RESEARCH_MATH",
        "ticker":ticker,"session":session,"start_ns":start,
        "end_ns":end,"decision_ns":decision,
        "source_quote_age_limit_ns":age,
        "source_manifest_sha256":source_manifest_sha256,
        "source_manifest_name_sha256":hashlib.sha256(manifest.encode()).hexdigest(),
        "source_watermark_receipt_sha256":hashlib.sha256(watermark.encode()).hexdigest(),
        "minute_observations_sha256":m["source_minutes_receipt_sha256"],
        "quote_observations_sha256":m["source_quote_observations_sha256"],
        "source_condition_rules_sha256":m["source_condition_rules_sha256"],
        "source_exchange_rules_sha256":m["source_exchange_rules_sha256"],
        "source_quote_condition_rules_sha256":m["source_quote_condition_rules_sha256"],
        "n_observations":counts,
        "notional_usd":notional,
        "classified_notional_coverage":coverage,
        "pressure_balance":pressure,
        "completed_window_midpoint_response_bps":response,
        "bid_size_recovery_proxy":bid,
        "ask_size_recovery_proxy":ask,
        "absorption_signal":None,
        "forward_label":None,
    }
    raw=(json.dumps(body,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")
    if len(raw)>MAX_BYTES:
        raise PrivateContextRefusal("private research context exceeds bounded representation")
    return {
        "schema":"equity.pressure_response.private_context_receipt/v0",
        "authority":"PRIVATE_RESEARCH_HANDOFF_ONLY",
        "state":"NOT_PUBLISHED",
        "source_claim":"EXTERNAL_OWNER_CUSTODY_REQUIRED",
        "sha256":hashlib.sha256(raw).hexdigest(),
        "content_length":len(raw),
        "bytes_private_only":raw,
        "public_delivery_allowed":False,
    }


_PRIVATE_KEYS = frozenset((
    "schema","source_schema","distribution_class","public_delivery_allowed",
    "rank_trade_alert_authority","source_authenticity",
    "market_capture_completeness","ticker","session","start_ns","end_ns",
    "decision_ns","source_quote_age_limit_ns","source_manifest_sha256",
    "source_manifest_name_sha256","source_watermark_receipt_sha256",
    "minute_observations_sha256","quote_observations_sha256",
    "source_condition_rules_sha256","source_exchange_rules_sha256",
    "source_quote_condition_rules_sha256","n_observations","notional_usd",
    "classified_notional_coverage","pressure_balance",
    "completed_window_midpoint_response_bps","bid_size_recovery_proxy",
    "ask_size_recovery_proxy","absorption_signal","forward_label",
))
_PRIVATE_COUNTER_KEYS = frozenset((
    "n_source_minute_packets","n_sampled_prints","n_unclassified",
    "n_quote_updates","n_quote_condition_unqualified",
))
_PRIVATE_RECOVERY_KEYS = frozenset((
    "state","depletion_shares","recovered_shares","original_shares",
    "final_shares","source_best_exchange","source_best_price",
))


def verify_private_research_context_bytes(*, expected_sha256, expected_byte_length, blob):
    """Validate an exact private *content* readback; never authenticate source.

    The actual private store, authorization, vendor rights and private object
    routing belong to incumbent operators. A matching SHA alone is insufficient
    to make altered or raw fields safe for consumer distribution.
    """
    _sha(expected_sha256,"expected_sha256")
    _int(expected_byte_length,"expected_byte_length")
    if type(blob) is not bytes or not 0 < len(blob) <= MAX_BYTES:
        raise PrivateContextRefusal("invalid bounded private research bytes")
    if len(blob)!=expected_byte_length:
        raise PrivateContextRefusal("private research readback byte length differs")
    if hashlib.sha256(blob).hexdigest()!=expected_sha256:
        raise PrivateContextRefusal("private research readback digest mismatch")

    def reject_nonfinite(text):
        raise PrivateContextRefusal("JSON nonfinite constant may not enter private source data")

    def reject_float(text):
        raise PrivateContextRefusal("JSON native float may not enter private source data")

    try:
        record=json.loads(blob.decode("utf-8"),
                          parse_constant=reject_nonfinite,
                          parse_float=reject_float)
    except PrivateContextRefusal:
        raise
    except (UnicodeDecodeError,ValueError) as exc:
        raise PrivateContextRefusal("malformed private source JSON") from exc
    if (not isinstance(record,dict)
            or set(record)!=_PRIVATE_KEYS
            or record.get("schema")!=SCHEMA
            or record.get("source_schema")!=SOURCE_SCHEMA
            or record.get("distribution_class")!="PRIVATE_SERVICE_HOLD_PENDING_LICENSE_REVIEW"
            or record.get("public_delivery_allowed") is not False
            or record.get("rank_trade_alert_authority") is not False
            or record.get("source_authenticity")!="ORIGINAL_TQ_RECEIPTS_REQUIRE_EXTERNAL_OWNER_PROOF"
            or record.get("market_capture_completeness")!="NOT_PROVEN_BY_RESEARCH_MATH"
            or record.get("absorption_signal") is not None
            or record.get("forward_label") is not None):
        raise PrivateContextRefusal("private research payload shape/authority invalid")

    ticker=_str(record.get("ticker"),"ticker")
    session=_str(record.get("session"),"session")
    if _SYMBOL.fullmatch(ticker) is None or re.fullmatch(r"\d{4}-\d{2}-\d{2}:RTH",session) is None:
        raise PrivateContextRefusal("private research symbol/session invalid")
    from datetime import date
    try:
        date.fromisoformat(session[:10])
    except ValueError as exc:
        raise PrivateContextRefusal("private research session date invalid") from exc
    start=_int(record.get("start_ns"),"start_ns")
    end=_int(record.get("end_ns"),"end_ns")
    cutoff=_int(record.get("decision_ns"),"decision_ns")
    _int(record.get("source_quote_age_limit_ns"),"source_quote_age_limit_ns")
    if (start%MINUTE_NS or not start<end<=cutoff
            or (end-start)%MINUTE_NS or (end-start)>5*MINUTE_NS):
        raise PrivateContextRefusal("private research window or cutoff invalid")
    for field in (
        "source_manifest_sha256","source_manifest_name_sha256",
        "source_watermark_receipt_sha256","minute_observations_sha256",
        "quote_observations_sha256","source_condition_rules_sha256",
        "source_exchange_rules_sha256","source_quote_condition_rules_sha256",
    ):
        _sha(record.get(field),field)
    counts=record.get("n_observations")
    notional=record.get("notional_usd")
    if (not isinstance(counts,dict) or set(counts)!=_PRIVATE_COUNTER_KEYS
            or not isinstance(notional,dict) or set(notional)!=set(_MONEY_FIELDS)):
        raise PrivateContextRefusal("private research nested fields outside allowlist")
    for key in _PRIVATE_COUNTER_KEYS:
        _int(counts[key],key)
    if (counts["n_source_minute_packets"]!=(end-start)//MINUTE_NS
            or counts["n_sampled_prints"]==0
            or counts["n_unclassified"]>counts["n_sampled_prints"]
            or counts["n_quote_condition_unqualified"]>counts["n_quote_updates"]):
        raise PrivateContextRefusal("private research count denominators inconsistent")
    money={key:Decimal(_decimal(notional[key],key)) for key in _MONEY_FIELDS}
    if (money["buy_proxy_notional_usd"]+money["sell_proxy_notional_usd"]
            +money["midpoint_notional_usd"]+money["unknown_notional_usd"]
            +money["ineligible_notional_usd"]!=money["gross_sampled_notional_usd"]):
        raise PrivateContextRefusal("private research notional conservation invalid")
    for key in ("classified_notional_coverage","pressure_balance"):
        val=record.get(key)
        if val is not None:
            dec=Decimal(_signed(val,key)) if key=="pressure_balance" else Decimal(_decimal(val,key))
            if (dec < -1 if key=="pressure_balance" else dec < 0) or dec>1:
                raise PrivateContextRefusal("private research ratio exceeds valid range")
    _signed(record.get("completed_window_midpoint_response_bps"),"midpoint_response_bps")
    for side in ("bid","ask"):
        proxy=record.get(side+"_size_recovery_proxy")
        if not isinstance(proxy,dict):
            raise PrivateContextRefusal("private source recovery proxy invalid")
        if proxy.get("state")=="UNKNOWN":
            if (set(proxy)!={"state","reason"}
                    or not isinstance(proxy.get("reason"),str)
                    or _REASONS.fullmatch(proxy["reason"]) is None):
                raise PrivateContextRefusal("private source recovery abstention invalid")
        elif proxy.get("state")=="MEASURED_NBBO_SIZE_PROXY_NOT_ORDER_REPLENISHMENT":
            if set(proxy)!=_PRIVATE_RECOVERY_KEYS:
                raise PrivateContextRefusal("private source recovery has extra fields")
            initial=Decimal(_decimal(proxy["original_shares"],"original_shares",positive=True))
            final=Decimal(_decimal(proxy["final_shares"],"final_shares",positive=True))
            depleted=Decimal(_decimal(proxy["depletion_shares"],"depletion_shares",positive=True))
            recovered=Decimal(_decimal(proxy["recovered_shares"],"recovered_shares"))
            _decimal(proxy["source_best_price"],"source_best_price",positive=True)
            venue=proxy.get("source_best_exchange")
            if (not isinstance(venue,str)
                    or re.fullmatch(r"[0-9]{1,5}",venue) is None):
                raise PrivateContextRefusal("private source recovery venue not an exchange code")
            if depleted>initial or final!=initial-depleted+recovered:
                raise PrivateContextRefusal("private source recovery amount inconsistent")
        else:
            raise PrivateContextRefusal("private source recovery label unknown")

    canonical=(json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")
    if canonical!=blob:
        raise PrivateContextRefusal("private source JSON readback is noncanonical")
    return record
