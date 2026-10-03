"""Unit tests for engine.subsector_track_record — the forward outcome ledger."""
from __future__ import annotations

import json
from datetime import date, timedelta

import pandas as pd

from engine import subsector_track_record as S


def _payload(subs, emerging, fading):
    return {"subsectors": subs, "highlights": {"emerging": emerging, "fading": fading}}


def test_snapshot_idempotent(tmp_path):
    pay = _payload([{"key": "a", "name": "A", "theme": "T", "emerging_score": 2.0,
                     "rs_mom": 1.0, "accel": 3.0, "quadrant": "improving"}],
                   ["a"], [])
    mm = {"a": ["NVDA", "AAPL", "MSFT"]}
    assert S.snapshot(pay, mm, today="2026-06-28", root=tmp_path) == 1
    assert S.snapshot(pay, mm, today="2026-06-28", root=tmp_path) == 0   # same day → no dupes
    rows = [json.loads(x) for x in (tmp_path / "data/subsector_rotation/snapshots.jsonl").read_text().splitlines()]
    assert rows[0]["stage"] == "emerging" and rows[0]["lean"] == 1 and rows[0]["members"] == ["NVDA", "AAPL", "MSFT"]


def test_accruing_when_empty(tmp_path):
    tr = S.compute(today="2026-06-28", root=tmp_path)
    assert tr["verdict"] == "accruing" and tr["any_matured"] is False and tr["n_snapshots"] == 0
    assert tr["is_context_only"] is True


def _fake_prices(monkeypatch):
    # entry = 100 for everyone; exit encodes the move via a per-ticker table.
    exit_px = {"W": 110.0, "L": 90.0, "SPY": 100.0}   # W up 10%, L down 10%, SPY flat
    monkeypatch.setattr(S, "_covers", lambda t, root, end: True)
    monkeypatch.setattr(S, "_level_asof", lambda t, root, start: 100.0)
    monkeypatch.setattr(S, "_close_at", lambda t, root, end: exit_px.get(t[0] if t != "SPY" else "SPY", 100.0))


def _write_rows(tmp_path, rows):
    p = tmp_path / "data/subsector_rotation/snapshots.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_maturation_grades_calls(tmp_path, monkeypatch):
    _fake_prices(monkeypatch)
    d0 = (date(2026, 6, 28) - timedelta(days=40)).isoformat()
    rows = [
        # emerging with WINNER members → fwd>0 → HIT
        {"date": d0, "key": "e_hit", "name": "Ehit", "theme": "T", "score": 2.5, "lean": 1,
         "stage": "emerging", "members": ["W1", "W2", "W3"]},
        # emerging with LOSER members → fwd<0 → MISS (false judgement → error ledger)
        {"date": d0, "key": "e_miss", "name": "Emiss", "theme": "T", "score": 2.0, "lean": 1,
         "stage": "emerging", "members": ["L1", "L2", "L3"]},
        # fading with LOSER members → fwd<0 → HIT (correctly called the roll-over)
        {"date": d0, "key": "f_hit", "name": "Fhit", "theme": "T", "score": -1.0, "lean": -1,
         "stage": "fading", "members": ["L4", "L5", "L6"]},
        # too few priceable members → unscored (members table prices all, but only 2 → < _MIN_PRICED)
        {"date": d0, "key": "thin", "name": "Thin", "theme": "T", "score": 0.1, "lean": 0,
         "stage": "neutral", "members": ["W9", "W8"]},
    ]
    _write_rows(tmp_path, rows)
    tr = S.compute(today="2026-06-28", root=tmp_path)
    h21 = tr["horizons"]["21"]
    assert h21["n_matured"] == 3                                  # the 2-member 'thin' is dropped
    bs = h21["by_stage"]
    assert bs["emerging"]["n"] == 2 and bs["emerging"]["hit_rate"] == 0.5   # 1 hit / 1 miss
    assert bs["fading"]["n"] == 1 and bs["fading"]["hit_rate"] == 1.0
    # the falsified emerging call is logged in the error ledger
    misses = {m["key"] for m in tr["recent_misses"]}
    assert "e_miss" in misses and "e_hit" not in misses
    # still no significance on a tiny sample → not 'validated'
    assert tr["verdict"] in ("measuring", "accruing")


def test_horizon_gating(tmp_path, monkeypatch):
    _fake_prices(monkeypatch)
    # a call only 7 days old: matures at 5d, not at 21d.
    d0 = (date(2026, 6, 28) - timedelta(days=7)).isoformat()
    _write_rows(tmp_path, [{"date": d0, "key": "e", "name": "E", "theme": "T", "score": 1.0,
                            "lean": 1, "stage": "emerging", "members": ["W1", "W2", "W3"]}])
    tr = S.compute(today="2026-06-28", root=tmp_path)
    assert tr["horizons"]["5"]["n_matured"] == 1
    assert tr["horizons"]["21"]["n_matured"] == 0


# --------------------------------------------------------------------------- #
# SESSION STAMPING (calendar-asof audit 2026-08-05)
#
# The nightly runs ~22:30 UTC seven nights a week against an END-OF-DAY board, so the
# Saturday and Sunday passes re-read Friday's unchanged numbers. Stamped from the clock
# they slipped past the (date,key) idempotency below and appended a full fresh row set
# per weekend night, which compute() then graded as extra independent IC days.
#
# Pinned weekday dates only — a fixture that reads the wall clock is a scheduled failure.
# 2026-07-10 Fri (session) · 2026-07-11 Sat · 2026-07-12 Sun.
# --------------------------------------------------------------------------- #
_FRI, _SAT, _SUN = "2026-07-10", "2026-07-11", "2026-07-12"


