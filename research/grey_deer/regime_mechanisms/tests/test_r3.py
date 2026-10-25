from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importlib.util
import json
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest


def module():
    assert importlib.util.find_spec('r3') is not None, 'R3 reconstruction module not implemented'
    import r3
    return r3


def archive():
    return pd.DataFrame([
        ['PAYEMS','2020-01-01','2020-02-07','2020-03-05',100.,2],
        ['PAYEMS','2020-01-01','2020-03-06','9999-12-31',101.,2],
        ['PAYEMS','2020-02-01','2020-03-06','9999-12-31',102.,2],
    ],columns=['series','period','realtime_start','realtime_end','value','source_output_type'])


def scores():
    d=pd.DataFrame({'growth_score':[.5,.3,-.3], 'inflation_score':[.2,.4,-.4],
                    'quad':['Q2','Q2','Q4'],
                    'available_at':pd.to_datetime(['2020-01-02T21:00Z','2020-01-03T21:00Z','2020-01-06T21:00Z'])},
                    index=pd.to_datetime(['2020-01-02','2020-01-03','2020-01-06']))
    return d


def native(frame):
    return {'asof':str(frame.index[-1].date()),'regime_probs_filtered':{'Q1':.1,'Q2':.6,'Q3':.2,'Q4':.1}}


def test_module_exists(): module()


def test_archive_never_uses_release_on_same_date():
    out=module().archive_asof(archive(),'PAYEMS','2020-03-06')
    assert list(out['levels'].values())==[100.]


def test_archive_accepts_next_day_revision():
    out=module().archive_asof(archive(),'PAYEMS','2020-03-07')
    assert list(out['levels'].values())==[101.,102.]


def test_archive_digest_unchanged_after_future_revision_added():
    d=archive();a=module().archive_asof(d.iloc[:1],'PAYEMS','2020-02-20');b=module().archive_asof(d,'PAYEMS','2020-02-20')
    assert a==b


def test_future_bad_value_not_poisoning_old_snapshot():
    d=archive();d.loc[1,'value']=np.nan
    assert module().archive_asof(d,'PAYEMS','2020-02-20')['status']=='ok'


def test_conflicting_duplicate_vintage_is_refused():
    d=pd.concat([archive(),archive().iloc[[0]]],ignore_index=True)
    with pytest.raises(ValueError,match='duplicate'):module().archive_asof(d,'PAYEMS','2020-02-20')


def test_expired_value_without_successor_is_missing_not_filled():
    d=archive().iloc[:1]
    assert module().archive_asof(d,'PAYEMS','2020-03-07')['status']=='unavailable'


@pytest.mark.parametrize('value',[0,-1,np.nan,np.inf,True])
def test_invalid_macro_value_refused(value):
    d=archive().astype({'value':object});d.loc[0,'value']=value
    with pytest.raises(ValueError):module().archive_asof(d,'PAYEMS','2020-02-20')


def test_initial_only_archive_is_not_full_knowledge():
    d=archive();d.source_output_type=4
    with pytest.raises(ValueError,match='full'):module().archive_asof(d,'PAYEMS','2020-03-07')


def test_unknown_series_is_unavailable():
    assert module().archive_asof(archive(),'INDPRO','2020-03-07')['status']=='unavailable'


def test_impossible_publication_interval_refused():
    d=archive();d.loc[0,'realtime_end']='2020-02-01'
    with pytest.raises(ValueError,match='interval'):module().archive_asof(d,'PAYEMS','2020-02-20')


def test_future_period_refused():
    d=archive();d.loc[0,'period']='2020-04-01'
    with pytest.raises(ValueError,match='period'):module().archive_asof(d,'PAYEMS','2020-02-20')


def test_endpoint_receives_only_available_prefix():
    seen=[]
    def callback(d): seen.append(d.copy());return native(d)
    r=module().endpoint_at(scores(),'2020-01-03T22:00Z',callback)
    assert len(seen[0])==2 and r['score_asof']=='2020-01-03'
    assert r['fit_cutoff']=='2020-01-03'


def test_future_scores_do_not_change_old_endpoint_or_hash():
    r=module();d=scores()
    assert r.endpoint_at(d.iloc[:2],'2020-01-03T22:00Z',native)==r.endpoint_at(d,'2020-01-03T22:00Z',native)


def test_later_score_revision_cannot_rewrite_earlier_read():
    d=scores();old=module().endpoint_at(d,'2020-01-03T22:00Z',native)
    rev=d.iloc[[0]].copy();rev.growth_score=-.8;rev.available_at=pd.to_datetime(['2020-01-07T21:00Z'])
    assert module().endpoint_at(pd.concat([d,rev]),'2020-01-03T22:00Z',native)==old


