"""Research-only industry analogue trial. No production or network writes."""
from pathlib import Path
import argparse, hashlib, io, json, platform, zipfile
import numpy as np
import pandas as pd

SOURCE_HASH = '13be85084196424aa85f29136af47f147a443275f90eb0955dbcdc6d6d25f448'
PROTOCOL_COMMIT = 'e1c3122f8260e8b3a3e00dfaebec0bbdbf226379'
BASE = ['proxy21','proxy63','proxy126','proxy_vol63','proxy_dd126',
        'breadth21','breadth63','breadth126','above50','above200']
EXTRA = ['persistent_positive63','persistent_negative63','low_net_progress63',
         'leader_turnover21','return_dispersion63','correlation63',
         'positive_gain_concentration63','breadth_change21']
TARGETS = ['future_positive_share','future_dispersion','future_proxy_vol',
           'future_rank_of_current_leaders','future_rank_of_current_losers']

def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple,np.ndarray)): return [clean(v) for v in x]
    if isinstance(x,(np.integer,)): return int(x)
    if isinstance(x,(np.floating,float)): return float(x) if np.isfinite(x) else None
    if isinstance(x,(np.bool_,)): return bool(x)
    return x

def save(path,obj):
    payload=json.dumps(clean(obj),indent=2,allow_nan=False)+'\n'
    with path.open('x') as f: f.write(payload)
    return hashlib.sha256(payload.encode()).hexdigest()

def neighbours(distance,positions,k=20):
    picked=[]
    for j in np.argsort(distance,kind='stable'):
        if all(abs(int(positions[j])-int(positions[p]))>=126 for p in picked):
            picked.append(int(j))
            if len(picked)==k: break
    return np.array(picked,dtype=int)

def parse_source(path):
    blob=path.read_bytes()
    assert hashlib.sha256(blob).hexdigest()==SOURCE_HASH,'SOURCE_DIGEST_CHANGED'
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        txt=z.read(z.namelist()[0]).decode('utf-8-sig')
    lines=txt.splitlines(); marker=next(i for i,v in enumerate(lines) if 'Average Value Weighted Returns -- Daily' in v)
    header=marker+1
    while not lines[header].strip(): header+=1
    end=header+1
    while end<len(lines) and lines[end][:8].isdigit(): end+=1
    frame=pd.read_csv(io.StringIO('\n'.join(lines[header:end])),index_col=0)
    frame.columns=frame.columns.str.strip()
    frame.index=pd.to_datetime(frame.index.astype(str),format='%Y%m%d')
    sentinel=int(frame.isin([-99.99,-999]).sum().sum())
    frame=frame.replace([-99.99,-999],np.nan)/100
    assert frame.shape[1]==49 and frame.index.is_monotonic_increasing and frame.index.is_unique
    assert not (frame<=-1).any().any()
    return frame,txt.splitlines()[0],sentinel