def _one_sub(key="a"):
    return _payload([{"key": key, "name": "A", "theme": "T", "emerging_score": 2.0,
                      "rs_mom": 1.0, "accel": 3.0, "quadrant": "improving"}], [key], [])


def test_weekend_snapshot_dedupes_against_the_friday_it_redescribes(tmp_path):
    """A Saturday re-read of Friday's board must be a NO-OP, not a second row set."""
    pay, mm = _one_sub(), {"a": ["NVDA", "AAPL", "MSFT"]}
    assert S.snapshot(pay, mm, today=_FRI, root=tmp_path) == 1
    p = tmp_path / "data/subsector_rotation/snapshots.jsonl"
    before = p.read_bytes()

    assert S.snapshot(pay, mm, today=_SAT, root=tmp_path) == 0, "Saturday re-fetch"
    assert S.snapshot(pay, mm, today=_SUN, root=tmp_path) == 0, "Sunday re-fetch"

    assert p.read_bytes() == before, "the weekend passes must not touch the ledger"
    rows = [json.loads(x) for x in p.read_text().splitlines()]
    assert [r["date"] for r in rows] == [_FRI]


def test_weekend_snapshot_still_logs_when_the_session_is_absent(tmp_path):
    """Normalization, not refusal: Friday's fetch failed and Saturday recovered it.

    The rows must still log — dated to the session they actually describe, so the
    board is not lost — which is why the fix normalizes rather than dropping weekend
    calls outright.
    """
    pay, mm = _one_sub(), {"a": ["NVDA", "AAPL", "MSFT"]}
    assert S.snapshot(pay, mm, today=_SAT, root=tmp_path) == 1

    rows = [json.loads(x) for x in
            (tmp_path / "data/subsector_rotation/snapshots.jsonl").read_text().splitlines()]
    assert [r["date"] for r in rows] == [_FRI]
    assert rows[0]["stage"] == "emerging" and rows[0]["members"] == ["NVDA", "AAPL", "MSFT"]


def test_compute_as_of_is_the_session_not_the_calendar_day(tmp_path):
    """A Sunday run reports Friday: there is no session between them to age into."""
    tr = S.compute(today=_SUN, root=tmp_path)
    assert tr["as_of"] == _FRI


def test_compute_maturity_clock_does_not_age_over_a_weekend(tmp_path, monkeypatch):
    """A call 5 sessions old on Friday is not 7 days old because someone ran on Sunday."""
    _fake_prices(monkeypatch)
    # 2026-07-03 is the observed Independence Day holiday; 2026-07-02 (Thu) is the
    # last session before it, exactly 8 calendar days before _SUN and 8 before _FRI.
    _write_rows(tmp_path, [{"date": "2026-07-05", "key": "e", "name": "E", "theme": "T",
                            "score": 1.0, "lean": 1, "stage": "emerging",
                            "members": ["W1", "W2", "W3"]}])
    # the row itself is weekend-dated legacy data; grading it is not this test's point —
    # what matters is that today= normalizes identically from Friday and from Sunday.
    fri = S.compute(today=_FRI, root=tmp_path)
    sun = S.compute(today=_SUN, root=tmp_path)
    assert fri["as_of"] == sun["as_of"] == _FRI
    assert {h: e["n_matured"] for h, e in fri["horizons"].items()} == \
           {h: e["n_matured"] for h, e in sun["horizons"].items()}


def test_unparseable_stamp_passes_through_and_never_raises(tmp_path):
    """degrade-never-raise: a stamp we cannot read is not given an invented session."""
    pay, mm = _one_sub(), {"a": ["NVDA", "AAPL", "MSFT"]}
    assert S.snapshot(pay, mm, today="not-a-date", root=tmp_path) == 1
    rows = [json.loads(x) for x in
            (tmp_path / "data/subsector_rotation/snapshots.jsonl").read_text().splitlines()]
    assert rows[0]["date"] == "not-a-date"

    tr = S.compute(today="not-a-date", root=tmp_path)
    assert tr["verdict"] == "accruing" and tr["compute_error"]


def test_session_stamp_maps_holidays_and_weekends(tmp_path):
    """The helper itself — pinned dates, including a holiday-extended closure."""
    assert S._session_stamp(_FRI) == _FRI                     # session: unchanged
    assert S._session_stamp(_SAT) == _FRI
    assert S._session_stamp(_SUN) == _FRI
    assert S._session_stamp(date(2026, 7, 11)) == _FRI        # date object, not a str
    # 2026-07-04 falls on a Saturday, so Independence Day is observed Fri 2026-07-03;
    # the last session of that week is Thursday 2026-07-02.
    assert S._session_stamp("2026-07-03") == "2026-07-02"
    assert S._session_stamp("2026-07-05") == "2026-07-02"
    # Labor Day 2026 = Mon 2026-09-07 → the prior Friday.
    assert S._session_stamp("2026-09-07") == "2026-09-04"


# Qualified replay acceptance cases are owned and executed by this existing CI suite.
# These synthetic cases were consolidated from PR #8299's research-only suites.
# No legacy test is removed, no waiver is introduced, and no production score changes.
import copy
from pathlib import Path
import subprocess
import sys
import pytest
from research.sector_intelligence.subtheme_qualification_2026_10_02 import qualification as q
from research.sector_intelligence.subtheme_qualification_2026_10_02.legacy_seams import (
    reproduce, calendar_endpoint, coverage_renormalized,
)


