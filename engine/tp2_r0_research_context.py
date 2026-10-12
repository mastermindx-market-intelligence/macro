"""Optional PRIVATE TP-2 observational sidecar for the now-merged R0 source.

Accept ONLY an *already canonically verified* R0 private research body, via
engine.market_microstructure.private_context_view.verify_private_research_context_bytes.
No original bytes, quote/signing reimplementation, data source, R2 writer,
authorization service, RTH controller, price prediction or trading authority.

This is a distinct candidate schema, not a breaking edit to the accepted
darkpool.tp2_private_offexchange_view/v0 and its frozen byte artifact.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation, localcontext
from zoneinfo import ZoneInfo

SCHEMA = "darkpool.tp2_r0_observed_research/v0"
_SOURCE_SCHEMA = "equity.pressure_response.private_context_view/v0"
_PRIVATE_KEYS = frozenset((
    "schema", "source_schema", "distribution_class",
    "public_delivery_allowed", "rank_trade_alert_authority",
    "source_authenticity", "market_capture_completeness",
    "ticker", "session", "start_ns", "end_ns", "decision_ns",
    "source_quote_age_limit_ns", "source_manifest_sha256",
    "source_manifest_name_sha256", "source_watermark_receipt_sha256",
    "minute_observations_sha256", "quote_observations_sha256",
    "source_condition_rules_sha256", "source_exchange_rules_sha256",
    "source_quote_condition_rules_sha256", "n_observations",
    "notional_usd", "classified_notional_coverage",
    "pressure_balance", "completed_window_midpoint_response_bps",
    "bid_size_recovery_proxy", "ask_size_recovery_proxy",
    "absorption_signal", "forward_label",
))
_SHA = re.compile(r"^[0-9a-f]{64}$")
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.\-]{0,19}$")
_SESSION = re.compile(r"^\d{4}-\d{2}-\d{2}:RTH$")
_FIXED = re.compile(r"^-?(?:0|[1-9]\d*)(?:\.\d+)?$")
_MINUTE_NS = 60_000_000_000
_MAX_CLOCK = (1 << 63) - 1
_MAX_SIGNED_CHARS = 544
_COUNTS = frozenset((
    "n_source_minute_packets", "n_sampled_prints", "n_unclassified",
    "n_quote_updates", "n_quote_condition_unqualified",
))
_AMOUNT_NAMES = frozenset((
    "gross_sampled_notional_usd", "buy_proxy_notional_usd",
    "sell_proxy_notional_usd", "midpoint_notional_usd",
    "unknown_notional_usd", "ineligible_notional_usd",
    "trf_gross_notional_usd",
))
_PROXY_STATES = ("UNKNOWN",
                 "MEASURED_NBBO_SIZE_PROXY_NOT_ORDER_REPLENISHMENT")


class TP2R0Refusal(ValueError):
    """A source/authority contradiction is not neutral pressure."""


def _clock(v, label):
    if type(v) is not int or not 0 < v <= _MAX_CLOCK:
        raise TP2R0Refusal(f"R0 {label}: native nanoseconds invalid")
    return v


def _sha(v, label):
    if type(v) is not str or _SHA.fullmatch(v) is None:
        raise TP2R0Refusal(f"R0 {label}: original receipt digest invalid")
    return v


def _decimal(v, label, *, signed=False, zero=True):
    if (type(v) is not str or not 0 < len(v) <= _MAX_SIGNED_CHARS
            or _FIXED.fullmatch(v) is None):
        raise TP2R0Refusal(f"R0 {label}: source decimal invalid")
    try:
        result = Decimal(v)
    except InvalidOperation as exc:
        raise TP2R0Refusal(f"R0 {label}: malformed source decimal") from exc
    if not result.is_finite() or (result < 0 and not signed) or (not zero and result == 0):
        raise TP2R0Refusal(f"R0 {label}: nonfinite/invalid source decimal")
    return result


def _hold(now, state, source=None, body=None):
    return {
        "schema": SCHEMA,
        "state": state,
        "authority": "PRIVATE_R0_RESEARCH_CONTEXT_HOLD",
        "view_asof_ns_decimal": str(now),
        "source_start_ns_decimal": str(source["start_ns"]) if source else None,
        "source_end_ns_decimal": str(source["end_ns"]) if source else None,
        "source_decision_ns_decimal": str(source["decision_ns"]) if source else None,
        "ticker": source["ticker"] if source else None,
        "session": source["session"] if source else None,
        "source_manifest_sha256": (
            source["source_manifest_sha256"] if source else None),
        "source_minutes_receipt_sha256": (
            source["minute_observations_sha256"] if source else None),
        "source_quotes_receipt_sha256": (
            source["quote_observations_sha256"] if source else None),
        "observed_proxy": body,
        "join_to_tp1_or_tpb": False,
        "source_authenticated": False,
        "public_delivery_allowed": False,
        "rank_trade_alert_authority": False,
        "forward_label": None,
        "absorption_signal": None,
    }


def project_tp2_r0_observation(*, source_context, view_asof_ns,
                               expected_ticker=None, expected_session=None):
    """Project a separate R0 as-seen read; never join estimates to trading data.

    The original R0 private verifier/source operator owns original bytes, raw
    snapshot/quote lineage and permissions. This bounded independent reader
    checks only consumer presentation/knowability; no vendor auth implied.
    """
    now = _clock(view_asof_ns, "view_asof_ns")
    if source_context is None:
        return _hold(now, "R0_CONTEXT_NOT_SUPPLIED")
    m = source_context
    if not isinstance(m, dict) or set(m) != _PRIVATE_KEYS:
        raise TP2R0Refusal("R0 source shape/exact fields invalid")
    if (m["schema"] != _SOURCE_SCHEMA
            or m["source_schema"] != "equity.pressure_response.tp1_context/v0"
            or m["distribution_class"] != "PRIVATE_SERVICE_HOLD_PENDING_LICENSE_REVIEW"
            or m["public_delivery_allowed"] is not False
            or m["rank_trade_alert_authority"] is not False
            or m["source_authenticity"] !=
               "ORIGINAL_TQ_RECEIPTS_REQUIRE_EXTERNAL_OWNER_PROOF"
            or m["market_capture_completeness"] !=
               "NOT_PROVEN_BY_RESEARCH_MATH"
            or m["forward_label"] is not None
            or m["absorption_signal"] is not None):
        raise TP2R0Refusal("R0 source or authority cannot become a live signal")
    ticker, session = m["ticker"], m["session"]
    if (type(ticker) is not str or _SYMBOL.fullmatch(ticker) is None
            or type(session) is not str or _SESSION.fullmatch(session) is None):
        raise TP2R0Refusal("R0 source identity invalid")
    if ((expected_ticker is not None and expected_ticker != ticker)
            or (expected_session is not None and expected_session != session)):
        raise TP2R0Refusal("R0 source identity disagrees with requested context")
    try:
        day = date.fromisoformat(session[:10])
    except ValueError as exc:
        raise TP2R0Refusal("R0 source session date invalid") from exc
    expected_open_ns = int(datetime.combine(
        day, time(9, 30), tzinfo=ZoneInfo("America/New_York")
    ).timestamp()) * 1_000_000_000
    start = _clock(m["start_ns"], "start_ns")
    end = _clock(m["end_ns"], "end_ns")
    decision = _clock(m["decision_ns"], "decision_ns")
    if (start < expected_open_ns or start % _MINUTE_NS
            or not start < end <= expected_open_ns + 390*_MINUTE_NS
            or (end-start) % _MINUTE_NS
            or not 1 <= (end-start)//_MINUTE_NS <= 5
            or decision < end):
        raise TP2R0Refusal("R0 original RTH source window/decision invalid")
    if decision > now:
        # Before decision neither minute/quote digest nor ticker even exists
        # in an as-seen research presentation.
        return _hold(now, "R0_CONTEXT_NOT_YET_KNOWABLE")
    _clock(m["source_quote_age_limit_ns"], "source_quote_age_limit_ns")
    for k in ("source_manifest_sha256", "source_manifest_name_sha256",
              "source_watermark_receipt_sha256",
              "minute_observations_sha256", "quote_observations_sha256",
              "source_condition_rules_sha256", "source_exchange_rules_sha256",
              "source_quote_condition_rules_sha256"):
        _sha(m[k], k)
    counts = m["n_observations"]
    if not isinstance(counts, dict) or set(counts) != _COUNTS:
        raise TP2R0Refusal("R0 source counts missing/extra fields")
    if any(type(n) is not int or not 0 <= n <= 100000 for n in counts.values()):
        raise TP2R0Refusal("R0 source counts unbounded")
    if (counts["n_source_minute_packets"] != (end-start)//_MINUTE_NS
            or counts["n_sampled_prints"] < 1
            or counts["n_unclassified"] > counts["n_sampled_prints"]
            or counts["n_quote_condition_unqualified"] > counts["n_quote_updates"]):
        raise TP2R0Refusal("R0 source counts inconsistent")
    notional = m["notional_usd"]
    if not isinstance(notional, dict) or set(notional) != _AMOUNT_NAMES:
        raise TP2R0Refusal("R0 original notional allowlist invalid")
    amounts = {k: _decimal(v, k) for k, v in notional.items()}
    with localcontext() as ctx:
        ctx.prec = 2*_MAX_SIGNED_CHARS + 20
        components = sum(
            (amounts[k] for k in ("buy_proxy_notional_usd",
             "sell_proxy_notional_usd", "midpoint_notional_usd",
             "unknown_notional_usd", "ineligible_notional_usd")), Decimal(0))
    if (components != amounts["gross_sampled_notional_usd"]
            or amounts["trf_gross_notional_usd"] > amounts["unknown_notional_usd"]):
        raise TP2R0Refusal("R0 original research measurement notional inconsistent")
    for k in ("bid_size_recovery_proxy", "ask_size_recovery_proxy"):
        v = m[k]
        if not isinstance(v, dict) or v.get("state") not in _PROXY_STATES:
            raise TP2R0Refusal("R0 source replenishment proxy state invalid")
    pressure = m["pressure_balance"]
    coverage = m["classified_notional_coverage"]
    if pressure is not None and abs(_decimal(
            pressure, "pressure_balance", signed=True)) > 1:
        raise TP2R0Refusal("R0 pressure balance outside descriptive range")
    if coverage is not None and _decimal(
            coverage, "classified_notional_coverage") > 1:
        raise TP2R0Refusal("R0 classified coverage >100%")
    response = m["completed_window_midpoint_response_bps"]
    if response is not None:
        _decimal(response, "completed_window_midpoint_response_bps", signed=True)
    research = {
        "basis": "LIT_QUOTE_LOCATION_RESEARCH_PROXY_NOT_AGGRESSOR_TRUTH",
        "sampled_prints": counts["n_sampled_prints"],
        "unclassified_prints": counts["n_unclassified"],
        "source_minute_packets": counts["n_source_minute_packets"],
        "buy_proxy_notional_usd": notional["buy_proxy_notional_usd"],
        "sell_proxy_notional_usd": notional["sell_proxy_notional_usd"],
        "unknown_notional_usd": notional["unknown_notional_usd"],
        "classified_notional_coverage": coverage,
        "pressure_balance": pressure,
        "completed_window_midpoint_response_bps": response,
        "bid_size_recovery_state": m["bid_size_recovery_proxy"]["state"],
        "ask_size_recovery_state": m["ask_size_recovery_proxy"]["state"],
        "quote_age_policy_ns_decimal": str(m["source_quote_age_limit_ns"]),
        "price_response_kind": "SAME_COMPLETED_WINDOW_DESCRIPTIVE_NOT_FORWARD",
        "trade_side_accuracy_calibrated": False,
    }
    return _hold(now, "R0_OBSERVATIONAL_CONTEXT_HOLD", source=m, body=research)
