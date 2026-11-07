"""Falsifiers for mathematical outcome inspection; all fixtures are synthetic."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from engine.market_navigator import ContractError
from engine.market_navigator_price_confirmation import ClosedBar
from engine.market_navigator_outcomes import OutcomeCase, inspect_case

T0=datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
CLAIM="a"*64
EPISODE="b"*64


def clock(dt):
    return dt.isoformat().replace("+00:00","Z")


def rule(kind="level_touch", operator="gte", threshold=100):
    return OutcomeCase(
        claim_id=CLAIM,episode_id=EPISODE,rule_ref="owner:original:ruler:1",
        subject="SPY:ARCX",horizon="intraday",
        original_rule_available_at=clock(T0-timedelta(days=1)),
        decision_at=clock(T0),deadline=clock(T0+timedelta(minutes=30)),
        kind=kind,operator=operator,threshold=threshold,unit="USD",
    )


def bars(closes=(99,101,102), first=40):
    data=[]
    for i,close in enumerate(closes):
        begin=T0+timedelta(minutes=5*(i+1))
        prev=closes[i-1] if i else close
        data.append(ClosedBar(
            subject="SPY:ARCX",horizon="intraday",generation_ref="owner:bar-generation-1",
            receipt_ref=f"owner:bar:{i}",revision="owner:vintage:1",
            session_ref="owner:session:20261021",
            sequence=first+i,begins_at=clock(begin),
            ends_at=clock(begin+timedelta(minutes=5)),
            available_at=clock(begin+timedelta(minutes=6)),
            valid_until=clock(T0+timedelta(days=1)),
            open=prev,high=max(prev,close)+0.5,
            low=min(prev,close)-0.5,close=close,unit="USD",
            completed=True,
        ))
    return tuple(data)


def resolve(*, case=None, rows=None, asof=None, first=None, last=None, owner=None):
    case=rule() if case is None else case
    rows=bars() if rows is None else rows
    return inspect_case(
        case=case, bars=rows,
        as_known_at=asof or clock(T0+timedelta(minutes=40)),
        expected_first_sequence=rows[0].sequence if first is None and rows else first,
        expected_last_sequence=rows[-1].sequence if last is None and rows else last,
        verify_owner=owner if owner is not None else lambda *_: True,
    )


@pytest.mark.parametrize("kind,operator,level,closes,expected",[
    ("level_touch","gte",100,(99,101,102),True),
    ("level_touch","gt",101.5,(99,101,102),True),
    ("level_touch","gt",102.5,(99,101,102),False),
    ("level_touch","lte",100,(101,99,98),True),
    ("level_touch","lt",98,(101,99,98),True),
    ("level_touch","lt",97.5,(101,99,98),False),
    ("terminal_close","gte",102,(99,101,102),True),
    ("terminal_close","gt",102,(99,101,102),False),
    ("terminal_close","lte",102,(99,101,102),True),
    ("terminal_close","lt",102,(99,101,102),False),
    ("terminal_close","gte",100,(110,105,90),False),
    ("level_touch","gte",100,(110,105,90),True),
])
def test_mathematical_literal_outcome_only(kind,operator,level,closes,expected):
    out=resolve(case=rule(kind,operator,level),rows=bars(closes))
    assert out["status"]=="mathematically_resolved"
    assert out["mathematical_outcome"] is expected
    assert out["owner_callback_qualified"] is True
    assert out["eligible_trial"] is False
    assert out["predictive_validation"] is False
    assert out["source_authenticity_proven"] is False
    assert out["probability"] is None
    assert out["recommendation"] is False and not any(out["authority"].values())


def test_open_window_does_not_score_an_early_winner():
    out=resolve(asof=clock(T0+timedelta(minutes=19)))
    assert out["status"]=="decision_window_open" and out["mathematical_outcome"] is None


def test_missing_window_or_calendar_attestation_never_means_false():
    rows=bars()
    assert inspect_case(case=rule(),as_known_at=clock(T0+timedelta(hours=1)),
                        bars=rows)["status"]=="coverage_not_attested"
    assert resolve(rows=(),first=40,last=42)["status"]=="coverage_not_attested"
    assert resolve(rows=rows[:-1],last=42)["status"]=="calendar_window_incomplete"
    assert resolve(rows=rows,first=39)["status"]=="calendar_window_incomplete"
    assert resolve(rows=rows,last=43)["status"]=="calendar_window_incomplete"


@pytest.mark.parametrize("mutate,status",[
    (lambda b:replace(b,subject="QQQ:XNAS"),"subject_or_horizon_mismatch"),
    (lambda b:replace(b,horizon="swing"),"subject_or_horizon_mismatch"),
    (lambda b:replace(b,unit="index_points"),"subject_or_horizon_mismatch"),
    (lambda b:replace(b,generation_ref="another:source"),"mixed_generation"),
    (lambda b:replace(b,sequence=41),"calendar_window_incomplete"),
    (lambda b:replace(b,begins_at=clock(T0+timedelta(minutes=9))),"calendar_sequence_inconsistent"),
    (lambda b:replace(b,completed=False),"unfinished_source_bar"),
    (lambda b:replace(b,available_at=clock(T0+timedelta(hours=2)),
                      valid_until=clock(T0+timedelta(days=2))),"bar_not_yet_available"),
    (lambda b:replace(b,valid_until=clock(T0+timedelta(minutes=35))),"expired_source_revision"),
])
def test_incomplete_source_or_mismatched_revision_abstains(mutate,status):
    rows=bars()
    rows=rows[:-1]+(mutate(rows[-1]),)
    out=resolve(rows=rows,first=40,last=42)
    assert out["status"]==status
    assert out["mathematical_outcome"] is None
    assert "observed_bar_count" not in out


def test_predecision_partial_bar_is_excluded_even_if_it_contains_touch():
    rows=bars()
    first=replace(rows[0],begins_at=clock(T0-timedelta(minutes=1)))
    out=resolve(rows=(first,)+rows[1:])
    assert out["status"]=="outside_predeclared_window"


def test_post_deadline_bar_does_not_count_a_future_win():
    rows=bars()
    last=replace(rows[-1],begins_at=clock(T0+timedelta(minutes=28)),
                 ends_at=clock(T0+timedelta(minutes=33)),
                 available_at=clock(T0+timedelta(minutes=34)))
    out=resolve(rows=rows[:-1]+(last,))
    assert out["status"]=="outside_predeclared_window"


def test_missing_owner_or_denial_never_means_observed_false():
    rows=bars()
    args=dict(case=rule(),as_known_at=clock(T0+timedelta(hours=1)),
              bars=rows,expected_first_sequence=40,expected_last_sequence=42)
    assert inspect_case(**args)["status"]=="source_owner_missing"
    for owner in (lambda *_:False,lambda *_:"yes",
                  lambda *_:(_ for _ in ()).throw(PermissionError("deny")),
                  lambda *_:(_ for _ in ()).throw(OSError("offline"))):
        out=inspect_case(**args,verify_owner=owner)
        assert out["status"]=="source_owner_refused" and out["mathematical_outcome"] is None


def test_owner_verifies_expected_calendar_bounds_and_receipts_at_cutoff():
    calls=[]
    def owner(spec,rows,first,last,asof):
        calls.append((spec.claim_id,first,last,asof))
        return rows[0].sequence==first and rows[-1].sequence==last
    out=resolve(owner=owner)
    assert out["mathematical_outcome"] is True
    assert calls==[(CLAIM,40,42,T0+timedelta(minutes=40))]


def test_no_raw_subject_or_rule_reference_in_public_result():
    out=resolve()
    body=json.dumps(out,sort_keys=True)
    for original in ("SPY:ARCX","owner:original:ruler:1","owner:bar-generation-1","owner:bar:1"):
        assert original not in body
    assert out["claim_id"]==CLAIM and out["episode_id"]==EPISODE
    assert len(out["generation_binding_sha256"])==64


@pytest.mark.parametrize("mutate",[
    dict(claim_id="aa"),dict(episode_id="bad"),dict(rule_ref=""),
    dict(subject=""),dict(horizon="weekly"),dict(kind="option_pnl"),
    dict(operator="equals"),dict(threshold=0),dict(threshold=True),
    dict(threshold=float("nan")),dict(threshold=float("inf")),
    dict(unit="contracts"),dict(original_rule_available_at=clock(T0+timedelta(minutes=1))),
    dict(deadline=clock(T0)),dict(decision_at=clock(T0+timedelta(hours=2))),
])
def test_unfrozen_or_invalid_claim_contract_refused(mutate):
    with pytest.raises(ContractError):
        replace(rule(),**mutate)


def test_outcome_types_never_guess_order_from_an_ohlc_bar():
    with pytest.raises(ContractError,match="outcome"):
        replace(rule(),kind="path_order")


@pytest.mark.parametrize("bound",[-1,True,1.2,1_000_000_000])
def test_invalid_calendar_owner_bounds_refused(bound):
    with pytest.raises(ContractError):
        resolve(first=bound)


def test_untyped_bar_or_unbounded_population_rejected():
    with pytest.raises(ContractError):
        inspect_case(case=rule(),as_known_at=clock(T0+timedelta(hours=1)),bars=list(bars()))
    with pytest.raises(ContractError):
        inspect_case(case=rule(),as_known_at=clock(T0+timedelta(hours=1)),bars=(1,2))
    with pytest.raises(ContractError):
        inspect_case(case=rule(),as_known_at=clock(T0+timedelta(hours=1)),bars=bars()*172)


def test_grounded_research_ruler_join_is_diagnostic_only():
    from engine.market_navigator_outcomes import research_link_diagnostics
    from engine.market_navigator_research import ResearchRuler

    case=rule()
    ruler=ResearchRuler(
        claim_id=CLAIM, annotation_ref="reviewer:manual",
        annotation_available_at=clock(T0-timedelta(hours=1)),
        subject="SPY:ARCX",horizon="intraday",outcome="level_touch",
        decision_at=case.decision_at,deadline=case.deadline,
        conditional=True,trigger_ref=case.rule_ref,
        invalidation_ref="reviewer:invalidation-original")
    row=dict(claim_id=CLAIM,status="ruler_fields_present_not_validated",
             annotation_status="externally_supplied_not_semantically_verified",
             gaps=[])
    linked=research_link_diagnostics(case=case,ruler=ruler,audited_claim=row)
    assert linked["status"]=="aligned_fields_not_authenticated"
    assert linked["source_authenticity_proven"] is False
    assert linked["trial_registered"] is False and linked["score_admitted"] is False
    assert not any(linked["authority"].values())
    assert "SPY:ARCX" not in json.dumps(linked)
    for changed,reason in [
        (replace(ruler,outcome="terminal_close"),"outcome_type_mismatch"),
        (replace(ruler,subject="QQQ:XNAS"),"research_subject_or_horizon_mismatch"),
        (replace(ruler,deadline=clock(T0+timedelta(hours=1))),"original_deadline_mismatch"),
        (replace(ruler,trigger_ref="different:ruler"),"original_rule_reference_mismatch"),
        (replace(ruler,annotation_available_at=clock(T0+timedelta(seconds=1))),
         "annotation_not_known_at_decision"),
    ]:
        result=research_link_diagnostics(case=case,ruler=changed,audited_claim=row)
        assert result["status"]=="unqualified" and reason in result["issues"]
    bad=dict(row,status="not_scoreable_as_specified")
    assert research_link_diagnostics(case=case,ruler=ruler,audited_claim=bad)["status"]=="unqualified"
    with pytest.raises(ContractError,match="identity"):
        research_link_diagnostics(case=case,ruler=ruler,
                                 audited_claim=dict(row,claim_id="c"*64))

def test_existing_navigator_ci_job_executes_outcome_falsifiers():
    from pathlib import Path
    import yaml
    root=Path(__file__).resolve().parents[1]
    job=yaml.safe_load((root/".github/ci/legacy-jobs.yml").read_text())["jobs"]["market-navigator-foundation"]
    suite="tests/test_market_navigator_outcomes.py"
    steps=" ".join(step.get("run","") for step in job["steps"])
    assert suite in steps, "new outcome suite must execute in incumbent CI job"
    assert "engine/market_navigator*.py" in job["paths"]
    assert "tests/test_market_navigator*.py" in job["paths"]
    assert job["scope"]=="exclusive"
