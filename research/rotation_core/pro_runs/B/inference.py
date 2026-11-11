"""Prespecified fixed-path paired circular-block bootstrap and metrics."""
import numpy as np
import pandas as pd
from scipy.stats import norm

NBOOT=5000; BLOCK=252; SEED=20261111; FAMILY=30

def years(index):
    # Include the interval ending at the first sampled close (one calendar day).
    return ((index[-1]-index[0]).days+1)/365.2425

def maxdd(r):
    v=np.r_[1.,np.cumprod(1+np.asarray(r))]
    return float(np.min(v/np.maximum.accumulate(v)-1))

def metrics(path,market):
    r=path['return'];yrs=years(r.index);ann=len(r)/yrs
    def capture(mask):
        den=market.loc[mask].mean()
        return 100*r.loc[mask].mean()/den if mask.any() and den!=0 else np.nan
    return {'n':len(r),'years':yrs,'start':str(r.index[0].date()),'end':str(r.index[-1].date()),
      'cagr':float(np.expm1(np.log1p(r).sum()/yrs)),'vol':float(r.std(ddof=1)*np.sqrt(ann)),
      'maxdd':maxdd(r),'up_capture':capture(market>0),'down_capture':capture(market<0),
      'turnover':path.turnover.sum()/yrs,'equity':path.equity.mean()}

def bootstrap_means(matrix,seed=SEED):
    """Exact n observations via complete circular blocks plus a final short block.

    Uses block cumulative sums to avoid a huge resample-by-day tensor.
    Columns use shared draws; seed+n yields identical draws for equal-length samples.
    """
    a=np.asarray(matrix,dtype=float)
    if a.ndim==1:a=a[:,None]
    if not np.isfinite(a).all():raise ValueError('Missing bootstrap input')
    n,k=a.shape;full,rem=divmod(n,BLOCK)
    rng=np.random.default_rng(seed+n)
    doubled=np.concatenate([a,a[:BLOCK]],axis=0)
    cs=np.vstack([np.zeros(k),np.cumsum(doubled,axis=0)])
    starts=np.arange(n)
    sums=cs[starts+BLOCK]-cs[starts]
    result=np.zeros((NBOOT,k))
    # n>=252 enforced for inference
    if full:
        draws=rng.integers(0,n,size=(NBOOT,full))
        result+=sums[draws].sum(axis=1)
    if rem:
        draw=rng.integers(0,n,size=NBOOT)
        result+=cs[draw+rem]-cs[draw]
    return result/n

def contrast(strategy,benchmarks):
    n=len(strategy);ann=n/years(strategy.index)
    cols=['strategy']+list(benchmarks)
    mat=np.column_stack([np.log1p(strategy.to_numpy())]+[np.log1p(b.to_numpy()) for b in benchmarks.values()])
    boot=bootstrap_means(mat);obs=mat.mean(axis=0)
    results={}
    for j,name in enumerate(cols[1:],1):
        diff=(boot[:,0]-boot[:,j])*ann
        point=(obs[0]-obs[j])*ann
        ci=np.quantile(diff,[.025,.975])
        cagr=np.expm1(boot[:,0]*ann)-np.expm1(boot[:,j]*ann)
        cgci=np.quantile(cagr,[.025,.975])
        centered=diff-point
        if np.max(np.abs(diff-point))<1e-14:
            p=1. if point<=0 else 1/(NBOOT+1)
        else:p=(1+np.sum(centered>=point))/(NBOOT+1)
        se=diff.std(ddof=1)
        results[name]={'log_excess':float(point),'log_lo':float(ci[0]),'log_hi':float(ci[1]),
         'cagr_excess':float(np.expm1(obs[0]*ann)-np.expm1(obs[j]*ann)),
         'cagr_lo':float(cgci[0]),'cagr_hi':float(cgci[1]),'p_raw':float(p),'se':float(se),
         'mde80':float((norm.ppf(1-.05/(2*FAMILY))+norm.ppf(.8))*se)}
    return results

def holm(pvalues):
    p=np.asarray(pvalues);order=np.argsort(p);ranked=p[order]
    adjusted=np.minimum(1.,np.maximum.accumulate(ranked*(len(p)-np.arange(len(p)))))
    out=np.empty(len(p));out[order]=adjusted;return out
