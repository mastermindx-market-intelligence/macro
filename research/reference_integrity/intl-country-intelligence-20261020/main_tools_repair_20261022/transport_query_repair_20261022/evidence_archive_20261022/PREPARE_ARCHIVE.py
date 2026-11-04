import pathlib,subprocess,json,hashlib,tarfile,gzip,io,datetime,os
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
out=pathlib.Path("/tmp/intl-resume-main-20261022T1252/evidence_archive_candidate")
out.mkdir(exist_ok=True)
head="ba4466fc170f2f4f3cdfdb131ca6b51508703934"
base="2d33475adef502ab6b00b8003356c1b0ad1673c0"
dirs=["research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/proposed_shelltools20261022_repair","research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_6a4_20261022/proposed_main6a420261022_repair","research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_90df_20261022/proposed_main90df20261022_repair","research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/proposed_shellquery20261022_repair","research/reference_integrity/intl-country-intelligence-20261020/proposed_composition20261022_repair","research/reference_integrity/intl-country-intelligence-20261020/proposed_main25020261022_repair"]
def git(*args):return subprocess.check_output(["git","-C",str(R),*args])
assert git("rev-parse","HEAD").decode().strip()==head
assert not git("status","--porcelain","--untracked-files=normal").strip()
inventory=json.loads(pathlib.Path("/tmp/intl-resume-main-20261022T1252/authority_full_path_inventory.json").read_text())
added={p for s,p in inventory["paths"] if s=="A"}
records=[]
for directory in dirs:
 tree=git("ls-tree","-r","-z",head,"--",directory)
 for entry in tree.split(b"\0"):
  if not entry:continue
  metadata,name=entry.split(b"\t",1)
  mode,kind,blob=metadata.decode().split()
  name=name.decode()
  assert kind=="blob" and mode in ("100644","100755") and name in added
  f=R/name
  assert f.is_file() and not f.is_symlink()
  data=f.read_bytes()
  assert hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()==blob
  records.append({"path":name,"git_mode":mode,"git_blob":blob,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()})
records.sort(key=lambda x:x["path"])
assert len(records)==259 and len({r["path"] for r in records})==259
archive=out/"superseded_build_copies.tar.gz"
assert not archive.exists()
with archive.open("wb") as raw:
 with gzip.GzipFile(filename="",mode="wb",fileobj=raw,mtime=0,compresslevel=9) as gz:
  with tarfile.open(fileobj=gz,mode="w",format=tarfile.PAX_FORMAT) as tf:
   for row in records:
    data=(R/row["path"]).read_bytes()
    assert hashlib.sha256(data).hexdigest()==row["sha256"]
    info=tarfile.TarInfo(row["path"]);info.size=len(data);info.mode=int(row["git_mode"][-3:],8);info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=""
    tf.addfile(info,io.BytesIO(data))
roundtrip=[]
with tarfile.open(archive,"r:gz") as tf:
 members=tf.getmembers()
 assert len(members)==len(records)
 for member,row in zip(members,records):
  assert member.isfile() and member.name==row["path"] and member.mode==int(row["git_mode"][-3:],8)
  assert not member.name.startswith("/") and ".." not in pathlib.PurePosixPath(member.name).parts
  data=tf.extractfile(member).read()
  assert len(data)==row["bytes"] and hashlib.sha256(data).hexdigest()==row["sha256"]
  assert data==(R/row["path"]).read_bytes()
  roundtrip.append({"path":member.name,"byte_equal":True,"mode_equal":True})
record={"schema":"intl.superseded_build_archive.v1","created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"original_head":head,"comparison_base":base,"reason":"Consolidate superseded generated build copies while keeping complete PR inventory within trusted ci-authority MAX_CHANGED_FILES=3000. No authority gate or product source is modified.","original_changed_paths":3080,"archived_files":len(records),"uncompressed_bytes":sum(x["bytes"] for x in records),"archive":{"file":archive.name,"bytes":archive.stat().st_size,"sha256":hashlib.sha256(archive.read_bytes()).hexdigest(),"format":"gzip mtime=0 containing POSIX pax tar; regular files only; repository-relative names; recorded git modes"},"directories":dirs,"all_members_roundtrip_verified":True,"all_members_equal_original_git_blobs":True,"all_members_added_relative_to_base":True,"records":records,"unchanged_obligations":["frozen proposed_dock4_repair artifact and source-trace bindings","all baseline and later screenshots","all raw runtime observations, logs, failure receipts and review reports","original input snapshot/archive","fresh proposed_scenariopop20261022_repair artifact","all product, test, configuration, workflow and authority-controller source"]}
(out/"ARCHIVE_MANIFEST.json").write_text(json.dumps(record,indent=2)+"\n")
(out/"ROUNDTRIP_RECEIPT.json").write_text(json.dumps({"schema":"intl.archive_roundtrip.v1","archive_sha256":record["archive"]["sha256"],"source_head":head,"members":len(records),"all_byte_equal":True,"all_mode_equal":True,"result":"PASS"},indent=2)+"\n")
print(json.dumps({k:v for k,v in record.items() if k!="records"},indent=2))
