"""TP-1 scalar equity NBBO classifier: fail-closed, not actor identification."""

import numpy as np
import pytest

from engine.flow_signing import classify_print, quote_rule_sign


def args(**kw):
    row = dict(
        ticker="SPY", quote_ticker="SPY", session="2026-10-08:RTH",
        quote_session="2026-10-08:RTH", trade_price="100.90",
        bid="100.00", ask="101.00", trade_sip_ns=130,
        quote_sip_ns=120, trade_received_ns=131, quote_received_ns=121,
        decision_ns=150, max_quote_age_ns=20,
        trade_source_receipt="actual:trade:123", quote_source_receipt="actual:quote:45",
        eligible_for_pressure=True, condition_rules_ref="conditions:sha256:version",
        venue_class="LIT")
    row.update(kw)
    return row


@pytest.mark.parametrize("price,bucket,reason", [
    ("100.90", "buy", None), ("100.10", "sell", None),
    ("100.50", "mid", None), ("101.00", "buy", None),
    ("100.00", "sell", None), ("101.01", "unclassified", "OUTSIDE_NBBO"),
    ("99.99", "unclassified", "OUTSIDE_NBBO"),
])
def test_at_trade_quote_location_and_midpoint_are_exact(price, bucket, reason):
    got = classify_print(**args(trade_price=price))
    assert got["bucket"] == bucket
    assert got["reason"] == reason
    assert got["quote_age_ns"] == 10
    assert got["authority"] == "OBSERVATIONAL_ONLY"
    assert got["method"] == "SIP_NBBO_QUOTE_LOCATION_PROXY"


@pytest.mark.parametrize("field,value,expected", [
    ("ticker", "AAPL", "SOURCE_IDENTITY_MISMATCH"),
    ("quote_session", "2026-10-07:RTH", "SOURCE_IDENTITY_MISMATCH"),
    ("venue_class", "UNKNOWN", "VENUE_UNKNOWN"),
    ("venue_class", "BROKEN", "INVALID_VENUE_CLASS"),
    ("condition_rules_ref", None, "CONDITION_POLICY_UNKNOWN"),
    ("eligible_for_pressure", None, "CONDITION_ELIGIBILITY_UNKNOWN"),
    ("eligible_for_pressure", False, "CONDITION_INELIGIBLE"),
    ("trade_source_receipt", None, "ORIGINAL_RECEIPT_MISSING"),
    ("quote_source_receipt", "", "ORIGINAL_RECEIPT_MISSING"),
    ("quote_sip_ns", 130, "SIP_CLOCK_ORDER_UNQUALIFIED"),
    ("quote_sip_ns", 131, "SIP_CLOCK_ORDER_UNQUALIFIED"),
    ("quote_sip_ns", 90, "QUOTE_STALE"),
    ("quote_received_ns", 151, "NOT_KNOWN_AT_DECISION"),
    ("trade_received_ns", 151, "NOT_KNOWN_AT_DECISION"),
    ("quote_received_ns", 119, "IMPOSSIBLE_RECEIPT_CLOCK"),
    ("trade_received_ns", 129, "IMPOSSIBLE_RECEIPT_CLOCK"),
    ("trade_sip_ns", 130.0, "CLOCK_MISSING_OR_INVALID"),
    ("quote_sip_ns", True, "CLOCK_MISSING_OR_INVALID"),
    ("max_quote_age_ns", -1, "CLOCK_MISSING_OR_INVALID"),
])
def test_invalid_source_time_policy_and_identity_abstain(field, value, expected):
    got = classify_print(**args(**{field: value}))
    assert got["bucket"] == "unclassified"
    assert got["reason"] == expected


@pytest.mark.parametrize("bid,ask,price", [
    ("100", "100", "100"),
    ("101", "100", "100.5"),
    ("0", "101", "100.5"),
    ("100", "-1", "100.5"),
    ("100", "101", "NaN"),
    ("100", "Infinity", "100.9"),
    ("100", "101", "not a number"),
    (True, "101", "100.5"),
])
def test_invalid_or_crossed_nbbo_is_unknown(bid, ask, price):
    x = classify_print(**args(bid=bid, ask=ask, trade_price=price))
    assert x["bucket"] == "unclassified"
    assert x["reason"] == "INVALID_NBBO_OR_PRICE"


def test_trf_report_does_not_masquerade_as_execution_clock():
    q = classify_print(**args(venue_class="TRF", trade_price="100.9"))
    assert q["bucket"] == "unclassified"
    assert q["reason"] == "TRF_EXECUTION_CLOCK_UNQUALIFIED"
    assert q["quote_age_ns"] is None


def test_lit_classifier_does_not_change_legacy_options_quote_rule_sign():
    observed = quote_rule_sign([1.2, 0.8, 1.0], [0.9] * 3, [1.1] * 3,
                               [1.0, 1.0, 0.9])
    assert list(observed) == [1.0, -1.0, 1.0]
    assert quote_rule_sign([1.0], [0.9], [1.1])[0] == 0.0


def test_native_nanoseconds_remain_int64_scale_without_loss():
    start = 1_728_000_000_000_000_000
    got = classify_print(**args(
        quote_sip_ns=start, trade_sip_ns=start + 12,
        quote_received_ns=start + 1, trade_received_ns=start + 13,
        decision_ns=start + 50, max_quote_age_ns=20))
    assert got["bucket"] == "buy"
    assert got["quote_age_ns"] == 12


def test_price_floats_are_normalized_via_decimal_string_not_epsilon():
    a = classify_print(**args(trade_price=100.9))
    b = classify_print(**args(trade_price=100.5))
    assert a["bucket"] == "buy"
    assert b["bucket"] == "mid"
