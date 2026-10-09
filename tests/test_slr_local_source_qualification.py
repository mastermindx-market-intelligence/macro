"""Frozen F01-F16 and supplementary, synthetic only; no source-store reads."""
from datetime import date
import json

import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def q():
    from research.structural_leadership_shock_resilience.local_source_qualification import adapter
    return adapter


def evidence(q, family='gics', **changes):
    payload = {'field': family, 'rows': [{'value': 'synthetic'}]}
    fields = dict(field_family=family, source_sha='1'*40,
                  source_owner_interface='lib/dataos/identity.py::VendorAliasTable',
                  dataset_designation='SYNTHETIC', source_object_sha256=q.digest(payload),
                  license_or_permission_receipt_ref='fixture:rights',
                  economic_valid_from='2013-01-01', economic_valid_to=None,
                  first_publication_or_filing_accepted_at='2013-01-01T00:00:00Z',
                  observed_ingested_at='2013-01-02T00:00:00Z',
                  revision_generation=0, knowledge_basis='ACTUALLY_FIRST_SEEN',
                  historical_identity_basis='OWNER_VALID_TIME',
                  coverage_by_era={'2014': 1}, evidence_refs=('fixture:source',),
                  status='PASS')
    fields.update(changes)
    return q.SourceQualificationResult(**fields), payload


def peer(i, **changes):
    row = dict(security_id=f'SEC:US-XNYS-S{i}', issuer_id=f'ISS:US-XNYS-I{i}',
               sector='Information Technology', instrument_type='CS',
               historical_identity_basis='OWNER_VALID_TIME',
               valid_from='2013-01-01', valid_to=None, known_at='2013-01-01T00:00:00Z',
               evidence_ref='fixture:historical-owner', lagged_adv=25_000_000,
               lagged_close=5, controls_at='2014-01-02', terminal_resolved=True)
    row.update(changes)
    return row


def test_F01_h7_does_not_condition_on_future_shock(q):
    rows = [{'id': i, 'baseline_eligible': True, 'R': r, 'Y': y, 'future_C': r == y}
            for i, (r, y) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)])]
    assert q.h7_risk_set(rows) == [0,1,2,3]
    full = np.array([(r['R'], r['Y']) for r in rows])
    selected = np.array([(r['R'], r['Y']) for r in rows if r['future_C']])
    assert (full[:,0]*full[:,1]).mean() == 0
    assert (selected[:,0]*selected[:,1]).mean() == 1


def test_F02_cash_ex_dividend_is_not_negative_total_return(q):
    assert q.economic_return(100, 99, cash=1, basis='split_adjusted') == 0
    price_only = 99/100-1
    assert price_only == pytest.approx(-.01)
    assert price_only/.02 == pytest.approx(-.5)
    with pytest.raises(q.NotQualified, match='DOUBLE_ADJUSTMENT'):
        q.economic_return(100,99,cash=1,basis=q.ADJUSTED)


def test_F03_peer_count_is_other_economic_issuers(q):
    rows = [peer(i) for i in range(20)] + [peer(20, issuer_id='ISS:US-XNYS-SUBJECT')]
    rows += [peer(21, issuer_id='ISS:US-XNYS-I0', lagged_adv=30_000_000)]
    chosen, excluded = q.freeze_peers(rows, 'ISS:US-XNYS-SUBJECT',
                                     'Information Technology', '2014-01-02')
    assert len(chosen) == 20
    assert chosen[0]['security_id'] == 'SEC:US-XNYS-S21'
    assert excluded['SAME_ISSUER'] == 1
    assert excluded['DUPLICATE_ISSUER'] == 1


def test_F04_ticker_reuse_gap_never_backfills_current_owner(q):
    rows = [dict(vendor='fixture',vendor_symbol='XYZ',security_id='SEC:US-XNYS-XYZ',
                 valid_from='2013-01-01',valid_to='2015-01-01'),
            dict(vendor='fixture',vendor_symbol='XYZ',security_id='SEC:US-XNYS-XYZ.2',
                 valid_from='2016-01-01',valid_to=None)]
    assert q.resolve_alias(rows,'fixture','XYZ','2014-01-01') == 'SEC:US-XNYS-XYZ'
    assert q.resolve_alias(rows,'fixture','XYZ','2015-06-01') is None
    assert q.resolve_alias(rows,'fixture','XYZ','2016-01-01') == 'SEC:US-XNYS-XYZ.2'


