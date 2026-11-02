"""Reproduce the published data snapshot in an ignored local QA tree.
Reads fixed JSON blobs from an existing Git commit. No checkout, collector,
production data write, remote fetch, or market timestamp substitution.
"""
import argparse, hashlib, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts.build_options_command import render
ap=argparse.ArgumentParser()
ap.add_argument("--source-pin",default="e4009c94d75770739844240b22f5fc915668aa9b")
args=ap.parse_args()
if not re.fullmatch(r"[0-9a-f]{40}",args.source_pin):raise SystemExit("Exact source commit required")
PIN=args.source_pin
OUT=HERE/"fixtures"/"published";OUT.mkdir(parents=True,exist_ok=True)
paths=[
"site/flow_desk.json","site/screenerdata/rows.json","site/flowleaders/leaders.json",
"data/market_structure/latest.json","site/vol/regime.json","site/gex/index.json",
"site/options_intel_brief.json","site/options_payoff_lab/latest.json",
"site/options_skew/latest.json","site/options_catalyst_links/latest.json",
"site/flowdata/cohorts.json",
]+["site/gex/"+s+".json" for s in ["SPX","SPY","QQQ","IWM"]]+[
"site/flow/SPY.json","site/session/SPY.json"]
records={};manifest={"source_pin":PIN,"template_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"reads":[]}
for path in paths:
    p=subprocess.run(["git","show",PIN+":"+path],cwd=ROOT,capture_output=True,timeout=35)
    if p.returncode:
        manifest["reads"].append({"path":path,"state":"ABSENT_AT_PIN"});continue
    try:value=json.loads(p.stdout)
    except (ValueError,UnicodeError):
        manifest["reads"].append({"path":path,"state":"INVALID_JSON"});continue
    records[path]=value
    target=OUT/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.stdout)
    manifest["reads"].append({"path":path,"state":"READ","bytes":len(p.stdout),"sha256":hashlib.sha256(p.stdout).hexdigest()})
stores={
"flow_desk":records.get("site/flow_desk.json"),
"screener":records.get("site/screenerdata/rows.json"),
"leaders":records.get("site/flowleaders/leaders.json"),
"market_structure":records.get("data/market_structure/latest.json"),
"vol":records.get("site/vol/regime.json"),
"gex":{s:records["site/gex/"+s+".json"] for s in ["SPX","SPY","QQQ","IWM"] if "site/gex/"+s+".json" in records},
"gex_index":records.get("site/gex/index.json")}
html=render(ROOT,stores=stores,intel_brief=records.get("site/options_intel_brief.json"),
payoff_lab=records.get("site/options_payoff_lab/latest.json"),
skew_source=records.get("site/options_skew/latest.json"),
catalyst_links=records.get("site/options_catalyst_links/latest.json"),
now=datetime(2026,11,2,3,30,tzinfo=timezone.utc))
setup='<base href="/templates/"><script>var qa=new URLSearchParams(location.search);localStorage.setItem("theme",qa.get("theme")||"light");localStorage.setItem("lang",qa.get("lang")||"en");</script>'
html=html.replace("<head>","<head>"+setup,1)
(OUT/"workspace.html").write_text(html,encoding="utf-8")
payloads={k.removeprefix("site/"):v for k,v in records.items() if k.startswith("site/")}
(OUT/"payloads.json").write_text(json.dumps(payloads),encoding="utf-8")
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(json.dumps({"source_pin":PIN,"template_head":manifest["template_head"],"read_count":len(records),"unavailable":[x["path"] for x in manifest["reads"] if x["state"]!="READ"],"output":str(OUT/"workspace.html"),"production_writes":False},indent=2))