def build_panel(frame):
    logs=np.log1p(frame); r=logs.to_numpy(); dates=frame.index
    proxy=np.log1p(frame.mean(axis=1).where(frame.notna().all(axis=1))).to_numpy()
    wealth=np.exp(logs.fillna(0).cumsum()).to_numpy()
    wp=np.exp(np.nancumsum(proxy))
    mom={h:logs.rolling(h,min_periods=h).sum().to_numpy() for h in [21,63,126]}
    vol=logs.rolling(63,min_periods=63).std(ddof=1).to_numpy()
    anchors=np.flatnonzero(np.r_[dates.to_period('M')[:-1]!=dates.to_period('M')[1:],True])
    records=[]; skipped=0
    for t in anchors:
        if dates[t]<pd.Timestamp('1980-01-01') or dates[t]>pd.Timestamp('2025-11-30'): continue
        if t<251 or t+20>=len(r) or dates[t+20]>pd.Timestamp('2025-12-31'): continue
        if not np.isfinite(r[t-251:t+21]).all() or not np.isfinite(proxy[t-251:t+21]).all():
            skipped+=1; continue
        m21,m63,m126=(mom[h][t] for h in [21,63,126])
        s=vol[t]; assert (s>0).all()
        now=np.argsort(-m63,kind='stable')[:10]
        old=np.argsort(-mom[63][t-21],kind='stable')[:10]
        neg=np.argsort(m63,kind='stable')[:10]
        intersection=len(set(now)&set(old)); corr=np.corrcoef(r[t-62:t+1],rowvar=False)
        gains=np.maximum(m63,0); total=gains.sum()
        f=dict(proxy21=proxy[t-20:t+1].sum(),proxy63=proxy[t-62:t+1].sum(),
          proxy126=proxy[t-125:t+1].sum(),proxy_vol63=proxy[t-62:t+1].std(ddof=1),
          proxy_dd126=wp[t]/wp[t-125:t+1].max()-1,
          breadth21=np.mean(m21>0),breadth63=np.mean(m63>0),breadth126=np.mean(m126>0),
          above50=np.mean(wealth[t]>wealth[t-49:t+1].mean(axis=0)),
          above200=np.mean(wealth[t]>wealth[t-199:t+1].mean(axis=0)),
          persistent_positive63=np.mean((m21>0)&(mom[21][t-21]>0)&(mom[21][t-42]>0)),
          persistent_negative63=np.mean((m21<0)&(mom[21][t-21]<0)&(mom[21][t-42]<0)),
          low_net_progress63=np.mean(np.abs(m63)<0.25*s*np.sqrt(63)),
          leader_turnover21=1-intersection/(20-intersection),return_dispersion63=m63.std(ddof=1),
          correlation63=(corr.sum()-49)/(49*48),
          positive_gain_concentration63=float(np.sum((gains/total)**2)) if total>0 else 0.,
          breadth_change21=np.mean(m63>0)-np.mean(mom[63][t-21]>0))
        future=r[t+1:t+21].sum(axis=0)
        ranks=pd.Series(future).rank(method='average',pct=True).to_numpy()
        y=[np.mean(future>0),future.std(ddof=1),proxy[t+1:t+21].std(ddof=1),ranks[now].mean(),ranks[neg].mean()]
        assert np.isfinite(list(f.values())).all() and np.isfinite(y).all()
        records.append(dict(date=str(dates[t].date()),position=int(t),features=f,
          outcomes=dict(zip(TARGETS,y)),no_positive_gains=bool(total<=0)))
    return records,skipped

def evaluate(records):
    pos=np.array([v['position'] for v in records]); dates=np.array([v['date'] for v in records])
    x=np.array([[v['features'][f] for f in BASE+EXTRA] for v in records])
    y=np.array([[v['outcomes'][f] for f in TARGETS] for v in records])
    predictions=[]; excluded=[]
    for qi,q in enumerate(records):
        if q['date']<'2000-01-01': continue
        ids=np.flatnonzero(pos+20<pos[qi]-252)
        train=x[ids]; sd=train.std(axis=0,ddof=1); sd=np.where(sd>0,sd,1.)
        delta=(train-x[qi])/sd
        d0=np.mean(delta[:,:len(BASE)]**2,axis=1)
        d1=.5*d0+.5*np.mean(delta[:,len(BASE):]**2,axis=1)
        picks=[neighbours(d,pos[ids]) for d in [d0,d1]]
        if any(len(p)<20 for p in picks):
            excluded.append(dict(date=q['date'],reason='fewer_than_20_separated_neighbours')); continue
        p0,p1=[ids[p] for p in picks]
        assert np.all(pos[p0]+20<pos[qi]-252) and np.all(pos[p1]+20<pos[qi]-252)
        for p in [p0,p1]:
            assert np.min(np.diff(np.sort(pos[p])))>=126
        preds=dict(unconditional=y[ids].mean(axis=0),conventional=y[p0].mean(axis=0),augmented=y[p1].mean(axis=0))
        detail={}
        for label,p,dist in zip(['conventional','augmented'],picks,[d0,d1]):
            members=ids[p]
            worst=np.mean(np.abs(delta[p]),axis=0)
            detail[label]=dict(dates=dates[members].tolist(),distance=dist[p].tolist(),
                largest_feature_mismatches=[dict(feature=(BASE+EXTRA)[j],mean_abs_z=float(worst[j]))
                  for j in np.argsort(-worst)[:3]],future_positive_shares=y[members,0].tolist())
        predictions.append(dict(date=q['date'],actual=q['outcomes'],
            predictions={k:dict(zip(TARGETS,v)) for k,v in preds.items()},
            candidates=len(ids),neighbours=detail))
    return predictions,excluded