def packet():
    # Explicit session axis supplied as a fixture, not an invented exchange calendar.
    days = ['2026-09-25','2026-09-28','2026-09-29','2026-09-30','2026-10-01','2026-10-02']
    sessions = [{'session': d, 'open_at':d+'T13:30:00Z', 'close_at':d+'T20:00:00Z'} for d in days]
    signals, prices = [], []
    for g in range(3):
        members = []
        for j in range(3):
            t = f'G{g}M{j}'
            members.append({'ticker':t, 'issuer_id':t, 'weight':1.0,
                            'known_at':'2026-09-01T00:00:00Z', 'weight_known_at':'2026-09-01T00:00:00Z',
                            'valid_from':'2026-09-01', 'valid_to':None})
            for k,d in enumerate(days):
                prices.append({'ticker':t,'session':d,'open':100.0,
                               'close':100.0+(g-1)*k,'known_at':d+'T20:01:00Z','basis_id':t+'-fixture-v1'})
        signals.append({'snapshot_id':f's{g}','group_id':f'g{g}','session':days[0],
                        'decision_at':days[0]+'T20:10:00Z','feature_known_at':days[0]+'T20:05:00Z',
                        'membership_basis':'POINT_IN_TIME','members':members,'benchmark':'SPY',
                        'scores':{'baseline':float(2-g),'challenger':float(g)}})
    for d in days:
        prices.append({'ticker':'SPY','session':d,'open':100.0,'close':100.0,
                       'known_at':d+'T20:01:00Z','basis_id':'SPY-fixture-v1'})
    return {'manifest':{'membership_basis':'POINT_IN_TIME','calendar_receipt':'SYNTHETIC_FIXTURE',
                        'price_receipt':'SYNTHETIC_FIXTURE','signal_receipt':'SYNTHETIC_FIXTURE',
                        'price_basis':'OWNER_QUALIFIED_ADJUSTED_OHLC','dataset_kind':'SYNTHETIC'},
            'sessions':sessions,'signals':signals,'prices':prices,'horizons':[1,5],
            'evaluation_at':'2026-10-02T21:00:00Z','baseline':'baseline','challenger':'challenger'}


def single(p=None,h=5):
    p = packet() if p is None else p
    pm = {(r['ticker'],r['session']):r for r in p['prices']}
    return q.label_group(p['signals'][0],h,p['sessions'],pm,p['evaluation_at'])


def test_replay_qualification_five_sessions_is_friday_not_wednesday():
    r=single()
    assert r['entry_session']=='2026-09-28'
    assert r['exit_session']=='2026-10-02'
    assert r['status']=='MEASURED'


def test_replay_qualification_one_session_is_next_open_to_next_close():
    r=single(h=1)
    assert r['entry_session']==r['exit_session']=='2026-09-28'
    assert r['absolute_return']==pytest.approx(-0.01)


def test_replay_qualification_immature_on_calendar_five_day_date():
    p=packet();p['evaluation_at']='2026-09-30T21:00:00Z'
    r=single(p)
    assert r['status']=='IMMATURE'
    assert 'forward_excess' not in r


def test_replay_qualification_horizon_beyond_supplied_axis_is_unavailable():
    assert single(h=6)['reason']=='CALENDAR_HORIZON_UNAVAILABLE'


@pytest.mark.parametrize('h',[0,-1,True,1.5])
def test_replay_qualification_invalid_horizon(h):
    assert single(h=h)['reason']=='INVALID_HORIZON'


@pytest.mark.parametrize('stamp',['2026-09-25','not-a-date','2026-09-25T20:10:00'])
def test_replay_qualification_unqualified_decision_clock(stamp):
    p=packet();p['signals'][0]['decision_at']=stamp
    assert single(p)['status']=='INELIGIBLE'


def test_replay_qualification_no_same_close_execution():
    p=packet();p['signals'][0]['decision_at']='2026-09-25T19:59:59Z'
    p['signals'][0]['feature_known_at']='2026-09-25T19:50:00Z'
    assert single(p)['reason']=='FINAL_SESSION_NOT_CLOSED'


def test_replay_qualification_signal_received_after_next_open_not_backdated():
    p=packet();p['signals'][0]['decision_at']='2026-09-28T13:30:00Z'
    assert single(p)['reason']=='DECISION_NOT_BEFORE_NEXT_OPEN'


@pytest.mark.parametrize('field,reason',[('feature_known_at','FEATURE_KNOWN_AFTER_DECISION')])
def test_replay_qualification_late_feature(field,reason):
    p=packet();p['signals'][0][field]='2026-09-26T00:00:00Z'
    assert single(p)['reason']==reason


@pytest.mark.parametrize('field,reason',[('known_at','MEMBERSHIP_KNOWN_AFTER_DECISION'),
                                         ('weight_known_at','WEIGHT_KNOWN_AFTER_DECISION')])
def test_replay_qualification_late_membership_or_weight(field,reason):
    p=packet();p['signals'][0]['members'][0][field]='2026-09-26T00:00:00Z'
    assert single(p)['reason']==reason


@pytest.mark.parametrize('basis',['CURRENT_ONLY','RECONSTRUCTED',None])
def test_replay_qualification_backcast_membership_cannot_be_pit(basis):
    p=packet();p['signals'][0]['membership_basis']=basis
    assert single(p)['reason']=='MEMBERSHIP_NOT_PIT'


@pytest.mark.parametrize('field,value',[('valid_from','2026-09-26'),('valid_to','2026-09-25')])
def test_replay_qualification_membership_effective_interval(field,value):
    p=packet();p['signals'][0]['members'][0][field]=value
    assert single(p)['reason']=='MEMBERSHIP_NOT_EFFECTIVE'


def test_replay_qualification_empty_group():
    p=packet();p['signals'][0]['members']=[]
    assert single(p)['reason']=='EMPTY_MEMBERSHIP'


