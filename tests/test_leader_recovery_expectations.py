from datetime import date,timedelta
import pandas as pd
import pytest
from engine.leader_recovery_expectations import project_expectations


def sample(**overrides):
    d={'asof':'2026-10-06','net_up_30d':3.,'breadth':1.,'n_analysts':3.,'n_covering':28.,'breadth_cov':.1071,'est_chg_30d':1.29,'est_chg_90d':11.92,'rev_growth_fwd':49.67,'eps_dispersion_norm':.4181}
    d.update(overrides);return pd.DataFrame([d],index=['PLTR'])


def run(df,ticker='PLTR'):
    return project_expectations(ticker,df,as_of=date(2026,10,8),sessions=[date(2026,10,5)+timedelta(days=i) for i in range(4)])


def test_percent_units_and_denominators_are_not_silently_changed():
    d=run(sample());r=d['readings']
    assert r['eps_estimate_change_30d']=={'value':1.29,'unit':'percent'}
    assert r['reviser_count_30d']['value']==3 and r['covering_analysts']['value']==28
    assert r['coverage_normalized_net_revisions']['value']==.1071
    assert d['revision_direction']=='POSITIVE_OBSERVATIONS'
    assert d['thesis_state']=='UNKNOWN' and not d['first_seen_qualified']
    assert d['source_age_sessions']==2


def test_negative_breadth_is_legal_not_dropped_as_missing():
    d=run(sample(net_up_30d=-3.,breadth=-1.,breadth_cov=-.1071,est_chg_30d=-1.29))
    assert d['readings']['net_reviser_breadth']['value']==-1
    assert d['revision_direction']=='NEGATIVE_OBSERVATIONS'


def test_source_dated_after_cut_is_refused():
    d=run(sample(asof='2026-10-09'))
    assert d['reason']=='source_after_price_cut' and d['readings']=={}


@pytest.mark.parametrize('asof',[None,'not a date'])
def test_undated_source_is_not_historical_evidence(asof):
    assert run(sample(asof=asof))['reason']=='source_date_unavailable'


def test_duplicate_ticker_and_unknown_identity_are_not_fuzzy_joined():
    assert run(pd.concat([sample(),sample()]))['reason']=='ambiguous_duplicate_ticker'
    assert run(sample(),'pltr')['reason']=='ticker_not_in_revisions_source'


def test_inconsistent_breadth_blocks_direction_but_preserves_source_readings():
    d=run(sample(breadth=.1))
    assert d['quality_flags']==['inconsistent_reviser_breadth']
    assert d['revision_direction']=='UNKNOWN'
    assert d['readings']['net_reviser_breadth']['value']==.1


def test_mixed_revision_signals_do_not_become_unqualified_positive():
    assert run(sample(est_chg_30d=-1.))['revision_direction']=='MIXED'


def test_nan_infinity_and_boolean_are_never_real_readings():
    d=run(sample(est_chg_30d=float('nan'),est_chg_90d=float('inf'),rev_growth_fwd=True))
    assert d['readings']['eps_estimate_change_30d']['value'] is None
    assert d['readings']['eps_estimate_change_90d']['value'] is None
    assert d['readings']['forward_revenue_growth_estimate']['value'] is None


def test_input_nonmutation_and_hash_changes_on_revision():
    df=sample();old=df.copy(deep=True);a=run(df);pd.testing.assert_frame_equal(df,old)
    b=run(sample(est_chg_30d=2.))
    assert a['source_fingerprint_sha256']!=b['source_fingerprint_sha256']


def test_coverage_ratio_is_not_assumed_to_be_bounded():
    d=run(sample(net_up_30d=5.,n_analysts=5.,n_covering=4.,breadth=1.,breadth_cov=1.25))
    assert d['readings']['coverage_normalized_net_revisions']=={'value':1.25,'unit':'ratio'}
    assert d['quality_flags']==[]


def test_numeric_timestamp_is_not_silently_treated_as_1970_source_date():
    assert run(sample(asof=1))['reason']=='source_date_unavailable'
