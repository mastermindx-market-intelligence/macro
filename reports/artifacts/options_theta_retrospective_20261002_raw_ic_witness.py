#!/usr/bin/env python3
"""Fixed-date independent raw cross-sectional IC witness; no trial selection."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HEAD="07186d356cf2a3ef9d24a2d17fe60bd397f570cd"; MANIFEST="6b678a65f531eb31735cca7641b898887739475a9c1a479c2a0ebbecd8a164dc"
DATES=(("2019-06-03",2019),("2021-04-06",2021),("2024-08-06",2024))
ROOTS=("QQQ","IWM","DIA","XLB","XLC","XLE","XLF","XLI","XLK","XLP","XLRE","XLU","XLV","XLY","SMH","SOXX","XBI","KRE","ARKK","NVDA")
GC=["root","date","expiration","strike","right","bid","ask","underlying_price","implied_vol","delta","gamma","vanna","charm"]; OC=["root","date","expiration","strike","right","open_interest"]; ID=["date","expiration","strike","right"]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
 return h.hexdigest()
def entries(manifest,store,prices):
 by={e["relative_path"]:e for e in manifest["entries"]}; paths=[]
 for _,year in DATES:
  for root in ROOTS:
   for kind in ("greeks","oi"): paths.append((f"theta/{kind}/{root}/{year}.parquet",Path(store)/kind/root/f"{year}.parquet"))
 for root in (*ROOTS,"SPY"): paths.append((f"price/data/yahoo/{root}.parquet",Path(prices)/f"{root}.parquet"))
 out={}
 for rel,p in paths:
  e=by.get(rel)
  if e is None: raise RuntimeError("not manifest selected "+rel)
  if e["state"]=="missing":
   if p.exists(): raise RuntimeError("missing slot appeared "+rel)
   out[rel]=None
  else:
   if not p.is_file() or sha(p)!=e["sha256"]: raise RuntimeError("input hash mismatch "+rel)
   out[rel]=e["sha256"]
 return out
def raw(path,cols,day): return pd.read_parquet(path,columns=cols,filters=[("date","=",pd.Timestamp(day))]) if path.is_file() else pd.DataFrame(columns=cols)
def clean(x,root,year,oi=False):
 if x.empty:return x.copy()
 x=x.copy(); x["date"]=pd.to_datetime(x.date,errors="coerce").dt.date; x["expiration"]=pd.to_datetime(x.expiration,errors="coerce").dt.date; x["right"]=x.right.astype(str).str.upper()
 for c in (["strike","open_interest"] if oi else ["strike","bid","ask","underlying_price","implied_vol","delta","gamma","vanna","charm"]):x[c]=pd.to_numeric(x[c],errors="coerce")
 ok=x.date.notna()&x.expiration.notna()&x.date.map(lambda d:d.year==year)&x.root.astype(str).str.upper().eq(root)&x.right.isin(["C","P"])&np.isfinite(x.strike)&x.strike.gt(0)&x.expiration.gt(x.date)
 x=x.loc[ok]; return x.loc[~x.duplicated(ID,keep=False)].copy()
def book(g,o,root,year):
 g,o=clean(g,root,year),clean(o,root,year,True).rename(columns={"open_interest":"oi"})
 if g.empty or o.empty:return pd.DataFrame()
 x=g.merge(o[ID+["oi"]],on=ID,how="inner",validate="one_to_one")
 q=np.isfinite(x.bid)&x.bid.gt(0)&np.isfinite(x.ask)&x.ask.gt(0)&x.bid.le(x.ask)&np.isfinite(x.underlying_price)&x.underlying_price.gt(0)&np.isfinite(x.implied_vol)&x.implied_vol.ge(.005)&np.isfinite(x.oi)&x.oi.gt(0)
 return x.loc[q].copy()
def exposure(b,greek):
 if b.empty:return None
 x=pd.to_numeric(b[greek],errors="coerce").to_numpy(float)
 if np.isfinite(x).mean()<.90:return None
 z=np.where(b.right.eq("C").to_numpy(),1.,-1.)*b.oi.to_numpy(float)*x; z=z[np.isfinite(z)]; den=np.abs(z).sum()
 return float(z.sum()/den) if den>0 else None
def label(mod,p,spy,t,h,era,expected):
 if len(expected)!=h+1 or expected[-1]>era:return None,None,"ERA_BOUNDARY_PURGE"
 if p is None:return None,None,"ROOT_PRICE_UNAVAILABLE"
 if spy is None:return None,None,"SPY_PRICE_UNAVAILABLE"
 fi,sfi=mod.fill_index(p,t),mod.fill_index(spy,t)
 if fi is None:return None,None,"ROOT_FILL_UNAVAILABLE"
 if sfi is None:return None,None,"SPY_FILL_UNAVAILABLE"
 a,b=p.iloc[fi:fi+h+1],spy.iloc[sfi:sfi+h+1]
 if not a.index.equals(expected):return None,None,"ROOT_NATIVE_SESSION_WINDOW_MISMATCH"
 if not b.index.equals(expected):return None,None,"SPY_NATIVE_SESSION_WINDOW_MISMATCH"
 if not(np.isfinite(a).all() and (a>0).all()):return None,None,"ROOT_INVALID_WINDOW_PRICE"
 if not(np.isfinite(b).all() and (b>0).all()):return None,None,"SPY_INVALID_WINDOW_PRICE"
 if mod._has_split_seam(p,fi,h):return None,None,"ROOT_SPLIT_SEAM"
 if mod._has_split_seam(spy,sfi,h):return None,None,"SPY_SPLIT_SEAM"
 if not mod._spy_window_matches(p,fi,spy,h,t.date().isoformat()):return None,None,"SPY_WINDOW_MISMATCH"
 return float(a.iloc[-1]/a.iloc[0]-b.iloc[-1]/b.iloc[0]),float(np.std(np.diff(np.log(a.to_numpy())),ddof=1)*np.sqrt(252)),None
def ic(x,y):
 x,y=np.asarray(x,float),np.asarray(y,float); m=np.isfinite(x)&np.isfinite(y); x,y=x[m],y[m]; n=len(x)
 if n<5:return None,n,"INSUFFICIENT_ROOTS"
 if np.ptp(x)==0:return None,n,"CONSTANT_FEATURE"
 if np.ptp(y)==0:return None,n,"CONSTANT_TARGET"
 return float(np.corrcoef(pd.Series(x).rank(method="average"),pd.Series(y).rank(method="average"))[0,1]),n,None
def main():
 a=argparse.ArgumentParser(); a.add_argument("--source-root",required=True);a.add_argument("--manifest",required=True);a.add_argument("--store",required=True);a.add_argument("--price-store",required=True);a.add_argument("--out",required=True);q=a.parse_args(); root=Path(q.source_root); sys.path.insert(0,str(root));from scripts.research import options_history_retrospective as mod
 # Immutable delivery has no .git metadata; source_digest is the executable binding.
 mpath=Path(q.manifest); m=json.loads(mpath.read_text());
 if sha(mpath)!=MANIFEST or mod.source_digest(root)!=m["source_code_digest"]:raise RuntimeError("frozen binding mismatch")
 before=entries(m,q.store,q.price_store); cal=mod.study_sessions(); spy,_=mod.read_prices(Path(q.price_store)/"SPY.parquet"); cells=[]; counts={}
 for ds,year in DATES:
  t=pd.Timestamp(ds); i=cal.get_loc(t); era=pd.Timestamp("2019-12-31" if year<=2019 else "2022-12-31" if year<=2022 else "2025-12-31"); rows={}
  for root_name in ROOTS:
   g=raw(Path(q.store)/"greeks"/root_name/f"{year}.parquet",GC,ds);o=raw(Path(q.store)/"oi"/root_name/f"{year}.parquet",OC,ds);b=book(g,o,root_name,year);p,_=mod.read_prices(Path(q.price_store)/f"{root_name}.parquet"); rows[root_name]={"gex":exposure(b,"gamma"),"vex":exposure(b,"vanna"),"cex":exposure(b,"charm"),"labels":{str(h):label(mod,p,spy,t,h,era,cal[i+1:i+h+2]) for h in (5,21)}};counts[f"{root_name}.{ds}"]={"greeks":len(g),"oi":len(o),"joined_usable":len(b)}
  for h in (5,21):
   for key,contrast,target in (("gex","GEX_NORM_TO_FWD_RV",1),("vex","VEX_NORM_TO_SPY_EXCESS",0),("cex","CEX_NORM_TO_SPY_EXCESS",0)):
    x=[rows[r][key] for r in ROOTS];y=[rows[r]["labels"][str(h)][target] for r in ROOTS];v,n,reason=ic(x,y);cells.append({"date":ds,"horizon":h,"contrast":contrast,"expected_ic":v,"n_roots":n,"reason":reason})
 after=entries(m,q.store,q.price_store)
 out={"source_head":HEAD,"frozen_manifest_sha256":MANIFEST,"witness_dates":[x[0] for x in DATES],"all_touched_inputs_match_before_after":before==after,"raw_row_counts":counts,"expected_ic_cells":cells,"result_comparison":"PENDING_RESULT_ARTIFACT"}
 out["all_cells_ranked_or_reasoned"]=len(cells)==18 and all(c["reason"] in (None,"INSUFFICIENT_ROOTS","CONSTANT_FEATURE","CONSTANT_TARGET") for c in cells)
 if not out["all_touched_inputs_match_before_after"]:raise RuntimeError("input changed")
 mod.write_artifact(Path(q.out),mod.canonical_bytes(out),[root,Path(q.store),Path(q.price_store)])
if __name__=="__main__":main()