@pytest.mark.parametrize('field',['ticker','issuer_id'])
def test_replay_qualification_duplicate_issuer_or_security_cannot_double_count(field):
    p=packet();p['signals'][0]['members'][1][field]=p['signals'][0]['members'][0][field]
    assert single(p)['reason']=='DUPLICATE_OR_EMPTY_SECURITY_ISSUER'


def test_replay_qualification_missing_loser_not_silently_dropped():
    p=packet();p['prices']=[r for r in p['prices'] if not(r['ticker']=='G0M0' and r['session']=='2026-10-02')]
    r=single(p)
    assert r['status']=='UNAVAILABLE' and r['expected_members']==3 and r['measured_members']==2
    assert r['covered_weight']==pytest.approx(2/3)
    assert 'absolute_return' not in r


def test_replay_qualification_missing_benchmark():
    p=packet();p['prices']=[r for r in p['prices'] if r['ticker']!='SPY']
    assert single(p)['reason']=='BENCHMARK_EXACT_ENDPOINT_MISSING'


@pytest.mark.parametrize('value',[0,-1,None,float('nan'),float('inf'),True])
def test_replay_qualification_bad_prices_do_not_become_measured_zero(value):
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['close']=value
    r=single(p)
    assert r['status']=='UNAVAILABLE' and 'forward_excess' not in r


def test_replay_qualification_mixed_corporate_action_basis():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['basis_id']='different-vintage'
    assert single(p)['missing_members']['G0M0']=='PRICE_BASIS_MISMATCH'


def test_replay_qualification_future_correction_not_visible_to_old_evaluation():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['known_at']='2026-10-03T00:00:00Z'
    assert single(p)['missing_members']['G0M0']=='PRICE_KNOWN_AFTER_EVALUATION'


def test_replay_qualification_final_bar_cannot_be_known_before_its_close():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['known_at']='2026-10-02T19:00:00Z'
    assert single(p)['missing_members']['G0M0']=='FINAL_BAR_KNOWN_BEFORE_CLOSE'


def test_replay_qualification_weight_scale_invariance():
    p=packet();a=single(p)
    for m in p['signals'][0]['members']:m['weight']*=21
    assert single(p)['absolute_return']==a['absolute_return']


@pytest.mark.parametrize('w',[0,-1,True,float('nan')])
def test_replay_qualification_invalid_weights(w):
    p=packet();p['signals'][0]['members'][0]['weight']=w
    assert single(p)['status']=='INELIGIBLE'


def test_replay_qualification_all_candidate_issuer_listings_excluded():
    rows=[{'ticker':'A','issuer_id':'a','weight':1},{'ticker':'A.ADR','issuer_id':'a','weight':1},
          {'ticker':'B','issuer_id':'b','weight':1}]
    assert q.peer_ex_issuer(rows,'a')==[{'ticker':'B','issuer_id':'b','weight':1.0}]
    assert q.peer_ex_issuer(rows[:2],'a')==[]


def test_replay_qualification_identical_score_comparison_has_zero_delta():
    p=packet()
    for s in p['signals']:s['scores']['challenger']=s['scores']['baseline']
    r=q.run_packet(p)
    assert all(x['mean_paired_ic_delta']==0 for x in r['comparison']['by_horizon'].values())
    assert r['comparison']['winner'] is None


def test_replay_qualification_missing_challenger_excludes_same_row_from_both_arms():
    p=packet();p['signals'][0]['scores']['challenger']=None
    r=q.run_packet(p)
    assert all(x['matched_rows']==2 for x in r['comparison']['per_date'])
    assert all(x['baseline_ic'] is None and x['challenger_ic'] is None for x in r['comparison']['per_date'])
    assert r['comparison']['excluded']['PAIR_SCORE_OR_TARGET_UNAVAILABLE']==2


def test_replay_qualification_insertion_order_does_not_pick_a_winner():
    p=packet();a=q.run_packet(p)
    p['horizons'].reverse();p['signals'].reverse()
    b=q.run_packet(p)
    assert a['comparison']==b['comparison']
    assert a['comparison']['winner'] is None


def test_replay_qualification_degenerate_cross_section_abstains():
    assert q.rank_ic([1,1,1],[1,2,3]) is None
    assert q.rank_ic([1,2,3],[1,1,1]) is None
    assert q.rank_ic([1,2],[2,1]) is None


def test_replay_qualification_tie_ranks_are_average_ranks():
    assert q.ranks([4,1,1,9])==[3,1.5,1.5,4]


def test_replay_qualification_duplicate_labels_refused():
    rows=q.run_packet(packet())['labels']
    with pytest.raises(q.QualificationError,match='DUPLICATE_LABEL_ID'):
        q.paired_comparison(rows+[rows[0]],'baseline','challenger')


def test_replay_qualification_duplicate_group_in_cross_section_refused():
    p=packet();p['signals'][1]['group_id']=p['signals'][0]['group_id']
    with pytest.raises(q.QualificationError,match='DUPLICATE_GROUP'):
        q.run_packet(p)


def evidence():
    return [{'claim_id':'a','known_at':'2026-09-01T10:00:00Z','published_at':'2026-09-01T09:00:00Z','source_cluster_id':'origin1','value':1},
            {'claim_id':'a','known_at':'2026-09-02T10:00:00Z','published_at':'2026-09-02T09:00:00Z','source_cluster_id':'origin1','value':2},
            {'claim_id':'b','known_at':'2026-09-01T11:00:00Z','published_at':'2026-09-01T09:30:00Z','source_cluster_id':'origin1','value':1}]


def test_replay_qualification_later_claim_correction_not_backfilled():
    out=q.evidence_at(evidence(),'2026-09-01T23:00:00Z')
    assert out['claims'][0]['value']==1


