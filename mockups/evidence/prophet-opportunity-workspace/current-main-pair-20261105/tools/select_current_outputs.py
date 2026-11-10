import pathlib,subprocess,json,hashlib,time,urllib.parse
from bs4 import BeautifulSoup
w=pathlib.Path("/home/ubuntu0/lanes/wt/d03-9495-ci-registration-c2-20261105")
head="9a8a28c557717441d2c5ef5529dad9fc7445e7b4"
prefix=pathlib.Path("/tmp/prophet-latest-main-frozen-9a8a28")
out=pathlib.Path(str(prefix)+".output-selection.json")
assert not out.exists(),"existing selection must be reconciled"
def git(*a):return subprocess.check_output(["git",*a],cwd=w)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert git("rev-parse","HEAD").decode().strip()==head
receipt=json.loads(pathlib.Path(str(prefix)+".receipt.json").read_text())
assert receipt["head"]==head and receipt.get("completed_at") and len(receipt["modules"])==4
assert all(m["exit"]==0 for m in receipt["modules"])
assert receipt["frozen_inputs_unchanged"] and not receipt["frozen_changed_paths"]
keep={"site/us_stocks.html","site/premiumdata/us_stocks.json"}
for p in keep:assert digest(w/p)==receipt["artifacts"][p]["sha256"],p
tracked=[p.decode() for p in git("diff","--name-only","-z").split(b"\0") if p]
untracked=[p.decode() for p in git("ls-files","--others","--exclude-standard","-z").split(b"\0") if p]
assert not untracked,{"unexpected_untracked":untracked[:50]}
restore=sorted(set(tracked)-keep)
record={"head":head,"started_at":time.time(),"adopted_paths":sorted(keep),"restored_incidental_count":len(restore),"restored_incidental_paths_sha256":hashlib.sha256(("\n".join(restore)+"\n").encode()).hexdigest(),"reason":"Retain native Prophet output pair only; restore build-owned incidental files to current merged source9a8a28."}
for start in range(0,len(restore),300):
 git("restore","--source="+head,"--worktree","--",*restore[start:start+300])
remaining=[p.decode() for p in git("diff","--name-only","-z").split(b"\0") if p]
assert set(remaining)==keep,remaining
source_inventory=json.loads(pathlib.Path(str(prefix)+".render-inputs.json").read_text())
for p,v in source_inventory.items():
 assert (w/p).stat().st_size==v["bytes"] and digest(w/p)==v["sha256"],p
frozen=json.loads(pathlib.Path(str(prefix)+".frozen-inputs.json").read_text())
current=set()
for rel in ("data/prophet","data/prophet_arena","site/prophet"):
 current.update(str(p.relative_to(w)) for p in (w/rel).rglob("*") if p.is_file())
current.update(("site/factordata/us_standouts.json","site/factordata/signal_gate.json"))
assert current==set(frozen)
for p,v in frozen.items():assert (w/p).stat().st_size==v["bytes"] and digest(w/p)==v["sha256"],p
for p in keep:assert digest(w/p)==receipt["artifacts"][p]["sha256"],p
doc=BeautifulSoup((w/"site/us_stocks.html").read_bytes(),"html.parser")
assets={}
for node,attr in [(n,"href") for n in doc.select('link[href]')]+[(n,"src") for n in doc.select('script[src]')]:
 url=urllib.parse.urlsplit(node.get(attr) or "")
 if url.scheme or url.netloc or not url.path:continue
 suffix=pathlib.PurePosixPath(url.path).suffix
 if suffix not in (".css",".js"):continue
 p=(w/"site"/url.path.lstrip("/")).resolve()
 assert p.is_relative_to((w/"site").resolve()) and p.is_file(),str(p)
 rel=str(p.relative_to(w))
 baseline=git("show",head+":"+rel)
 assert hashlib.sha256(baseline).hexdigest()==digest(p),rel
 assets[rel]=digest(p)
assert assets.get("site/prophet_save.js")=="63364e5bf444b4ebcd3ca7689362b7f393a64ea0b5d9539445c14ba4631fa193"
record.update({"completed_at":time.time(),"remaining_diff":sorted(remaining),"referenced_assets":assets,"referenced_asset_count":len(assets),"paired_artifacts_unchanged":True,"all_render_inputs_restored_to_clean_source":True,"all_referenced_assets_unchanged":True,"all_frozen_inputs_unchanged":True,"frozen_input_count":len(frozen),"render_input_count":len(source_inventory)})
out.write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps({k:v for k,v in record.items() if k!="referenced_assets"},indent=2))
