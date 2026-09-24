"""Post-result audit and descriptive attribution. Never refits a forecast."""
from pathlib import Path
import hashlib,json
from collections import Counter
import numpy as np
import industry_analogue_v1 as a

ROOT=Path(__file__).resolve().parent
EXPECTED={
 'analogue_v1_summary.json':'f0aaec4538bec2bc8a14cb1b2a7c30898a84679de7db8e090a13bf7ab0222285',
 'analogue_v1_panel.json':'4bcde563d722e962dc04b8beb30108b047ff598051b2924b37bddcc8df285015',
 'analogue_v1_predictions.json':'a88aec19a8cfbc554e682885a37e7a92f23c09fa2b6d4a36cb03760f61cc0fcc'}

def main():
    objects={}
    for name,digest in EXPECTED.items():
        b=(ROOT/name).read_bytes();assert hashlib.sha256(b).hexdigest()==digest
        objects[name]=json.loads(b)
    summary=objects['analogue_v1_summary.json'];panel=objects['analogue_v1_panel.json'];preds=objects['analogue_v1_predictions.json']
    bydate={v['date']:v for v in panel};n=len(preds)
    errors={};validated=0;constants=[]
    for label in ['unconditional','conventional','augmented']:
        errors[label]=np.array([[v['predictions'][label][k]-v['actual'][k] for k in a.TARGETS] for v in preds])
        for j,k in enumerate(a.TARGETS):
            assert np.isclose(np.sqrt(np.mean(errors[label][:,j]**2)),summary['targets'][k]['metrics'][label]['rmse'],rtol=1e-12)
            assert np.isclose(np.mean(abs(errors[label][:,j])),summary['targets'][k]['metrics'][label]['mae'],rtol=1e-12)
    for q in preds:
        pos=bydate[q['date']]['position']
        candidates=[v for v in panel if v['position']+20<pos-252]
        x=np.array([[v['features'][f] for f in a.BASE+a.EXTRA] for v in candidates])
        cols=np.flatnonzero(x.std(axis=0,ddof=1)==0)
        if len(cols):constants.append({'date':q['date'],'columns':[(a.BASE+a.EXTRA)[j] for j in cols]})
        for label in ['conventional','augmented']:
            nn=q['neighbours'][label];ps=np.array([bydate[d]['position'] for d in nn['dates']])
            assert len(ps)==20 and np.min(np.diff(np.sort(ps)))>=126 and np.all(ps+20<pos-252)
            for j,d in enumerate(nn['dates']):
                assert bydate[d]['outcomes']['future_positive_share']==nn['future_positive_shares'][j]
                validated+=1
    rng=np.random.default_rng(2026092303);starts=rng.integers(0,n,(5000,int(np.ceil(n/12))))
    idx=((starts[:,:,None]+np.arange(12))%n).reshape(5000,-1)[:,:n]
    gains={};support={}
    for label in ['conventional','augmented']:
        gain=errors['unconditional'][:,0]**2-errors[label][:,0]**2
        gains[label]={'mse_gain_over_unconditional':float(gain.mean()),'nominal_95pct_interval':np.quantile(gain[idx].mean(axis=1),[.025,.975]).tolist()}
        near=[];far=[];width=[];covered=[]
        for q in preds:
            nn=q['neighbours'][label];distance=np.sqrt(nn['distance'])
            near.append(distance.min());far.append(distance.max())
            lo,hi=np.quantile(nn['future_positive_shares'],[.1,.9]);actual=q['actual']['future_positive_share']
            width.append(hi-lo);covered.append(lo<=actual<=hi)
        support[label]={'nearest_rms_distance_quantiles_10_50_90':np.quantile(near,[.1,.5,.9]).tolist(),
          'furthest_rms_distance_quantiles_10_50_90':np.quantile(far,[.1,.5,.9]).tolist(),
          'uncalibrated_10_90_range_mean_width':float(np.mean(width)),
          'uncalibrated_10_90_range_empirical_coverage':float(np.mean(covered))}
    frame,_,_=a.parse_source(ROOT/'49_industries_daily_source.zip')
    r=np.log1p(frame.to_numpy()); proxy=np.log1p(frame.mean(axis=1).where(frame.notna().all(axis=1))).to_numpy()
    cases={}
    for date in ['1992-01-31','2013-11-29']:
        t=bydate[date]['position'];blocks=np.vstack([r[t-62:t-41].sum(axis=0),r[t-41:t-20].sum(axis=0),r[t-20:t+1].sum(axis=0)])
        sign=np.where(abs(blocks)<=1e-12,'0',np.where(blocks>0,'+','-'))
        patterns=Counter(''.join(sign[:,j]) for j in range(49));assert sum(patterns.values())==49
        cases[date]={'patterns_oldest_to_newest':dict(sorted(patterns.items())),
          'median_industry_block_simple_returns':np.median(np.expm1(blocks),axis=1).tolist(),
          'proxy_block_simple_returns':[float(np.expm1(proxy[s:e].sum())) for s,e in [(t-62,t-41),(t-41,t-20),(t-20,t+1)]],
          'industry_63day_positive_count':int((r[t-62:t+1].sum(axis=0)>0).sum())}
    totals={'absolute':[0,0],'relative':[0,0]};monthly=[]
    for q in preds:
        t=bydate[q['date']]['position'];new=r[t-20:t+1].sum(axis=0);expired=r[t-83:t-62].sum(axis=0)
        delta=r[t-62:t+1].sum(axis=0)-r[t-83:t-20].sum(axis=0)
        assert np.allclose(delta,new-expired,rtol=1e-11,atol=1e-13)
        row={'date':q['date']}
        for label,fresh,old in [('absolute',new,expired),('relative',new-proxy[t-20:t+1].sum(),expired-proxy[t-83:t-62].sum())]:
            improved=(fresh-old)>1e-12;without=improved&(fresh<=1e-12)
            den=int(improved.sum());num=int(without.sum());totals[label][0]+=num;totals[label][1]+=den
            row[label]={'improved':den,'without_positive_fresh':num,'fraction':num/den if den else None}
        monthly.append(row)
    rolloff={k:{'without_positive_fresh_count':v[0],'improving_count':v[1],'pooled_fraction':v[0]/v[1],
      'monthly_fraction_quantiles_10_50_90':np.quantile([r[k]['fraction'] for r in monthly if r[k]['fraction'] is not None],[.1,.5,.9]).tolist()} for k,v in totals.items()}
    out={'status':'POST_RESULT_DIAGNOSTIC_NO_REFIT','audit':{'rmse_mae_recomputed':True,'neighbour_date_and_outcome_checks':validated,
        'constant_training_features':constants,'chronology_and_spacing_pass':True,'source_hash_unchanged':hashlib.sha256((ROOT/'49_industries_daily_source.zip').read_bytes()).hexdigest()==a.SOURCE_HASH},
      'comparisons_with_unconditional':gains,'support_diagnostics_not_calibrated_forecasts':support,
      'selected_sequence_cases':cases,'rolloff_attribution':rolloff,'iid_symmetric_zero_drift_reference':.25,
      'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'scope':'49 industry portfolios, 311 monthly anchors; not stock forecasts, no current-market claim',
      'diagnostic_note':'v1 conventional largest_feature_mismatches included unused added fields; use only conventional input fields when narrating its distance. Forecasts unaffected.'}
    detail=a.save(ROOT/'analogue_audit_path_v1_monthly.json',monthly);out['monthly_hash']=detail
    digest=a.save(ROOT/'analogue_audit_path_v1_results.json',out)
    print(json.dumps(a.clean(out),indent=2,allow_nan=False));print('RESULT_SHA256',digest)

if __name__=='__main__':main()