def test_replay_qualification_reposts_and_corrections_not_independent_confirmation():
    out=q.evidence_at(evidence(),'2026-09-03T00:00:00Z')
    assert len(out['claims'])==2 and out['independent_source_clusters']==1
    assert out['claims'][0]['value']==2


def test_replay_qualification_future_published_evidence_refused():
    e=evidence();e[0]['published_at']='2026-10-01T00:00:00Z'
    with pytest.raises(q.QualificationError,match='PUBLICATION_AFTER_KNOWLEDGE'):
        q.evidence_at(e,'2026-10-02T00:00:00Z')


def test_replay_qualification_ambiguous_correction_clock_refused():
    e=evidence()
    with pytest.raises(q.QualificationError,match='AMBIGUOUS_CLAIM_VERSION'):
        q.evidence_at(e+[e[0]],'2026-10-02T00:00:00Z')


def test_replay_qualification_no_source_cluster_no_independence_claim():
    e=evidence();e[0].pop('source_cluster_id')
    with pytest.raises(q.QualificationError,match='SOURCE_CLUSTER_REQUIRED'):
        q.evidence_at(e,'2026-10-02T00:00:00Z')


def test_replay_qualification_overlapping_training_outcomes_purged():
    train=[{'snapshot_id':'ok','decision_at':'2026-09-01T00:00:00Z','exit_at':'2026-09-03T00:00:00Z','outcome_known_at':'2026-09-03T00:01:00Z'},
           {'snapshot_id':'leak','decision_at':'2026-09-02T00:00:00Z','exit_at':'2026-09-05T00:00:00Z','outcome_known_at':'2026-09-05T00:01:00Z'}]
    valid=[{'decision_at':'2026-09-05T00:00:00Z'}]
    assert q.purged_training_ids(train,valid)==['ok']


def test_replay_qualification_cross_section_does_not_multiply_temporal_windows():
    rows=q.run_packet(packet())['labels']
    assert len(rows)==6
    assert q.nonoverlapping_time_windows(rows)==1


def test_replay_qualification_authority_false_everywhere():
    r=q.run_packet(packet())
    assert not any(r['authority'].values())
    assert not any(r['comparison']['authority'].values())
    assert all(not any(x['authority'].values()) for x in r['labels'])
    assert r['independent_episodes'] is None


@pytest.mark.parametrize('key',['calendar_receipt','price_receipt','signal_receipt'])
def test_replay_qualification_missing_manifest_receipt_refused(key):
    p=packet();p['manifest'].pop(key)
    with pytest.raises(q.QualificationError,match='SOURCE_RECEIPT_REQUIRED'):
        q.run_packet(p)


def test_replay_qualification_duplicate_price_row_refused():
    p=packet();p['prices'].append(p['prices'][0])
    with pytest.raises(q.QualificationError,match='DUPLICATE_PRICE_ROW'):
        q.run_packet(p)


def test_replay_qualification_duplicate_snapshot_refused():
    p=packet();p['signals'].append(p['signals'][0])
    with pytest.raises(q.QualificationError,match='DUPLICATE_SNAPSHOT_ID'):
        q.run_packet(p)


def test_replay_qualification_duplicate_session_refused():
    p=packet();p['sessions'].append(p['sessions'][-1])
    with pytest.raises(q.QualificationError,match='SESSION_AXIS_NOT_UNIQUE_SORTED'):
        q.run_packet(p)


def test_replay_qualification_overlapping_session_clock_refused():
    p=packet();p['sessions'][1]['open_at']=p['sessions'][0]['close_at']
    with pytest.raises(q.QualificationError,match='SESSION_AXIS_OVERLAP'):
        q.run_packet(p)


def test_replay_qualification_cli_end_to_end(tmp_path):
    inp=tmp_path/'input.json';out=tmp_path/'result.json'
    inp.write_text(json.dumps(packet()))
    proc=subprocess.run([sys.executable,str(Path(q.__file__)),str(inp),'--output',str(out)],capture_output=True,text=True)
    assert proc.returncode==0,proc.stdout+proc.stderr
    r=json.loads(out.read_text())
    assert r['label_status_counts']=={'MEASURED':6}
    assert r['manifest']['dataset_kind']=='SYNTHETIC'
    assert len(r['input_sha256'])==64


def test_replay_qualification_cli_rejects_unqualified_input(tmp_path):
    inp=tmp_path/'input.json';p=packet();p['manifest']['membership_basis']='CURRENT_ONLY'
    inp.write_text(json.dumps(p))
    proc=subprocess.run([sys.executable,str(Path(q.__file__)),str(inp)],capture_output=True,text=True)
    assert proc.returncode==2
    assert json.loads(proc.stdout)['status']=='REFUSED'


def test_replay_qualification_weight_sum_overflow_fails_closed():
    p=packet()
    for m in p['signals'][0]['members']:m['weight']=1e308
    assert single(p)['status']=='INELIGIBLE'


def test_replay_qualification_out_of_range_integer_rejected_as_qualification_error():
    with pytest.raises(q.QualificationError):
        q.number(10**1000)


def test_replay_qualification_malformed_session_label_not_accepted():
    p=packet();p['sessions'][0]['session']='2026-09-25garbage'
    with pytest.raises(q.QualificationError):
        q.session_axis(p['sessions'])


