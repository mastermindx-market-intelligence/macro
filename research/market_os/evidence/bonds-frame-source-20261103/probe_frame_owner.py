import io,json,subprocess,sys,copy,types
from pathlib import Path
from unittest.mock import patch
import pandas as pd
repo=Path(sys.argv[1]);sys.path.insert(0,str(repo))
from engine import inputs,intl_bonds as ib,yield_momentum as ym
h="ed9fb81da853429ce87495d6c012467ebf057548"
raw_bytes=subprocess.check_output(["git","show",h+":data/fred/DGS10.parquet"],cwd=repo)
raw=pd.read_parquet(io.BytesIO(raw_bytes)).iloc[:,0].dropna().loc[:"2026-10-16"]
idx=pd.bdate_range("2026-09-01","2026-10-30")
tickers={t for group in inputs.config.load()["yahoo"]["tickers"].values() for t in group}
closes=pd.DataFrame({t:100.0 for t in tickers},index=idx)
with patch.object(inputs,"yahoo_closes",return_value=closes),patch.object(inputs,"_fred",return_value={"us10y":raw}),patch.object(inputs.store,"read",return_value=None):
 f=inputs.build_features()
 prior=f.copy(deep=True);prior_attrs=copy.deepcopy(f.attrs)
 old=types.ModuleType("bonds_frame_predecessor")
 old.__file__=str(repo/"engine/intl_bonds.py")
 exec(compile(subprocess.check_output(["git","show","486afc845321a23c3508f3252bd2e52ae9de3c8c:engine/intl_bonds.py"],cwd=repo,text=True),old.__file__,"exec"),old.__dict__)
 before=old._country_row(next(s for s in old.ROSTER if s["code"]=="US"),f,None)
 row=ib._country_row(next(s for s in ib.ROSTER if s["code"]=="US"),f,None)
 pd.testing.assert_frame_equal(prior,f)
 assert prior_attrs==f.attrs
 ignored={"stale","observed_as_of","observation_qualified","sources"}
 assert all(before[k]==row[k] for k in before if k not in ignored)
 tail=ym._finite(f.us10y).iloc[-ym.TURN_LOOKBACK:]
 dates,status,item=ym._origin(tail,"us10y",f.attrs.get(ym.ORIGIN_ATTR))
record={"scope":"Actual native inputs.build_features→put→capture_rate_observations→IB composition; retained FRED source plus synthetic calendar/closes solely to control frame; no provider/store writes or model claim","source_cutoff":str(raw.index[-1].date()),"analysis_endpoint":str(f.index[-1].date()),"feature_last_finite":str(f.us10y.dropna().index[-1].date()),"receipt_schema":item["schema"],"receipt_source_id":item["source_id"],"receipt_basis":item["source_basis"],"receipt_origin_status":status,"receipt_origin_at_last_finite":dates[tail.index.get_loc(f.us10y.dropna().index[-1])],"selected_yield":row["y10"],"disclosed_observation":row["observed_as_of"],"stale":row["stale"],"expected_source_age_days":14,"existing_daily_threshold":12,"predecessor_observed":before["observed_as_of"],"predecessor_stale":before["stale"],"all_original_nonclock_fields_equal":True,"input_values_and_receipts_unchanged":True}
phase=sys.argv[2];out=Path(__file__).parent;(out/("frame-owner-"+phase+".json")).write_text(json.dumps(record,indent=2)+"\n");print(json.dumps(record,indent=2))