def test_endpoint_chooses_latest_available_score_revision():
    d=scores();rev=d.iloc[[0]].copy();rev.growth_score=-.8;rev.available_at=pd.to_datetime(['2020-01-07T21:00Z'])
    seen=[]
    def cb(d):seen.append(d.copy());return native(d)
    module().endpoint_at(pd.concat([d,rev]),'2020-01-08T21:00Z',cb)
    assert seen[0].growth_score.iloc[0]==-.8


def test_endpoint_cannot_mutate_input():
    d=scores();before=d.copy(deep=True)
    def cb(f):r=native(f);f.iloc[0,0]=100;return r
    module().endpoint_at(d,'2020-01-08T21:00Z',cb)
    pd.testing.assert_frame_equal(d,before)


def test_missing_endpoint_stays_unknown():
    r=module().endpoint_at(scores(),'2020-01-03T22:00Z',lambda d:None)
    assert r['status']=='unavailable' and r['probabilities'] is None


def test_no_observations_does_not_call_endpoint():
    def cb(d):raise AssertionError('unexpected call')
    assert module().endpoint_at(scores(),'2019-01-01T22:00Z',cb)['status']=='unavailable'


def test_asof_mismatch_is_refused():
    def cb(d):r=native(d);r['asof']='2030-01-01';return r
    with pytest.raises(ValueError,match='asof'):module().endpoint_at(scores(),'2020-01-03T22:00Z',cb)


def test_invalid_probability_is_refused():
    def cb(d):r=native(d);r['regime_probs_filtered']['Q2']=np.nan;return r
    with pytest.raises(ValueError,match='probab'):module().endpoint_at(scores(),'2020-01-03T22:00Z',cb)


def test_unknown_evidence_does_not_receive_forecast_authority():
    r=module().endpoint_at(scores(),'2020-01-03T22:00Z',native)
    assert r['input_qualification']=='NOT_ESTABLISHED'
    assert r['authority']=={'rank':False,'size':False,'gate':False,'execute':False}
    json.dumps(r,allow_nan=False)


def test_naive_availability_is_rejected():
    d=scores();d.available_at=d.available_at.dt.tz_localize(None)
    with pytest.raises(ValueError,match='timezone'):module().endpoint_at(d,'2020-01-03T22:00Z',native)


def test_current_loss_excluded_from_future_target():
    s=pd.Series([100.,50.,50.,50.,50.],index=pd.bdate_range('2020-01-01',periods=5))
    r=module().future_path(s,3,.05)
    assert r.event.iloc[0]==1 and r.event.iloc[1]==0 and r.event.iloc[-3:].isna().all()


def test_missing_future_session_is_not_removed_or_filled():
    s=pd.Series([100.,99.,np.nan,90.,91.],index=pd.bdate_range('2020-01-01',periods=5))
    assert np.isnan(module().future_path(s,3,.05).event.iloc[0])


def test_negative_future_price_is_invalid_not_crash():
    s=pd.Series([100.,99.,-1.,90.,91.],index=pd.bdate_range('2020-01-01',periods=5))
    assert np.isnan(module().future_path(s,3,.05).event.iloc[0])


def test_future_path_matches_independent_oracle():
    rng=np.random.default_rng(19);s=pd.Series(100*np.exp(np.cumsum(rng.normal(0,.02,80))),index=pd.bdate_range('2020-01-01',periods=80));s.iloc[35]=np.nan
    out=module().future_path(s,7,.05)
    for i in range(len(s)):
        vals=s.iloc[i:i+8].to_numpy()
        expected=np.nan if len(vals)!=8 or not np.isfinite(vals).all() else float(min(vals[1:])/vals[0]-1<=-.05)
        assert (np.isnan(expected) and np.isnan(out.event.iloc[i])) or out.event.iloc[i]==expected


def test_common_sample_does_not_count_missing_recipient_as_calm():
    r=module().cross_table(pd.Series([1.,0.,1.,np.nan]),pd.Series([1.,1.,np.nan,0.]))
    assert r['n']==2 and r['recipient_only']==1 and r['both']==1


def test_recipient_tables_and_fixed_grid():
    from run_r3 import recipient_audit
    idx=pd.bdate_range('2007-01-01',periods=90)
    s=pd.Series(100.,index=idx);bank=s.copy();bank.iloc[30:]=70
    r=recipient_audit({'SPY':s,'KRE':bank,'XLF':s})
    assert r['tables']['0.05']['full']['KRE']['recipient_only']==21
    assert r['tables']['0.05']['full']['XLF']['recipient_only']==0
    assert r['independent_label_mismatches']==0
    assert r['tables']['0.05']['nonoverlap_21']['KRE']['n']==4


def test_source_extractor_requires_both_existing_functions():
    from run_r3 import existing_endpoint
    with pytest.raises(ValueError):existing_endpoint('def other(): pass')
