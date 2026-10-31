"""Bind actual P0B runs while preserving all three pinned evidence generations."""
import datetime,hashlib,json,pathlib,re,subprocess
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
C=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_brain_20261022")
P=R/"mockups/evidence/prophet-p0b-zero-fouc"
SOURCE="f1fafde0bbf95550ed964de3a60920a2619778e4"
if not re.fullmatch(r"[0-9a-f]{40}",SOURCE):
 raise SystemExit("Set SOURCE to the exact committed C1 SHA before this producer or binder can run")
GENERATIONS=[
 ("incoming_main","081475dcbe8828c71240add2538fcd9c2ff91611"),
 ("incoming_main_24559","24559ffa06bcf06fa8e9f36bb7e078412bd769fe"),
 ("previous_published","92dac636b20467c7a6de1efa9a27b328da976f45"),
]
ARCHIVED_NAMES=("manifest.json","mobile-layout.json","mobile-layout-canada.json")
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"))
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()==SOURCE
execution=json.loads((C/"p0b_execution.json").read_text())
assert execution["source_commit"]==SOURCE and execution["state"]=="PASS"
for row in execution["actual_receipts"]: assert sha(R/row["path"])==row["sha256"],row
assert not (C/"p0b_rebind.json").exists(),"Preserve and reconcile the existing bind receipt"
manifests={}; preserved_generations=[]
for label,ref in GENERATIONS:
 files=[]
 for name in ARCHIVED_NAMES:
  archived=C/label/name
  committed=subprocess.check_output(["git","show",ref+":mockups/evidence/prophet-p0b-zero-fouc/"+name],cwd=R)
  assert archived.read_bytes()==committed,(label,name,"archive differs from pinned Git object")
  files.append({"name":name,"sha256":sha(archived)})
 manifests[label]=json.loads((C/label/"manifest.json").read_text())
 preserved_generations.append({"label":label,"source_commit":ref,"files":files})
assert execution["preserved_generations"]==preserved_generations,"Archived custody changed after capture"
incoming=manifests["incoming_main_24559"]
local=manifests["previous_published"]
current=json.loads((P/"manifest.json").read_text())
assert (P/"manifest.json").read_bytes()==(C/"incoming_main_24559/manifest.json").read_bytes(),"Inspect unexpected manifest changes rather than replacing them"
history=[]; seen=set(); history_preservation=[]
for label,ref in GENERATIONS:
 manifest=manifests[label]; before=len(history)
 extensions=manifest.get("repair_extension_history",[])+[manifest["repair_extension"]]
 for extension in extensions:
  key=canon(extension)
  if key not in seen: seen.add(key);history.append(extension)
 history_preservation.append({"label":label,"source_commit":ref,
  "historical_extensions":len(manifest.get("repair_extension_history",[])),
  "current_extensions":1,"unique_extensions":len({canon(x) for x in extensions}),
  "added_unique_extensions":len(history)-before,"archived_manifest_sha256":sha(C/label/"manifest.json")})
expected_union={canon(x) for manifest in manifests.values() for x in manifest.get("repair_extension_history",[])+[manifest["repair_extension"]]}
assert seen==expected_union and len(history)==len(expected_union)==29,"The exact three-generation historical union changed"
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
assert canon(extension) not in seen,"The proposed current extension is already historical; inspect capture custody"
current["repair_extension_history"]=history;current["repair_extension"]=extension
assert {k:v for k,v in current.items() if k not in {"repair_extension","repair_extension_history"}}=={k:v for k,v in incoming.items() if k not in {"repair_extension","repair_extension_history"}}
assert {canon(x) for x in current["repair_extension_history"]}==expected_union
(P/"manifest.json").write_text(json.dumps(current,indent=2)+"\n")
report={"schema":"intl.p0b_composition_rebind.v1","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source_commit":SOURCE,"execution_receipt":str((C/"p0b_execution.json").relative_to(R)),"execution_receipt_sha256":sha(C/"p0b_execution.json"),"manifest_sha256":sha(P/"manifest.json"),"preserved_incoming_history":len(incoming.get("repair_extension_history",[])),"preserved_local_history":len(local.get("repair_extension_history",[])),"preserved_generations":preserved_generations,"history_preservation":history_preservation,"composed_history":len(history),"both_parent_current_extensions_preserved":all(canon(m["repair_extension"]) in seen for m in [incoming,local]),"full_historical_union_preserved":{canon(x) for x in history}==expected_union,"all_generation_current_extensions_preserved":all(canon(m["repair_extension"]) in seen for m in manifests.values()),"newest_incoming_wrapper_preserved":True,"actual_browser_cases":128,"actual_screenshots":16,"claims":claims,"pass":True}
(C/"p0b_rebind.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2),flush=True)
