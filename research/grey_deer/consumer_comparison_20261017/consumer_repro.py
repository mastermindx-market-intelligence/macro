"""Bounded source-function reproduction; never load live Portfolio modules or policy state."""
from __future__ import annotations
import argparse, ast, builtins, copy, hashlib, json, subprocess, sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

PIN = "a552a5e506ae808efa575c2e13cb56f478c72b87"
MACRO_PIN = "ab5156a4b2c336181f3c5256e7c0766f04f99598"
SOURCES = {
 "brain__market_view.py": "0dbf3c0dfd6beb0dec09cf7566967e4c0729a75d108bf3041145c76da2789e2b",
 "brain__regime_frame.py": "d3105e21265da63574a2076300b3bdaeda56383d2ca5679e081976ac57832abc",
 "portfolio__held_risk.py": "28aec4f1e9a6c57d1b7aecdb511967303eebfaefc6a4ba22d3a0d3381fb54856",
 "portfolio__context_gate.py": "bac914207c9d5d61bf1558a8fc5b40d5f1319bca3a2b29183040f7bc60a28033",
 "brain__neural_web_context.py": "2a4075b5a4bb54c0f2a964f44abcbbd7acdbdbc264b9076bd7f5ad17fd64f30f",
}
FIXED_NOW = datetime(2026, 10, 17, 7, 30, tzinfo=timezone.utc)
class FrozenDatetime(datetime):
 @classmethod
 def now(cls, tz=None):
  return FIXED_NOW.astimezone(tz) if tz else FIXED_NOW.replace(tzinfo=None)

def digest(raw):
 return hashlib.sha256(raw).hexdigest()
def json_digest(value):
 return digest(json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode())
def deny_live_import(name, *args, **kwargs):
 if name.split(".")[0] in {"brain", "portfolio", "engine", "core"}:
  raise ModuleNotFoundError("live first-party import intentionally unavailable in isolated reproduction")
 return builtins.__import__(name, *args, **kwargs)
def namespace():
 return {"__builtins__": {**vars(builtins), "__import__": deny_live_import},
         "json": json, "date": date, "datetime": FrozenDatetime,
         "timedelta": timedelta, "timezone": timezone}
