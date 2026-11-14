import sys,json,numpy as np,pandas as pd
sys.path.insert(0,sys.argv[1])
from engine.risk_radar_eval import labels as L, pivots as P
s=pd.read_csv(sys.argv[1]+"/data/risk_radar/walkforward_alert_series.csv",comment="#",parse_dates=["date"]).set_index("date")["loud"]
s=s.loc["2022-01-03":"2023-12-29"].astype(bool)
assert s.index.max()<=pd.Timestamp("2023-12-29")
px=L.spy_total_return()
idx=s.index; p=px.reindex(idx).ffill().to_numpy(float); n=len(idx)
runs=[e-b+1 for b,e in P._run_bounds(s.to_numpy(bool))]
M=sum(runs)
def elig(near,tol=0.01):
    hi=np.maximum.accumulate(np.where(np.isnan(p),-np.inf,p))
    if near=="high": return p>=hi*(1-tol)
    lo=np.empty(n)
    for i in range(n):
        lo[i]=p[i] if (i==0 or hi[i]!=hi[i-1] or p[i]>=hi[i]) else min(lo[i-1],p[i])
    return p<=lo*(1+tol)
def admissible(a,E,ln):
    # start s eligible, s+ln<=n, a[max(0,s-1):min(n,s+ln+1)] all False
    occ=np.concatenate([[0],np.cumsum(a)])
    ss=np.arange(0,n-ln+1)
    lo=np.maximum(0,ss-1); hi=np.minimum(n,ss+ln+1)
    free=(occ[hi]-occ[lo])==0
    return ss[E[ss]&free]
def draw(rng,E,order):
    a=np.zeros(n,bool)
    seq=rng.permutation(runs) if order=="random" else sorted(runs,reverse=True)
    for ln in seq:
        c=admissible(a,E,int(ln))
        if not len(c): return None
        s0=int(rng.choice(c)); a[s0:s0+int(ln)]=True
    return a
def rule(near,order,ndraws=2000,cap=20000,seed=0):
    E=elig(near); rng=np.random.default_rng(seed)
    kept=[];att=0
    while len(kept)<ndraws and att<cap:
        att+=1; a=draw(rng,E,order)
        if a is not None:
            assert a.sum()==M and sorted(e-b+1 for b,e in P._run_bounds(a))==sorted(runs)
            kept.append(a)
    inband=float(np.mean([E[np.flatnonzero(a)].mean() for a in kept])) if kept else None
    return dict(near=near,order=order,eligible_sessions=int(E.sum()),attempts=att,kept=len(kept),
                discarded=att-len(kept),acceptance=round(len(kept)/att,4),
                defined=len(kept)==ndraws,mass_kept=M if kept else None,
                share_of_placed_mass_in_band=round(inband,4) if inband is not None else None)
obs_inband={nr:round(float(elig(nr)[s.to_numpy(bool)].mean()),4) for nr in ("high","low")}
out=dict(series="walkforward loud 2022-01-03..2023-12-29",n=n,runs=runs,mass=M,
         observed_share_of_mass_in_band=obs_inband,rules=[rule(nr,o) for nr in ("high","low") for o in ("random","longest_first")])
print(json.dumps(out,indent=1))
Eh=elig("high"); print("high eligible dates:",[str(d.date()) for d in idx[Eh]])
def widen(E,w):
    W=E.copy()
    for i in np.flatnonzero(E): W[i:min(n,i+w+1)]=True
    return W
res=[]
for nr in ("high","low"):
    for w in (10,21):
        E0=elig(nr); E=widen(E0,w); rng=np.random.default_rng(0); kept=[];att=0
        while len(kept)<2000 and att<20000:
            att+=1; a=draw(rng,E,"random")
            if a is not None: kept.append(a)
        res.append(dict(near=nr,w=w,start_pool=int(E.sum()),attempts=att,kept=len(kept),acceptance=round(len(kept)/att,4),
                        defined=len(kept)==2000,share_mass_in_strict_band=round(float(np.mean([E0[np.flatnonzero(a)].mean() for a in kept])),4) if kept else None))
print(json.dumps(res,indent=1))