def summarize(predictions):
    actual=np.array([[v['actual'][k] for k in TARGETS] for v in predictions])
    names=['unconditional','conventional','augmented']
    pred={n:np.array([[v['predictions'][n][k] for k in TARGETS] for v in predictions]) for n in names}
    loss={n:(v-actual)**2 for n,v in pred.items()}
    n=len(predictions); rng=np.random.default_rng(2026092303)
    starts=rng.integers(0,n,size=(5000,int(np.ceil(n/12))))
    idx=((starts[:,:,None]+np.arange(12))%n).reshape(5000,-1)[:,:n]
    target_results={}
    for j,k in enumerate(TARGETS):
        gain=loss['conventional'][:,j]-loss['augmented'][:,j]
        target_results[k]=dict(metrics={a:dict(rmse=float(np.sqrt(loss[a][:,j].mean())),
          mae=float(np.mean(np.abs(pred[a][:,j]-actual[:,j])))) for a in names},
          paired_mse_gain=float(gain.mean()),nominal_95pct_block_interval=np.quantile(gain[idx].mean(axis=1),[.025,.975]).tolist())
    years=np.array([int(v['date'][:4]) for v in predictions]); primary=loss['conventional'][:,0]-loss['augmented'][:,0]
    eras={}
    for a,b in [(2000,2009),(2010,2019),(2020,2025)]:
        take=(years>=a)&(years<=b)
        eras[f'{a}-{b}']=dict(n=int(take.sum()),gain=float(primary[take].mean()),
           rmse={v:float(np.sqrt(loss[v][take,0].mean())) for v in names})
    return dict(n_test=n,first=predictions[0]['date'],last=predictions[-1]['date'],
      targets=target_results,primary_by_era=eras,
      primary_leave_one_year_out={str(yr):float(primary[years!=yr].mean()) for yr in np.unique(years)})

def case_pair(records):
    best=None
    for i,a in enumerate(records):
        fa=a['features']
        for b in records[:i]:
            fb=b['features']
            if a['position']-b['position']<126: continue
            if abs(fa['breadth63']-fb['breadth63'])>2/49+1e-12: continue
            if abs(fa['proxy63']-fb['proxy63'])>.03: continue
            if abs(fa['proxy_vol63']-fb['proxy_vol63'])>.002: continue
            spread=abs(fa['persistent_positive63']-fb['persistent_positive63'])
            if best is None or spread>best['spread']:
                best=dict(spread=spread,a=dict(date=a['date'],features=fa),b=dict(date=b['date'],features=fb))
    return best

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args(); args.out.mkdir(parents=True,exist_ok=True)
    for name in ['analogue_v1_summary.json','analogue_v1_predictions.json','analogue_v1_panel.json']:
        assert not (args.out/name).exists(),f'EXISTING_OUTPUT: {name}'
    frame,header,sentinel=parse_source(args.source)
    records,skipped=build_panel(frame); predictions,excluded=evaluate(records)
    result=summarize(predictions)
    result.update(status='RESEARCH_ONLY_NOT_VALIDATED_ALPHA',protocol_commit=PROTOCOL_COMMIT,
      source_sha256=SOURCE_HASH,source_header=header,source_start=str(frame.index[0].date()),
      source_end=str(frame.index[-1].date()),source_rows=len(frame),source_missing_cells=sentinel,
      script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      environment=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__),
      panel_anchors=len(records),skipped_incomplete=skipped,excluded_queries=excluded,
      descriptive_case_pair=case_pair(records),
      limitations=['Industry portfolios, not individual stocks','Current-vintage history, not archived real-time releases',
        'Forced matches; no calibrated no-match rule','Nominal intervals, not familywise-adjusted claims',
        'Overlapping test outcomes and episodes remain dependent; block inference is approximate',
        'No current September market forecast or executable PnL'])
    hashes={}
    hashes['panel']=save(args.out/'analogue_v1_panel.json',records)
    hashes['predictions']=save(args.out/'analogue_v1_predictions.json',predictions)
    result['detail_hashes']=hashes
    digest=save(args.out/'analogue_v1_summary.json',result)
    assert hashlib.sha256(args.source.read_bytes()).hexdigest()==SOURCE_HASH
    print(json.dumps(clean(result),indent=2,allow_nan=False)); print('RESULT_SHA256',digest)

if __name__=='__main__': main()
