from copy import deepcopy
from datetime import datetime, timezone
import pytest

from engine.exposure_outlook_prices import audit_terminal_intraday


def payload(day='2026-09-17'):
    epoch = int(datetime.fromisoformat(day+'T09:30:00+00:00').timestamp())
    return {'t':'SPY','tf':'5m','session_date':day,'bars':[[epoch,100.,101.,99.,100.5,1000]],
            'source_evidence':{'schema':'terminal.intraday_source_evidence.v1','symbol':'SPY',
              'requested_timeframe':'5m','session':'regular',
              'timestamp_basis':'market_local_display_epoch',
              'response_scope':{'requested_date':day,'returned_bars':1,
                                'first_bar_time':epoch,'last_bar_time':epoch},
              'source_counts':{'stored_5m':1,'stored_1h':0,'live_tail':0,'unattributed':0},
              'point_in_time_availability':'not_verified','instrument_identity':'not_verified',
              'price_adjustment':'not_verified','completeness':'not_assessed'}}


def audit(doc, **kwargs):
    return audit_terminal_intraday(doc,root='SPY',session='2026-09-17',
                                   as_of='2026-09-18T20:00:00Z',**kwargs)


def test_market_display_epoch_is_not_a_utc_market_timestamp():
    out=audit(payload())
    assert out['first_bar_open_utc']=='2026-09-17T13:30:00+00:00'
    assert out['last_bar_close_utc']=='2026-09-17T13:35:00+00:00'
    assert out['bar_count']==1
    assert out['forecast_eligible'] is False
    assert 'POINT_IN_TIME_AVAILABILITY_NOT_VERIFIED' in out['reason_codes']


def test_dst_uses_session_date_not_current_offset():
    out=audit_terminal_intraday(payload('2026-01-15'),root='SPY',session='2026-01-15',
                                as_of='2026-01-15T21:00:00Z')
    assert out['first_bar_open_utc']=='2026-01-15T14:30:00+00:00'


def test_unknown_timestamp_basis_is_not_guessed():
    doc=payload();doc['source_evidence']['timestamp_basis']='unknown'
    out=audit(doc)
    assert out['first_bar_open_utc'] is None
    assert 'UNSUPPORTED_TIMESTAMP_BASIS' in out['reason_codes']


def test_evidence_root_and_count_have_to_match_bytes():
    doc=payload();doc['source_evidence']['symbol']='QQQ'
    doc['source_evidence']['response_scope']['returned_bars']=10
    codes=audit(doc)['reason_codes']
    assert 'IDENTITY_MISMATCH' in codes
    assert 'SOURCE_EVIDENCE_COUNT_MISMATCH' in codes


@pytest.mark.parametrize('bar', [[1,100,99,101,100,2],[1,100,101,99,0,2],
                                  [1,100,101,99,100,-1], [True,100,101,99,100,1],
                                  [1,100,101,99,float('nan'),1], [1,100,101]])
def test_invalid_ohlc_cannot_be_a_price_feature(bar):
    doc=payload();doc['bars']=[bar]
    assert 'INVALID_PRICE_BARS' in audit(doc)['reason_codes']


def test_bar_close_after_cutoff_is_not_available_input():
    out=audit_terminal_intraday(payload(),root='SPY',session='2026-09-17',
                                as_of='2026-09-17T13:32:00Z')
    assert 'BAR_NOT_CLOSED_BY_CUTOFF' in out['reason_codes']


def test_scope_date_and_first_last_must_match():
    doc=payload();doc['source_evidence']['response_scope']['last_bar_time']+=300
    assert 'SOURCE_EVIDENCE_RANGE_MISMATCH' in audit(doc)['reason_codes']


def test_no_evidence_no_inferred_identity_or_availability():
    doc=payload();del doc['source_evidence']
    assert 'SOURCE_EVIDENCE_MISSING' in audit(doc)['reason_codes']


def test_blank_bars_not_a_zero_return():
    doc=payload();doc['bars']=[]
    assert 'PRICE_BARS_UNAVAILABLE' in audit(doc)['reason_codes']


def test_validity_flags_cannot_promote_model():
    doc=payload()
    for key in ('point_in_time_availability','instrument_identity','price_adjustment','completeness'):
        doc['source_evidence'][key]='verified'
    out=audit(doc)
    assert out['forecast_eligible'] is False
    assert out['authority_tier']=='research'


