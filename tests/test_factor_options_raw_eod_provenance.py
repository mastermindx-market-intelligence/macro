"""Source-provenance audit over synthetic vendor-like EOD Greek CSV inputs."""
from datetime import date
from importlib import import_module
from pathlib import Path
import json
import pandas as pd
import pytest

MODULE='research.factor_atlas.session3.raw_eod_provenance'
DAY=date(2026,10,8)

@pytest.fixture
def m():
    assert (Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/raw_eod_provenance.py').is_file(), 'raw vendor clock/mark audit module missing'
    return import_module(MODULE)

@pytest.fixture
def cohort():
    raw=pd.DataFrame([{
        'symbol':'AAPL','expiration':'20261106','strike':250.,'right':side,
        'timestamp':'2026-10-08T15:59:00','underlying_timestamp':'2026-10-08T17:00:00',
        'bid':bid,'ask':ask,'underlying_price':255.,
        'implied_vol':iv,'iv_error':0.,'delta':delta,'gamma':.01,'vanna':.005,'charm':-.01,
        'bid_condition':1,'ask_condition':1
    } for side,bid,ask,iv,delta in [('CALL',15.,15.5,.25,.5),('PUT',9.5,10.,.27,-.5)]])
    stored=raw.drop(columns=['timestamp','underlying_timestamp','bid_condition','ask_condition']).rename(columns={'symbol':'root'}).copy()
    stored['expiration']=pd.to_datetime(stored['expiration'],format='%Y%m%d')
    stored['right']=stored['right'].map({'CALL':'C','PUT':'P'})
    stored['date']=pd.Timestamp(DAY)
    return raw,stored

def test_reproduces_original_archive_and_explicit_clock_loss(m,cohort):
    raw,stored=cohort
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['raw_rows']==r['archived_rows']==r['matching_contract_keys']==2
    assert all(n==0 for n in r['numeric_field_disagreements'].values())
    assert r['numeric_report_reproduced'] is True
    assert r['original_option_timestamp_in_vendor_report'] is True
    assert r['original_underlier_timestamp_in_vendor_report'] is True
    assert r['option_timestamp_lost_in_archive'] is True
    assert r['underlier_timestamp_lost_in_archive'] is True
    assert r['persisted_bid_ask_conditions_available'] is False
    assert r['historical_quote_time_qualified'] is False
    assert r['historical_known_at_qualified'] is False
    assert r['source_rights_for_publication_certified'] is False
    assert r['publishable_original_market_data'] is False
    assert '250.0' not in json.dumps(r) and '255.0' not in json.dumps(r)

def test_detects_archived_price_mismatch_without_exposing_price(m,cohort):
    raw,stored=cohort
    stored.loc[stored.right=='C','bid']*=1.1
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['numeric_field_disagreements']['bid']==1
    assert r['numeric_report_reproduced'] is False
    assert r['source_consistency_reasons']==['NUMERIC_REPRODUCTION_MISMATCH']

def test_missing_expiry_contract_refused_as_missing_key(m,cohort):
    raw,stored=cohort
    stored=stored.loc[stored.right=='C'].copy()
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['missing_from_archive']==1 and r['numeric_report_reproduced'] is False

def test_identical_vendor_duplicate_contract_rows_are_deduped_with_count(m,cohort):
    raw,stored=cohort
    dupe=pd.concat([raw,raw.iloc[[0]]],ignore_index=True)
    r=m.audit_eod_report(raw=dupe,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['raw_rows']==3 and r['vendor_duplicate_full_rows']==1
    assert r['numeric_report_reproduced'] is True

def test_conflicting_vendor_same_contract_refused(m,cohort):
    raw,stored=cohort
    contradiction=raw.iloc[[0]].copy()
    contradiction['implied_vol']=.92
    raw=pd.concat([raw,contradiction],ignore_index=True)
    with pytest.raises(ValueError,match='duplicate contract'):
        m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)

def test_future_or_wrong_root_identity_refused(m,cohort):
    raw,stored=cohort
    raw.loc[0,'symbol']='MSFT'
    with pytest.raises(ValueError,match='root'):
        m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)

def test_raw_timestamp_calendar_mismatch_is_explicit_not_backdated(m,cohort):
    raw,stored=cohort
    raw.loc[0,'timestamp']='2026-10-07T16:00:00'
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['raw_report_timestamp_wrong_session_rows']==1
    assert r['numeric_report_reproduced'] is False
    assert 'SOURCE_DATE_AMBIGUOUS' in r['source_consistency_reasons']

def test_missing_raw_clock_never_invented_from_stored_date(m,cohort):
    raw,stored=cohort
    raw=raw.drop(columns=['underlying_timestamp'])
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['original_underlier_timestamp_in_vendor_report'] is False
    assert r['historical_quote_time_qualified'] is False

def test_raw_timestamp_unique_count_is_not_quote_age_certification(m,cohort):
    raw,stored=cohort
    raw.loc[0,'timestamp']='2026-10-08T09:00:00'
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['option_report_timestamp_distinct_count']==2
    assert r['historical_quote_time_qualified'] is False