def test_F05_alias_end_is_exclusive_and_timeless_is_unknown(q):
    rows = [dict(vendor='fixture',vendor_symbol='OLD',security_id='SEC:US-XNYS-OLD',
                 valid_from='2018-01-01',valid_to='2018-06-01')]
    assert q.resolve_alias(rows,'fixture','OLD','2018-05-31')
    assert q.resolve_alias(rows,'fixture','OLD','2018-06-01') is None
    rows[0]['valid_from'] = rows[0]['valid_to'] = None
    with pytest.raises(q.NotQualified, match='UNDATED_ALIAS'):
        q.resolve_alias(rows,'fixture','OLD','2014-01-01')


@pytest.mark.parametrize('change,old,new', [('2016-09-01','Financials','Real Estate'),
    ('2018-10-01','Information Technology','Communication Services'),
    ('2023-03-20','Information Technology','Financials')])
def test_F06_dated_gics_and_etf_inception(q,change,old,new):
    records = [dict(valid_from='2013-01-01', valid_to=change, sector=old, taxonomy='GICS',
               knowledge_basis='ACTUALLY_FIRST_SEEN',known_at='2013-01-02T00:00:00Z',
               first_publication_or_filing_accepted_at='2013-01-01T00:00:00Z'),
               dict(valid_from=change,valid_to=None,sector=new,taxonomy='GICS',
               knowledge_basis='ACTUALLY_FIRST_SEEN',known_at='2013-01-02T00:00:00Z',
               first_publication_or_filing_accepted_at='2013-01-01T00:00:00Z')]
    before = str((pd.Timestamp(change)-pd.Timedelta(days=1)).date())
    assert q.historical_sector(records,before) == old
    assert q.historical_sector(records,change) == new
    with pytest.raises(q.NotQualified,match='BENCHMARK_NOT_LISTED'):
        q.check_benchmark_inception('2018-01-02','2018-06-18')


def test_F07_report_period_does_not_establish_public_availability(q):
    r,p = evidence(q,'market_cap',report_period_end='2019-06-29',
                   first_publication_or_filing_accepted_at='2019-07-31T20:30:00Z',
                   observed_ingested_at='2019-08-01T00:00:00Z')
    assert q.qualify(r,p,'2019-06-29T20:00:00Z').status == 'FAIL'
    assert q.qualify(r,p,'2019-08-01T20:00:00Z').status == 'PASS'


def test_F08_exchange_session_is_not_compressed(q):
    sessions = list(range(65))
    prices = {s:100+s for s in sessions if s != 50}
    with pytest.raises(q.NotQualified,match='MISSING_SESSION'):
        q.session_window(prices,sessions,64,21,master_sessions=sessions)


def test_F09_first_unknown_candidate_cannot_be_replaced(q):
    days = [{'offset':i,'status':'NONSHOCK'} for i in range(21,64)]
    days[0]['status'] = 'UNKNOWN'
    days[5]['status'] = 'SHOCK'
    assert q.first_challenge(days,0)['status'] == 'FIRST_CHALLENGE_UNOBSERVABLE'


def test_F10_fixed_effect_cells_need_distinct_issuers_and_variation(q):
    rows = [dict(issuer='A',date_index=1,sector='Tech',z=1),
            dict(issuer='B',date_index=1,sector='Tech',z=1),
            dict(issuer='C',date_index=2,sector='Tech',z=2)]
    counts = q.information_census(rows)
    assert counts['zero_within_cell_z_cells'] == 1
    assert counts['singleton_cells'] == 1
    assert counts['identifying_rows'] == 0


def test_F11_forward_label_window_starts_C_plus_one(q):
    assert q.measurement_window(10,21,40) == tuple(range(11,32))
    with pytest.raises(q.NotQualified,match='TERMINAL_UNRESOLVED'):
        q.economic_return(100,None,terminal_proceeds=None)
    assert q.economic_return(100,None,terminal_proceeds=40) == -.6


