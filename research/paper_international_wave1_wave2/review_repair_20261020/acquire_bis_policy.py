"""Acquire the official BIS policy artifact and exercise the normal parser."""
from pathlib import Path
import sys,json,urllib.request
from datetime import datetime,timezone
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from collectors.intl_country_sources import parse_bis,BIS_POLICY
from lib.intl_policy_evidence import select_policy_decision
OUT=Path(__file__).resolve().parent
started=datetime.now(timezone.utc).isoformat()
request=urllib.request.Request(BIS_POLICY,headers={"User-Agent":"Mastermind-X country research source validation"})
with urllib.request.urlopen(request,timeout=45) as response:
    status=response.status
    blob=response.read(16_000_001)
retrieved=datetime.now(timezone.utc).isoformat()
assert status==200 and len(blob)<=16_000_000
(OUT/"bis_policy_source.zip").write_bytes(blob)
parsed=parse_bis(blob,"policy",retrieved_at=retrieved)
(OUT/"bis_policy_parsed.json").write_text(json.dumps(parsed,indent=2,ensure_ascii=False)+"\n")
base=json.loads((ROOT/"config/intl_country_baseline.json").read_text())
today=datetime.now(timezone.utc).date()
summary={}
for cc,p in parsed["observations"].items():
    selected=select_policy_decision(base["policy_decisions"],cc,today=today,monthly=p,
                                   review_events=base.get("policy_reviews"))
    summary[cc]={"value":p["value"],"period":p["period"],
                 "comparison_qualification":p.get("comparison_qualification"),
                 "instrument":p.get("instrument"),"qualifier":p.get("setting_qualifier"),
                 "comparison_observation_date":p.get("comparison_observation_date"),
                 "decision_state":selected.get("state") if selected else None}
receipt={"schema":"intl_bis_source_validation.v1","url":BIS_POLICY,"http_status":status,
         "request_started_at":started,"retrieved_at":retrieved,
         "source_sha256":sha256(blob).hexdigest(),"source_bytes":len(blob),
         "countries":summary,"canonical_store_written":False,"baseline_admitted":False,
         "source_documentation":"https://www.bis.org/statistics/cbpol/cbpol_doc.pdf"}
(OUT/"bis_policy_acquisition.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt),flush=True)
