"""Synthetic contract tests, never historical market-performance evidence."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qualification as q


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


def test_five_sessions_is_friday_not_wednesday():
    r=single()
    assert r['entry_session']=='2026-09-28'
    assert r['exit_session']=='2026-10-02'
    assert r['status']=='MEASURED'


def test_one_session_is_next_open_to_next_close():
    r=single(h=1)
    assert r['entry_session']==r['exit_session']=='2026-09-28'
    assert r['absolute_return']==pytest.approx(-0.01)


def test_immature_on_calendar_five_day_date():
    p=packet();p['evaluation_at']='2026-09-30T21:00:00Z'
    r=single(p)
    assert r['status']=='IMMATURE'
    assert 'forward_excess' not in r


def test_horizon_beyond_supplied_axis_is_unavailable():
    assert single(h=6)['reason']=='CALENDAR_HORIZON_UNAVAILABLE'


@pytest.mark.parametrize('h',[0,-1,True,1.5])
def test_invalid_horizon(h):
    assert single(h=h)['reason']=='INVALID_HORIZON'


@pytest.mark.parametrize('stamp',['2026-09-25','not-a-date','2026-09-25T20:10:00'])
def test_unqualified_decision_clock(stamp):
    p=packet();p['signals'][0]['decision_at']=stamp
    assert single(p)['status']=='INELIGIBLE'


def test_no_same_close_execution():
    p=packet();p['signals'][0]['decision_at']='2026-09-25T19:59:59Z'
    p['signals'][0]['feature_known_at']='2026-09-25T19:50:00Z'
    assert single(p)['reason']=='FINAL_SESSION_NOT_CLOSED'


def test_signal_received_after_next_open_not_backdated():
    p=packet();p['signals'][0]['decision_at']='2026-09-28T13:30:00Z'
    assert single(p)['reason']=='DECISION_NOT_BEFORE_NEXT_OPEN'


@pytest.mark.parametrize('field,reason',[('feature_known_at','FEATURE_KNOWN_AFTER_DECISION')])
def test_late_feature(field,reason):
    p=packet();p['signals'][0][field]='2026-09-26T00:00:00Z'
    assert single(p)['reason']==reason


@pytest.mark.parametrize('field,reason',[('known_at','MEMBERSHIP_KNOWN_AFTER_DECISION'),
                                         ('weight_known_at','WEIGHT_KNOWN_AFTER_DECISION')])
def test_late_membership_or_weight(field,reason):
    p=packet();p['signals'][0]['members'][0][field]='2026-09-26T00:00:00Z'
    assert single(p)['reason']==reason


@pytest.mark.parametrize('basis',['CURRENT_ONLY','RECONSTRUCTED',None])
def test_backcast_membership_cannot_be_pit(basis):
    p=packet();p['signals'][0]['membership_basis']=basis
    assert single(p)['reason']=='MEMBERSHIP_NOT_PIT'


@pytest.mark.parametrize('field,value',[('valid_from','2026-09-26'),('valid_to','2026-09-25')])
def test_membership_effective_interval(field,value):
    p=packet();p['signals'][0]['members'][0][field]=value
    assert single(p)['reason']=='MEMBERSHIP_NOT_EFFECTIVE'


def test_empty_group():
    p=packet();p['signals'][0]['members']=[]
    assert single(p)['reason']=='EMPTY_MEMBERSHIP'


@pytest.mark.parametrize('field',['ticker','issuer_id'])
def test_duplicate_issuer_or_security_cannot_double_count(field):
    p=packet();p['signals'][0]['members'][1][field]=p['signals'][0]['members'][0][field]
    assert single(p)['reason']=='DUPLICATE_OR_EMPTY_SECURITY_ISSUER'


def test_missing_loser_not_silently_dropped():
    p=packet();p['prices']=[r for r in p['prices'] if not(r['ticker']=='G0M0' and r['session']=='2026-10-02')]
    r=single(p)
    assert r['status']=='UNAVAILABLE' and r['expected_members']==3 and r['measured_members']==2
    assert r['covered_weight']==pytest.approx(2/3)
    assert 'absolute_return' not in r


def test_missing_benchmark():
    p=packet();p['prices']=[r for r in p['prices'] if r['ticker']!='SPY']
    assert single(p)['reason']=='BENCHMARK_EXACT_ENDPOINT_MISSING'


@pytest.mark.parametrize('value',[0,-1,None,float('nan'),float('inf'),True])
def test_bad_prices_do_not_become_measured_zero(value):
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['close']=value
    r=single(p)
    assert r['status']=='UNAVAILABLE' and 'forward_excess' not in r


def test_mixed_corporate_action_basis():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['basis_id']='different-vintage'
    assert single(p)['missing_members']['G0M0']=='PRICE_BASIS_MISMATCH'


def test_future_correction_not_visible_to_old_evaluation():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['known_at']='2026-10-03T00:00:00Z'
    assert single(p)['missing_members']['G0M0']=='PRICE_KNOWN_AFTER_EVALUATION'


def test_final_bar_cannot_be_known_before_its_close():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['known_at']='2026-10-02T19:00:00Z'
    assert single(p)['missing_members']['G0M0']=='FINAL_BAR_KNOWN_BEFORE_CLOSE'


def test_weight_scale_invariance():
    p=packet();a=single(p)
    for m in p['signals'][0]['members']:m['weight']*=21
    assert single(p)['absolute_return']==a['absolute_return']


@pytest.mark.parametrize('w',[0,-1,True,float('nan')])
def test_invalid_weights(w):
    p=packet();p['signals'][0]['members'][0]['weight']=w
    assert single(p)['status']=='INELIGIBLE'


def test_all_candidate_issuer_listings_excluded():
    rows=[{'ticker':'A','issuer_id':'a','weight':1},{'ticker':'A.ADR','issuer_id':'a','weight':1},
          {'ticker':'B','issuer_id':'b','weight':1}]
    assert q.peer_ex_issuer(rows,'a')==[{'ticker':'B','issuer_id':'b','weight':1.0}]
    assert q.peer_ex_issuer(rows[:2],'a')==[]


def test_identical_score_comparison_has_zero_delta():
    p=packet()
    for s in p['signals']:s['scores']['challenger']=s['scores']['baseline']
    r=q.run_packet(p)
    assert all(x['mean_paired_ic_delta']==0 for x in r['comparison']['by_horizon'].values())
    assert r['comparison']['winner'] is None


def test_missing_challenger_excludes_same_row_from_both_arms():
    p=packet();p['signals'][0]['scores']['challenger']=None
    r=q.run_packet(p)
    assert all(x['matched_rows']==2 for x in r['comparison']['per_date'])
    assert all(x['baseline_ic'] is None and x['challenger_ic'] is None for x in r['comparison']['per_date'])
    assert r['comparison']['excluded']['PAIR_SCORE_OR_TARGET_UNAVAILABLE']==2


def test_insertion_order_does_not_pick_a_winner():
    p=packet();a=q.run_packet(p)
    p['horizons'].reverse();p['signals'].reverse()
    b=q.run_packet(p)
    assert a['comparison']==b['comparison']
    assert a['comparison']['winner'] is None


def test_degenerate_cross_section_abstains():
    assert q.rank_ic([1,1,1],[1,2,3]) is None
    assert q.rank_ic([1,2,3],[1,1,1]) is None
    assert q.rank_ic([1,2],[2,1]) is None


def test_tie_ranks_are_average_ranks():
    assert q.ranks([4,1,1,9])==[3,1.5,1.5,4]


def test_duplicate_labels_refused():
    rows=q.run_packet(packet())['labels']
    with pytest.raises(q.QualificationError,match='DUPLICATE_LABEL_ID'):
        q.paired_comparison(rows+[rows[0]],'baseline','challenger')


def test_duplicate_group_in_cross_section_refused():
    p=packet();p['signals'][1]['group_id']=p['signals'][0]['group_id']
    with pytest.raises(q.QualificationError,match='DUPLICATE_GROUP'):
        q.run_packet(p)


def evidence():
    return [{'claim_id':'a','known_at':'2026-09-01T10:00:00Z','published_at':'2026-09-01T09:00:00Z','source_cluster_id':'origin1','value':1},
            {'claim_id':'a','known_at':'2026-09-02T10:00:00Z','published_at':'2026-09-02T09:00:00Z','source_cluster_id':'origin1','value':2},
            {'claim_id':'b','known_at':'2026-09-01T11:00:00Z','published_at':'2026-09-01T09:30:00Z','source_cluster_id':'origin1','value':1}]


def test_later_claim_correction_not_backfilled():
    out=q.evidence_at(evidence(),'2026-09-01T23:00:00Z')
    assert out['claims'][0]['value']==1


def test_reposts_and_corrections_not_independent_confirmation():
    out=q.evidence_at(evidence(),'2026-09-03T00:00:00Z')
    assert len(out['claims'])==2 and out['independent_source_clusters']==1
    assert out['claims'][0]['value']==2


def test_future_published_evidence_refused():
    e=evidence();e[0]['published_at']='2026-10-01T00:00:00Z'
    with pytest.raises(q.QualificationError,match='PUBLICATION_AFTER_KNOWLEDGE'):
        q.evidence_at(e,'2026-10-02T00:00:00Z')


def test_ambiguous_correction_clock_refused():
    e=evidence()
    with pytest.raises(q.QualificationError,match='AMBIGUOUS_CLAIM_VERSION'):
        q.evidence_at(e+[e[0]],'2026-10-02T00:00:00Z')


def test_no_source_cluster_no_independence_claim():
    e=evidence();e[0].pop('source_cluster_id')
    with pytest.raises(q.QualificationError,match='SOURCE_CLUSTER_REQUIRED'):
        q.evidence_at(e,'2026-10-02T00:00:00Z')


def test_overlapping_training_outcomes_purged():
    train=[{'snapshot_id':'ok','decision_at':'2026-09-01T00:00:00Z','exit_at':'2026-09-03T00:00:00Z','outcome_known_at':'2026-09-03T00:01:00Z'},
           {'snapshot_id':'leak','decision_at':'2026-09-02T00:00:00Z','exit_at':'2026-09-05T00:00:00Z','outcome_known_at':'2026-09-05T00:01:00Z'}]
    valid=[{'decision_at':'2026-09-05T00:00:00Z'}]
    assert q.purged_training_ids(train,valid)==['ok']


def test_cross_section_does_not_multiply_temporal_windows():
    rows=q.run_packet(packet())['labels']
    assert len(rows)==6
    assert q.nonoverlapping_time_windows(rows)==1


def test_authority_false_everywhere():
    r=q.run_packet(packet())
    assert not any(r['authority'].values())
    assert not any(r['comparison']['authority'].values())
    assert all(not any(x['authority'].values()) for x in r['labels'])
    assert r['independent_episodes'] is None


@pytest.mark.parametrize('key',['calendar_receipt','price_receipt','signal_receipt'])
def test_missing_manifest_receipt_refused(key):
    p=packet();p['manifest'].pop(key)
    with pytest.raises(q.QualificationError,match='SOURCE_RECEIPT_REQUIRED'):
        q.run_packet(p)


def test_duplicate_price_row_refused():
    p=packet();p['prices'].append(p['prices'][0])
    with pytest.raises(q.QualificationError,match='DUPLICATE_PRICE_ROW'):
        q.run_packet(p)


def test_duplicate_snapshot_refused():
    p=packet();p['signals'].append(p['signals'][0])
    with pytest.raises(q.QualificationError,match='DUPLICATE_SNAPSHOT_ID'):
        q.run_packet(p)


def test_duplicate_session_refused():
    p=packet();p['sessions'].append(p['sessions'][-1])
    with pytest.raises(q.QualificationError,match='SESSION_AXIS_NOT_UNIQUE_SORTED'):
        q.run_packet(p)


def test_overlapping_session_clock_refused():
    p=packet();p['sessions'][1]['open_at']=p['sessions'][0]['close_at']
    with pytest.raises(q.QualificationError,match='SESSION_AXIS_OVERLAP'):
        q.run_packet(p)


def test_cli_end_to_end(tmp_path):
    inp=tmp_path/'input.json';out=tmp_path/'result.json'
    inp.write_text(json.dumps(packet()))
    proc=subprocess.run([sys.executable,str(Path(q.__file__)),str(inp),'--output',str(out)],capture_output=True,text=True)
    assert proc.returncode==0,proc.stdout+proc.stderr
    r=json.loads(out.read_text())
    assert r['label_status_counts']=={'MEASURED':6}
    assert r['manifest']['dataset_kind']=='SYNTHETIC'
    assert len(r['input_sha256'])==64


def test_cli_rejects_unqualified_input(tmp_path):
    inp=tmp_path/'input.json';p=packet();p['manifest']['membership_basis']='CURRENT_ONLY'
    inp.write_text(json.dumps(p))
    proc=subprocess.run([sys.executable,str(Path(q.__file__)),str(inp)],capture_output=True,text=True)
    assert proc.returncode==2
    assert json.loads(proc.stdout)['status']=='REFUSED'


def test_weight_sum_overflow_fails_closed():
    p=packet()
    for m in p['signals'][0]['members']:m['weight']=1e308
    assert single(p)['status']=='INELIGIBLE'


def test_out_of_range_integer_rejected_as_qualification_error():
    with pytest.raises(q.QualificationError):
        q.number(10**1000)


def test_malformed_session_label_not_accepted():
    p=packet();p['sessions'][0]['session']='2026-09-25garbage'
    with pytest.raises(q.QualificationError):
        q.session_axis(p['sessions'])


def test_future_known_evidence_does_not_change_historical_view():
    cutoff='2026-09-01T23:00:00Z'
    original=q.evidence_at(evidence(),cutoff)
    future={'claim_id':'future','known_at':'2026-10-01T10:00:00Z',
            'published_at':'2026-10-02T00:00:00Z','source_cluster_id':'future_origin'}
    assert q.evidence_at(evidence()+[future],cutoff)==original


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),None,True])
def test_direct_ic_helper_does_not_rank_invalid_values(bad):
    assert q.rank_ic([1,bad,3],[1,2,3]) is None


def test_nonfinite_derived_return_never_marked_measured():
    p=packet()
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-09-28')['open']=1e-300
    next(r for r in p['prices'] if r['ticker']=='G0M0' and r['session']=='2026-10-02')['close']=1e308
    result=single(p)
    assert result['status']=='UNAVAILABLE'
    assert 'forward_excess' not in result


def test_label_preserves_latest_outcome_knowledge_clock():
    result=single()
    assert result['outcome_known_at']=='2026-10-02T20:01:00+00:00'


def test_train_label_known_after_validation_start_is_purged():
    train=[{'snapshot_id':'late-label','decision_at':'2026-09-01T00:00:00Z',
            'exit_at':'2026-09-03T00:00:00Z','outcome_known_at':'2026-09-06T00:00:00Z'}]
    assert q.purged_training_ids(train,[{'decision_at':'2026-09-05T00:00:00Z'}])==[]


def test_train_label_with_unknown_knowledge_clock_is_refused():
    train=[{'snapshot_id':'unknown','decision_at':'2026-09-01T00:00:00Z',
            'exit_at':'2026-09-03T00:00:00Z'}]
    with pytest.raises(q.QualificationError,match='OUTCOME_KNOWLEDGE_CLOCK_REQUIRED'):
        q.purged_training_ids(train,[{'decision_at':'2026-09-05T00:00:00Z'}])
