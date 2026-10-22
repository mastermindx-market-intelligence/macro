"""Deterministic falsifiers for qualified completed-bar confirmation.

All source-owner callbacks here are explicit fixtures, NOT production source proof.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from engine.market_navigator import ContractError, Receipt, Scenario, Condition, compose
from engine.market_navigator_price_confirmation import ClosedBar, LevelRule, inspect, qualified_observation

START = datetime(2026, 10, 21, 14, 0, tzinfo=timezone.utc)
CUTOFF = datetime(2026, 10, 21, 14, 30, tzinfo=timezone.utc)
END = datetime(2026, 10, 23, 20, 0, tzinfo=timezone.utc)


def utc(dt):
    return dt.isoformat().replace("+00:00", "Z")


def make_bars(closes, *, horizon="intraday", first=10, sessions=None):
    bars = []
    for i, close in enumerate(closes):
        start = START + timedelta(minutes=5*i)
        previous = float(closes[i-1]) if i else float(close)
        close = float(close)
        bars.append(ClosedBar(
            subject="SPY:ARCX", horizon=horizon, generation_ref="generation:one",
            receipt_ref=f"owner:receipt:{i}", revision="revision:one",
            session_ref=(sessions or ["session:one"]*len(closes))[i],
            sequence=first+i, begins_at=utc(start),
            ends_at=utc(start+timedelta(minutes=5)),
            available_at=utc(start+timedelta(minutes=6)),
            valid_until=utc(END),
            open=previous, high=max(previous, close)+0.5,
            low=min(previous, close)-0.5, close=close, unit="USD", completed=True,
        ))
    return tuple(bars)


def make_rule(event="cross_above", minimum_bars=2):
    return LevelRule("SPY:ARCX", "intraday", event, 100.0, "USD",
                     minimum_bars, "definition:user-source-original",
                     utc(START-timedelta(days=1)), utc(END))


def run(closes, event="cross_above", *, rule=None, bars=None, verifier=None,
        expected=None, as_of=utc(CUTOFF)):
    bars = make_bars(closes) if bars is None else bars
    rule = make_rule(event) if rule is None else rule
    return inspect(rule=rule, as_of=as_of, bars=bars,
                   expected_last_sequence=(bars[-1].sequence if expected is None and bars else expected),
                   verify_owner=(lambda *_: True) if verifier is None else verifier)


@pytest.mark.parametrize("event,closes,met", [
    ("cross_above", [99, 100.5, 101], True),
    ("cross_above", [100, 100.5, 101], True),
    ("cross_above", [99, 100, 101], False),
    ("cross_above", [101, 102, 103], False),
    ("cross_above", [99, 100.1, 99.9], False),
    ("cross_below", [101, 99.5, 99], True),
    ("cross_below", [100, 99.5, 99], True),
    ("cross_below", [101, 100, 99], False),
    ("cross_below", [99, 98, 97], False),
    ("hold_above", [101, 102], True),
    ("hold_above", [100, 102], False),
    ("hold_below", [99, 98], True),
    ("hold_below", [100, 98], False),
])
def test_exact_mathematical_confirmation(event, closes, met):
    result = run(closes, event)
    assert result["condition_met"] is met
    assert result["status"] == ("confirmed" if met else "not_confirmed")
    assert result["source_verified"] is True
    assert result["is_trading_signal"] is False and result["probability"] is None
    assert not any(result["authority"].values())


def test_lookback_three_bars_and_limited_window():
    rule = make_rule(minimum_bars=3)
    assert run([80, 99, 100.1, 102, 101],rule=rule)["status"] == "confirmed"
    assert run([80, 99, 100.1, 102],rule=rule)["status"] == "not_confirmed"
    assert run([99, 101, 102],rule=rule)["status"] == "coverage_incomplete"


@pytest.mark.parametrize("mutated,status", [
    (lambda b: replace(b, completed=False), "incomplete_bar"),
    (lambda b: replace(b, available_at="2026-10-22T14:15:00Z",
                       valid_until="2026-10-25T14:15:00Z"), "not_yet_available"),
    (lambda b: replace(b, valid_until="2026-10-21T14:29:00Z"), "expired_source_revision"),
    (lambda b: replace(b, subject="META:XNAS"), "subject_horizon_or_unit_mismatch"),
    (lambda b: replace(b, horizon="swing"), "subject_horizon_or_unit_mismatch"),
    (lambda b: replace(b, unit="index_points"), "subject_horizon_or_unit_mismatch"),
    (lambda b: replace(b, generation_ref="gen:old"), "mixed_generation"),
    (lambda b: replace(b, sequence=b.sequence+1), "noncontiguous_owner_sequence"),
    (lambda b: replace(b, begins_at="2026-10-21T14:08:00Z"), "noncontiguous_owner_sequence"),
    (lambda b: replace(b, session_ref="new-session"), "intraday_session_boundary"),
])
def test_unavailable_or_misaligned_bar_abstains(mutated,status):
    bars = make_bars([99, 101, 102])
    bars = bars[:-1]+(mutated(bars[-1]),)
    outcome=run([],bars=bars,expected=bars[-1].sequence)
    assert outcome["status"]==status, outcome
    assert outcome["condition_met"] is None and not outcome["source_verified"]


def test_source_bar_fills_a_later_index_while_expected_latest_is_missing():
    bars=make_bars([99, 101, 102])
    assert run([],bars=bars,expected=14)["status"] == "latest_expected_bar_missing"


def test_no_expected_owner_sequence_never_claims_confirmation():
    bars=make_bars([99, 101, 102])
    out=inspect(rule=make_rule(),as_of=utc(CUTOFF),bars=bars,verify_owner=lambda *_:True)
    assert out["status"]=="coverage_incomplete"


def test_missing_verifier_or_denied_verifier_abstains():
    bars=make_bars([99,101,102])
    args=dict(rule=make_rule(),as_of=utc(CUTOFF),bars=bars,expected_last_sequence=12)
    assert inspect(**args)["status"]=="owner_verification_missing"
    for verifier in (lambda *_: False, lambda *_:"true", lambda *_:None,
                     lambda *_: (_ for _ in ()).throw(PermissionError("source denied")),
                     lambda *_: (_ for _ in ()).throw(OSError("offline"))):
        result=inspect(**args,verify_owner=verifier)
        assert result["status"]=="owner_verification_failed" and result["condition_met"] is None


def test_expired_or_future_rule_never_rewrites_original_definition():
    bars=make_bars([99,101,102])
    assert run([],bars=bars,as_of=utc(END))["status"]=="expired"
    late=replace(make_rule(),definition_available_at=utc(CUTOFF+timedelta(minutes=1)))
    with pytest.raises(ContractError, match="was not known"):
        run([],bars=bars,rule=late)


def test_completed_bar_receipts_before_as_of_and_no_future_measurement():
    bars=make_bars([99,101,102])
    assert run([],bars=bars,as_of=utc(START+timedelta(minutes=14)))["status"]=="incomplete_bar"
    one=replace(bars[-1], available_at="2026-10-21T14:28:00Z",
                valid_until="2026-10-24T14:28:00Z")
    assert run([],bars=bars[:-1]+(one,),as_of="2026-10-21T14:20:00Z")["status"]=="not_yet_available"


def test_no_hour_difference_assumption_for_daily_market_calendar():
    bars=make_bars([99,101,102],horizon="swing")
    stretched=tuple(replace(b,session_ref=f"session:{i}",
                            begins_at=utc(START+timedelta(days=2*i)),
                            ends_at=utc(START+timedelta(days=2*i, minutes=5)),
                            available_at=utc(START+timedelta(days=2*i, minutes=6)),
                            valid_until=utc(START+timedelta(days=14)))
                    for i,b in enumerate(bars))
    rule=replace(make_rule(),horizon="swing",deadline=utc(START+timedelta(days=15)))
    result=run([],bars=stretched,rule=rule,as_of=utc(START+timedelta(days=5)))
    assert result["status"]=="confirmed"


@pytest.mark.parametrize("bad", [
    dict(open=0),dict(high=0),dict(low=0),dict(close=float("nan")),
    dict(close=float("inf")),dict(open=True),dict(sequence=1.2),dict(sequence=-1),
    dict(completed="true"),dict(unit="contracts"),dict(subject=""),
    dict(available_at="2026-10-21T14:03:00Z"),
    dict(begins_at="2026-10-21"),dict(high=99),
])
def test_bad_bar_is_refused(bad):
    with pytest.raises(ContractError):
        replace(make_bars([101])[0],**bad)


@pytest.mark.parametrize("bad", [
    dict(minimum_bars=1),dict(minimum_bars=17),dict(minimum_bars=True),
    dict(event="weekly"),dict(level=0),dict(level=float("inf")),
    dict(unit="contracts"),dict(horizon="unsupported"),dict(rule_ref=""),
    dict(definition_available_at=utc(END)),
])
def test_invalid_rule_is_refused(bad):
    with pytest.raises(ContractError):
        replace(make_rule(),**bad)


def test_bounded_inputs_no_unknown_or_untyped_bars():
    with pytest.raises(ContractError):
        inspect(rule=make_rule(), as_of=utc(CUTOFF), bars=make_bars([101])*65)
    with pytest.raises(ContractError):
        inspect(rule=make_rule(), as_of=utc(CUTOFF), bars=[1,2,3])
    with pytest.raises(ContractError):
        inspect(rule=make_rule(), as_of=utc(CUTOFF), bars=(1,2,3))
    with pytest.raises(ContractError):
        inspect(rule=make_rule(), as_of=utc(CUTOFF), bars=make_bars([99,101,102]),
                expected_last_sequence=True)


def test_results_are_serializable_and_do_not_expose_data_or_trade_capability():
    out=run([99,101,102])
    assert not any(out["authority"].values())
    assert out["bar_count"]==3
    assert "SPY:ARCX" not in json.dumps(out)
    assert "generation:one" not in json.dumps(out)
    assert "definition:user-source-original" not in json.dumps(out)
    assert len(out["subject_binding_sha256"]) == 64
    assert len(out["generation_sha256"]) == 64
    assert out["last_qualified_bar_end"]==make_bars([99,101,102])[-1].ends_at

def derived_receipt(bars):
    last=bars[-1]
    return Receipt("owner:derived-price-event",last.generation_ref,
                   last.ends_at,last.available_at,last.available_at,utc(END))


def test_evidence_composes_into_existing_scenario_without_providing_trade_authority():
    bars=make_bars([99,101,102])
    obs=qualified_observation(rule=make_rule(),as_of=utc(CUTOFF),
        bars=bars,expected_last_sequence=12,verify_owner=lambda *_:True,
        receipt=derived_receipt(bars),key="confirmed_reclaim")
    assert obs is not None and obs.value==1.0 and obs.unit=="ratio"
    scenario=Scenario(key="level_reclaim",subject="SPY:ARCX",horizon="intraday",
        definition_available_at=utc(START-timedelta(days=1)),
        definition_ref="user:rule-original",deadline=utc(END),
        triggers=(Condition("confirmed_reclaim","gte",1.0,"ratio"),),
        invalidations=(Condition("confirmed_reclaim","lt",1.0,"ratio"),),
        support=("confirmed_reclaim",),counterevidence=())
    state=compose(subject="SPY:ARCX",horizon="intraday",as_of=utc(CUTOFF),
                  observations=(obs,),scenarios=(scenario,))
    assert state["scenarios"][0]["status"]=="conditions_met"
    assert state["observations"][0]["value"]==1.0
    assert not any(state["authority"].values())
    assert state["readiness"]=="research_only"


def test_nonconfirmation_is_never_missing_or_probability():
    bars=make_bars([101,102,103])
    obs=qualified_observation(rule=make_rule(),as_of=utc(CUTOFF),
        bars=bars,expected_last_sequence=12,verify_owner=lambda *_:True,
        receipt=derived_receipt(bars),key="confirmed_reclaim")
    assert obs is not None and obs.value==0.0 and obs.quality=="observed"


def test_unverified_or_too_short_sequence_cannot_become_zero_observation():
    bars=make_bars([99,101,102])
    inputs=dict(rule=make_rule(),as_of=utc(CUTOFF),bars=bars,
                expected_last_sequence=12,receipt=derived_receipt(bars),key="reclaim")
    assert qualified_observation(**inputs,verify_owner=lambda *_:False) is None
    assert qualified_observation(**{**inputs,"bars":bars[-2:]},
        verify_owner=lambda *_:True) is None


@pytest.mark.parametrize("bad", [
    lambda r: replace(r,observed_at="2026-10-21T14:10:00Z"),
    lambda r: replace(r,revision="different:generation"),
    lambda r: replace(r,available_at="2026-10-21T14:14:00Z"),
    lambda r: replace(r,valid_until="2026-10-24T20:00:00Z"),
])
def test_derived_receipt_must_not_change_identity_or_extend_validity(bad):
    bars=make_bars([99,101,102])
    with pytest.raises(ContractError):
        qualified_observation(rule=make_rule(),as_of=utc(CUTOFF),bars=bars,
            expected_last_sequence=12,verify_owner=lambda *_:True,
            receipt=bad(derived_receipt(bars)),key="reclaim")


def test_expired_derived_receipt_refuses_an_observation():
    bars=make_bars([99,101,102])
    receipt=replace(derived_receipt(bars),valid_until="2026-10-21T14:29:00Z")
    assert qualified_observation(rule=make_rule(),as_of=utc(CUTOFF),bars=bars,
            expected_last_sequence=12,verify_owner=lambda *_:True,
            receipt=receipt,key="reclaim") is None
