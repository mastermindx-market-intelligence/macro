#!/usr/bin/env python3
"""Fixed-date arithmetic audit for frozen Theta v1.1; no hypothesis results."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd

WITNESSES = (("QQQ", 2019, "2019-06-03"), ("IWM", 2021, "2021-04-06"), ("NVDA", 2024, "2024-08-06"))
GCOLS = ["root","date","expiration","strike","right","bid","ask","underlying_price","implied_vol","delta","gamma","vanna","charm"]
OCOLS = ["root","date","expiration","strike","right","open_interest"]
ID = ["date","expiration","strike","right"]

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()

def paths(manifest, store, prices, roots):
    entries={e["relative_path"]:e for e in manifest["entries"]}; out=[]
    for root,year,_ in roots:
        for kind in ("greeks","oi"):
            rel=f"theta/{kind}/{root}/{year}.parquet"; out.append((rel,Path(store)/kind/root/f"{year}.parquet"))
    for root in {"SPY",*(x[0] for x in roots)}:
        rel=f"price/data/yahoo/{root}.parquet"; out.append((rel,Path(prices)/f"{root}.parquet"))
    checked={}
    for rel,p in out:
        e=entries.get(rel)
        if e is None or e.get("state") != "present" or not p.is_file(): raise RuntimeError("unbound input "+rel)
        checked[rel]=sha(p)==e.get("sha256")
    if not all(checked.values()): raise RuntimeError("manifest hash mismatch")
    return checked

def raw(path, cols, day):
    return pd.read_parquet(path, columns=cols, filters=[("date", "=", pd.Timestamp(day))])

def norm(g, o, root, year):
    def clean(x, oi=False):
        x=x.copy(); x["date"]=pd.to_datetime(x.date,errors="coerce").dt.date; x["expiration"]=pd.to_datetime(x.expiration,errors="coerce").dt.date
        for c in (["strike","open_interest"] if oi else ["strike","bid","ask","underlying_price","implied_vol","delta","gamma","vanna","charm"]): x[c]=pd.to_numeric(x[c],errors="coerce")
        x["right"]=x.right.astype(str).str.upper()
        ok=x.date.notna()&x.expiration.notna()&x.date.map(lambda d:d.year==year)&x.root.astype(str).str.upper().eq(root)&x.right.isin(["C","P"])&np.isfinite(x.strike)&x.strike.gt(0)&x.expiration.gt(x.date)
        x=x.loc[ok]; return x.loc[~x.duplicated(ID,keep=False)].copy()
    g,o=clean(g),clean(o,True).rename(columns={"open_interest":"oi"})
    m=g.merge(o[ID+["oi"]],on=ID,how="inner",validate="one_to_one")
    q=np.isfinite(m.bid)&m.bid.gt(0)&np.isfinite(m.ask)&m.ask.gt(0)&m.bid.le(m.ask)&np.isfinite(m.underlying_price)&m.underlying_price.gt(0)&np.isfinite(m.implied_vol)&m.implied_vol.ge(.005)&np.isfinite(m.oi)&m.oi.gt(0)
    return m.loc[q].copy()

def manual(book, greek):
    if book.empty or greek not in book: return None, "NO_USABLE_QUOTES"
    x=pd.to_numeric(book[greek],errors="coerce").to_numpy(float)
    if np.isfinite(x).mean() < .90: return None, "COVERAGE_LT_90"
    z=np.where(book.right.eq("C").to_numpy(),1.,-1.)*book.oi.to_numpy(float)*x
    den=np.abs(z[np.isfinite(z)]).sum()
    return (float(z[np.isfinite(z)].sum()/den),"OK") if den>0 else (None,"ZERO_DENOM")

def same(a,b):
    null=lambda x: x is None or (isinstance(x,(float,np.floating)) and not np.isfinite(x))
    return (null(a) and null(b)) or (not null(a) and not null(b) and bool(np.isclose(a,b,rtol=0,atol=1e-12)))

def direct_label(mod, prices, spy, t, h, era_end, expected):
    if len(expected)!=h+1 or expected[-1]>era_end: return None,None,"ERA_BOUNDARY_PURGE"
    if prices is None: return None,None,"ROOT_PRICE_UNAVAILABLE"
    if spy is None: return None,None,"SPY_PRICE_UNAVAILABLE"
    fill=mod.fill_index(prices,t); sf=mod.fill_index(spy,t)
    if fill is None: return None,None,"ROOT_FILL_UNAVAILABLE"
    if sf is None: return None,None,"SPY_FILL_UNAVAILABLE"
    a,b=prices.iloc[fill:fill+h+1],spy.iloc[sf:sf+h+1]
    if not a.index.equals(expected): return None,None,"ROOT_NATIVE_SESSION_WINDOW_MISMATCH"
    if not b.index.equals(expected): return None,None,"SPY_NATIVE_SESSION_WINDOW_MISMATCH"
    if not (np.isfinite(a).all() and (a>0).all()): return None,None,"ROOT_INVALID_WINDOW_PRICE"
    if not (np.isfinite(b).all() and (b>0).all()): return None,None,"SPY_INVALID_WINDOW_PRICE"
    if mod._has_split_seam(prices,fill,h): return None,None,"ROOT_SPLIT_SEAM"
    if mod._has_split_seam(spy,sf,h): return None,None,"SPY_SPLIT_SEAM"
    if not mod._spy_window_matches(prices,fill,spy,h,t.date().isoformat()): return None,None,"SPY_WINDOW_MISMATCH"
    return float(a.iloc[-1]/a.iloc[0]-b.iloc[-1]/b.iloc[0]),float(np.std(np.diff(np.log(a.to_numpy())),ddof=1)*np.sqrt(252)),None

def main():
    p=argparse.ArgumentParser(); p.add_argument("--source-root",required=True); p.add_argument("--manifest",required=True); p.add_argument("--store",required=True); p.add_argument("--price-store",required=True); p.add_argument("--out",required=True); a=p.parse_args()
    root=Path(a.source_root); sys.path.insert(0,str(root)); from scripts.research import options_history_retrospective as mod
    manifest_path=Path(a.manifest); manifest=json.loads(manifest_path.read_text()); mh=sha(manifest_path); before=paths(manifest,a.store,a.price_store,WITNESSES)
    assert mh == "fa1453f1de296150055eea27fce440722ff491f9083145ebd5e4d66c5cb8e3d3", "frozen manifest mismatch"
    assert mod.source_digest(root) == manifest["source_code_digest"], "source mismatch"
    cal=mod.study_sessions(); spy,_=mod.read_prices(Path(a.price_store)/"SPY.parquet"); rows=[]
    for ticker,year,ds in WITNESSES:
        g=raw(Path(a.store)/"greeks"/ticker/f"{year}.parquet",GCOLS,ds); o=raw(Path(a.store)/"oi"/ticker/f"{year}.parquet",OCOLS,ds); book=norm(g,o,ticker,year)
        prod,_=mod.features_for_year(g,o,ticker,year); at=prod.loc[pd.Timestamp(ds)] if pd.Timestamp(ds) in prod.index else pd.Series(dtype=object)
        feats={};
        for greek,name in (("gamma","net_gamma_norm"),("vanna","net_vanna_norm"),("charm","net_charm_norm")):
            value,reason=manual(book,greek); got=at.get(name); feats[name]={"match":same(value,got),"null_reason":reason if value is None else None}
        prices,_=mod.read_prices(Path(a.price_store)/f"{ticker}.parquet"); i=cal.get_loc(pd.Timestamp(ds)); era_end=pd.Timestamp("2019-12-31" if year<=2019 else "2022-12-31" if year<=2022 else "2025-12-31")
        labels={}
        for h in (5,21):
            expected=cal[i+1:i+h+2]; got=mod.label_at(prices,spy,pd.Timestamp(ds),h,era_end,expected); ex,rv,reason=direct_label(mod,prices,spy,pd.Timestamp(ds),h,era_end,expected)
            labels[str(h)]={"match":reason==got["reason"] and (reason is not None or (same(ex,got["excess"]) and same(rv,got["rv"]))),"null_reason":reason}
        rows.append({"root":ticker,"date":ds,"input_counts":{"greeks":len(g),"oi":len(o),"joined_usable":len(book)},"features":feats,"labels":labels})
    after=paths(manifest,a.store,a.price_store,WITNESSES); receipt={"source_head":"a7ee15312486cac5992e2fb658135adff465939e","frozen_manifest_sha256":mh,"witness_dates":[x[2] for x in WITNESSES],"hashes_match_before_and_after":before==after and all(after.values()),"witnesses":rows}
    receipt["all_match"]=receipt["hashes_match_before_and_after"] and all(x["features"][k]["match"] and x["labels"][h]["match"] for x in rows for k in x["features"] for h in x["labels"])
    assert mod.source_digest(root) == manifest["source_code_digest"], "source changed"
    mod.write_artifact(Path(a.out), mod.canonical_bytes(receipt), [root, Path(a.store), Path(a.price_store)])
    if not receipt["all_match"]: raise SystemExit(1)
if __name__=="__main__": main()
