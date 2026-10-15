"""A13 comparison-guard tests: stale FX, closed-market, and proxy refusals.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings (Stock Identity / Data OS) and never mint issuer or security ids.
HISTORICAL-DESCRIPTIVE only: rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority and trade_authority stay literal
False. Fixtures are synthetic. Proxy stays proxy by the instrument_role
field, never by ticker.

This module does not register, validate, or feed a ranker, gate, sizer,
signal, escalation, or trade path.
"""
from __future__ import annotations

import ast
import copy
import math
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research" / "single_name_intelligence" / "common"))

from sni_comparison_guard import (  # noqa: E402
    AUTHORITY_FLAGS,
    INSTRUMENT_ROLES,
    REASONS,
    SESSION_STATES_KNOWN,
    SESSION_STATES_TRADING,
    ComparisonVerdict,
    check_comparison,
    refuse_nonfalse_authority,
)

MODULE_PATH = (
    ROOT
    / "research"
    / "single_name_intelligence"
    / "common"
    / "sni_comparison_guard.py"
)

FLAG_NAMES = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AS_OF = "2026-06-15T16:00:00+00:00"
PRICE_TS = "2026-06-15T15:30:00+00:00"
KNOWN_AT = "2026-06-15T15:31:00+00:00"

NON_TRADING_STATES = tuple(
    state for state in SESSION_STATES_KNOWN if state not in SESSION_STATES_TRADING
)


class _Omit:
    pass


_OMIT = _Omit()


