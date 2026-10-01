"""Offline, non-promotion pilot frozen in Macro commit 4d4b1011.
Reads only hash-pinned parquets. No network, production imports, or source writes.
"""
from pathlib import Path
import datetime as dt
from decimal import Decimal
import hashlib
import io
import json
import sys
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit

PREREG = '4d4b10116601adf241ec985556dc586abdcf3c8b'
SECTORS = ['XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY']
HASHES = {
'SPY':'a04b4b27782c90707f84f9b19903914ca26e72bca9d739077da7df787a14fda6',
'QQQ':'ab1a48e218dd4ca7a2ff322dffb023ddfab39301ee7b1f8743ed57fc079bab68',
'IWM':'be4d143db7968a41455488b0b5479b48e863b0480155856f55002375bc596079',
'XLB':'8b2041adf453ce008f6e1c4b0f4ad8061360b9026ebcb4c382ab7b9a190b59ab',
'XLC':'7073b95f5d02c072500eae8053b0e2416b24f36660a9deadc0ce45fec8369c33',
'XLE':'67f287d27d63fe5dc58a7782c4bc484ca9e49ee49f7e4ad1e096f503aa9de4f6',
'XLF':'c88c9d3b3821fdfbb4f294c4f2404aa8401e2c898287d613d9c284ab921b28e5',
'XLI':'68244cc7b74e240db59ff06f0a02d270e3c82ea33e06a80fb364b0a4d1c602e1',
'XLK':'a218245c0d112ef9aa0b621378fab388be3d9b0d943f9e74152c104d8d0ce2d2',
'XLP':'8f32475cb279dca7ab8ad43b5c0ed42ac0d2c2ffa6431faddf6b065869d827ca',
'XLRE':'11f7b6c824150f8883035b7f56c4a295c6878d06afed027622ce27a0c9fecf52',
'XLU':'b16d5dfee6f521d4d01e86ca21a06ffd511a79b0d0cdff56e82a604c9f25f557',
'XLV':'5b9c776f8127222d4796fab85c0cf4977dc9536f5549adb85749a1bd3211c6fc',
'XLY':'0f9b38c77afe1cb3b29e56274a49ee2452d6d29b199dc7ef972228626067761f'}

def make_frame(frames):
    idx = frames['SPY'].index
    if not idx.is_unique or not idx.is_monotonic_increasing:
        raise ValueError('SPY dates not unique/increasing')
    bodies, ranges, lows, invalid = {}, {}, {}, {}
    for symbol, frame in frames.items():
        if not frame.index.equals(idx):
            raise ValueError('Different date index: '+symbol)
        q = frame[['open','high','low','close']].astype(float)
        ok = np.isfinite(q).all(axis=1) & (q > 0).all(axis=1)
        ok &= q.low.le(q[['open','close']].min(axis=1))
        ok &= q.high.ge(q[['open','close']].max(axis=1)) & q.high.ge(q.low)
        invalid[symbol] = int((~ok).sum())
        bodies[symbol] = (q.close/q.open-1).where(ok)
        ranges[symbol] = ((q.high-q.low)/q.open).where(ok)
        lows[symbol] = (q.low/q.open-1).where(ok)
    body = pd.DataFrame(bodies)
    sector = body[SECTORS]
    negative = sector.lt(0).astype(float).where(sector.notna()).mean(axis=1,skipna=False)
    x = pd.DataFrame({'spy_abs_body':body.SPY.abs()*100,
        'spy_range':ranges['SPY']*100,'sector_negative_fraction':negative,
        'sector_mean_body':sector.mean(axis=1,skipna=False)*100,
        'negative_fraction_change':negative.rolling(5).mean()-negative.rolling(20).mean(),
        'qqq_spy_body':(body.QQQ-body.SPY)*100},index=idx).shift(2)
    # Financial decimal boundary: an exact 1% loss must not flip on float division.
    q = frames['SPY'][['open','low','close']].astype(float)
    y = {k: pd.Series([
        float(Decimal(str(v))*100 <= Decimal(str(o))*99) if good else np.nan
        for v,o,good in zip(q[column],q.open,body.SPY.notna())], index=idx)
        for k,column in [('body','close'),('low','low')]}
    return {'X':x,'y':y,'invalid':invalid}

