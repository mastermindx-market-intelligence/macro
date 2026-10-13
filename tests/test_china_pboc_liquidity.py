"""Synthetic tests for the typed PBOC liquidity read. No store, no network."""
from __future__ import annotations

import datetime
import inspect
import json

import pytest

from engine.china_pboc_liquidity import (
    LABELS,
    SCHEMA,
    FutureDatedInput,
    LiquidityInputs,
    OmoDay,
    classify_liquidity,
)

ASOF = datetime.date(2026, 10, 13)
STATES = (
    "insufficient_data",
    "zero_op_ample",
    "zero_op_tight",
    "rollover",
    "net_support",
    "net_drain",
)


def _day(offset: int, injection, maturity, op_count, *, asof: datetime.date = ASOF) -> OmoDay:
    return OmoDay(
        date=asof + datetime.timedelta(days=offset),
        injection_cny_bn=injection,
        maturity_cny_bn=maturity,
        op_count=op_count,
    )


def _span(start: int, n: int, injection, maturity, op_count) -> list[OmoDay]:
    return [_day(start + i, injection, maturity, op_count) for i in range(n)]


def _read(days, *, mlf=0.0, fr007=1.8, policy=1.8, source="synthetic", asof=ASOF, **kw):
    got = classify_liquidity(
        LiquidityInputs(
            asof=asof,
            window=tuple(days),
            mlf_net_cny_bn=mlf,
            fr007_pct=fr007,
            policy_rate_7d_pct=policy,
            source=source,
        ),
        **kw,
    )
    assert got.schema == SCHEMA
    assert got.state in LABELS
    assert got.source == source
    return got


def test_state_insufficient_data_when_fewer_than_three_days_are_observed():
    got = _read(_span(-4, 5, None, None, None))
    assert got.state == "insufficient_data"
    assert got.stale is False
    assert got.days_observed == 0
    assert got.days_missing == 5
    assert got.reasons == ("fewer_than_3_observed", "partial_window")
    assert got.net_cny_bn == 0.0


def test_state_zero_op_ample():
    got = _read(_span(-4, 5, 0.0, 0.0, 0))
    assert got.state == "zero_op_ample"
    assert got.spread_bp == 0.0
    assert got.stale is False
    assert got.days_observed == 5
    assert got.days_missing == 0
    assert got.reasons == ()
    assert got.net_cny_bn == 0.0
    assert LABELS[got.state]["en"] == "Quiet: no operations, money is ample"
    assert LABELS[got.state]["zh"] == "无操作：资金充裕"


def test_zero_op_ample_even_when_money_is_maturing():
    # Announced quiet days stay quiet. Maturities stay in the net figure.
    got = _read(_span(-4, 5, 0.0, 40.0, 0))
    assert got.state == "zero_op_ample"
    assert got.gross_injection_cny_bn == 0.0
    assert got.gross_maturity_cny_bn == 200.0
    assert got.net_cny_bn == -200.0


def test_state_zero_op_tight():
    got = _read(_span(-4, 5, 0, 0, 0), fr007=1.5, policy=1.0)
    assert got.state == "zero_op_tight"
    assert got.spread_bp == 50.0
    assert got.reasons == ()


def test_zero_op_spread_boundary_is_inclusive():
    days = _span(-4, 5, 0.0, 0.0, 0)
    at_band = _read(days, fr007=1.5, policy=1.0, tight_spread_bp=50.0)
    above_band = _read(days, fr007=1.5, policy=1.0, tight_spread_bp=49.0)
    assert at_band.spread_bp == 50.0
    assert at_band.state == "zero_op_ample"
    assert above_band.state == "zero_op_tight"


def test_zero_op_without_spread_is_insufficient():
    got = _read(_span(-4, 5, 0.0, 0.0, 0), fr007=None, policy=1.8)
    assert got.state == "insufficient_data"
    assert got.stale is False
    assert got.days_observed == 5
    assert got.spread_bp is None
    assert got.reasons == ("spread_unknown", "zero_op_spread_unknown")


def test_state_rollover():
    got = _read(_span(-4, 5, 0.0, 0.0, 1))
    assert got.state == "rollover"
    assert got.net_cny_bn == 0.0
    assert got.reasons == ()


def test_state_net_support():
    got = _read(_span(-4, 5, 2.0, 0.0, 1))
    assert got.state == "net_support"
    assert got.gross_injection_cny_bn == 10.0
    assert got.gross_maturity_cny_bn == 0.0
    assert got.net_cny_bn == 10.0


def test_state_net_drain():
    got = _read(_span(-4, 5, 0.0, 2.0, 1))
    assert got.state == "net_drain"
    assert got.net_cny_bn == -10.0
    assert got.gross_maturity_cny_bn == 10.0