def _outcome_payload():
    from datetime import datetime, timezone
    start = int(datetime(2026, 9, 18, 9, 30, tzinfo=timezone.utc).timestamp())
    bars = [[start+i*300, 100., 100.1, 99.9, 100., 10.] for i in range(78)]
    return dict(t='SPY', tf='5m', session_date='2026-09-18', bars=bars,
                source_evidence=dict(schema='terminal.intraday_source_evidence.v1',
                    symbol='SPY', requested_timeframe='5m', session='regular',
                    timestamp_basis='market_local_display_epoch',
                    response_scope=dict(requested_date='2026-09-18', returned_bars=78,
                        first_bar_time=bars[0][0], last_bar_time=bars[-1][0]),
                    source_counts=dict(live_tail=78)))


def _label_outcomes(p=None, **kwargs):
    import importlib.util
    assert importlib.util.find_spec('engine.exposure_outlook_outcomes') is not None
    from engine.exposure_outlook_outcomes import label_price_outcomes
    options=dict(root='SPY', session='2026-09-18', origin='2026-09-18T14:00:00Z',
                 as_of='2026-09-18T21:00:00Z', session_open='2026-09-18T13:30:00Z',
                 session_close='2026-09-18T20:00:00Z', calendar_ref='fixture:session',
                 barriers=dict(lower=99., upper=101., known_at='2026-09-18T14:00:00Z',
                               source_ref='fixture:frozen-band'))
    options.update(kwargs)
    return label_price_outcomes(p or _outcome_payload(), **options)


def _outcome(result, horizon=30):
    return next(row for row in result['outcomes'] if row['horizon']==horizon)


def test_outcomes_exact_horizons_and_close_are_observations_not_forecasts():
    p = _outcome_payload(); p['bars'][11][4] = 100.05
    out = _label_outcomes(p); row = _outcome(out)
    assert [r['horizon'] for r in out['outcomes']] == [30, 60, 90, 120, 'close']
    assert row['endpoint_return_pct'] == pytest.approx(.05)
    assert row['target_end'] == '2026-09-18T14:30:00+00:00'
    assert row['endpoint_status'] == 'observed' and row['path_status'] == 'complete'
    assert out['can_publish_forecast'] is False
    assert out['input_research_admission'] == 'not_qualified'
    assert out['outcome_known_at'] is None


def test_outcomes_same_bar_double_touch_does_not_invent_order():
    p = _outcome_payload(); p['bars'][6][2:4] = [101.2, 98.8]
    row = _outcome(_label_outcomes(p))
    assert row['upper_touched'] and row['lower_touched'] and row['exited_band']
    assert row['first_touch'] == 'same_bar_unknown_order'


def test_outcomes_touch_is_not_exit_and_endpoint_containment_is_separate():
    p = _outcome_payload(); p['bars'][6][2] = 101.
    row = _outcome(_label_outcomes(p))
    assert row['upper_touched'] is True and row['exited_band'] is False
    assert row['endpoint_inside_band'] is True and row['first_touch'] == 'upper'


def test_outcomes_missing_band_is_null_not_false():
    row = _outcome(_label_outcomes(barriers=None))
    assert row['upper_touched'] is None and row['endpoint_inside_band'] is None


def _refresh_outcome_scope(p):
    e = p['source_evidence']; b = p['bars']
    e['response_scope'].update(returned_bars=len(b), first_bar_time=b[0][0], last_bar_time=b[-1][0])
    e['source_counts'] = dict(live_tail=len(b))


def test_outcomes_gap_preserves_endpoint_but_not_false_path_claim():
    p = _outcome_payload(); del p['bars'][8]; _refresh_outcome_scope(p)
    row = _outcome(_label_outcomes(p))
    assert row['endpoint_status'] == 'observed' and row['endpoint_return_pct'] == 0.
    assert row['path_status'] == 'incomplete' and row['upper_touched'] is None
    assert row['first_touch'] is None and 'PATH_INCOMPLETE' in row['reason_codes']


def test_outcomes_pending_horizon_cannot_read_future_bars():
    row = _outcome(_label_outcomes(as_of='2026-09-18T14:20:00Z'))
    assert row['endpoint_status'] == 'pending' and row['endpoint_return_pct'] is None
    assert row['upper_touched'] is None and 'OUTCOME_NOT_MATURE' in row['reason_codes']


