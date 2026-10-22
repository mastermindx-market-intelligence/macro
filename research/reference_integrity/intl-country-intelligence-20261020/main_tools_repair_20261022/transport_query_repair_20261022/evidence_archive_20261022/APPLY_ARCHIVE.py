import pathlib,subprocess,json,hashlib,tarfile,shutil,datetime,time,os
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
staging=pathlib.Path("/tmp/intl-resume-main-20261022T1252/evidence_archive_candidate")
dest=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/evidence_archive_20261022")
head="ba4466fc170f2f4f3cdfdb131ca6b51508703934"
base="2d33475adef502ab6b00b8003356c1b0ad1673c0"
def git(*args):return subprocess.check_output(["git","-C",str(R),*args])
def sha(b):return hashlib.sha256(b).hexdigest()
assert git("rev-parse","HEAD").decode().strip()==head
assert not git("status","--porcelain","--untracked-files=normal").strip()
assert not dest.exists()
manifest=json.loads((staging/"ARCHIVE_MANIFEST.json").read_text())
assert manifest["original_head"]==head and len(manifest["records"])==259
archive=staging/manifest["archive"]["file"]
assert sha(archive.read_bytes())==manifest["archive"]["sha256"]
# Complete verification precedes any original-path removal.
with tarfile.open(archive,"r:gz") as tf:
 members=tf.getmembers()
 assert len(members)==259
 for member,row in zip(members,manifest["records"]):
  f=R/row["path"]
  assert member.isfile() and member.name==row["path"] and not f.is_symlink()
  b=f.read_bytes()
  assert sha(b)==row["sha256"] and tf.extractfile(member).read()==b
  assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==row["git_blob"]
dest.mkdir()
for name in ("superseded_build_copies.tar.gz","ARCHIVE_MANIFEST.json","ROUNDTRIP_RECEIPT.json","README.md","OWNER_CAPTURED_INDEPENDENT_ARCHIVE_REVIEW.md","AUTHORITY_REJECTION.json"):
 shutil.copyfile(staging/name,dest/name)
 assert (dest/name).read_bytes()==(staging/name).read_bytes()
shutil.copyfile(pathlib.Path("/tmp/intl-resume-main-20261022T1252/prepare_evidence_archive.py"),dest/"PREPARE_ARCHIVE.py")
for row in manifest["records"]:
 f=R/row["path"]
 assert sha(f.read_bytes())==row["sha256"]
 f.unlink()
changed=git("diff","--name-status",head).decode().splitlines()
assert len(changed)==259 and all(line.startswith("D\t") for line in changed)
assert {line.split("\t",1)[1] for line in changed}=={r["path"] for r in manifest["records"]}
protected=[
"research/reference_integrity/intl-country-intelligence-20261020/proposed_dock4_repair",
"research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/proposed_scenariopop20261022_repair",
"research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/candidate_parent_scenario_v13",
"templates/intl_workspace.js","site/intl_workspace.js","templates/shared_shell_bridge.js","site/shared_shell_bridge.js",
"tests/intl_workspace_controller.test.cjs","tests/intl_workspace_history_independent.test.cjs"]
bound=[]
for entry in git("ls-tree","-r","-z",head,"--",*protected).split(b"\0"):
 if not entry:continue
 m,name=entry.split(b"\t",1);mode,kind,blob=m.decode().split();name=name.decode()
 assert kind=="blob"
 b=(R/name).read_bytes()
 assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==blob
 bound.append({"path":name,"git_blob":blob,"sha256":sha(b)})
checks=[]
for label,args in [
 ("frozen_reference",["scripts/check_reference_integrity.py","--evaluate","intl-country-intelligence-20261020"]),
 ("reference_registry",["scripts/check_reference_integrity.py"])]:
 log=dest/(label+".log")
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
 with log.open("wb") as stream:
  p=subprocess.run(["/tmp/intl-country-cockpit-ci-20261021/bin/python",*args],cwd=R,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"},stdout=stream,stderr=subprocess.STDOUT,timeout=120)
 checks.append({"name":label,"command":args,"started_at":start,"duration_seconds":round(time.monotonic()-tick,2),"exit_code":p.returncode,"log":str(log.relative_to(R)),"sha256":sha(log.read_bytes())})
receipt={"schema":"intl.archive_application.v1","original_head":head,"archive_sha256":manifest["archive"]["sha256"],"manifest_sha256":sha((dest/"ARCHIVE_MANIFEST.json").read_bytes()),"removed_exact_reviewed_paths":259,"other_tracked_changes":[],"protected_bindings":bound,"checks":checks,"completed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"pass":all(x["exit_code"]==0 for x in checks)}
(dest/"ARCHIVE_APPLICATION_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
tracked=set(git("diff","--name-only",base).decode().splitlines())
untracked=set(git("ls-files","--others","--exclude-standard").decode().splitlines())
receipt["projected_full_pr_changed_files"]=len(tracked|untracked)
receipt["new_evidence_paths"]=sorted(untracked)
(dest/"ARCHIVE_APPLICATION_RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({k:v for k,v in receipt.items() if k not in ("protected_bindings","new_evidence_paths")},indent=2))
print(json.dumps({"protected_binding_count":len(bound),"new_evidence_paths":sorted(untracked)},indent=2))
assert receipt["pass"] and receipt["projected_full_pr_changed_files"]<3000
