"""W2 T1 feasibility census — dates/tickers only, NO outcomes, prices or grades read."""
import glob, json, sys
import pandas as pd
ROOT="data/us_prophet_rank"
GEN=f"{ROOT}/episodes/generations/peg:23be3409c3a57944dd08e09e38e3b7541926c0f244e9d0d3b4a0b4a8aacedbf9"
cols=["stamp_date","ticker","tier","lane","eligible","buyable","featured","pool_in_buy_lane","pool_admission_class","pool_open_plan","signal_asof"]
frames=[]
for f in sorted(glob.glob(f"{ROOT}/candidates/2026-*.parquet")):
    d=pd.read_parquet(f); d=d[[c for c in cols if c in d.columns]].copy(); d["_file"]=f[-15:]; frames.append(d)
c=pd.concat(frames,ignore_index=True)
c["stamp_date"]=pd.to_datetime(c["stamp_date"]).dt.strftime("%Y-%m-%d")
out={}
cov=c.groupby("stamp_date").agg(rows=("ticker","size"),tier_curated=("tier",lambda s:(s=="curated").sum()),lane_buy=("lane",lambda s:(s=="buy").sum()),featured=("featured",lambda s:(s==True).sum()),buyable=("buyable",lambda s:(s==True).sum()),eligible=("eligible",lambda s:(s==True).sum()),pool_buy=("pool_in_buy_lane",lambda s:(s==True).sum()) if "pool_in_buy_lane" in c else ("ticker","size"))
out["stamp_dates"]=len(cov); out["first_last_stamp"]=[cov.index[0],cov.index[-1]]
out["dates_with_tier"]=int((cov.tier_curated>0).sum()); out["dates_with_lane_buy"]=int((cov.lane_buy>0).sum()); out["dates_with_featured"]=int((cov.featured>0).sum()); out["dates_with_buyable"]=int((cov.buyable>0).sum())
out["last_date_with"]={k:str(cov[cov[k]>0].index[-1]) for k in ["tier_curated","lane_buy","featured","buyable","eligible"] if (cov[k]>0).any()}
out["median_rows_per_date"]={k:float(cov[cov[k]>0][k].median()) for k in ["tier_curated","lane_buy","featured","buyable","eligible","pool_buy"]}
if "signal_asof" in c: 
    sa=pd.to_datetime(c["signal_asof"],errors="coerce").dt.strftime("%Y-%m-%d"); out["signal_asof_after_stamp_rows"]=int((sa>c["stamp_date"]).sum())
if "pool_admission_class" in c: out["pool_admission_class"]=c["pool_admission_class"].value_counts(dropna=False).head(8).to_dict()
# OPENED episodes
ev=[json.loads(l) for l in open(f"{GEN}/events.jsonl")] if False else None
import os
opened=[]
for evfile in sorted(glob.glob(f"{GEN}/events/*.jsonl")):
  for l in open(evfile):
        e=json.loads(l)
        if e.get("event_type","")=="OPENED" or e.get("type")=="OPENED" or e.get("kind")=="OPENED":
            p=e.get("payload",{}); opened.append((e.get("episode_id"),p.get("ticker_at_observation"),p.get("opened_session"),p.get("security_id")))
out["opened"]=len(opened)
grid=sorted(cov.index); gi={d:i for i,d in enumerate(grid)}
defs={"curated":c.tier=="curated","curated_buyable":(c.tier=="curated")&(c.buyable==True),"buyable":c.buyable==True,"eligible":c.eligible==True,"lane_buy":c.lane=="buy","featured":c.featured==True}
if "pool_in_buy_lane" in c: defs["pool_in_buy_lane"]=c.pool_in_buy_lane==True
res={}
for name,mask in defs.items():
    sub=c[mask][["stamp_date","ticker"]]
    by=sub.groupby("ticker")["stamp_date"].apply(sorted).to_dict()
    lags=[]; never=0; nogrid=0; prior=0
    for eid,tk,s,sid in opened:
        if not s: nogrid+=1; continue
        ds=by.get(tk,[])
        if any(d<s for d in ds): prior+=1
        later=[d for d in ds if d>=s]
        if not later: never+=1; continue
        t=later[0]
        # lag in grid sessions: index of first grid date >= s
        gs=[d for d in grid if d>=s]
        lags.append(gi[t]-gi[gs[0]] if gs else None)
    lags=[l for l in lags if l is not None]
    ser=pd.Series(lags) if lags else pd.Series(dtype=float)
    res[name]={"n_open":len(opened),"with_t1":len(lags),"never":never,"no_session":nogrid,"already_before_open":prior,
               "zero_lag":int((ser==0).sum()),"zero_lag_share":round(float((ser==0).mean()),3) if len(ser) else None,
               "median_lag":float(ser.median()) if len(ser) else None,"median_pos_lag":float(ser[ser>0].median()) if (ser>0).any() else None,
               "p25_p75":[float(ser.quantile(.25)),float(ser.quantile(.75))] if len(ser) else None,"lag_le_10":int((ser<=10).sum())}
out["t1_defs"]=res
print(json.dumps(out,indent=1,default=str))
