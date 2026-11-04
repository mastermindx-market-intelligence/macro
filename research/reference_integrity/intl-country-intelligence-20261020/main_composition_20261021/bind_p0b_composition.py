"""Bind actual P0B runs while preserving the exact two-parent evidence histories."""
import datetime,hashlib,json,pathlib,subprocess
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
C=R/"research/reference_integrity/intl-country-intelligence-20261020/main_composition_20261021"
P=R/"mockups/evidence/prophet-p0b-zero-fouc"
SOURCE="eac74360b9a423ece8b1af786aca5fd29cb48c3f"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"))
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()==SOURCE
execution=json.loads((C/"p0b_execution.json").read_text())
assert execution["source_commit"]==SOURCE and execution["state"]=="PASS"
for row in execution["actual_receipts"]: assert sha(R/row["path"])==row["sha256"],row
incoming=json.loads((C/"incoming_main/manifest.json").read_text())
local=json.loads((C/"accepted_local/manifest.json").read_text())
current=json.loads((P/"manifest.json").read_text())
assert current==incoming,"Inspect unexpected manifest changes rather than replacing them"
history=[]; seen=set()
for manifest in [incoming,local]:
 for extension in manifest.get("repair_extension_history",[])+[manifest["repair_extension"]]:
  key=canon(extension)
  if key not in seen: seen.add(key);history.append(extension)
claims={"source_contract":"browser_fixture","browser_fixture":"reproducible","canonical_build":"unavailable","production":"none"}
browser_receipts={}; shots=[]
for market,name in [("hk","mobile-layout.json"),("ca","mobile-layout-canada.json")]:
 path=P/name; receipt=json.loads(path.read_text()); matrix=receipt["owner_projection_matrix"]
 assert receipt["pass"] and matrix["pass"] and receipt["claims"]==claims
 assert matrix["primary_passed"]==48 and matrix["degraded_controls_passed"]==16 and len(matrix["cases"])==64
 assert all(row["pass"] for row in matrix["cases"])
 market_shots=[{"path":row["screenshot"]["path"],"sha256":row["screenshot"]["sha256"]} for row in matrix["cases"] if row.get("screenshot")]
 assert len(market_shots)==matrix["screenshot_count"]==8
 for row in market_shots: assert sha(R/row["path"])==row["sha256"]
 shots.extend(market_shots)
 for path,expected in receipt["loaded_assets"].items(): assert sha(R/path)==expected,path
 for input_path,expected in receipt["construction_inputs"].items(): assert sha(R/input_path)==expected,input_path
 browser_receipts[market]={"path":str(pathlib.Path("mockups/evidence/prophet-p0b-zero-fouc")/name),"sha256":sha(P/name),"pass":True,"primary_cases":48,"degraded_control_cases":16,"screenshots":8}
extension={"schema":"mastermind.prophet_p0b_owner_empty_repair_extension.v1","operation":"prophet-cockpit-p0b-zero-fouc-20260904-sol-001","generated_at":execution["completed_at"],"claims":claims,"pass":True,"fixture_receipt":{"path":str((P/"rendered-fixture.json").relative_to(R)),"sha256":sha(P/"rendered-fixture.json")},"browser_receipts":browser_receipts,"screenshots":sorted(shots,key=lambda x:x["path"]),"totals":{"markets":2,"owner_cases_per_market":3,"primary_cases":96,"degraded_control_cases":32,"total_cases":128,"screenshots":16}}
current["repair_extension_history"]=history;current["repair_extension"]=extension
(P/"manifest.json").write_text(json.dumps(current,indent=2)+"\n")
report={"schema":"intl.p0b_composition_rebind.v1","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":SOURCE,"execution_receipt":str((C/"p0b_execution.json").relative_to(R)),"execution_receipt_sha256":sha(C/"p0b_execution.json"),"manifest_sha256":sha(P/"manifest.json"),"preserved_incoming_history":len(incoming.get("repair_extension_history",[])),"preserved_local_history":len(local.get("repair_extension_history",[])),"composed_history":len(history),"both_parent_current_extensions_preserved":all(canon(m["repair_extension"]) in seen for m in [incoming,local]),"actual_browser_cases":128,"actual_screenshots":16,"claims":claims,"pass":True}
(C/"p0b_rebind.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2),flush=True)