def test_replay_qualification_future_known_evidence_does_not_change_historical_view():
    cutoff='2026-09-01T23:00:00Z'
    original=q.evidence_at(evidence(),cutoff)
    future={'claim_id':'future','known_at':'2026-10-01T10:00:00Z',
            'published_at':'2026-10-02T00:00:00Z','source_cluster_id':'future_origin'}
    assert q.evidence_at(evidence()+[future],cutoff)==original


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),None,True])
def test_replay_qualification_direct_ic_helper_does_not_rank_invalid_values(bad):
    assert q.rank_ic([1,bad,3],[1,2,3]) is None


def test_replay_qualification_nonfinite_derived_return_never_marked_measured():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-09-28')['open']=1e-300
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['close']=1e308
    result=single(p)
    assert result['status']=='UNAVAILABLE'
    assert 'forward_excess' not in result


def test_replay_qualification_label_preserves_latest_outcome_knowledge_clock():
    result=single()
    assert result['outcome_known_at']=='2026-10-02T20:01:00+00:00'


def test_replay_qualification_train_label_known_after_validation_start_is_purged():
    train=[{'snapshot_id':'late-label','decision_at':'2026-09-01T00:00:00Z',
            'exit_at':'2026-09-03T00:00:00Z','outcome_known_at':'2026-09-06T00:00:00Z'}]
    assert q.purged_training_ids(train,[{'decision_at':'2026-09-05T00:00:00Z'}])==[]


def test_replay_qualification_train_label_with_unknown_knowledge_clock_is_refused():
    train=[{'snapshot_id':'unknown','decision_at':'2026-09-01T00:00:00Z',
            'exit_at':'2026-09-03T00:00:00Z'}]
    with pytest.raises(q.QualificationError,match='OUTCOME_KNOWLEDGE_CLOCK_REQUIRED'):
        q.purged_training_ids(train,[{'decision_at':'2026-09-05T00:00:00Z'}])


def test_replay_qualification_calendar_discriminator():
    r=reproduce()
    assert r['calendar_endpoint']=='2026-09-30'
    assert r['calendar_endpoint']!=r['explicit_five_session_endpoint']


def test_replay_qualification_iteration_order_changes_legacy_headline():
    r=reproduce()
    assert r['leader_5_then_21']=='v2'
    assert r['leader_21_then_5']=='incumbent'


def test_replay_qualification_missing_loser_can_flip_legacy_group_label():
    r=reproduce()
    assert r['full_population_mean']==pytest.approx(-0.035)
    assert r['missing_loser_legacy_mean']==pytest.approx(0.02)


def test_replay_qualification_legacy_three_member_floor_does_not_measure_coverage():
    assert coverage_renormalized([0.02]*3+[None]*97)==pytest.approx(0.02)


@pytest.mark.parametrize('field', ['snapshot_id','group_id'])
@pytest.mark.parametrize('bad', ['', ' ', None, 4])
def test_replay_qualification_continuation_signal_identity(field, bad):
    p=packet(); p['signals'][0][field]=bad
    assert single(p)['status']=='INELIGIBLE'


@pytest.mark.parametrize('field', ['ticker','issuer_id'])
def test_replay_qualification_continuation_noncanonical_member_identity(field):
    p=packet(); p['signals'][0]['members'][0][field]=' G0M0 '
    assert single(p)['status']=='INELIGIBLE'


@pytest.mark.parametrize('field,bad', [('valid_from','2026-00-01'),('valid_to','2099-bad'),('valid_from','')])
def test_replay_qualification_continuation_malformed_effective_dates(field,bad):
    p=packet(); p['signals'][0]['members'][0][field]=bad
    assert single(p)['status']=='INELIGIBLE'


@pytest.mark.parametrize('field,bad',[('ticker','WRONG'),('session','2026-09-29')])
def test_replay_qualification_continuation_price_map_identity(field,bad):
    p=packet(); pm={(r['ticker'],r['session']):r.copy() for r in p['prices']}
    pm[('G0M0','2026-09-28')][field]=bad
    r=q.label_group(p['signals'][0],5,p['sessions'],pm,p['evaluation_at'])
    assert r['status']=='UNAVAILABLE'


@pytest.mark.parametrize('field', ['baseline','challenger'])
def test_replay_qualification_continuation_empty_model_identity(field):
    p=packet(); p[field]=''
    with pytest.raises(q.QualificationError): q.run_packet(p)


def test_replay_qualification_continuation_same_model_is_not_a_comparison():
    p=packet(); p['challenger']=p['baseline']
    with pytest.raises(q.QualificationError): q.run_packet(p)


def test_replay_qualification_continuation_content_digest_changes_with_score():
    p=packet(); a=q.run_packet(p)['comparison']['per_date'][0]['pair_digest']
    p['signals'][0]['scores']['baseline']+=0.1
    b=q.run_packet(p)['comparison']['per_date'][0]['pair_digest']
    assert a!=b


def test_replay_qualification_continuation_content_digest_changes_with_target():
    p=packet(); a=q.run_packet(p)['comparison']['per_date'][0]['pair_digest']
    for r in p['prices']:
        if r['ticker']=='G0M0' and r['session']=='2026-09-28':r['close']-=1
    b=q.run_packet(p)['comparison']['per_date'][0]['pair_digest']
    assert a!=b


def test_replay_qualification_continuation_content_digest_is_input_order_invariant():
    p=packet(); a=q.run_packet(p)['comparison']['per_date']
    p['signals'].reverse();p['prices'].reverse()
    b=q.run_packet(p)['comparison']['per_date']
    assert a==b


def test_replay_qualification_continuation_population_fingerprint_changes_with_weights():
    p=packet(); a=single(p)
    p['signals'][0]['members'][0]['weight']=2
    b=single(p)
    assert a['population_digest']!=b['population_digest']


def test_replay_qualification_continuation_disjoint_counts_are_per_horizon():
    r=q.run_packet(packet())
    assert r['disjoint_time_windows_by_horizon']=={'1':1,'5':1}


