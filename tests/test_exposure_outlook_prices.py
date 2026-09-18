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