def test_outcomes_early_close_is_explicit_without_horizon_clipping():
    out = _label_outcomes(origin='2026-09-18T16:30:00Z', session_close='2026-09-18T17:00:00Z')
    assert _outcome(out, 30)['endpoint_status'] == 'observed'
    assert _outcome(out, 60)['reason_codes'] == ['HORIZON_BEYOND_SESSION']
    assert _outcome(out, 'close')['duration_minutes'] == 30


def test_outcomes_missing_anchor_refuses_all_targets():
    out = _label_outcomes(origin='2026-09-18T14:01:00Z')
    assert out['status'] == 'unavailable' and 'ANCHOR_CLOSE_MISSING' in out['reason_codes']


def test_outcomes_refuses_post_origin_barrier_definition():
    with pytest.raises(ValueError, match='barrier'):
        _label_outcomes(barriers=dict(lower=99., upper=101.,
            known_at='2026-09-18T14:01:00Z', source_ref='fixture:late'))


def test_outcomes_pre_origin_excursion_is_not_a_future_touch():
    p = _outcome_payload(); p['bars'][4][2:4] = [105., 95.]
    row = _outcome(_label_outcomes(p))
    assert row['upper_touched'] is False and row['lower_touched'] is False


def test_outcomes_duplicate_candle_cannot_be_silently_overwritten():
    p = _outcome_payload(); p['bars'].insert(8, list(p['bars'][8])); _refresh_outcome_scope(p)
    out = _label_outcomes(p)
    assert out['status'] == 'unavailable' and 'DUPLICATE_BAR_TIME' in out['reason_codes']


def test_outcomes_source_identity_failure_is_not_a_label():
    p = _outcome_payload(); p['source_evidence']['symbol'] = 'QQQ'
    out = _label_outcomes(p)
    assert out['status'] == 'unavailable' and 'IDENTITY_MISMATCH' in out['reason_codes']


def test_outcomes_corrected_source_keeps_target_and_changes_observation():
    p = _outcome_payload(); before = _outcome(_label_outcomes(p))
    p['bars'][11][4] = 100.05; after = _outcome(_label_outcomes(p))
    assert before['target_id'] == after['target_id']
    assert before['observation_id'] != after['observation_id']


def test_outcomes_response_clock_cannot_predate_the_outcome_it_claims():
    p = _outcome_payload()
    p['source_evidence']['assembly_clock'] = dict(served_at='2026-09-18T14:10:00Z')
    row = _outcome(_label_outcomes(p))
    assert row['endpoint_status'] == 'unavailable'
    assert row['reason_codes'] == ['RESPONSE_PREDATES_OUTCOME']


def test_outcomes_response_after_cutoff_does_not_backdate_availability():
    p = _outcome_payload()
    p['source_evidence']['assembly_clock'] = dict(served_at='2026-09-18T21:01:00Z')
    out = _label_outcomes(p)
    assert out['reason_codes'] == ['RESPONSE_OBSERVED_AFTER_CUTOFF']
    assert out['outcome_known_at'] is None


def test_outcomes_gap_may_prove_touch_but_never_first_touch_order():
    p = _outcome_payload(); p['bars'][9][2] = 101.2
    del p['bars'][8]; _refresh_outcome_scope(p)
    row = _outcome(_label_outcomes(p))
    assert row['upper_touched'] is True and row['lower_touched'] is None
    assert row['first_touch'] is None and row['exited_band'] is True


def test_outcomes_opening_price_can_resolve_a_double_touch_bar():
    p = _outcome_payload(); p['bars'][6][1:4] = [101.1, 101.2, 98.8]
    row = _outcome(_label_outcomes(p))
    assert row['first_touch'] == 'upper'
    assert row['first_touch_interval']['start'] == '2026-09-18T14:00:00+00:00'


def test_outcomes_missing_endpoint_never_interpolates():
    p = _outcome_payload(); del p['bars'][11]; _refresh_outcome_scope(p)
    row = _outcome(_label_outcomes(p))
    assert row['endpoint_price'] is None and row['endpoint_return_pct'] is None
    assert 'ENDPOINT_CLOSE_MISSING' in row['reason_codes']


def test_outcomes_caller_window_is_not_a_second_verified_calendar():
    out = _label_outcomes()
    assert out['session_window']['qualification'] == 'caller_declared'
    assert out['session_window']['source_ref'] == 'fixture:session'