def bind(source, names, constants=(), extra=None):
 tree=ast.parse(source)
 picked=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
 assert {n.name for n in picked}==set(names)
 ns=namespace()
 for n in tree.body:
  targets=n.targets if isinstance(n,ast.Assign) else [n.target] if isinstance(n,ast.AnnAssign) else []
  for target in targets:
   if isinstance(target,ast.Name) and target.id in constants:
    ns[target.id]=ast.literal_eval(n.value)
 if extra: ns.update(extra)
 compiled=ast.Module(body=[ast.ImportFrom(module="__future__",names=[ast.alias(name="annotations")],level=0),*picked],type_ignores=[])
 exec(compile(ast.fix_missing_locations(compiled),"<pinned-selected-functions>","exec"),ns)
 return ns

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--sources",type=Path,required=True)
 ap.add_argument("--macro-repo",type=Path,required=True)
 ap.add_argument("--output",type=Path,required=True)
 args=ap.parse_args()
 if args.output.exists(): raise SystemExit("refuse existing output directory")
 sources={k:(args.sources/k).read_bytes() for k in SOURCES}
 assert {k:digest(v) for k,v in sources.items()}==SOURCES
 text={k:v.decode() for k,v in sources.items()}
 before_status=subprocess.check_output(["git","status","--porcelain"],cwd=args.macro_repo,text=True)
 assert not before_status, "source checkout must be clean"
 args.output.mkdir(parents=True)
 log=args.output/"old_tail_fixture.jsonl"
 old={"asof":"2000-01-03","state":"caution","definition_id":"obsolete_fixture","mature":False}
 log.write_text(json.dumps(old)+"\n")
 rf=bind(text["brain__regime_frame.py"],
         ["_as_float","_trading_days_since","_read_radar_forward_log_state"],
         extra={"_RADAR_FORWARD_LOG":log})
 mv=bind(text["brain__market_view.py"],
         ["_stale_after_td","_freshness","_absent_record","_plane_record","_block",
          "_adapt_risk_radar","_adapt_neural_web","_tilt_score","_net_posture_tilt"],
         ["_STALE_TD_FALLBACK","_RISK_OFF","_RISK_ON","_NEUTRAL","PLANE_ORDER"],
         {"_rf":SimpleNamespace(**rf),"_cfg":lambda:{}})
 held=bind(text["portfolio__held_risk.py"],["_lane","_lane_market_regime"])
 nw=bind(text["brain__neural_web_context.py"],
         ["_risk_date","_risk_timestamp","_qualify_risk_envelope_context"],
         ["_STALE_DAYS","_RISK_SCHEMA","_RISK_FIELDS","_RISK_AUTHORITY_FLAGS","_ROTATION_LABELS"],
         {"_RISK_TIMEZONE":ZoneInfo("America/New_York")})
 def gate(raw):
  ns=bind(text["portfolio__context_gate.py"],["_default_risk"],
          extra={"_cached_board":lambda name:raw if name=="data/regime/latest.json" else {}})
  return ns["_default_risk"]()
 raw_sources={}
 for path in ["data/regime/latest.json","data/risk_envelope/latest.json"]:
  data=subprocess.check_output(["git","show",MACRO_PIN+":"+path],cwd=args.macro_repo)
  raw_sources[path]={"sha256":digest(data),"blob":subprocess.check_output(["git","rev-parse",MACRO_PIN+":"+path],cwd=args.macro_repo,text=True).strip()}
  raw_sources[path]["value"]=json.loads(data)
 raw=raw_sources["data/regime/latest.json"]["value"]
 envelope=raw_sources["data/risk_envelope/latest.json"]["value"]
 original_input_hashes={"regime":json_digest(raw),"envelope":json_digest(envelope)}
 base=mv["_adapt_risk_radar"](raw)
 qenv,qstatus=nw["_qualify_risk_envelope_context"](envelope,envelope["source_session"],now=FIXED_NOW)
 cases={}
 withheld=copy.deepcopy(raw)
 withheld["risk_radar"].update({"state":"caution","alert":False,"can_force":False,
  "drawdown_prob":{"h5":None,"h10":None,"h21":None},
  "drawdown_prob_evidence":{"precision_grade":False,"reason":"withheld_fixture"}})
 plane=mv["_adapt_risk_radar"](withheld)
 cases["1_withheld_forecast_caution"]={"input":withheld["risk_radar"],"legacy_plane":plane,
  "tilt":mv["_net_posture_tilt"]({"risk_radar":plane}),"gate_projection":gate(withheld)}
 intensity={}
 for score in (30,90):
  sample=copy.deepcopy(withheld);sample["risk_radar"]["top_score"]=score
  p=mv["_adapt_risk_radar"](sample)
  intensity[str(score)]={"confidence":p["confidence"],"magnitude":p["magnitude"],
   "direction":p["direction"],"tilt":mv["_net_posture_tilt"]({"risk_radar":p})}
 cases["2_intensity_only"]=intensity
 vocabulary={}
 for state in ["calm","watch","caution","elevated","risk-off","unknown",None,"BLOCK_ABSENT"]:
  sample=copy.deepcopy(withheld)
  if state=="BLOCK_ABSENT":sample.pop("risk_radar")
  else:sample["risk_radar"]["state"]=state
  sample["risk_state"]={"state":"risk-on"}
  p=mv["_adapt_risk_radar"](sample)
  vocabulary[str(state)]={"legacy_direction":p["direction"],"legacy_status":p["status"],
   "held_lane":held["_lane_market_regime"](sample,FIXED_NOW.date()),"gate_projection":gate(sample)}
 cases["3_vocabulary"]=vocabulary
 older,status=nw["_qualify_risk_envelope_context"](envelope,"2026-10-17",now=FIXED_NOW)
 cases["4_new_wrapper_old_source"]={"wrapper_asof":"2026-10-17","inner_session":envelope["source_session"],
  "qualified_value":older,"status":status}
 cases["5_measured_with_unavailable_hazard"]={"qualification":qstatus,
  "measured_state":qenv.get("measured_state") if qenv else None,
  "hazard_summary":qenv.get("hazard_summary") if qenv else None,
  "coverage":qenv.get("coverage") if qenv else None,
  "authority":qenv.get("authority") if qenv else None}
 cases["6_recent_file_old_tail"]={"fixture":old,"fixture_file_mtime":datetime.fromtimestamp(log.stat().st_mtime,timezone.utc).isoformat(),
  "native_return":rf["_read_radar_forward_log_state"](),
  "date_definition_maturity_returned":False,
  "gate_projection":gate({"risk_radar":old})}
 nw_plane=mv["_adapt_neural_web"]({"asof":envelope["source_session"],"stale":False,"verdict":{},
  "regime":{},"risk_envelope":qenv,"risk_envelope_status":qstatus})
 cases["7_duplicate_descriptive_path"]={"without_nw":mv["_net_posture_tilt"]({"risk_radar":base}),
  "with_nw":mv["_net_posture_tilt"]({"risk_radar":base,"neural_web":nw_plane}),
  "native_nw_status":nw_plane["status"],"native_nw_direction":nw_plane["direction"],
  "independence_inference":False,"risk_context_preserved":nw_plane["raw"].get("risk_envelope")==qenv}
 future=copy.deepcopy(withheld);future["risk_radar"]["asof"]="2099-01-01"
 future_plane=mv["_adapt_risk_radar"](future)
 cases["9_future_date_guard"]={"fixture_asof":"2099-01-01","legacy_plane":future_plane,
  "tilt":mv["_net_posture_tilt"]({"risk_radar":future_plane})}
 after_status=subprocess.check_output(["git","status","--porcelain"],cwd=args.macro_repo,text=True)
 after_hashes={k:digest((args.sources/k).read_bytes()) for k in SOURCES}
 unchanged={"source_snapshot_hashes":after_hashes==SOURCES,"macro_checkout_status":before_status==after_status,
  "captured_inputs":original_input_hashes=={"regime":json_digest(raw),"envelope":json_digest(envelope)},
  "live_first_party_modules_loaded":[k for k in sys.modules if k.split(".")[0] in {"brain","portfolio","engine","core"}]}
 cases["8_no_effect_boundary"]={"observed":unchanged,
  "live_book_policy_prompt_ledger_parity":"NOT_TESTED; no live assembler, policy, sizing, rank, execution or persistence path was called",
  "full_consumer_cutover_acceptance":False}
 assert all(unchanged[k] for k in ["source_snapshot_hashes","macro_checkout_status","captured_inputs"])
 assert not unchanged["live_first_party_modules_loaded"]
 result={"schema":"risk-radar-isolated-consumer-reproduction/v1","executed_at":datetime.now(timezone.utc).isoformat(),
  "analysis_clock":FIXED_NOW.isoformat(),"source_commit":PIN,"source_sha256":SOURCES,
  "macro_commit":MACRO_PIN,"macro_sources":{k:{a:b for a,b in v.items() if a!="value"} for k,v in raw_sources.items()},
  "runner_sha256":digest(Path(__file__).read_bytes()),"scope":"Exact selected source functions; dependency-injected fixtures and source-only isolation, not full application/runtime delivery.",
  "bindings":{"market_view_config":"empty fixture config; native fallback five sessions","calendar":"first-party imports denied; native weekday fallback, only October16->17 age path in fresh fixtures","clock":"fixed declared research clock; executed_at separate"},
  "real_captured_result":{"legacy_plane":base,"held_lane":held["_lane_market_regime"](raw,FIXED_NOW.date()),"gate_projection":gate(raw),"envelope_status":qstatus},
  "cases":cases,"fits":0,"trial_registrations":0,"production_writes":0,"mission_complete":False}
 (args.output/"receipt.json").write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print(json.dumps({"receipt":str(args.output/"receipt.json"),"receipt_sha256":digest((args.output/"receipt.json").read_bytes()),
  "runner_sha256":result["runner_sha256"],"actual_legacy":base,"actual_envelope_status":qstatus,
  "intensity_only":intensity,"elevated":vocabulary["elevated"],"future_freshness":future_plane["freshness"],
  "future_status":future_plane["status"],"source_no_effect":unchanged}))
if __name__=="__main__":main()