def test_replay_qualification_continuation_evidence_retraction_does_not_count_as_confirmation():
    rs=[{'claim_id':'c1','source_cluster_id':'origin1','known_at':'2026-01-01T01:00Z',
         'published_at':'2026-01-01T00:00Z','status':'ACTIVE'},
        {'claim_id':'c1','source_cluster_id':'origin1','known_at':'2026-01-02T01:00Z',
         'published_at':'2026-01-02T00:00Z','status':'RETRACTED'}]
    assert q.evidence_at(rs,'2026-01-01T12:00Z')['independent_source_clusters']==1
    r=q.evidence_at(rs,'2026-01-03T00:00Z')
    assert r['claims']==[] and r['independent_source_clusters']==0
    assert len(r['retracted_claims'])==1


def test_replay_qualification_continuation_unknown_evidence_status_refused():
    r={'claim_id':'c','source_cluster_id':'s','known_at':'2026-01-01T01:00Z',
       'published_at':'2026-01-01T00:00Z','status':'MAGIC'}
    with pytest.raises(q.QualificationError):q.evidence_at([r],'2026-01-02T00:00Z')


def test_replay_qualification_continuation_comparison_rejects_mixed_target_basis():
    rows=q.run_packet(packet())['labels'];rows[2]['target_basis']='other_definition'
    with pytest.raises(q.QualificationError):q.paired_comparison(rows,'baseline','challenger')


# Fixed public industry-reference checks; no data download or trading authority.
import numpy as np
from research.sector_intelligence.subtheme_qualification_2026_10_02 import industry_reference as _ir


def _ir_panel(n=320,m=49):
    rng=np.random.default_rng(42)
    idx=pd.bdate_range('2008-01-01',periods=n)
    return pd.DataFrame(rng.normal(.0003,.01,(n,m)),index=idx,columns=[f'i{x:02d}' for x in range(m)]),pd.Series(rng.normal(.0002,.005,n),index=idx)


def test_industry_reference_parser_missing_is_missing():
    text='Average Value Weighted Returns -- Daily\n A B\n20200102 1.0 -99.99\n20200103 -999 2\n\nOther table'
    r=_ir.parse_table(text,'Average Value Weighted Returns -- Daily',2)
    assert r.iloc[0,0]==.01 and r.iloc[1,1]==.02
    assert np.isnan(r.iloc[0,1]) and np.isnan(r.iloc[1,0])

@pytest.mark.parametrize('dates',['20200102\n20200102','20200103\n20200102'])
def test_industry_reference_parser_refuses_duplicate_or_unsorted(dates):
    rows='\n'.join(d+' 1 2' for d in dates.splitlines())
    with pytest.raises(ValueError,match='DATES'):
        _ir.parse_table('Mkt-RF RF\n'+rows,'Mkt-RF',2)

@pytest.mark.parametrize('h',[0,-1,True,1.0])
def test_industry_reference_invalid_horizon(h):
    with pytest.raises(ValueError): _ir.forward_returns(pd.DataFrame([.1]*5),h)

@pytest.mark.parametrize('h',[1,5,10,20])
def test_industry_reference_forward_exact_sessions(h):
    r,_=_ir_panel()
    f=_ir.forward_returns(r,h)
    for t in [0,1,250]:
        assert np.allclose(f.iloc[t],(1+r.iloc[t+1:t+h+1]).prod()-1)
    assert f.iloc[-h:].isna().all().all()

@pytest.mark.parametrize('name',_ir.NAMES)
def test_industry_reference_future_does_not_change_features(name):
    r,m=_ir_panel()
    a=_ir.features(r,m)[name]
    changed=r.copy(); changed.iloc[300:]=.9
    changedm=m.copy(); changedm.iloc[300:]=-.1
    b=_ir.features(changed,changedm)[name]
    pd.testing.assert_frame_equal(a.iloc[:300],b.iloc[:300])


def test_industry_reference_feature_formula_and_missing_positive():
    r,m=_ir_panel()
    x=np.log1p(r).sub(np.log1p(m),axis=0)
    fs=_ir.features(r,m)
    assert np.allclose(fs['accel5_20'].iloc[280],x.iloc[276:281].mean()-x.iloc[261:276].mean())
    assert np.allclose(fs['mom252_skip21'].iloc[280],x.iloc[29:260].sum())
    r.iloc[275,0]=np.nan
    assert np.isnan(_ir.features(r,m)['persistence20'].iloc[280,0])


def test_industry_reference_missing_loser_removes_whole_cross_section():
    r,m=_ir_panel()
    y=_ir.forward_returns(r,10)
    fs=_ir.features(r,m)
    assert _ir.common_mask(fs,y)[280]
    r.iloc[285,0]=np.nan
    assert not _ir.common_mask(fs,_ir.forward_returns(r,10))[280]


def test_industry_reference_delayed_book_excludes_immediate_rally():
    r=np.zeros((5,2)); r[1,0]=1
    target=np.tile([1,0],(5,1))
    assert _ir.book(r,np.zeros(5),target,0)['terminal_wealth']==1
    r[2,0]=.1
    assert _ir.book(r,np.zeros(5),target,0)['terminal_wealth']==pytest.approx(1.1)


def test_industry_reference_self_financing_entry_exit_cost():
    r=np.zeros((5,1)); rf=np.zeros(5); target=np.ones((5,1))
    got=_ir.book(r,rf,target,10)
    assert got['terminal_wealth']==pytest.approx(.999/1.001)
    assert got['max_drawdown']<0