def test_valid_zero_is_not_the_same_as_missing():
    zeros_int = _span(-4, 5, 0, 0, 0)
    zeros_float = _span(-4, 5, 0.0, 0.0, 0)
    missing = _span(-4, 5, None, None, None)
    announced = _read(zeros_int)
    announced_float = _read(zeros_float)
    blank = _read(missing)
    assert announced.state == announced_float.state == "zero_op_ample"
    assert announced.to_dict() == announced_float.to_dict()
    assert blank.state == "insufficient_data"
    assert blank.days_observed == 0
    assert blank.days_missing == 5
    assert "partial_window" in blank.reasons
    assert announced.days_observed == 5


def test_partial_window_adds_reason_and_skips_incomplete_amounts():
    quiet = _span(-4, 4, 0.0, 0.0, 0) + [_day(0, None, None, None)]
    got = _read(quiet)
    assert got.state == "zero_op_ample"
    assert got.reasons == ("partial_window",)
    assert got.days_observed == 4
    assert got.days_missing == 1

    # injection is present, maturity is not: the day is missing, and 100 is unused.
    partial_amount = _span(-4, 3, 1.0, 0.0, 1) + [
        _day(-1, 100.0, None, 1),
        _day(0, None, None, None),
    ]
    summed = _read(partial_amount)
    assert summed.days_observed == 3
    assert summed.days_missing == 2
    assert summed.gross_injection_cny_bn == 3.0
    assert summed.net_cny_bn == 3.0
    assert "partial_window" in summed.reasons
    assert summed.state == "rollover"


def test_future_dated_entry_raises():
    days = _span(-4, 5, 0.0, 0.0, 0) + [_day(1, 0.0, 0.0, 0)]
    with pytest.raises(FutureDatedInput):
        _read(days)
    assert issubclass(FutureDatedInput, ValueError)
    # The same as-of date is allowed.
    assert _read([_day(0, 0.0, 0.0, 0), *_span(-4, 2, 0.0, 0.0, 0)]).state == "zero_op_ample"


def test_stale_latest_date_is_insufficient():
    # Gap of 4 calendar days is still fresh. Gap of 5 is stale.
    fresh = _span(-8, 5, 2.0, 0.0, 1)
    fresh_read = _read(fresh)
    assert fresh_read.stale is False
    assert fresh_read.state == "net_support"
    assert (ASOF - fresh[-1].date).days == 4

    stale_days = _span(-9, 5, 2.0, 0.0, 1)
    got = _read(stale_days)
    assert (ASOF - stale_days[-1].date).days == 5
    assert got.stale is True
    assert got.state == "insufficient_data"
    assert got.reasons == ("stale",)
    assert got.days_observed == 5
    assert got.net_cny_bn == 10.0


def test_no_entries_is_stale_insufficient():
    got = _read(())
    assert got.stale is True
    assert got.state == "insufficient_data"
    assert got.days_observed == 0
    assert got.days_missing == 0
    assert got.reasons == ("stale", "fewer_than_3_observed")


def test_mlf_unknown_keeps_omo_only_net():
    days = _span(-4, 5, 3.0, 1.0, 1)
    unknown = _read(days, mlf=None)
    known_zero = _read(days, mlf=0.0)
    known_plus = _read(days, mlf=4.0)
    assert unknown.net_cny_bn == 10.0
    assert known_zero.net_cny_bn == unknown.net_cny_bn
    assert known_plus.net_cny_bn == 14.0
    assert unknown.reasons == ("mlf_unknown",)
    assert "mlf_unknown" not in known_zero.reasons
    assert unknown.gross_injection_cny_bn == 15.0
    assert unknown.gross_maturity_cny_bn == 5.0


def test_negative_values_raise():
    with pytest.raises(ValueError):
        _day(0, -0.1, 0.0, 1)
    with pytest.raises(ValueError):
        _day(0, 0.0, -1.0, 1)
    with pytest.raises(ValueError):
        _day(0, 0.0, 0.0, -1)
    # An unobserved injection beside a zero operation count is incomplete, not illegal.
    held = _day(0, None, None, 0)
    assert held.op_count == 0
    assert held.injection_cny_bn is None


def test_inconsistent_op_count_raises():
    with pytest.raises(ValueError, match="inconsistent bulletin"):
        _day(0, 1.0, 0.0, 0)
    allowed = _day(0, 0.0, 5.0, 0)
    assert allowed.op_count == 0
    assert allowed.maturity_cny_bn == 5.0


def test_duplicate_dates_raise():
    days = [_day(0, 0.0, 0.0, 0), _day(0, 1.0, 0.0, 1), _day(-1, 0.0, 0.0, 0)]
    with pytest.raises(ValueError, match="duplicate") as exc_info:
        _read(days)
    assert not isinstance(exc_info.value, FutureDatedInput)