def test_F12_h5_future_rebound_requires_separate_landmark(q):
    with pytest.raises(q.NotQualified,match='FUTURE_FEATURE'):
        q.validate_feature_clock(10,dict(U=(12,.2)))
    assert q.measurement_window(12,21,40)[0] == 13


def test_F13_unknown_or_nonordinary_peers_do_not_count(q):
    rows = [peer(i) for i in range(20)]
    rows[0]['instrument_type'] = None
    rows[1]['instrument_type'] = 'PFD'
    rows[2]['historical_identity_basis'] = 'UNKNOWN'
    chosen, excluded = q.freeze_peers(rows,'ISS:US-XNYS-SUBJECT',
                                     'Information Technology','2014-01-02')
    assert len(chosen) == 17
    assert sum(excluded.values()) == 3


def test_F14_documentation_without_delivered_feed_is_not_admission(q):
    r,p = evidence(q,license_or_permission_receipt_ref=None,source_object_sha256=None)
    result = q.qualify(r,None,'2014-01-02T20:00:00Z')
    assert result.status == 'UNKNOWN'
    report = q.qualification_report([result])
    assert report['RESULT'] == 'NOT_ADMITTED'
    assert report['qualified_event_count'] is None
    assert report['admission_granted'] is False


def test_F15_schedule_announced_later_is_unknown(q):
    assert q.scheduled_earnings(10,15,12) is None
    assert q.scheduled_earnings(10,15,9) is True


def test_F16_mixed_basis_or_identity_splice_abstains(q):
    with pytest.raises(q.NotQualified,match='BASIS_CONFLICT'):
        q.validate_price_segment([q.ADJUSTED,'unadjusted_vendor_print'],['S','S'])
    with pytest.raises(q.NotQualified,match='IDENTITY_SPLICE'):
        q.validate_price_segment([q.ADJUSTED]*2,['OLD','NEW'])


@pytest.mark.parametrize('family', ['gics','identity','instrument_type','aliases',
                                  'total_returns','corporate_actions','membership',
                                  'market_cap','events','earnings_schedule'])
def test_each_source_family_pass_fail_unknown_and_digest_integrity(q,family):
    r,p = evidence(q,family)
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'PASS'
    assert q.qualify(r,{'tampered':True},'2014-01-02T20:00:00Z').status == 'FAIL'
    r,p = evidence(q,family,status='UNKNOWN')
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'UNKNOWN'
    r,p = evidence(q,family,status='FAIL')
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'FAIL'


@pytest.mark.parametrize('field', ['Y21','forward_return_21d','durable_winner',
                                  'clean_hold','CR1_state','AF1_outcome','RH1'])
def test_input_graph_rejects_outcome_columns(q,field):
    with pytest.raises(q.NotQualified,match='INPUT_GRAPH'):
        q.validate_input_graph({'nested':{field:0}})


@pytest.mark.parametrize('path', ['data/personality_timing/a.parquet',
    'data/research/winner_episodes.parquet','data/CR1/x','../data/AF1/x'])
def test_input_graph_rejects_protected_or_unprojected_paths(q,path):
    with pytest.raises(q.NotQualified,match='INPUT_GRAPH'):
        q.validate_input_graph({'input_path':path})


def test_hash_is_deterministic_order_invariant_and_finite(q):
    assert q.digest({'a':1,'b':2}) == q.digest({'b':2,'a':1})
    with pytest.raises(ValueError):
        q.digest({'a':float('nan')})


def test_first_seen_cannot_be_backdated_or_restated(q):
    r,p = evidence(q,observed_ingested_at='2012-01-01T00:00:00Z')
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'FAIL'
    r,p = evidence(q,observed_ingested_at='2026-01-01T00:00:00Z',revision_generation=2)
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'FAIL'
    r,p = evidence(q,observed_ingested_at='2026-01-01T00:00:00Z',
                   knowledge_basis='FINAL_VINTAGE_VALID_TIME_ONLY')
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'PASS'


@pytest.mark.parametrize('pages,expected', [
    ([{'page':1,'next_page':2,'events':['a']},{'page':2,'next_page':None,'events':['b']}],['a','b']),
    ([{'page':1,'next_page':2,'events':['a']}],None),
    ([{'page':1,'next_page':None,'events':['a','a']}],None),
    ([{'page':1,'next_page':None,'events':['a']}],None)])