def standardize(train, other):
    mean, scale = train.mean(axis=0), train.std(axis=0)
    scale = np.where(scale > 0,scale,1.)
    return (train-mean)/scale, (other-mean)/scale, mean, scale

def fit_logistic(x,y):
    if len(np.unique(y)) != 2: raise ValueError('Training target needs both classes')
    design=np.column_stack([np.ones(len(x)),x])
    def objective(b):
        z=design@b
        loss=np.mean(np.logaddexp(0,z)-y*z)+.005*np.sum(b[1:]**2)
        grad=design.T@(expit(z)-y)/len(y)
        grad[1:]+=.01*b[1:]
        return loss,grad
    initial=np.zeros(design.shape[1]); initial[0]=np.log((1+y.sum())/(1+len(y)-y.sum()))
    opt=minimize(objective,initial,jac=True,method='L-BFGS-B',options={'maxiter':2000,'ftol':1e-12})
    if not opt.success: raise RuntimeError('Fit failed: '+str(opt.message))
    return opt.x

def prob(x,b):
    return expit(b[0]+x@b[1:])

def calibrate(p,y):
    z=logit(np.clip(p,1e-12,1-1e-12))
    def objective(ab):
        v=ab[0]*z+ab[1]; delta=expit(v)-y
        penalty=.00005*((ab[0]-1)**2+ab[1]**2)
        grad=np.array([np.mean(delta*z)+.0001*(ab[0]-1),np.mean(delta)+.0001*ab[1]])
        return np.mean(np.logaddexp(0,v)-y*v)+penalty,grad
    opt=minimize(objective,[1.,0.],jac=True,method='L-BFGS-B',bounds=[(0,10),(-10,10)],options={'maxiter':2000,'ftol':1e-12})
    if not opt.success: raise RuntimeError('Calibration failed: '+str(opt.message))
    return opt.x

def metrics(y,p):
    p=np.clip(p,1e-12,1-1e-12)
    return {'n':len(y),'events':int(y.sum()),'prevalence':float(y.mean()),
        'mean_probability':float(p.mean()),'brier':float(np.mean((p-y)**2)),
        'log_loss':float(-np.mean(y*np.log(p)+(1-y)*np.log1p(-p)))}