def _leg(**overrides):
    body = {
        "issuer_id": "SYN-ISSUER-1",
        "instrument_role": "target",
        "price": 100.0,
        "price_ts": PRICE_TS,
        "currency": "USD",
        "session_state": "continuous",
        "known_at": KNOWN_AT,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _fx(**overrides):
    body = {
        "base": "USD",
        "quote": "HKD",
        "rate": 7.8,
        "rate_ts": PRICE_TS,
        "known_at": KNOWN_AT,
    }
    body.update(overrides)
    drop = [key for key, val in body.items() if val is _OMIT]
    for key in drop:
        del body[key]
    return body


def _same_ccy():
    left = _leg()
    right = _leg(price=101.5)
    return left, right, None


def _cross_ccy():
    left = _leg()
    right = _leg(price=780.0, currency="HKD")
    return left, right, _fx()


def _check(left, right, fx, **kwargs):
    params = {
        "as_of": AS_OF,
        "max_fx_staleness_seconds": 300,
        "max_price_skew_seconds": 60,
        "requested_role": "target",
    }
    params.update(kwargs)
    return check_comparison(left, right, fx, **params)


def _assert_contract(verdict: ComparisonVerdict) -> None:
    for code in verdict.reasons:
        assert code in REASONS, (code, verdict.reasons)
    assert verdict.reasons == tuple(code for code in REASONS if code in verdict.reasons)
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
        assert verdict.authority_flags[name] is not True
    if verdict.allowed:
        assert verdict.reasons == ()
    else:
        assert verdict.reasons


def _assert_allowed(verdict: ComparisonVerdict) -> None:
    assert verdict.allowed is True, verdict.reasons
    assert verdict.reasons == ()
    _assert_contract(verdict)


def _assert_refused(verdict: ComparisonVerdict, *codes: str) -> None:
    assert verdict.allowed is False, verdict
    got = set(verdict.reasons)
    for code in codes:
        assert code in got, (code, verdict.reasons)
    _assert_contract(verdict)


def _assert_only(verdict: ComparisonVerdict, *codes: str) -> None:
    _assert_refused(verdict, *codes)
    assert set(verdict.reasons) == set(codes), verdict.reasons


# ---------------------------------------------------------------------------
# Positive controls
# ---------------------------------------------------------------------------


def test_same_currency_pair_with_fx_none_allowed():
    left, right, fx = _same_ccy()
    _assert_allowed(_check(left, right, fx))


def test_cross_currency_pair_with_fresh_fx_allowed():
    left, right, fx = _cross_ccy()
    _assert_allowed(_check(left, right, fx))


def test_fx_age_exactly_max_fx_staleness_seconds_allowed():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate_ts"] = "2026-06-15T15:25:00+00:00"
    _assert_allowed(_check(left, right, fx, max_fx_staleness_seconds=300))


def test_fx_age_one_second_over_max_is_fx_stale():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate_ts"] = "2026-06-15T15:24:59+00:00"
    _assert_only(_check(left, right, fx, max_fx_staleness_seconds=300), "FX_STALE")


def test_price_skew_exactly_max_price_skew_seconds_allowed():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["price_ts"] = "2026-06-15T15:31:00+00:00"
    _assert_allowed(_check(left, right, fx, max_price_skew_seconds=60))


def test_price_skew_one_second_over_max_is_price_skew():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["price_ts"] = "2026-06-15T15:31:01+00:00"
    _assert_only(_check(left, right, fx, max_price_skew_seconds=60), "PRICE_SKEW")


def test_closing_auction_session_is_trading_allowed():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    right = copy.deepcopy(right)
    left["session_state"] = "closing_auction"
    right["session_state"] = "closing_auction"
    _assert_allowed(_check(left, right, fx))


def test_reversed_fx_pair_base_quote_swapped_is_accepted():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["base"] = "HKD"
    fx["quote"] = "USD"
    _assert_allowed(_check(left, right, fx))


def test_zulu_timestamps_are_timezone_aware_and_allowed():
    left = _leg(price_ts="2026-06-15T15:30:00Z", known_at="2026-06-15T15:31:00Z")
    right = _leg(
        price=101.5, price_ts="2026-06-15T15:30:00Z", known_at="2026-06-15T15:31:00Z"
    )
    _assert_allowed(_check(left, right, None, as_of="2026-06-15T16:00:00Z"))


def test_same_currency_applies_no_fx_reasons_even_if_fx_supplied():
    left, right, _ = _same_ccy()
    bad_fx = _fx(rate=0, rate_ts="1999-01-01T00:00:00+00:00", base="EUR", quote="GBP")
    _assert_allowed(_check(left, right, bad_fx))


# ---------------------------------------------------------------------------
# Dedicated single-flip tests (one per REASONS entry)
# ---------------------------------------------------------------------------


def test_single_flip_price_missing():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = None
    _assert_only(_check(left, right, fx), "PRICE_MISSING")


def test_single_flip_price_ts_missing():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price_ts"] = None
    _assert_only(_check(left, right, fx), "PRICE_TS_MISSING")


def test_single_flip_price_nonfinite():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = -1
    _assert_only(_check(left, right, fx), "PRICE_NONFINITE")


def test_single_flip_session_state_unknown():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["session_state"] = "open_outcry"
    _assert_only(_check(left, right, fx), "SESSION_STATE_UNKNOWN")


def test_single_flip_session_not_trading():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["session_state"] = "closed"
    _assert_only(_check(left, right, fx), "SESSION_NOT_TRADING")


def test_single_flip_fx_missing():
    left, right, _ = _cross_ccy()
    _assert_only(_check(left, right, None), "FX_MISSING")


def test_single_flip_fx_ts_missing():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate_ts"] = None
    _assert_only(_check(left, right, fx), "FX_TS_MISSING")


def test_single_flip_fx_nonfinite():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate"] = 0
    _assert_only(_check(left, right, fx), "FX_NONFINITE")


def test_single_flip_fx_stale():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate_ts"] = "2026-06-15T15:24:59+00:00"
    _assert_only(_check(left, right, fx), "FX_STALE")


def test_single_flip_price_skew():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["price_ts"] = "2026-06-15T15:31:01+00:00"
    _assert_only(_check(left, right, fx), "PRICE_SKEW")


def test_single_flip_currency_pair_mismatch():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["base"] = "EUR"
    fx["quote"] = "GBP"
    _assert_only(_check(left, right, fx), "CURRENCY_PAIR_MISMATCH")


def test_single_flip_role_unknown():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["instrument_role"] = "hedge"
    _assert_only(_check(left, right, fx), "ROLE_UNKNOWN")


def test_single_flip_proxy_as_target():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["instrument_role"] = "proxy"
    _assert_only(_check(left, right, fx), "PROXY_AS_TARGET")


def test_single_flip_issuer_mismatch():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["issuer_id"] = "SYN-ISSUER-2"
    _assert_only(_check(left, right, fx), "ISSUER_MISMATCH")


def test_single_flip_not_known_as_of():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["known_at"] = "2026-06-15T16:00:01+00:00"
    _assert_only(_check(left, right, fx), "NOT_KNOWN_AS_OF")


# ---------------------------------------------------------------------------
# Session states
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("session_state", NON_TRADING_STATES)
def test_every_non_trading_session_state_refuses_session_not_trading(session_state):
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["session_state"] = session_state
    _assert_only(_check(left, right, fx), "SESSION_NOT_TRADING")


def test_session_state_unknown_does_not_also_emit_session_not_trading():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["session_state"] = "overnight"
    verdict = _check(left, right, fx)
    _assert_only(verdict, "SESSION_STATE_UNKNOWN")
    assert "SESSION_NOT_TRADING" not in verdict.reasons


def test_blank_session_state_is_session_state_unknown():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["session_state"] = None
    _assert_only(_check(left, right, fx), "SESSION_STATE_UNKNOWN")


# ---------------------------------------------------------------------------
# Adversarial prices and rates
# ---------------------------------------------------------------------------


def test_adversarial_price_true_refused():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = True
    _assert_only(_check(left, right, fx), "PRICE_NONFINITE")


def test_adversarial_price_string_refused():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = "100"
    _assert_only(_check(left, right, fx), "PRICE_NONFINITE")


def test_adversarial_price_zero_refused():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = 0
    _assert_only(_check(left, right, fx), "PRICE_NONFINITE")


def test_adversarial_price_negative_refused():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = -1
    _assert_only(_check(left, right, fx), "PRICE_NONFINITE")


def test_adversarial_price_nan_refused():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = float("nan")
    _assert_only(_check(left, right, fx), "PRICE_NONFINITE")


def test_adversarial_price_inf_refused():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = float("inf")
    _assert_only(_check(left, right, fx), "PRICE_NONFINITE")


def test_adversarial_rate_true_refused():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate"] = True
    _assert_only(_check(left, right, fx), "FX_NONFINITE")


def test_adversarial_rate_string_refused():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate"] = "100"
    _assert_only(_check(left, right, fx), "FX_NONFINITE")


def test_adversarial_rate_zero_refused():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate"] = 0
    _assert_only(_check(left, right, fx), "FX_NONFINITE")


def test_adversarial_rate_negative_refused():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate"] = -1
    _assert_only(_check(left, right, fx), "FX_NONFINITE")


def test_adversarial_rate_nan_refused():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate"] = float("nan")
    _assert_only(_check(left, right, fx), "FX_NONFINITE")


def test_adversarial_rate_inf_refused():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate"] = float("inf")
    _assert_only(_check(left, right, fx), "FX_NONFINITE")


def test_adversarial_naive_price_ts_refused():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price_ts"] = "2026-06-15T15:30:00"
    _assert_only(_check(left, right, fx), "PRICE_TS_MISSING")


def test_adversarial_naive_fx_rate_ts_refused():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["rate_ts"] = "2026-06-15T15:30:00"
    _assert_only(_check(left, right, fx), "FX_TS_MISSING")


def test_adversarial_issuer_trailing_space_mismatch():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["issuer_id"] = "SYN-ISSUER-1 "
    _assert_only(_check(left, right, fx), "ISSUER_MISMATCH")


def test_adversarial_issuer_case_mismatch():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["issuer_id"] = "syn-issuer-1"
    _assert_only(_check(left, right, fx), "ISSUER_MISMATCH")


def test_adversarial_issuer_cyrillic_lookalike_mismatch():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    right = copy.deepcopy(right)
    left["issuer_id"] = "SYN-ISSUER-A"
    right["issuer_id"] = "SYN-ISSUER-\u0410"
    _assert_only(_check(left, right, fx), "ISSUER_MISMATCH")


def test_adversarial_role_target_wrong_case_is_role_unknown():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["instrument_role"] = "Target"
    _assert_only(_check(left, right, fx), "ROLE_UNKNOWN")


def test_adversarial_proxy_role_requested_role_target_is_proxy_as_target():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["instrument_role"] = "proxy"
    _assert_only(_check(left, right, fx, requested_role="target"), "PROXY_AS_TARGET")


# ---------------------------------------------------------------------------
# Roles, issuers, then-known
# ---------------------------------------------------------------------------


def test_blank_issuer_id_on_target_role_is_issuer_mismatch():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    right = copy.deepcopy(right)
    left["issuer_id"] = ""
    right["issuer_id"] = ""
    _assert_only(_check(left, right, fx, requested_role="target"), "ISSUER_MISMATCH")


def test_none_issuer_id_on_one_target_leg_is_issuer_mismatch():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["issuer_id"] = None
    _assert_only(_check(left, right, fx, requested_role="target"), "ISSUER_MISMATCH")


def test_proxy_stays_proxy_field_driven_not_ticker_driven():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["instrument_role"] = "proxy"
    left["price"] = 42.0
    left["currency"] = "USD"
    verdict = _check(left, right, fx, requested_role="target")
    _assert_only(verdict, "PROXY_AS_TARGET")
    assert "ROLE_UNKNOWN" not in verdict.reasons


def test_requested_role_proxy_does_not_emit_proxy_as_target():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    right = copy.deepcopy(right)
    left["instrument_role"] = "proxy"
    right["instrument_role"] = "proxy"
    _assert_allowed(_check(left, right, fx, requested_role="proxy"))


def test_fx_known_at_later_than_as_of_is_not_known_as_of():
    left, right, fx = _cross_ccy()
    fx = copy.deepcopy(fx)
    fx["known_at"] = "2026-06-15T16:00:01+00:00"
    _assert_only(_check(left, right, fx), "NOT_KNOWN_AS_OF")


def test_unparseable_price_ts_is_price_ts_missing():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price_ts"] = "not-a-timestamp"
    _assert_only(_check(left, right, fx), "PRICE_TS_MISSING")


def test_unparseable_known_at_is_not_known_as_of():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["known_at"] = "later-than-clock"
    _assert_only(_check(left, right, fx), "NOT_KNOWN_AS_OF")


def test_empty_price_string_is_price_missing():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    left["price"] = ""
    _assert_only(_check(left, right, fx), "PRICE_MISSING")


# ---------------------------------------------------------------------------
# Accumulation, order, either-leg
# ---------------------------------------------------------------------------


def test_accumulate_every_applicable_reason_no_short_circuit():
    left = _leg(price=None, session_state="closed", instrument_role="proxy")
    right = _leg(price=101.5, issuer_id="SYN-ISSUER-2", session_state="halted")
    verdict = _check(left, right, None)
    _assert_refused(
        verdict,
        "PRICE_MISSING",
        "SESSION_NOT_TRADING",
        "PROXY_AS_TARGET",
        "ISSUER_MISMATCH",
    )
    assert verdict.reasons == tuple(
        code
        for code in REASONS
        if code
        in {
            "PRICE_MISSING",
            "SESSION_NOT_TRADING",
            "PROXY_AS_TARGET",
            "ISSUER_MISMATCH",
        }
    )


def test_fx_stale_when_either_leg_exceeds_staleness():
    left, right, fx = _cross_ccy()
    right = copy.deepcopy(right)
    fx = copy.deepcopy(fx)
    right["price_ts"] = "2026-06-15T15:30:30+00:00"
    fx["rate_ts"] = "2026-06-15T15:25:29+00:00"
    verdict = _check(
        left, right, fx, max_fx_staleness_seconds=300, max_price_skew_seconds=60
    )
    _assert_only(verdict, "FX_STALE")


def test_right_leg_defects_are_accumulated():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["price"] = math.nan
    right["session_state"] = "holiday"
    _assert_refused(_check(left, right, fx), "PRICE_NONFINITE", "SESSION_NOT_TRADING")


def test_reasons_deduplicated_in_reasons_tuple_order():
    left = _leg(session_state="closed", instrument_role="proxy")
    right = _leg(price=101.5, session_state="closed", instrument_role="proxy")
    verdict = _check(left, right, None)
    _assert_refused(verdict, "SESSION_NOT_TRADING", "PROXY_AS_TARGET")
    assert verdict.reasons.count("SESSION_NOT_TRADING") == 1
    assert verdict.reasons.count("PROXY_AS_TARGET") == 1
    assert verdict.reasons == ("SESSION_NOT_TRADING", "PROXY_AS_TARGET")


def test_allowed_is_true_iff_reasons_empty():
    left, right, fx = _same_ccy()
    ok = _check(left, right, fx)
    _assert_allowed(ok)
    assert ok.allowed is True
    bad = _check(_leg(price=None), right, fx)
    assert bad.allowed is False
    assert bad.reasons != ()


def test_price_skew_refuses_even_when_session_state_is_trading():
    left, right, fx = _same_ccy()
    right = copy.deepcopy(right)
    right["session_state"] = "continuous"
    right["price_ts"] = "2026-06-15T15:40:00+00:00"
    _assert_only(_check(left, right, fx, max_price_skew_seconds=60), "PRICE_SKEW")


def test_known_at_equal_to_as_of_is_allowed():
    left, right, fx = _same_ccy()
    left = copy.deepcopy(left)
    right = copy.deepcopy(right)
    left["known_at"] = AS_OF
    right["known_at"] = AS_OF
    _assert_allowed(_check(left, right, fx))


def test_instrument_roles_and_session_tuples_match_contract():
    assert SESSION_STATES_TRADING == ("continuous", "closing_auction")
    assert SESSION_STATES_KNOWN == (
        "pre_open",
        "continuous",
        "lunch_break",
        "closing_auction",
        "closed",
        "halted",
        "suspended",
        "holiday",
    )
    assert INSTRUMENT_ROLES == ("target", "proxy")
    assert REASONS == (
        "PRICE_MISSING",
        "PRICE_TS_MISSING",
        "PRICE_NONFINITE",
        "SESSION_STATE_UNKNOWN",
        "SESSION_NOT_TRADING",
        "FX_MISSING",
        "FX_TS_MISSING",
        "FX_NONFINITE",
        "FX_STALE",
        "PRICE_SKEW",
        "CURRENCY_PAIR_MISMATCH",
        "ROLE_UNKNOWN",
        "PROXY_AS_TARGET",
        "ISSUER_MISMATCH",
        "NOT_KNOWN_AS_OF",
    )


# ---------------------------------------------------------------------------
# Authority
# ---------------------------------------------------------------------------


def test_authority_flags_immutable_and_all_literal_false():
    for name in FLAG_NAMES:
        assert AUTHORITY_FLAGS[name] is False
        assert AUTHORITY_FLAGS[name] is not True
    with pytest.raises(TypeError):
        AUTHORITY_FLAGS["rank_authority"] = True
    left, right, fx = _same_ccy()
    verdict = _check(left, right, fx)
    for name in FLAG_NAMES:
        assert verdict.authority_flags[name] is False
    refused = _check(_leg(price=None), right, fx)
    for name in FLAG_NAMES:
        assert refused.authority_flags[name] is False


def test_refuse_nonfalse_authority_raises_on_true_zero_none_false_string():
    refuse_nonfalse_authority()
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    refuse_nonfalse_authority(dict(AUTHORITY_FLAGS))
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"rank_authority": True})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"gate_authority": 0})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"size_authority": None})
    with pytest.raises(ValueError):
        refuse_nonfalse_authority({"signal_authority": "false"})