def test_action_pages_duplicates_and_missing_events(q,pages,expected):
    if expected is None:
        with pytest.raises(q.NotQualified):
            q.action_receipt(pages,required_ids={'a','b'})
    else:
        assert q.action_receipt(pages,required_ids={'a','b'}) == expected


def test_lagged_peer_controls_no_current_day_rescue(q):
    rows = [peer(1,lagged_adv=24_999_999),peer(2,lagged_close=4.99),
            peer(3,controls_at='2014-01-03'),peer(4)]
    chosen,_ = q.freeze_peers(rows,'ISS:US-XNYS-SUBJECT','Information Technology','2014-01-02')
    assert [r['security_id'] for r in chosen] == ['SEC:US-XNYS-S4']


def test_first_challenge_requires_complete_window_and_same_D(q):
    days = [{'offset':i,'status':'NONSHOCK'} for i in range(21,64)]
    days[0]['status'] = 'SHOCK'
    result = q.first_challenge(days,0,watch={'onset':1,'state':'continuation'})
    assert result['status'] == 'ONSET_MISMATCH'
    assert q.first_challenge(days[1:],0)['status'] == 'FIRST_CHALLENGE_UNOBSERVABLE'
    assert q.first_challenge(days,0,watch={'onset':0,'state':'breakaway'})['status'] == 'NOT_CONTINUATION'


def test_shock_requires_200_of_252_complete_days_and_no_exits_disappear(q):
    history = np.tile(np.linspace(-.02,.02,252)[:,None],(1,20))
    today = np.full(20,-.04)
    assert q.common_shock(history,today,np.zeros(252))['status'] == 'SHOCK'
    history[:53,0] = np.nan
    assert q.common_shock(history,today,np.zeros(252))['status'] == 'UNKNOWN'
    history[:53,0] = 0
    today[0] = np.nan
    assert q.common_shock(history,today,np.zeros(252))['status'] == 'UNKNOWN'


def test_information_counts_occupied_blocks_not_event_rows(q):
    rows = [dict(issuer=f'I{i}', date_index=i,sector='Tech',z=i) for i in [0,1,62,63,125,126]]
    c = q.information_census(rows)
    assert c['occupied_63_session_blocks'] == 3
    assert c['dates'] == 6


def detector_fixture():
    dates = pd.bdate_range('2014-01-01',periods=190)
    c = np.full(190,100.)
    c[70:90] = np.linspace(100,140,20)
    c[90:] = 139
    v = np.full(190,300_000.)
    v[70:90] = 1_500_000
    bars = pd.DataFrame({'close':c,'volume':v},index=dates)
    benchmark = pd.Series(100.,index=dates)
    sectors = pd.Series('Information Technology',index=dates)
    return bars,{'XLK':benchmark,'SPY':benchmark},sectors


def test_full_prefix_detector_parity_and_cooldown(q):
    from engine.winner_autopsy import detect_episodes
    bars,bench,sectors = detector_fixture()
    original = detect_episodes({'S':bars},bench,{'S':'Information Technology'})
    replay = q.replay_detector(bars,bench,sectors,master_sessions=bars.index)
    assert replay['onsets'] == list(original.t0)
    assert len(replay['onsets']) > 0
    assert all((bars.index.get_loc(b)-bars.index.get_loc(a))>63
               for a,b in zip(replay['onsets'],replay['onsets'][1:]))
    assert q.parent_parity(replay,list(original.t0))['status'] == 'REPRODUCED_EXACTLY'


def test_watch_last_five_override_and_same_onset(q):
    from engine.winner_autopsy import compute_watch_states
    bars,bench,sectors = detector_fixture()
    for end in [85,95,110]:
        prefix=bars.iloc[:end]
        replay=q.replay_detector(prefix,bench,sectors.reindex(prefix.index),master_sessions=prefix.index)
        state=q.continuation(replay,prefix,replay['onsets'][0])
        expected=compute_watch_states({'S':prefix},bench,{'S':'Information Technology'},as_of=prefix.index[-1])
        assert state['state'] == expected.iloc[0]['state']
    assert q.continuation(replay,prefix,prefix.index[1])['status'] == 'ONSET_MISMATCH'