def test_industry_reference_costs_monotone():
    r,_=_ir_panel(500)
    t=_ir.top_mask(r.to_numpy())
    vals=[_ir.book(r.to_numpy(),np.zeros(500),t,c)['terminal_wealth'] for c in (0,5,10,25)]
    assert all(a>b for a,b in zip(vals,vals[1:]))


def test_industry_reference_top_ties_deterministic():
    x=np.ones((2,49)); mask=_ir.top_mask(x)
    assert np.allclose(mask[:,:10],.1) and np.all(mask[:,10:]==0)
    assert np.allclose(mask.sum(axis=1),1)


def test_industry_reference_holm_monotone():
    assert _ir.holm({'a':.01,'b':.04,'c':.2})=={'a':.03,'b':.08,'c':.2}


def test_industry_reference_hac_detects_positive_autocorrelation():
    rng=np.random.default_rng(55)
    x=np.convolve(rng.normal(size=1500),np.ones(10)/10,mode='valid')
    assert _ir.hac_summary(x,20)['se']>_ir.hac_summary(x,0)['se']


def test_industry_reference_ridge_training_labels_precede_test():
    r,m=_ir_panel(800)
    out=_ir.ridge_walkforward(_ir.features(r,m),r,m)
    assert out['folds']
    for f in out['folds']:
        assert f['last_training_outcome']<f['first_test']


def test_industry_reference_refuse_misaligned_calendar():
    r,m=_ir_panel()
    with pytest.raises(ValueError,match='CALENDAR'): _ir.features(r,m.iloc[:-1])


def test_industry_reference_no_authority():
    assert _ir.CAPS and not any(_ir.CAPS.values())


def test_industry_reference_rolling_leader_can_emerge_without_new_returns():
    # All three groups earn exactly zero tomorrow. Only window expiry changes rank.
    history=pd.DataFrame({'A':[-.20,.05,.05,.05], 'B':[.01]*4, 'C':[0.0]*4})
    before=(1+history).prod()-1
    after=(1+pd.concat([history.iloc[1:],pd.DataFrame([[0.,0.,0.]],columns=history.columns)])).prod()-1
    assert before.idxmax()=='B' and after.idxmax()=='A'
    assert before['A']==pytest.approx(-.0739)
    assert after['A']==pytest.approx(.157625)
    new_returns=pd.Series(0.,index=history.columns)
    assert (new_returns-new_returns.mean()).eq(0).all()


def test_industry_reference_persistence_maturity_extends_beyond_entry_horizon():
    # Entry by session 10 plus five following confirmation sessions is not a
    # ten-session information-availability window. Use the actual label clock.
    entry_horizon, confirmation_sessions=10,5
    sessions=pd.bdate_range('2026-09-01',periods=25)
    decision=sessions[0]
    nominal_end=sessions[entry_horizon]
    actual_end=sessions[entry_horizon+confirmation_sessions]
    validation=sessions[entry_horizon+1]
    assert decision<nominal_end<validation<actual_end
    row={'snapshot_id':'example', 'decision_at':decision.isoformat()+'Z',
         'exit_at':actual_end.isoformat()+'Z', 'outcome_known_at':actual_end.isoformat()+'Z'}
    assert q.purged_training_ids([row],[{'decision_at':validation.isoformat()+'Z'}])==[]


# --------------------------------------------------------------------------- #
# Exact-session production evaluator repair (2026-10-02 continuation)
# --------------------------------------------------------------------------- #
def test_track_record_session_horizon_skips_weekends_and_holidays():
    assert S._session_horizon_end("2026-09-25", 5) == "2026-10-02"
    assert S._session_horizon_end("2026-09-04", 1) == "2026-09-08"  # Labor Day


def test_track_record_maturity_waits_for_exact_session_horizon(tmp_path, monkeypatch):
    rows=[{"date":"2026-09-25","key":"x","members":["A","B","C"],"score":1.0}]
    monkeypatch.setattr(S, "_covers", lambda *args, **kwargs: True)
    monkeypatch.setattr(S, "_fwd_basket", lambda *args, **kwargs: 0.1)
    assert S._matured(rows, tmp_path, 5, date(2026, 9, 30)) == []
    got=S._matured(rows, tmp_path, 5, date(2026, 10, 2))
    assert len(got)==1 and got[0]["fwd"]==pytest.approx(0.1)


def test_track_record_window_span_counts_actual_sessions():
    got=S._window_span(["2026-09-04","2026-09-08"], 1)
    assert got["ic_span_days"]==4
    assert got["ic_span_sessions"]==1
    assert got["indep_windows"]==1.0


def test_track_record_head_to_head_is_paired_and_order_invariant():
    h5={"n_matured":100,"score_ic":0.9,
        "v2":{"n_matured":20,"score_ic":-0.8},
        "comparison":{"n_paired":20,"score_ic":0.1,"score_ic_v2":0.2,
                      "score_ic_t_hac":0.5,"score_ic_t_hac_v2":0.6}}
    h21={"n_matured":80,"score_ic":-0.7,
         "v2":{"n_matured":30,"score_ic":0.9},
         "comparison":{"n_paired":30,"score_ic":0.3,"score_ic_v2":0.1,
                       "score_ic_t_hac":0.4,"score_ic_t_hac_v2":0.2}}
    a=S._head_to_head({"5":h5,"21":h21})
    b=S._head_to_head({"21":h21,"5":h5})
    assert a["leader"] is None and b["leader"] is None
    assert a["by_horizon"]["5"]["n_paired"]==20
    assert a["by_horizon"]["5"]["gap"]==pytest.approx(0.1)
    assert a["by_horizon"]["21"]["gap"]==pytest.approx(-0.2)
    assert a["by_horizon"]==b["by_horizon"]
