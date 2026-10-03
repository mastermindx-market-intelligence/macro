"""Event/result binding: canonical owner -> read-only projection, no live IO."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import events_news_release_evidence as view
from engine import release_actuals as official

EVENT = {'type':'PCE','date':'2026-09-30','reference_period':'2026-08'}
ASOF = '2026-09-30T13:00:00Z'

@pytest.fixture
def policy(tmp_path):
    p=tmp_path/'defects.json'
    p.write_text(json.dumps({'schema':'official_actual_defects.v1','defects_by_receipt':{}}))
    return p


def publication(family='PCE', **changes):
    c=official._SOURCE_CONTRACTS[family]
    raw={'reference_period':'August 2026','unit':c['raw_unit'],
         'headline_mom':.3,'core_mom':.2,'payroll_change':175000,'initial_claims':203000,
         'real_gdp_annualized':3.0}
    if family=='CLAIMS': raw['reference_period']='September 26, 2026'
    if family=='GDP':
        raw['reference_period']='Q2 2026'
        raw['vintage']='advance'
    p={'type':family,'date':'2026-09-30','data_ready':True,
       'source_url':f"https://www.{c['host']}/fixture/not-live",'source_sha256':'a'*64,
       'publisher':c['publisher'],'source_id':c['source_id'],
       'parser':{'name':c['parser'][0],'version':c['parser'][1]},
       'first_seen_at':'2026-09-30T12:31:00Z',
       'source_released_at':'2026-09-30T12:30:00Z','verified_at':'2026-09-30T12:32:00Z',
       'actual':raw}
    p.update(changes)
    return p


def receipts(policy, family='PCE', **changes):
    rows=official.normalize_publication(publication(family,**changes),defects_path=policy)
    assert rows,'canonical fixture generation must succeed'
    return rows


def project(policy, rows, event=None, cutoff=ASOF):
    return view.event_actual_evidence(EVENT if event is None else event,rows,as_of=cutoff,defects_path=policy)


def test_canonical_dependency_identity_is_known():
    # Private registry interfaces are deliberately pinned; no parallel mapping.
    assert set(official._TARGETS)=={'CPI','PPI','PCE','GDP','NFP','CLAIMS'}
    for specs in official._TARGETS.values():
        for release,_,metric,unit,scale in specs:
            assert official._SPEC_BY_RELEASE[release]==(metric,unit,scale)

@pytest.mark.parametrize('family,n',[('CPI',2),('PPI',1),('PCE',2),('GDP',1),('NFP',1),('CLAIMS',1)])
def test_each_family_reuses_canonical_units(policy,family,n):
    ev={'type':family,'date':'2026-09-30'}
    before=receipts(policy,family);rows=deepcopy(before)
    v=project(policy,rows,ev)
    assert v['status']=='available' and v['available_count']==n
    assert v['display_only'] is True and v['authority'] is False
    assert rows==before and 'official_evidence' not in ev
    assert [m['actual'] for m in v['metrics']]==[r['actual'] for r in rows]
    assert all(m['sequence']=='first' for m in v['metrics'])
    if family=='GDP':
        assert v['metrics'][0]['display_value']=='3.0'
        assert v['metrics'][0]['unit']=='percent_annualized'
        assert v['metrics'][0]['period']=='2026-Q2'
    if family=='NFP': assert v['metrics'][0]['display_value']=='175'
    if family=='CLAIMS': assert v['metrics'][0]['display_value']=='203'

@pytest.mark.parametrize('ev,reason',[(None,'invalid_event'),({},'invalid_event'),
    ({'type':'pce','date':'2026-09-30'},'unsupported_event_type'),
    ({'type':'FOMC','date':'2026-09-30'},'unsupported_event_type'),
    ({'label':'PCE','date':'2026-09-30'},'invalid_event'),
    ({'type':[],'date':'2026-09-30'},'invalid_event'),
    ({'type':'PCE','date':'2026-02-30'},'invalid_event')])
def test_event_identity_is_typed_not_inferred(policy,ev,reason):
    v=view.event_actual_evidence(ev,receipts(policy),as_of=ASOF,defects_path=policy)
    assert v['reason']==reason and not v['metrics']




def test_gdp_second_estimate_is_not_demoted_to_correction(policy):
    advance=publication(
        'GDP',
        date='2026-07-30',
        first_seen_at='2026-07-30T12:30:30Z',
        source_released_at='2026-07-30T12:30:00Z',
        verified_at='2026-07-30T12:31:00Z',
        source_sha256='a'*64,
    )
    advance['actual']['vintage']='advance'
    advance_rows=official.normalize_publication(advance,defects_path=policy)
    assert len(advance_rows)==1

    second=publication(
        'GDP',
        date='2026-08-27',
        first_seen_at='2026-08-27T12:30:30Z',
        source_released_at='2026-08-27T12:30:00Z',
        verified_at='2026-08-27T12:31:00Z',
        source_sha256='b'*64,
    )
    second['actual']['vintage']='second'
    second['actual']['real_gdp_annualized']=3.2
    second_rows=official.reconcile_receipts(
        {'schema':'release_publications.v2','publications':[second]},
        advance_rows,defects_path=policy)
    assert len(second_rows)==1
    assert second_rows[0]['row_type']=='actual'
    assert second_rows[0]['estimate_vintage']=='second'
    assert second_rows[0].get('supersedes_receipt_id') is None

    evidence=view.event_actual_evidence(
        {'type':'GDP','date':'2026-08-27','reference_period':'Q2 2026'},
        advance_rows+second_rows,
        as_of='2026-08-27T13:00:00Z',defects_path=policy)
    assert evidence['status']=='available'
    assert evidence['metrics'][0]['actual']==3.2
    assert evidence['metrics'][0]['estimate_vintage']=='second'


def test_gdp_watcher_parser_shape_flows_into_canonical_result(policy):
    from scripts.official_release_parsers import parse_gdp_actual

    body=b'''<html><body>
    <h1>GDP (Advance Estimate), Second Quarter 2026</h1>
    <p>Real gross domestic product (GDP) increased at an annual rate of 3.0
    percent in the second quarter of 2026, according to the advance estimate.</p>
    <p>In the first quarter, real GDP decreased 0.5 percent.</p>
    </body></html>'''
    actual=parse_gdp_actual(body)
    assert actual is not None
    assert actual['real_gdp_annualized']==3.0
    assert actual['vintage']=='advance'
    assert actual['reference_period']=='Q2 2026'
    assert actual['unit']=='percent'

    source_url='https://www.bea.gov/news/2026/gdp-advance-estimate-2nd-quarter-2026'
    publication={
        'type':'GDP','date':'2026-07-30','reference_period':'Q2 2026',
        'data_ready':True,'source_url':source_url,
        'source_sha256':hashlib.sha256(body).hexdigest(),
        'publisher':'U.S. Bureau of Economic Analysis','source_id':'bea_gdp',
        'parser':{'name':'gdp','version':1},
        'first_seen_at':'2026-07-30T12:30:30Z',
        'source_released_at':'2026-07-30T12:30:00Z',
        'verified_at':'2026-07-30T12:31:00Z',
        'actual':{**actual,'source_url':source_url},
    }
    rows=official.normalize_publication(publication,defects_path=policy)
    assert len(rows)==1
    assert rows[0]['release']=='gdp_real_annualized'
    assert rows[0]['period']=='2026-Q2'
    assert rows[0]['estimate_vintage']=='advance'

    evidence=view.event_actual_evidence(
        {'type':'GDP','date':'2026-07-30','reference_period':'Q2 2026'},
        rows,as_of='2026-07-30T13:00:00Z',defects_path=policy)
    assert evidence['status']=='available'
    assert evidence['available_count']==1
    metric=evidence['metrics'][0]
    assert metric['actual']==3.0
    assert metric['display_value']=='3.0'
    assert metric['estimate_vintage']=='advance'


def test_gdp_reference_binding_uses_quarter_not_month_guessing(policy):
    rows=receipts(policy,'GDP')
    event={'type':'GDP','date':'2026-09-30','reference_period':'Q2 2026'}
    v=project(policy,rows,event)
    assert v['status']=='available'
    assert v['metrics'][0]['period']=='2026-Q2'
    assert v['metrics'][0]['unit']=='percent_annualized'

    drift={**event,'reference_period':'Q1 2026'}
    withheld=project(policy,rows,drift)
    assert withheld['status']=='unavailable'
    assert all(m['reason']=='reference_period_mismatch' for m in withheld['metrics'])


def test_gdp_result_without_forecast_context_stays_fact_only(policy):
    rows=receipts(policy,'GDP')
    event={'type':'GDP','date':'2026-09-30','reference_period':'Q2 2026'}
    attached=view.attach_event_actual_evidence(
        [event],rows,as_of=ASOF,defects_path=policy)
    assert attached[0]['official_evidence']['status']=='available'
    expectation=view.event_expectation_context(
        attached[0],
        {'schema':'release_forecast.v2','asof':ASOF,'display_only':True,
         'authority':{'can_score':False,'can_size':False,'can_trade':False},
         'methodology_status':{'street_consensus':'unavailable'},
         'upcoming':[],'last_scored_all_forward':[]},
        as_of=ASOF,official_evidence=attached[0]['official_evidence'])
    assert expectation['status']=='unavailable'
    assert expectation['street_survey_status']=='unavailable'
    assert expectation['metrics'][0]['reason']=='no_matching_frozen_model_context'


@pytest.mark.parametrize('cutoff',['2026-09-30','2026-09-30 13:00','invalid',None,'2026-09-30T25:00:00Z'])
def test_invalid_cutoff_has_no_values(policy,cutoff):
    v=project(policy,receipts(policy),cutoff=cutoff)
    assert v['reason']=='invalid_as_of' and v['metrics']==[]

@pytest.mark.parametrize('delta',[-1,0,1])
def test_verification_cutoff_is_inclusive(policy,delta):
    t=datetime(2026,9,30,12,32,tzinfo=timezone.utc)+timedelta(seconds=delta)
    v=project(policy,receipts(policy),cutoff=t.isoformat())
    assert v['status']==('unavailable' if delta<0 else 'available')
    if delta<0: assert all(m['actual'] is None for m in v['metrics'])


def test_old_observed_clock_does_not_leak_later_verification(policy):
    rows=receipts(policy,verified_at='2026-10-03T13:00:00Z')
    assert project(policy,rows)['status']=='unavailable'
    assert project(policy,rows,cutoff='2026-10-03T13:00:00Z')['status']=='available'


def test_future_event_date_is_not_now_in_new_york(policy):
    rows=receipts(policy)
    v=project(policy,rows,cutoff='2026-09-30T02:00:00Z')
    assert v['reason']=='not_available_as_of' and not v['metrics']

@pytest.mark.parametrize('change',[{'reference_period':'2026-07'},
    {'expected_reference_period':'2026-07'}, {'forecast_period':'July 2026'}])
def test_explicit_reference_conflict_is_never_guessed(policy,change):
    ev={**EVENT,**change};v=project(policy,receipts(policy),ev)
    if len(change)==1 and 'reference_period' in change:
        assert all(m['reason']=='reference_period_mismatch' for m in v['metrics'])
    else: assert v['reason']=='reference_period_conflict'


def test_delayed_release_keeps_explicit_reference(policy):
    p=publication(expected_reference_period='July 2026')
    p['actual']['reference_period']='July 2026'
    rows=official.normalize_publication(p,defects_path=policy)
    v=project(policy,rows,{'type':'PCE','date':'2026-09-30','reference_period':'July 2026'})
    assert v['status']=='available' and v['metrics'][0]['period']=='2026-07'

@pytest.mark.parametrize('ref',['The',[],{},'2026-13'])
def test_invalid_reference_is_visible(policy,ref):
    v=project(policy,receipts(policy),{**EVENT,'reference_period':ref})
    assert v['reason']=='invalid_reference_period'


def test_no_explicit_period_does_not_choose_between_two_eligible_periods(policy):
    later=publication(expected_reference_period='July 2026',source_sha256='b'*64)
    later['actual']['reference_period']='July 2026'
    rows=receipts(policy)+official.normalize_publication(later,defects_path=policy)
    v=project(policy,rows,{'type':'PCE','date':'2026-09-30'})
    assert all(m['reason']=='ambiguous_reference_period' for m in v['metrics'])


def test_exact_event_day_and_release_alias(policy):
    v=project(policy,receipts(policy),{'type':'CPI','date':'2026-09-30'})
    assert all(m['reason']=='no_matching_receipt' for m in v['metrics'])
    v=project(policy,receipts(policy),{'type':'PCE','date':'2026-09-29'})
    assert all(m['reason']=='no_matching_receipt' for m in v['metrics'])

@pytest.mark.parametrize('field,value',[
    ('unit','basis_points'),('metric_id','pce_headline_yoy'),('sequence','revised'),
    ('schema','untrusted.v1'),('receipt_id','made-up'),('source_sha256','x'*64),
    ('actual',True),('actual','0.3'),('actual',float('nan')),('actual',float('inf')),
    ('actual_raw',True),('actual_raw',{}),('publisher','a website'),('parser_version',True),
    ('observed_at',[]),('verified_at','2026-09-30T00:00:00Z'),
    ('automatic_scoring_eligible',False),('source_released_at','2026-09-29T12:30:00Z'),
    ('source_url','https://www.bea.gov@evil.example/news'),
    ('source_url','https://user@www.bea.gov/news'),('source_url','https://www.bea.gov:444/news'),
    ('source_url','https://www.bea.gov/news\n'),('source_url','javascript:alert(1)'),
    ('source_url','https://www.bea.gov\\evil.example/'),
])
def test_integrity_failures_are_local_and_do_not_surface_a_number(policy,field,value):
    rows=receipts(policy);rows[0][field]=value
    v=project(policy,rows)
    assert v['status']=='partial'
    assert v['metrics'][0]['actual'] is None
    assert v['metrics'][1]['status']=='available'


def test_zero_and_negative_values_not_missing(policy):
    p=publication();p['actual'].update(headline_mom=0,core_mom=-.1)
    rows=official.normalize_publication(p,defects_path=policy)
    v=project(policy,rows)
    assert [m['display_value'] for m in v['metrics']]==['0.0','-0.1']


def test_duplicate_identical_receipt_is_not_confirmation_or_ambiguity(policy):
    rows=receipts(policy);v=project(policy,rows+deepcopy(rows))
    assert v['available_count']==2 and v['status']=='available'


def test_same_receipt_id_with_conflicting_evidence_is_withheld(policy):
    rows=receipts(policy);other=dict(rows[0],verified_at='2026-09-30T12:33:00Z')
    v=project(policy,rows+[other])
    assert v['metrics'][0]['reason']=='conflicting_first_receipts'


def test_equal_time_different_first_receipts_not_list_order_winner(policy):
    rows=receipts(policy)+receipts(policy,source_sha256='b'*64)
    v=project(policy,rows)
    assert all(m['reason']=='conflicting_first_receipts' for m in v['metrics'])
    assert v==project(policy,list(reversed(rows)))


def test_selection_delegates_to_canonical_owner(policy,monkeypatch):
    calls=[];original=official.canonical_actual
    def spy(*args,**kw): calls.append(args[1:3]);return original(*args,**kw)
    monkeypatch.setattr(official,'canonical_actual',spy)
    assert project(policy,receipts(policy))['status']=='available'
    assert calls==[('pce_headline','2026-08'),('pce_core','2026-08')]


def test_correction_candidate_never_replaces_first_and_is_time_bound(policy):
    rows=receipts(policy);p=publication(source_sha256='b'*64,first_seen_at='2026-09-30T14:01:00Z',
        verified_at='2026-09-30T14:02:00Z');p['actual']['headline_mom']=.9
    novel=official.reconcile_receipts({'schema':'release_publications.v2','publications':[p]},rows,defects_path=policy)
    assert novel[0]['row_type']=='correction_candidate'
    early=project(policy,rows+novel)
    assert not early['metrics'][0]['correction_pending'] and early['metrics'][0]['actual']==.3
    late=project(policy,rows+novel,cutoff='2026-09-30T14:02:00Z')
    assert late['metrics'][0]['correction_pending'] and late['metrics'][0]['actual']==.3
    alone=project(policy,novel,cutoff='2026-09-30T14:02:00Z')
    assert alone['metrics'][0]['reason']=='no_canonical_first_receipt'


def test_quarantine_never_revived_by_missing_or_damaged_policy(policy):
    rows=receipts(policy)
    policy.write_text(json.dumps({'schema':'official_actual_defects.v1','defects_by_receipt':{rows[0]['receipt_id']:None}}))
    assert project(policy,rows)['metrics'][0]['reason']=='quarantined'
    policy.unlink()
    assert project(policy,rows)['reason']=='quarantine_policy_unavailable'
    policy.write_text('{')
    assert project(policy,rows)['reason']=='quarantine_policy_unavailable'


def test_policy_change_mid_projection_is_not_mixed_evidence(policy,monkeypatch):
    rows=receipts(policy);orig=official.canonical_actual
    def changing(*args,**kwargs):
        out=orig(*args,**kwargs)
        policy.write_text(policy.read_text()+' ')
        return out
    monkeypatch.setattr(official,'canonical_actual',changing)
    v=project(policy,rows)
    assert v['reason']=='quarantine_policy_changed' and v['available_count']==0 and not v['metrics']

@pytest.mark.parametrize('rows',[None,'',{},2])
def test_absent_source_not_empty(policy,rows):
    assert project(policy,rows)['reason']=='source_unavailable'


def test_loaded_empty_and_partial_inputs_remain_distinct(policy):
    empty=project(policy,[])
    assert empty['reason'] is None and all(m['reason']=='no_matching_receipt' for m in empty['metrics'])
    partial=project(policy,[None]+receipts(policy))
    assert partial['source_partial'] is True and partial['available_count']==2


def test_attach_preserves_copies_and_malformed_members(policy):
    events=[dict(EVENT),None];before=deepcopy(events)
    out=view.attach_event_actual_evidence(events,receipts(policy),as_of=ASOF,defects_path=policy)
    assert events==before and out[0] is not events[0] and out[1] is None
    assert out[0]['official_evidence']['status']=='available'
    assert view.attach_event_actual_evidence(None,[],as_of=ASOF,defects_path=policy) is None
    assert view.attach_event_actual_evidence([],[],as_of=ASOF,defects_path=policy)==[]


def test_actual_committed_pce_repair_does_not_leak_later_verification():
    fixture=json.loads((ROOT/'tests/fixtures/events_news_official_receipts.json').read_text())
    rows=fixture['rows'];policy=ROOT/'tests/fixtures/events_news_actual_defects.json'
    event={'type':'PCE','date':'2026-07-30','reference_period':'June 2026'}
    early=view.event_actual_evidence(event,rows,as_of='2026-07-31T23:59:59Z',defects_path=policy)
    assert early['available_count']==0 and all(m['reason']=='quarantined' for m in early['metrics'])
    late=view.event_actual_evidence(event,rows,as_of='2026-08-11T08:24:15.196500Z',defects_path=policy)
    assert late['status']=='available'
    assert [m['receipt_id'] for m in late['metrics']]==['official_actual:fdb31afc7a857ad770470afe','official_actual:51508ae0ef8aae836a814def']
    assert late['metrics'][0]['observed_at'].startswith('2026-07-30')
    assert late['metrics'][0]['available_at'].startswith('2026-08-11')


def test_actual_committed_cpi_positive_without_fresh_publisher_claim():
    rows=json.loads((ROOT/'tests/fixtures/events_news_official_receipts.json').read_text())['rows']
    v=view.event_actual_evidence({'type':'CPI','date':'2026-08-12'},rows,as_of='2026-08-12T12:31:00Z',defects_path=ROOT/'tests/fixtures/events_news_actual_defects.json')
    assert v['status']=='available'
    assert [m['display_value'] for m in v['metrics']]==['0.1','0.2']


def test_missing_verification_time_stays_unavailable_even_with_valid_observed_time(policy):
    rows=receipts(policy)
    for row in rows:row['verified_at']=None
    v=project(policy,rows)
    assert v['available_count']==0
    assert all(m['reason']=='verification_time_missing' for m in v['metrics'])


def test_cutoff_input_is_retained_for_exact_renderer_binding(policy):
    assert project(policy,receipts(policy))['as_of_input']==ASOF


@pytest.mark.parametrize('precision',[0,-1,2,True,None,12])
def test_inconsistent_precision_cannot_change_or_overstate_the_display(policy,precision):
    rows=receipts(policy);rows[0]['published_precision']=precision
    v=project(policy,rows)
    assert v['metrics'][0]['actual'] is None
    assert v['metrics'][0]['reason']=='published_precision_mismatch'
    assert v['metrics'][1]['display_value']=='0.2'


def test_a_number_is_not_rounded_into_a_different_observation(policy):
    p=publication();p['actual']['headline_mom']=.31
    rows=official.normalize_publication(p,defects_path=policy)
    assert rows and rows[0]['actual']==.31
    v=project(policy,rows)
    assert v['metrics'][0]['reason']=='published_precision_mismatch'
    assert v['metrics'][0]['actual'] is None


def test_recent_release_bridge_keeps_forward_calendar_and_adds_ledger_result(policy):
    future={'type':'GDP','date':'2026-10-02','label':'GDP'}
    rows=receipts(policy)
    out=view.attach_recent_event_actual_evidence(
        [future],rows,as_of=ASOF,lookback_days=7,defects_path=policy)
    assert out[0]['type']=='GDP' and 'official_evidence' in out[0]
    recent=[e for e in out if isinstance(e,dict) and e.get('result_only')]
    assert len(recent)==1
    assert recent[0]['type']=='PCE' and recent[0]['date']=='2026-09-30'
    assert recent[0]['official_evidence']['status']=='available'
    assert recent[0]['source']=='official_actual_ledger'
    assert recent[0]['is_context_only'] is True


def test_recent_release_bridge_deduplicates_existing_typed_event(policy):
    rows=receipts(policy)
    event={'type':'PCE','date':'2026-09-30','label':'scheduled row'}
    out=view.attach_recent_event_actual_evidence(
        [event],rows,as_of=ASOF,lookback_days=7,defects_path=policy)
    assert len(out)==1 and out[0]['label']=='scheduled row'
    assert out[0]['official_evidence']['status']=='available'


def test_recent_release_bridge_ignores_old_correction_and_malformed_rows(policy):
    rows=receipts(policy)
    old=[dict(r,release_date='2026-09-01') for r in rows]
    correction=dict(rows[0],row_type='correction_candidate',release_date='2026-09-30')
    out=view.attach_recent_event_actual_evidence(
        [],old+[correction,None,{'release':'made-up','release_date':'2026-09-30'}],
        as_of=ASOF,lookback_days=7,defects_path=policy)
    assert out==[]


@pytest.mark.parametrize('lookback',[-1,32,True])
def test_recent_release_bridge_invalid_lookback_falls_back_without_synthetic_rows(policy,lookback):
    rows=receipts(policy)
    out=view.attach_recent_event_actual_evidence(
        [],rows,as_of=ASOF,lookback_days=lookback,defects_path=policy)
    assert out==[]


def test_recent_release_bridge_invalid_cutoff_does_not_invent_history(policy):
    rows=receipts(policy)
    out=view.attach_recent_event_actual_evidence(
        [],rows,as_of='bad',lookback_days=7,defects_path=policy)
    assert out==[]