def test_missing_past_benchmark_blocks_full_prefix_parity(q):
    bars,bench,sectors = detector_fixture()
    bench['XLK']=bench['XLK'].drop(bars.index[69])
    with pytest.raises(q.NotQualified,match='BENCHMARK_HISTORY'):
        q.replay_detector(bars,bench,sectors,master_sessions=bars.index)


def test_primary_report_never_grants_review_or_zero_alpha(q):
    rows=[evidence(q,f)[0] for f in q.FAMILIES]
    report=q.qualification_report(rows)
    assert report['RESULT'] == 'SOURCE_QUALIFIED_FOR_INDEPENDENT_REVIEW'
    assert report['admission_granted'] is False
    assert report['qualified_event_count'] is None
    assert report['primary_estimate'] is None


def cli(q,monkeypatch,capsys,*,packet=None):
    import io
    import sys
    monkeypatch.setattr(sys,'argv',['slr-qualification']+(['--stdin'] if packet is not None else []))
    monkeypatch.setattr(sys,'stdin',io.StringIO(json.dumps(packet) if packet is not None else ''))
    code=q.main()
    return code,json.loads(capsys.readouterr().out)


def test_cli_default_is_reproducible_blocked_result(q,monkeypatch,capsys):
    outputs=[]
    for _ in range(2):
        code,report=cli(q,monkeypatch,capsys)
        assert code == 2
        outputs.append(report)
    assert outputs[0] == outputs[1]
    assert outputs[0]['RESULT'] == 'NOT_ADMITTED'


def test_cli_qualifies_stdin_packet_and_cannot_skip_outcome_firewall(q,monkeypatch,capsys):
    from dataclasses import asdict
    sources=[]
    for family in q.FAMILIES:
        r,p=evidence(q,family)
        sources.append({'receipt':asdict(r),'source_object':p})
    packet={'decision_at':'2014-01-02T20:00:00Z','sources':sources,'synthetic':True}
    code,report=cli(q,monkeypatch,capsys,packet=packet)
    assert code == 0
    assert report['admission_granted'] is False
    packet['sources'][0]['source_object']['forward_return_21d']=.2
    code,report=cli(q,monkeypatch,capsys,packet=packet)
    assert code == 2
    assert 'INPUT_GRAPH' in report['BLOCKERS'][0]


def test_complete_lookback_requires_504_master_sessions(q):
    with pytest.raises(q.NotQualified,match='LOOKBACK_UNAVAILABLE'):
        q.session_window({i:100. for i in range(504)},list(range(504)),503,504,master_sessions=list(range(504)))
    assert len(q.session_window({i:100. for i in range(505)},list(range(505)),504,504,master_sessions=list(range(505)))) == 505


def test_full_prefix_missing_subject_session_not_hidden(q):
    bars,bench,sectors=detector_fixture()
    master=bars.index
    bars=bars.drop(master[69])
    with pytest.raises(q.NotQualified,match='MASTER_SESSION'):
        q.replay_detector(bars,bench,sectors.reindex(bars.index),master_sessions=master)


def test_source_ref_and_zero_coverage_do_not_pass(q):
    r,p=evidence(q,study_spec_ref='wrong-study')
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'FAIL'
    r,p=evidence(q,coverage_by_era={'2014':0})
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status != 'PASS'


def test_history_basis_no_sec_sic_fallback(q):
    with pytest.raises(q.NotQualified,match='GICS_NOT_ADMITTED'):
        q.historical_sector([dict(valid_from='2013-01-01',valid_to=None,
                                  sector='Information Technology',taxonomy='SIC')], '2014-01-02')


def test_minimum_twenty_other_issuers_no_basket_reweight(q):
    assert q.common_shock(np.ones((252,19)),np.full(19,-.04),np.zeros(252))['status'] == 'UNKNOWN'


