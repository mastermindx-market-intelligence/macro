import ast, hashlib, json, subprocess
from pathlib import Path
W = "/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/risk-radar-meta-ceo-census-20261017-01c18c888a133151"
REF = "646cc093b4982eabc736862926fe7f1fc458b8a1"
PINS = {}
def selected(path, names, pinned_blob=None):
    ref = pinned_blob or REF + ":" + path
    raw = subprocess.check_output(["git", "show", ref], cwd=W)
    text = raw.decode()
    found=[]
    for node in ast.parse(text).body:
        name=getattr(node,"name",None)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
        if name in names: found.append(node)
    assert len(found)==len(names), (path,len(found),names)
    PINS[path]={"blob":subprocess.check_output(["git","rev-parse",ref],cwd=W,text=True).strip(),"sha256":hashlib.sha256(raw).hexdigest(),"executed_symbols":sorted(names)}
    return ast.unparse(ast.Module(body=found,type_ignores=[]))
reader=selected("scripts/publish_r2.py", {"_POOL_FLOOR","_POOL_HEADROOM","_TRANSFER_CONCURRENCY","_pool_size","_client"})
om_code=selected("lib/observed_moves.py", {"LOSS_THRESHOLD","_as_series","forward_max_loss","loss_event"})
stage_code=selected("scripts/research/grey_deer_pullback_stage1.py", {"AS_OF","IDENTITY_COLUMNS","_enc","normalize_subframe","subframe_sha256","HORIZONS","THRESHOLD","EPISODE_PRE","build_labels","event_clusters","cluster_window","merge_episodes"})
t12_code=selected("scripts/research/grey_deer_episode_samples.py", {"SCHEMA","DEFAULT_HORIZONS","DEFAULT_SEED","DEFAULT_PER_EPISODE","DEFAULT_BUFFER_SESSIONS","DEFAULT_MAX_TRIES","_iso_dates","_input_sha256","_event_origin_indices","event_episodes","_eligible_pools","_propose","negative_controls","build_sample"}, "0a0eecb98e743b780db1ee3b0382e268d592fa67")
spec=subprocess.check_output(["git","cat-file","blob","fe68838867982e845297aeb0daf518e0387120f9"],cwd=W)
PINS["research/grey_deer/EPISODE_SAMPLE_SPEC_2026-10-13.md"]={"blob":"fe68838867982e845297aeb0daf518e0387120f9","sha256":hashlib.sha256(spec).hexdigest()}
prior=json.loads(Path("/tmp/risk-radar-spy-input-identity-20261017.json").read_text())
assert prior["status"]=="INPUT_IDENTITY_ADMITTED"
remote="""from __future__ import annotations
import os, io, json, hashlib, platform, types
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from dotenv import dotenv_values
for k,v in dotenv_values('/etc/macro-api.env').items():
    if v is not None and k.startswith('R2_'): os.environ[k]=v
"""
remote+=reader+"\n"
remote+="om=types.ModuleType('observed_moves')\nom.__dict__.update(np=np,pd=pd)\nexec("+repr(om_code)+",om.__dict__)\n"
remote+="stage1=types.ModuleType('grey_deer_pullback_stage1')\nstage1.__dict__.update(np=np,pd=pd,hashlib=hashlib,om=om)\nexec("+repr(stage_code)+",stage1.__dict__)\n"
remote+="t12=types.ModuleType('grey_deer_episode_samples')\nt12.__dict__.update(np=np,pd=pd,hashlib=hashlib,stage1=stage1)\nexec("+repr(t12_code)+",t12.__dict__)\n"
remote+="PINS="+repr(PINS)+"\nPRIOR="+repr(prior)+"\n"
remote+="""
assert tuple(stage1.HORIZONS)==(5,10,21) and stage1.EPISODE_PRE==21 and stage1.THRESHOLD==0.05
client=_client(1)
assert client is not None
obj=client.get_object(Bucket=os.environ["R2_BUCKET"], Key=PRIOR["source_key"], IfMatch='"'+PRIOR["object"]["etag"]+'"')
assert obj["ContentLength"]==PRIOR["object"]["bytes"] and obj["ContentLength"]<=262144
raw=obj["Body"].read(262145);obj["Body"].close()
assert hashlib.sha256(raw).hexdigest()==PRIOR["object"]["sha256"]
frame=stage1.normalize_subframe(pd.read_parquet(io.BytesIO(raw)))
assert stage1.subframe_sha256(frame)==PRIOR["expected_normalized_sha256"]
assert len(frame)==1321
close=pd.Series(frame["close"].to_numpy(dtype=float), index=pd.to_datetime(frame["date"]))
sample=t12.build_sample(close,ticker="SPY",horizons=(5,10,21),seed=20261013)
payload=json.dumps(sample,sort_keys=True).encode("utf-8")
digest=hashlib.sha256(payload).hexdigest()
support={}
for hs,part in sample["horizons"].items():
    h=int(hs);episodes=part["episodes"];controls=part["controls"]
    per=[]
    for e in episodes:
        cs=[c for c in controls if c["episode_id"]==e["episode_id"]]
        per.append({"episode_id":e["episode_id"],"requested":3,"placed":len(cs),"shortfall":3-len(cs)})
    immature=[]
    warmup=[]
    for c in controls:
        lo,hi=c["window_idx"]
        tail=max(0,hi-max(lo,len(close)-h)+1)
        if tail: immature.append({"control_id":c["control_id"],"immature_origin_count":tail,"window":c["window"]})
        cold=max(0,min(hi,62)-lo+1)
        if cold: warmup.append({"control_id":c["control_id"],"pre_warmup_origin_count":cold})
    support[hs]={"episodes":len(episodes),"event_origins":sum(e["n_event_origins"] for e in episodes),
                 "requested_controls":len(episodes)*3,"placed_controls":len(controls),"control_shortfall":part["shortfall"],
                 "month_matched_controls":sum(c["month_matched"] for c in controls),"per_episode":per,
                 "controls_with_immature_origins":immature,"controls_with_pre_warmup_origins":warmup,
                 "independent_episode_count":None}
receipt={"schema":"grey_deer.t12_sample_freeze.v1","frozen_at_utc":datetime.now(timezone.utc).isoformat(),
         "status":"SAMPLE_IDENTITY_FROZEN","method_owner":"Sol / Meta-CEO, current Chairman commission",
         "source_ref":PRIOR["source_ref"],"source_pins":PINS,"input_admission":PRIOR,
         "environment":{"python":platform.python_version(),"numpy":np.__version__,"pandas":pd.__version__},
         "sample_sha256":digest,"sample_bytes":len(payload),"canonical_serialization":"json.dumps(sample, sort_keys=True).encode('utf-8'); no trailing newline",
         "sample_identity":{k:v for k,v in sample.items() if k!="horizons"},"support_by_horizon":support,
         "execution":{"original_builder_calls":1,"original_label_helpers_used":True,"pure_source_AST_isolation":True,
                      "stage1_study_rerun":False,"sample_label_construction":True,"hypothesis_outcomes_scored":False,
                      "macro_feature_join":False,"fits":0,"trial_writes":0,"namespace_hydration":False,
                      "production_file_writes":False,"provider_fetch":False},
         "t13_fit_admitted":False,"daily_origin_projection_frozen":False,"publication_admitted":False,
         "limitations":["Retrospective event/control proportions are not a daily base rate or calibrated probability.",
                        "Control shortfalls and immature-tail intersections are retained unchanged.",
                        "No warmup cut is applied by the original T12 builder.",
                        "Cross-horizon overlap is not independent replication.",
                        "No source-purpose or model validation gate is waived by sample identity."]}
print(json.dumps({"receipt":receipt,"sample":sample}))
"""
r=subprocess.run(["ssh","-i","/Users/chriswong/.ssh/macro_dashboard_deploy_v2","-o","BatchMode=yes","-o","ConnectTimeout=12",
                  "root@146.190.142.17","/opt/macro-api/.venv/bin/python","-"],input=remote,text=True,capture_output=True,timeout=150)
if r.returncode:
    print(json.dumps({"status":"SAMPLE_FREEZE_EXECUTION_FAILED","exit_code":r.returncode,"stderr":r.stderr[-1500:]}));raise SystemExit(r.returncode)
j=json.loads(r.stdout);receipt=j["receipt"];sample=j["sample"]
payload=json.dumps(sample,sort_keys=True).encode("utf-8")
assert hashlib.sha256(payload).hexdigest()==receipt["sample_sha256"]
receipt["orchestrator_script_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
base=Path("/tmp/risk-radar-t12-freeze-20261017");base.mkdir(exist_ok=True)
(base/"sample.json").write_bytes(payload)
(base/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":receipt["status"],"sample_sha256":receipt["sample_sha256"],"sample_bytes":len(payload),
                  "sample_identity":receipt["sample_identity"],"support_by_horizon":receipt["support_by_horizon"],
                  "environment":receipt["environment"],"artifact_dir":str(base)}))