def test_rollover_boundary_is_inclusive():
    def _net(injection_last: float, maturity_last: float):
        days = _span(-4, 4, 0.0, 0.0, 1) + [_day(0, injection_last, maturity_last, 1)]
        return _read(days)

    assert _net(5.0, 0.0).net_cny_bn == 5.0
    assert _net(5.0, 0.0).state == "rollover"
    assert _net(0.0, 5.0).net_cny_bn == -5.0
    assert _net(0.0, 5.0).state == "rollover"
    assert _net(6.0, 0.0).state == "net_support"
    assert _net(0.0, 6.0).state == "net_drain"

    # Relative band dominates: 10% of 100 is 10, which is above the absolute 5.
    relative = _read(_span(-4, 5, 22.0, 20.0, 1))
    assert relative.gross_maturity_cny_bn == 100.0
    assert relative.net_cny_bn == 10.0
    assert relative.state == "rollover"
    just_over = _read(_span(-4, 4, 22.0, 20.0, 1) + [_day(0, 23.0, 20.0, 1)])
    assert just_over.net_cny_bn == 11.0
    assert just_over.state == "net_support"


def test_last_window_days_are_kept_by_date():
    older = _day(-10, 1000.0, 0.0, 1)
    recent = _span(-4, 5, 0.0, 0.0, 0)
    dropped = _read([recent[-1], older, *recent[:-1]])
    assert dropped.state == "zero_op_ample"
    assert dropped.gross_injection_cny_bn == 0.0
    assert dropped.days_observed == 5
    kept = _read([older, *recent], window_days=6)
    assert kept.gross_injection_cny_bn == 1000.0
    assert kept.state == "net_support"
    assert _read(recent).to_dict() == dropped.to_dict()


def test_non_positive_window_days_keeps_nothing():
    days = _span(-4, 5, 2.0, 0.0, 1)
    empty = _read(days, window_days=0)
    assert empty.stale is True
    assert empty.days_observed == 0
    assert empty.state == "insufficient_data"
    with pytest.raises(ValueError, match="window_days"):
        _read(days, window_days=-1)


def test_to_dict_is_deterministic_and_json_safe():
    days = _span(-4, 4, 0.0, 0.0, 0) + [_day(0, None, None, None)]
    first = _read(days, mlf=None, fr007=1.5, policy=1.0, source="fixture")
    second = _read(days, mlf=None, fr007=1.5, policy=1.0, source="fixture")
    assert first.to_dict() == second.to_dict()
    payload = first.to_dict()
    encoded = json.dumps(payload)
    assert encoded == json.dumps(second.to_dict())
    decoded = json.loads(encoded)
    assert decoded["schema"] == SCHEMA
    assert decoded["asof"] == "2026-10-13"
    assert decoded["state"] == "zero_op_tight"
    assert decoded["reasons"] == ["partial_window", "mlf_unknown"]
    assert decoded["spread_bp"] == 50.0
    assert decoded["stale"] is False
    assert set(payload) == {
        "schema",
        "asof",
        "state",
        "net_cny_bn",
        "gross_injection_cny_bn",
        "gross_maturity_cny_bn",
        "spread_bp",
        "stale",
        "days_observed",
        "days_missing",
        "reasons",
        "source",
    }
    for value in payload.values():
        assert not isinstance(value, tuple)
        assert not isinstance(value, datetime.date)


def test_labels_cover_six_states_in_plain_words():
    assert set(LABELS) == set(STATES)
    for state in STATES:
        labels = LABELS[state]
        assert set(labels) == {"en", "zh"}
        assert labels["en"].strip()
        assert labels["zh"].strip()
        blob = (labels["en"] + labels["zh"]).upper()
        assert "OMO" not in blob
        assert "MLF" not in blob


def test_signature_defaults_match_the_spec():
    sig = inspect.signature(classify_liquidity)
    assert list(sig.parameters) == [
        "inputs",
        "window_days",
        "tight_spread_bp",
        "rollover_abs_cny_bn",
        "rollover_rel",
        "stale_after_days",
    ]
    assert sig.parameters["inputs"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in (
        "window_days",
        "tight_spread_bp",
        "rollover_abs_cny_bn",
        "rollover_rel",
        "stale_after_days",
    ):
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["window_days"].default == 5
    assert sig.parameters["tight_spread_bp"].default == 15.0
    assert sig.parameters["rollover_abs_cny_bn"].default == 5.0
    assert sig.parameters["rollover_rel"].default == 0.10
    assert sig.parameters["stale_after_days"].default == 4
