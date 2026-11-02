"""Synthetic QA only. Uses the repository's existing deterministic test fixtures."""
import copy, json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from tests.test_build_options_command import _stores
from tests.test_options_intel_brief_ui import _brief, _card
from scripts.build_options_command import render
out=HERE/"fixtures"
out.mkdir(exist_ok=True)
stores=_stores()
def set_fixture_dates(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k in ("asof","as_of","session_date") and isinstance(v,str) and v.startswith("2026-07-"):
                value[k]="2026-08-12T20:10:00+00:00" if "T" in v else "2026-08-12"
            else: set_fixture_dates(v)
    elif isinstance(value,list):
        for v in value:set_fixture_dates(v)
set_fixture_dates(stores)
# Deliberately different clocks: a rebuild must not promote the research session.
stores["leaders"]["as_of"]="2026-11-02T03:00:00+00:00"
stores["leaders"]["session_date"]="2026-08-12"
for sym in stores["gex"]:
    stores["gex"][sym]["meta"]["asof"]="2026-08-12"
brief=_brief(opportunities=[_card("AAPL",direction="LONG",r=344),_card("QQQ",direction="SHORT",r=278)],
    as_of="2026-08-12",oi_counted="2026-08-13")
html=render(ROOT,stores=stores,intel_brief=brief,now=datetime(2026,8,13,10,tzinfo=timezone.utc))
html=html.replace("<head>","<head><base href=\"/templates/\">",1)
html=html.replace('<body class="page-options">','<body class="page-options"><div style="padding:8px 24px;color:var(--ink-warn);font:14px var(--font-ui)">SYNTHETIC QA FIXTURE — NOT MARKET DATA</div>',1)
(out/"workspace-current.html").write_text(html,encoding="utf-8")
payloads={"flow_desk.json":stores["flow_desk"],"flowdata/cohorts.json":{},
 "screenerdata/rows.json":stores["screener"],"flowleaders/leaders.json":stores["leaders"]}
for sym,record in stores["gex"].items():
    payloads["gex/"+sym+".json"]=record
    payloads["flow/"+sym+".json"]={}
    payloads["session/"+sym+".json"]={}
(out/"payloads.json").write_text(json.dumps(payloads,indent=2),encoding="utf-8")
print("Rendered synthetic UI fixture; no site/data writes.")
