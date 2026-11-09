import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest


def module():
    p=Path(__file__).parents[1]/'r2_d1.py'
    assert p.exists(), 'R2-D1 research implementation does not exist'
    spec=importlib.util.spec_from_file_location('r2_d1',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def vintage():
    periods=pd.date_range('2018-01-01',periods=30,freq='MS')
    return pd.DataFrame([{'series':'X','period':p,'realtime_start':pd.Timestamp('2020-07-10'),
                         'value':100+i,'source_output_type':2} for i,p in enumerate(periods)])


def test_module_exists(): module()


def test_macro_uses_same_vintage_for_both_growth_rates():
    d=vintage();r=module().macro_events(d,'X').iloc[-1]
    assert np.isclose(r['yoy'],100*(129/117-1))
    assert np.isclose(r['accel'],100*(129/117-126/114))


def test_future_vintage_does_not_rewrite_earlier_macro_events():
    d=vintage();new=d.copy();new['realtime_start']=pd.Timestamp('2020-08-10');new['value']*=2
    a=module().macro_events(d,'X');b=module().macro_events(pd.concat([d,new]),'X')
    pd.testing.assert_frame_equal(a,b.loc[a.index])


def test_duplicate_macro_period_vintage_refused():
    d=vintage()
    with pytest.raises(ValueError): module().macro_events(pd.concat([d,d.iloc[-1:]]),'X')


def test_missing_twelve_month_reference_is_not_compressed_into_yoy():
    d=vintage();d=d[d.period!=pd.Timestamp('2019-06-01')]
    assert module().macro_events(d,'X').empty


def test_same_date_source_is_unavailable():
    idx=pd.bdate_range('2020-01-06',periods=4)
    data=pd.DataFrame({'v':[1,2,3,4]},index=idx)
    r=module().prior_join(idx,data)
    assert np.isnan(r.v.iloc[0]) and r.v.iloc[1]==1
    assert (r.dropna().source_date<r.dropna().index).all()


def test_large_source_gap_excluded():
    idx=pd.bdate_range('2020-01-06',periods=8)
    d=pd.DataFrame({'v':[1.]},index=idx[:1]);r=module().prior_join(idx,d,max_sessions=3)
    assert np.isnan(r.v.iloc[-1])


def test_outcome_never_counts_current_loss():
    s=pd.Series([100,50,50,50,50],index=pd.bdate_range('2020-01-01',periods=5))
    r=module().forward_event(s,3,.05)
    assert r.iloc[0]==1 and r.iloc[1]==0 and r.iloc[2:].isna().all()


def test_outcome_requires_complete_future_window():
    s=pd.Series([100,90,np.nan,80,80],index=pd.bdate_range('2020-01-01',periods=5))
    assert np.isnan(module().forward_event(s,3,.05).iloc[0])


def test_midrank_flat_history_is_half():
    s=pd.Series(np.ones(600),index=pd.bdate_range('2000-01-01',periods=600))
    assert module().vol_features(s)['pctile'].iloc[-1]==50


def test_scale_is_training_only_and_predictions_deterministic():
    m=module();rng=np.random.default_rng(3);X=rng.normal(size=(100,2));y=(X[:,0]>0).astype(int)
    model=m.fit_ridge(X,y,1.)
    np.testing.assert_allclose(model['mean'],X.mean(axis=0))
    a=m.predict(model,X[:3]);b=m.predict(model,np.vstack([X[:3],[[1e6,1e6]]]))[:3]
    np.testing.assert_allclose(a,b)
    assert model['gradient_inf']<1e-3


def test_constant_training_column_does_not_explode():
    X=np.column_stack([np.arange(100),np.ones(100)]);y=(X[:,0]>50).astype(int)
    model=module().fit_ridge(X,y,.1)
    assert np.isfinite(module().predict(model,X)).all()


def test_single_class_fit_refused():
    with pytest.raises(ValueError): module().fit_ridge(np.ones((100,2)),np.ones(100),1)


def test_auc_and_ap_ties_are_honest():
    r=module().quality(np.array([0,1,0,1]),np.ones(4)*.5)
    assert r['auc']==.5 and r['average_precision']==.5 and r['brier']==.25


def test_perfect_probabilities_metrics():
    r=module().quality(np.array([0,1,0,1]),np.array([0,1,0,1]))
    assert r['auc']==1 and r['average_precision']==1 and r['brier']==0


def test_missing_quiet_day_cannot_rearm():
    flags=np.array([True]+[False]*21+[True]);known=np.ones(23,dtype=bool);known[11]=False
    a=module().anchors(flags,known)
    assert a.sum()==1


def test_twenty_one_known_quiet_days_rearm():
    a=module().anchors(np.array([True]+[False]*21+[True]),np.ones(23,dtype=bool))
    assert a.sum()==2


def test_training_purge_uses_calendar_not_sparse_eligible_rows():
    idx=pd.bdate_range('2010-01-01',periods=500)
    mask=module().training_mask(idx,idx[400],63)
    assert not mask[337:].any() and mask[:337].all()


def test_nested_validation_never_uses_outer_year_or_unmatured_tail(monkeypatch):
    m=module();idx=pd.bdate_range('2007-01-01','2015-12-31')
    panel=pd.DataFrame({'x':np.arange(len(idx)),'Y21':np.arange(len(idx))%2},index=idx)
    seen=[]
    monkeypatch.setattr(m,'fit_ridge',lambda X,y,C:{})
    def prediction(model,X):
        seen.extend(X.x.tolist());return np.full(len(X),.5)
    monkeypatch.setattr(m,'predict',prediction)
    m.select_c(panel,['x'],'Y21',2015,pd.Series(True,index=idx))
    outer_first=idx[idx.year==2015][0];cut=int(idx.searchsorted(outer_first))-63
    assert max(seen)<cut


def test_whole_synthetic_panel_retains_source_dates_and_matures_targets():
    m=module();idx=pd.bdate_range('2010-01-01','2016-12-31');n=len(idx)
    data={k:pd.Series(100+np.arange(n)*.02,index=idx) for k in ['spy','tlt','move','vix']}
    for k in ['n2','n10','r10','oas']:data[k]=pd.Series(2+np.sin(np.arange(n)/100)*.2,index=idx)
    for key,sid in [('payroll','PAYEMS'),('cpi','CPIAUCSL')]:
        rows=[]
        for release in pd.date_range('2009-01-15','2017-01-15',freq='MS'):
            periods=pd.date_range('2006-01-01',release-pd.DateOffset(months=1),freq='MS')
            for j,p in enumerate(periods):rows.append({'series':sid,'period':p,'realtime_start':release,'value':100+j*.2,'source_output_type':2})
        data[key]=pd.DataFrame(rows)
    f,lineage=m.build_panel(data)
    assert set(m.BASE+m.INTER).issubset(f.columns)
    assert np.isfinite(f[m.BASE+m.INTER].iloc[-1]).all()
    assert f.Y21.iloc[-21:].isna().all() and f.Y63.iloc[-63:].isna().all()
    assert (lineage.iloc[-1]<idx[-1]).all()