def test_lagged_factor_ruler_is_full_rank_and_does_not_fit_C(q):
    t=np.arange(252)
    market=np.sin(t)/100
    peers=.5*market+np.cos(t)/100
    subject=.001+1.2*market+.7*(np.cos(t)/100)+np.sin(t*.7)/1000
    fit=q.expected_move(subject,peers,market,subject_C=.01,peer_C=-.03,market_C=-.02)
    assert fit['training_n'] == 252
    assert fit['sector_beta'] == pytest.approx(.7,abs=.003)
    assert fit['market_beta'] == pytest.approx(1.2,abs=.003)
    changed=q.expected_move(subject,peers,market,subject_C=-.5,peer_C=.5,market_C=.3)
    assert changed['market_beta'] == fit['market_beta']
    assert changed['sector_beta'] == fit['sector_beta']
    with pytest.raises(q.NotQualified,match='FACTOR_RANK'):
        q.expected_move(subject,market,market,subject_C=0,peer_C=0,market_C=0)


def test_frozen_cutoff_uses_126_sessions_from_archive_end(q):
    sessions=list(range(300))
    assert q.onset_cutoff(sessions,299) == 173


def test_exact_200_complete_lagged_factor_observations(q):
    t=np.arange(252)
    m=np.sin(t)/100
    p=np.cos(t)/100
    r=.3*m+.5*p+np.sin(t*.7)/1000
    r[:52]=np.nan
    assert q.expected_move(r,p,m,subject_C=0,peer_C=0,market_C=0)['training_n'] == 200
    r[52]=np.nan
    with pytest.raises(q.NotQualified,match='FACTOR_COVERAGE'):
        q.expected_move(r,p,m,subject_C=0,peer_C=0,market_C=0)


def test_peer_publication_clock_compares_instant_not_calendar_day(q):
    rows=[peer(1,known_at='2014-01-02T21:01:00Z'),
          peer(2,known_at='2014-01-02T20:59:00Z')]
    chosen,excluded=q.freeze_peers(rows,'ISS:US-XNYS-SUBJECT','Information Technology',
                                  '2014-01-02',decision_at='2014-01-02T21:00:00Z')
    assert [r['security_id'] for r in chosen] == ['SEC:US-XNYS-S2']
    assert excluded['IDENTITY_NOT_KNOWN'] == 1


def test_terminal_cash_distribution_is_preserved_in_split_adjusted_units(q):
    assert q.economic_return(100,None,cash=1,basis='split_adjusted',terminal_proceeds=40) == pytest.approx(-.59)


def test_explicit_peer_cutoff_cannot_be_after_lagged_session(q):
    with pytest.raises(q.NotQualified,match='PEER_CUTOFF'):
        q.freeze_peers([peer(1)],'ISS:US-XNYS-SUBJECT','Information Technology',
                       '2014-01-02',decision_at='2014-01-03T21:00:00Z')


@pytest.mark.parametrize('path',['data/cr1.parquet','data/AF1_history.csv','data/RH1.json'])
def test_input_graph_protected_family_file_names(q,path):
    with pytest.raises(q.NotQualified,match='INPUT_GRAPH'):
        q.validate_input_graph({'source_path':path})


def test_full_prefix_cooldown_exact_63_boundary(q):
    dates=pd.bdate_range('2014-01-01',periods=200)
    candidates=pd.Series(False,index=dates)
    candidates.iloc[[63,126,127,190,191]]=True
    # A fire at exactly D+63 stays in the prior episode; D+64 starts a new one.
    assert q._onsets(candidates) == [dates[63],dates[127],dates[191]]


def test_peer_subject_must_be_economic_issuer_not_security_identifier(q):
    with pytest.raises(q.NotQualified,match='SUBJECT_ISSUER'):
        q.freeze_peers([peer(1)],'SEC:US-XNYS-SUBJECT','Information Technology','2014-01-02')


@pytest.mark.parametrize('clock', ['vendor_asof_date','report_period_end'])
def test_review_future_vendor_or_report_clock_not_first_seen(q,clock):
    r,p=evidence(q,**{clock:'2026-10-08'})
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'FAIL'


def gics_row(**changes):
    row=dict(valid_from='2013-01-01',valid_to=None,sector='Information Technology',
             taxonomy='GICS',knowledge_basis='ACTUALLY_FIRST_SEEN',
             first_publication_or_filing_accepted_at='2013-01-01T00:00:00Z',
             known_at='2013-01-02T00:00:00Z')
    row.update(changes)
    return row