def evaluate(frame, endpoint):
    x,y=frame['X'],frame['y'][endpoint]
    finite=x.notna().all(axis=1)&y.notna()&(x.index<='2026-06-30')
    masks={k:finite&(x.index>=lo)&(x.index<=hi) for k,lo,hi in [
        ('train','2021-07-06','2023-12-31'),('cal','2024-01-01','2024-12-31'),
        ('test','2025-01-01','2026-06-30')]}
    if min(int(m.sum()) for m in masks.values())<50: raise ValueError('Insufficient split')
    xx={k:x.loc[m].to_numpy() for k,m in masks.items()}
    yy={k:y.loc[m].to_numpy() for k,m in masks.items()}
    pre=np.concatenate([yy['train'],yy['cal']]); p0=(pre.sum()+1)/(len(pre)+2)
    predictions={'P0':np.full(len(yy['test']),p0)}; models={}
    for name,ncols in [('P1',2),('P2',6)]:
        xt,xc,mu,sd=standardize(xx['train'][:,:ncols],xx['cal'][:,:ncols])
        xv=(xx['test'][:,:ncols]-mu)/sd
        coeff=fit_logistic(xt,yy['train']); ab=calibrate(prob(xc,coeff),yy['cal'])
        raw=prob(xv,coeff); calibrated=expit(ab[0]*logit(np.clip(raw,1e-12,1-1e-12))+ab[1])
        predictions[name+'_raw']=raw; predictions[name]=calibrated
        models[name]={'coefficients':coeff.tolist(),'calibrator':ab.tolist(),'training_mean':mu.tolist(),'training_scale':sd.tolist(),'optimizer_success':True}
    scores={name:metrics(yy['test'],p) for name,p in predictions.items()}
    date_index=x.loc[masks['test']].index
    by_era={str(year):{name:metrics(yy['test'][date_index.year==year],p[date_index.year==year]) for name,p in predictions.items()} for year in [2025,2026]}
    diff=(predictions['P2']-yy['test'])**2-(predictions['P1']-yy['test'])**2
    rng=np.random.default_rng(20260910); n=len(diff); samples=[]
    for _ in range(1000):
        starts=rng.integers(0,n,size=int(np.ceil(n/10)))
        indices=((starts[:,None]+np.arange(10))%n).ravel()[:n]
        samples.append(diff[indices].mean())
    ci=np.percentile(samples,[2.5,50,97.5]).tolist()
    adequate=n>=100 and int(yy['test'].sum())>=20
    consistent=all(v['P2']['brier']<=v['P1']['brier'] for v in by_era.values())
    interesting=diff.mean()<0 and ci[2]<0 and consistent
    verdict='UNDERPOWERED' if not adequate else ('NEEDS_PIT_AND_FORWARD_VALIDATION' if interesting else 'NO_INCREMENTAL_SUPPORT')
    return {'endpoint':endpoint,'split_counts':{k:int(v.sum()) for k,v in masks.items()},
        'split_events':{k:int(v.sum()) for k,v in yy.items()},'total_rows':len(x),
        'invalid_or_warmup_rows_before_cutoff':int(((x.index<='2026-06-30')&~finite).sum()),
        'test_first':str(date_index[0]),'test_last':str(date_index[-1]),'models':models,
        'test_scores':scores,'subperiod_scores':by_era,'paired_brier_difference':float(diff.mean()),
        'paired_block_bootstrap_95pct':ci,'subperiod_consistency':consistent,'verdict':verdict}

def run(root):
    frames={}; census={}
    for symbol,expected in HASHES.items():
        blob=(root/(symbol+'.parquet')).read_bytes(); found=hashlib.sha256(blob).hexdigest()
        if found!=expected: raise ValueError('Input hash changed: '+symbol)
        table=pd.read_parquet(io.BytesIO(blob)).loc[:'2026-06-30']
        frames[symbol]=table
        census[symbol]={'sha256':found,'rows_through_cutoff':len(table),'first':str(table.index.min()),'last':str(table.index.max())}
    frame=make_frame(frames)
    report={'kind':'RETROSPECTIVE_ARCHIVE_DIAGNOSTIC','prereg_commit':PREREG,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'computed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'source_census':census,
        'invalid_ohlc_rows':frame['invalid'],'lag_observations':2,'feature_names':list(frame['X'].columns),
        'results':{endpoint:evaluate(frame,endpoint) for endpoint in ['body','low']},
        'promotion':False,'actual_historical_availability_proven':False,'execution_backtest':False}
    return report

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('Usage: archive_pilot.py READ_ONLY_STORE NEW_RESULT_JSON')
    output=Path(sys.argv[2])
    if output.exists(): raise SystemExit('Refusing to overwrite an existing result')
    result=run(Path(sys.argv[1]))
    with output.open('x') as handle: json.dump(result,handle,indent=2,allow_nan=False); handle.write('\n')
    print(json.dumps({k:{'verdict':v['verdict'],'counts':v['split_counts'],'events':v['split_events'],'delta':v['paired_brier_difference'],'interval':v['paired_block_bootstrap_95pct']} for k,v in result['results'].items()},indent=2))