def test_verdict_authority_flags_property_is_module_flags():
    left, right, fx = _same_ccy()
    verdict = _check(left, right, fx)
    assert verdict.authority_flags is AUTHORITY_FLAGS
    frozen = ComparisonVerdict(allowed=True, reasons=())
    assert frozen.authority_flags is AUTHORITY_FLAGS
    assert frozen.allowed is True


def test_verdict_coerces_allowed_from_reasons():
    coerced = ComparisonVerdict(allowed=True, reasons=("PRICE_MISSING",))
    assert coerced.allowed is False
    assert coerced.reasons == ("PRICE_MISSING",)
    empty = ComparisonVerdict(allowed=False, reasons=())
    assert empty.allowed is True
    assert empty.reasons == ()


# ---------------------------------------------------------------------------
# Static source contract
# ---------------------------------------------------------------------------


def test_module_source_has_every_reason_no_tickers_no_clock():
    source = MODULE_PATH.read_text(encoding="utf-8")
    for code in REASONS:
        assert code in source, code
    forbidden = (
        "BABA",
        "TCEHY",
        "KWEB",
        "AAPL",
        "MSFT",
        "NVDA",
        "GOOGL",
        "AMZN",
        "META",
        "TSLA",
    )
    for token in forbidden:
        assert token not in source, token
    assert re.search(r"\b\d{4,5}\.HK\b", source) is None
    assert "datetime.now" not in source
    assert "time.time" not in source
    tree = ast.parse(source)
    clock_hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in {"now", "utcnow", "time"}:
            clock_hits.append((getattr(func, "attr", None), getattr(node, "lineno", None)))
        if isinstance(func, ast.Name) and func.id in {"now", "time"}:
            clock_hits.append((func.id, getattr(node, "lineno", None)))
    assert clock_hits == [], clock_hits
    fn_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "check_comparison" in fn_names
    assert "refuse_nonfalse_authority" in fn_names
