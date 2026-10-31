import collections, datetime, hashlib, json, pathlib, re, subprocess
ROOT=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
E=ROOT/"research/reference_integrity/intl-country-intelligence-20261020"
C=E/"main_composition_20261021"
LOCAL="3a329e6837915d4833a89952245f6509c0bec3f0"
MAIN="2fed30a5a14f6bdd5e69d42c5bfcbac5814b3915"
def git(*args,check=True):
    p=subprocess.run(["git",*args],cwd=ROOT,capture_output=True)
    if check and p.returncode: raise RuntimeError((args,p.returncode,p.stderr.decode()[:2000]))
    return p
assert git("rev-parse","HEAD").stdout.decode().strip()==LOCAL
assert git("rev-parse","MERGE_HEAD").stdout.decode().strip()==MAIN
assert not git("diff","--name-only","--diff-filter=U").stdout
def tree(ref):
    rows={}
    for row in git("ls-tree","-rz",ref).stdout.split(b"\0"):
        if not row: continue
        meta,name=row.split(b"\t",1)
        mode,typ,oid=meta.decode().split()
        rows[name.decode()]=oid
    return rows
parents={LOCAL:tree(LOCAL),MAIN:tree(MAIN)}
index={}
for row in git("ls-files","--stage","-z").stdout.split(b"\0"):
    if not row: continue
    meta,name=row.split(b"\t",1); mode,oid,stage=meta.decode().split()
    assert stage=="0",name
    index[name.decode()]=oid
checks=[]
for label,ref in [("from_accepted_local",LOCAL),("from_incoming_main",MAIN)]:
    result=git("diff","--cached","--check",ref,check=False)
    logfile=C/(label+"_whitespace.log")
    logfile.write_bytes(result.stdout+result.stderr)
    warnings=collections.Counter()
    for line in result.stdout.decode().splitlines():
        m=re.match(r"^(.+):([0-9]+): (trailing whitespace|new blank line at EOF|space before tab in indent)\.",line)
        if m: warnings[m.group(1)]+=1
    rows=[]
    for path,count in sorted(warnings.items()):
        bindings=[sha for sha,files in parents.items() if files.get(path)==index.get(path)]
        rows.append({"path":path,"warnings":count,"index_blob":index.get(path),"byte_identical_parents":bindings})
    assert result.returncode in (0,2),(label,result.returncode)
    assert result.returncode==0 or rows,(label,"unclassified output")
    assert all(row["byte_identical_parents"] for row in rows),(label,[r for r in rows if not r["byte_identical_parents"]])
    checks.append({"relative_to":ref,"exit_code":result.returncode,"log":str(logfile.relative_to(ROOT)),"log_sha256":hashlib.sha256(logfile.read_bytes()).hexdigest(),"paths":rows,"warning_count":sum(warnings.values())})
new_composed=[p for p,oid in index.items() if not p.startswith("research/") and not any(files.get(p)==oid for files in parents.values())]
source_check=git("diff","--cached","--check",MAIN,"--",*new_composed,check=False)
(C/"resolved_source_whitespace.log").write_bytes(source_check.stdout+source_check.stderr)
assert source_check.returncode==0,source_check.stdout.decode()[:6000]
payload={"schema":"intl.main_composition_whitespace_classification.v1","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":LOCAL,"merge_head":MAIN,"broad_checks":checks,"newly_composed_source_paths":new_composed,"newly_composed_source_check_exit":source_check.returncode,"classification":"Every broad whitespace warning is in a staged blob byte-identical to an immutable parent. Historical screenshots, HTML, reviews, and raw diagnostic logs remain unmodified. The newly composed source delta passes the whitespace check.","pass":True}
(C/"whitespace_classification.json").write_text(json.dumps(payload,indent=2)+"\n")
fabric={"schema":"intl.fabric_interrupted_request_reconciliation.v1","recorded_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"One interrupted request only; not a general provider-availability conclusion","root_id":"01a1101f-2a37-7320-9a9b-5df3ce1b890d","parent_id_submitted":"/root","run_id":"intl-20261021-shell-country-repair-r1","task_class":"fix_build","task_complexity":"C1_ROUTINE_BOUNDED","intended_effect":"Scratch-only patch return for International country adapter shared-shell location event and its real-bridge harness tests; original workspace writes, Git publication, deployment, and messaging prohibited.","original_observation":"Tool exchange aborted after 277.2 seconds without a canonical response, action ref, or controller PID.","status_observations":{"observations":2,"state":"NOT_FOUND","root_verified":False,"execution_absence_proven":False,"retry_allowed":False,"result_available":False,"controller_return":"NOT_APPLICABLE","prior_attempts":[]},"principal_diagnosis":{"protected_pin":"c9cbee5569ba50e30e28715d930809061a169517","source_path":"integrations/studio_direct_mcp/fabric-backend.mjs","parent_id_pattern":"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$","submitted_parent_id_valid":False,"validation_precedes_dispatch":True,"known_installed_backend_release":"386ab9336b50600f81d767474bf6b26479a5cb55","known_installed_backend_sha256":"918dd56f60639c0b9720af0fbbff9dc335b4ca918fb474850e65faf319035d09","limitation":"The inspected installation cannot be bound to the original interrupted exchange. This is a diagnosis, not a canonical original no-effect receipt."},"effect_state":"EFFECT_UNKNOWN","retry_authority":False,"resolution_needed":"Original tool/transport response proving INVALID_ARGUMENT for this exact request, or original gateway correlation/controller PID plus generation.","no_retry_or_alternate_dispatch":True,"patch_work_fenced":True,"independent_work_continues":["normal main integration","P0B browser remint","International runtime proof","original PR publication when otherwise ready"],"production_claim":False}
(C/"fabric_request_reconciliation.json").write_text(json.dumps(fabric,indent=2)+"\n")
print(json.dumps({"pass":True,"whitespace_checks":[{"relative_to":x["relative_to"],"exit_code":x["exit_code"],"paths":len(x["paths"]),"warnings":x["warning_count"]} for x in checks],"newly_composed_source_paths":new_composed,"fabric_effect_state":"EFFECT_UNKNOWN"},indent=2),flush=True)
