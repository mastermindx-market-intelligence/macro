import io,json,hashlib,subprocess,sys
from pathlib import Path
import pandas as pd
repo=Path(sys.argv[1]);phase=sys.argv[2] if len(sys.argv)>2 else "before";sys.path.insert(0,str(repo))
from engine import intl_bonds as ib
if phase=="before":
 import types
 original=types.ModuleType("bonds_depth_original_intl")
 original.__file__=str(repo/"engine/intl_bonds.py")
 exec(compile(subprocess.check_output(["git","show","ed9fb81da853429ce87495d6c012467ebf057548:engine/intl_bonds.py"],cwd=repo,text=True),original.__file__,"exec"),original.__dict__)
 ib=original
head="ed9fb81da853429ce87495d6c012467ebf057548"
cache={};receipts={}
def read(grp,key):
 path=f"data/{grp}/{key}.parquet"
 if path not in cache:
  r=subprocess.run(["git","show",head+":"+path],cwd=repo,capture_output=True)
  if r.returncode:cache[path]=None
  else:
   cache[path]=pd.read_parquet(io.BytesIO(r.stdout))
   receipts[path]={"sha256":hashlib.sha256(r.stdout).hexdigest(),"rows":len(cache[path])}
 return cache[path]
ib.store.read=read
frames=[]
for key,alias in [("DGS10","us10y"),("DGS2","us2y"),("DGS3MO","us3m"),("DFII10","us10y_real")]:
 d=read("fred",key);s=d.iloc[:,0].rename(alias);frames.append(s)
f=pd.concat(frames,axis=1).iloc[-800:]
from engine.yield_momentum import ORIGIN_ATTR,SERIES,capture_rate_observations
rate_columns=set(SERIES.values())
f.attrs[ORIGIN_ATTR]={}
for sid,col in [("DGS10","us10y"),("DGS2","us2y"),("DGS3MO","us3m"),("DFII10","us10y_real")]:
 if col in rate_columns:
  f.attrs[ORIGIN_ATTR][col]=capture_rate_observations(read("fred",sid).iloc[:,0],f[col],source_id=sid,source_column=col)
if len(sys.argv)>3 and sys.argv[3]=="missing_receipt":f.attrs.pop(ORIGIN_ATTR)

snapshot=ib.snapshot(f)
rows=[]
for spec in ib.ROSTER:
 row=next((r for r in snapshot["countries"] if r["code"]==spec["code"]),None)
 raw=ib._series(spec,"y10",f)
 if row and raw is not None and not raw.dropna().empty:
  actual=raw.dropna();observed=actual.index[-1];age=(f.index[-1]-observed).days
  rows.append({"code":spec["code"],"source_key":spec["y10"],"ccy":row["ccy"],"slope_basis":row["slope_basis"],"cadence":row["cadence"],"actual_observation":str(observed.date()),"analysis_endpoint":str(f.index[-1].date()),"raw_age_days":age,"existing_stale_flag":row["stale"],"expected_by_existing_threshold":bool(age>ib.STALE_DAYS[spec["cadence"]]),"y10":row["y10"]})
result={"retained_data_source":head,"scope":"Native intl_bonds.snapshot over exact retained Git parquet values; no provider, acquisition or full feature-engine run","rows":rows,"input_receipts":receipts}
out=Path(__file__).parent;(out/("retained-owner-source-probe.json" if phase=="before" else "retained-owner-source-probe-"+phase+".json")).write_text(json.dumps(result,indent=2)+"\n");(out/("native-intl-snapshot-"+phase+".json")).write_text(json.dumps(snapshot,indent=2)+"\n")
print(json.dumps({"source":head,"rows":rows},indent=2))