@pytest.mark.parametrize('value',[None,1.2,{},False])
def test_invalid_date_refused(m,cohort,value):
    raw,stored=cohort
    with pytest.raises(ValueError,match='session'):
        m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=value)

def test_empty_report_refused_without_false_zero_quality(m):
    with pytest.raises(ValueError,match='nonempty'):
        m.audit_eod_report(raw=pd.DataFrame(),persisted=pd.DataFrame(),root='AAPL',requested_session=DAY)

def test_extra_source_row_is_detected(m,cohort):
    raw,stored=cohort
    extra=stored.iloc[[0]].copy()
    extra['strike']=255.
    stored=pd.concat([stored,extra],ignore_index=True)
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['not_in_new_vendor_report']==1
    assert r['numeric_report_reproduced'] is False

def test_source_dataframes_untouched(m,cohort):
    raw,stored=cohort
    oldraw=raw.copy(deep=True)
    oldstore=stored.copy(deep=True)
    m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    pd.testing.assert_frame_equal(raw,oldraw)
    pd.testing.assert_frame_equal(stored,oldstore)

def test_raw_eod_reconciliation_suite_inside_existing_options_code_job():
    import yaml
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    job=yaml.safe_load((root/'.github/ci/legacy-jobs.yml').read_text())['jobs']['options-skew-engine']
    assert job['gate']=='code' and job['scope']=='exclusive'
    assert 'research/factor_atlas/session3/raw_eod_provenance.py' in job['paths']
    assert 'tests/test_factor_options_raw_eod_provenance.py' in job['paths']
    commands='\n'.join(x.get('run','') for x in job['steps'])
    assert 'tests/test_factor_options_raw_eod_provenance.py' in commands

def test_vendor_iso_date_expiry_also_matches_incumbent_normalizer(m,cohort):
    raw,stored=cohort
    raw['expiration']='2026-11-06'
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['numeric_report_reproduced'] is True


def test_non_numeric_vendor_value_cannot_equal_missing_archive_numeric(m,cohort):
    raw,stored=cohort
    raw['implied_vol']=raw['implied_vol'].astype(object)
    raw.loc[0,'implied_vol']='not-a-number'
    stored.loc[0,'implied_vol']=float('nan')
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['numeric_report_reproduced'] is False
    assert r['numeric_field_disagreements']['implied_vol']==1


def test_infinite_greek_values_are_never_valid_matching_prices(m,cohort):
    raw,stored=cohort
    raw.loc[0,'gamma']=float('inf')
    stored.loc[0,'gamma']=float('inf')
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['numeric_report_reproduced'] is False
    assert r['numeric_field_disagreements']['gamma']==1


def test_legitimate_two_null_numeric_fields_can_be_reproduced(m,cohort):
    raw,stored=cohort
    raw.loc[0,'charm']=float('nan')
    stored.loc[0,'charm']=float('nan')
    r=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert r['numeric_field_disagreements']['charm']==0
    assert r['numeric_report_reproduced'] is True


def test_cross_session_underlying_mark_clock_is_disclosed_and_refused(m,cohort):
    raw,stored=cohort
    raw.loc[0,'underlying_timestamp']='2026-10-07T17:00:00'
    out=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert out['raw_underlier_timestamp_wrong_session_rows']==1
    assert 'UNDERLIER_MARK_SESSION_MISMATCH' in out['source_consistency_reasons']
    assert out['numeric_report_reproduced'] is False
    assert out['historical_quote_time_qualified'] is False


def test_malformed_underlying_mark_clock_counts_as_wrong_session(m,cohort):
    raw,stored=cohort
    raw.loc[0,'underlying_timestamp']='not-a-time'
    out=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert out['raw_underlier_timestamp_wrong_session_rows']==1
    assert 'UNDERLIER_MARK_SESSION_MISMATCH' in out['source_consistency_reasons']
    assert out['historical_known_at_qualified'] is False


def test_missing_underlying_clock_is_explicit_unknown_not_wrong_date(m,cohort):
    raw,stored=cohort
    raw=raw.drop(columns=['underlying_timestamp'])
    out=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert out['raw_underlier_timestamp_wrong_session_rows'] is None
    assert out['original_underlier_timestamp_in_vendor_report'] is False
    assert out['historical_quote_time_qualified'] is False


def test_ambiguous_numeric_epoch_report_time_is_never_accepted_as_calendar(m,cohort):
    raw,stored=cohort
    raw['timestamp']=raw['timestamp'].astype(object)
    raw.loc[0,'timestamp']=1791480000000000000
    with pytest.raises(ValueError,match='timestamp'):
        m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)


def test_explicit_iso8601_raw_clock_is_supported_without_inference_warning(m,cohort):
    raw,stored=cohort
    raw.loc[0,'timestamp']='2026-10-08T15:59:00.120'
    raw.loc[1,'underlying_timestamp']='2026-10-08T17:00:00.120'
    import warnings
    with warnings.catch_warnings(record=True) as logged:
        warnings.simplefilter('always')
        result=m.audit_eod_report(raw=raw,persisted=stored,root='AAPL',requested_session=DAY)
    assert result['numeric_report_reproduced'] is True
    assert not any('Could not infer format' in str(w.message) for w in logged)