def test_review_gics_restatement_does_not_claim_first_seen(q):
    row=gics_row(known_at='2018-01-01T00:00:00Z')
    with pytest.raises(q.NotQualified,match='GICS'):
        q.historical_sector([row],'2014-01-02')
    row['knowledge_basis']='FINAL_VINTAGE_VALID_TIME_ONLY'
    assert q.historical_sector([row],'2014-01-02') == 'Information Technology'


@pytest.mark.parametrize('row',[gics_row(sector='Technology'),
    gics_row(valid_from='2013-1-1'),gics_row(known_at=None),
    gics_row(first_publication_or_filing_accepted_at='2014-01-02T23:59:59Z')])
def test_review_gics_official_names_dates_and_publication_required(q,row):
    with pytest.raises(q.NotQualified,match='GICS'):
        q.historical_sector([row],'2014-01-02',decision_at='2014-01-02T21:00:00Z')


def test_review_terminal_payoff_cannot_be_silently_ignored(q):
    with pytest.raises(q.NotQualified,match='TERMINAL'):
        q.economic_return(100,50,basis='split_adjusted',terminal_proceeds=80)


def test_review_homogeneous_split_adjusted_segment_is_supported(q):
    q.validate_price_segment(['split_adjusted']*2,['S','S'])


def test_review_master_calendar_is_required_even_for_unique_compressed_index(q):
    bars,bench,sectors=detector_fixture()
    bars=bars.drop(bars.index[80])
    with pytest.raises(q.NotQualified,match='MASTER_SESSION'):
        q.replay_detector(bars,bench,sectors.reindex(bars.index))
    with pytest.raises(q.NotQualified,match='MASTER_SESSION'):
        q.session_window({i:100 for i in range(65)},list(range(65)),64,21)


def test_review_lookback_rejects_unsorted_calendar(q):
    sessions=[0,2,1,3]
    with pytest.raises(q.NotQualified,match='MASTER_SESSION'):
        q.session_window({i:100 for i in sessions},sessions,3,2,master_sessions=sessions)


def test_review_unknown_receipt_exclusions_remain_unknown(q):
    r,p=evidence(q,status='UNKNOWN',exclusion_codes=('GICS_NOT_ADMITTED',))
    result=q.qualify(r,p,'2014-01-02T20:00:00Z')
    assert result.status == 'UNKNOWN'
    assert 'GICS_NOT_ADMITTED' in result.exclusion_codes
    assert q.qualify(r,{'tampered':True},'2014-01-02T20:00:00Z').status == 'FAIL'


@pytest.mark.parametrize('old,new,old_etf,new_etf',[
    ('Financials','Real Estate','XLF','XLRE'),
    ('Information Technology','Communication Services','XLK','XLC'),
    ('Information Technology','Financials','XLK','XLF')])
def test_review_dated_sector_switch_requires_new_benchmark_prehistory(q,old,new,old_etf,new_etf):
    bars,_,sectors=detector_fixture()
    sectors.iloc[:100]=old
    sectors.iloc[100:]=new
    constant=pd.Series(100.,index=bars.index)
    benchmarks={old_etf:constant.copy(),new_etf:constant.copy()}
    before=q.replay_detector(bars.iloc[:100],benchmarks,sectors.iloc[:100],
                             master_sessions=bars.index[:100])
    full=q.replay_detector(bars,benchmarks,sectors,master_sessions=bars.index)
    assert [d for d in full['onsets'] if d < bars.index[100]] == before['onsets']
    benchmarks[new_etf].iloc[:90]=np.nan
    with pytest.raises(q.NotQualified,match='BENCHMARK_HISTORY'):
        q.replay_detector(bars,benchmarks,sectors,master_sessions=bars.index)


def test_review_detector_rejects_current_catalog_sector_alias(q):
    bars,bench,sectors=detector_fixture()
    sectors[:]='Technology'
    with pytest.raises(q.NotQualified,match='GICS_NOT_ADMITTED'):
        q.replay_detector(bars,bench,sectors,master_sessions=bars.index)


def test_review_final_vintage_vendor_date_is_not_local_first_possession(q):
    r,p=evidence(q,knowledge_basis='FINAL_VINTAGE_VALID_TIME_ONLY',
                 observed_ingested_at='2026-10-08T00:00:00Z',vendor_asof_date='2026-10-08')
    assert q.qualify(r,p,'2014-01-02T20:00:00Z').status == 'PASS'
