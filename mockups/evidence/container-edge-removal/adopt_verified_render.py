"""Adopt an accepted CI update and subsequent data-only main commits.

Retain the exact verified presentation tree. This one-use recipe is fenced to the
owned native HEAD and pending merge; it does not publish or modify shared config.
"""
from pathlib import Path
import subprocess, json, os, time
H="bac05c4c15f648acb845a67caa54a7103b28fa6b"
B="43b5acdb0d0f264091f5aa33c129625fd0b28b8c"
C="82930233f83a2e62734e605becb1076508eefc31"
ENV=os.environ.copy();ENV["GIT_NO_LAZY_FETCH"]="1"
def git(*a):return subprocess.check_output(["git",*a],env=ENV)
assert git("rev-parse","HEAD").decode().strip()==H
assert git("rev-parse","MERGE_HEAD").decode().strip()==B
M=git("rev-parse","refs/remotes/origin/main").decode().strip()
assert subprocess.run(["git","merge-base","--is-ancestor",C,M],env=ENV).returncode==0
control=[".github/ci/legacy-jobs.yml","tests/test_ci_pack.py","tests/test_ticker_news_snapshot_cursor_reconnect.py"]
assert git("diff","--name-only",B,C).decode().splitlines()==control
extras=git("diff","--name-only",C,M).decode().splitlines()
data_suffixes=(".json",".jsonl",".parquet",".csv",".tsv")
assert all(p.startswith(("data/","site/")) and Path(p).suffix in data_suffixes for p in extras),extras
objects={}
for row in git("ls-tree","-r","-z",M,"--",*(control+extras)).split(b"\0"):
    if row:
        meta,path=row.split(b"\t",1);objects[meta.decode().split()[2]]=path.decode()
p=subprocess.run(["git","cat-file","--batch-check=%(objectname) %(objecttype)"],input="\n".join(objects)+"\n",env=ENV,capture_output=True,text=True)
assert p.returncode==0
missing=[{"sha":r.split()[0],"path":objects[r.split()[0]]} for r in p.stdout.splitlines() if r.endswith(" missing")]
print(json.dumps({"protected_base":M,"extra_data_paths":len(extras),"missing":missing}),flush=True)
assert not missing,"Hydrate exact missing objects before applying merge"
E=Path("mockups/evidence/container-edge-removal");D=E/"integration-render-refresh"
v=json.loads((D/"validation-receipt.json").read_text());assert v["overall"]=="passed"
subprocess.run(["git","add","--","site",str(E)],env=ENV,check=True)
assert not git("diff","--name-only").strip()
tree=git("write-tree").decode().strip();site_tree=git("rev-parse",tree+":site").decode().strip()
Path(".cache/glossary-output-repair/verified-tree-before-ci-adoption.json").write_text(json.dumps({
    "tree":tree,"site_tree":site_tree,"source_head":H,"verified_base":B,"adopted_base":M,"control_base":C
},indent=2)+"\n")
subprocess.run(["git","merge","--abort"],env=ENV,check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
started=time.monotonic()
p=subprocess.run(["git","merge","--no-commit","--no-ff",M],env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
assert p.returncode in (0,1),p.stdout[-2000:]
subprocess.run(["git","restore","--source="+tree,"--staged","--worktree","--","site",str(E)],env=ENV,check=True)
site_data=[p for p in extras if p.startswith("site/")]
if site_data:
    subprocess.run(["git","restore","--source="+M,"--staged","--worktree","--",*site_data],env=ENV,check=True)
unresolved=git("diff","--name-only","--diff-filter=U").decode().splitlines()
assert set(unresolved)<=set(control),unresolved
site_delta=git("diff","--cached","--name-only",tree,"--","site").decode().splitlines()
assert set(site_delta)==set(site_data),(site_delta,site_data)
assert not git("diff","--cached","--name-only",M,"--","data").strip()
data_delta=[p for p in git("diff","--cached","--name-only",M,"--","site").decode().splitlines() if Path(p).suffix in data_suffixes]
assert not data_delta,data_delta
record={
    "schema":"mastermind.container_edge_verified_tree_adoption.v1",
    "source_head":H,"verified_main":B,"control_main":C,"adopted_main":M,
    "verified_tree":tree,"verified_site_tree":site_tree,"control_paths":control,
    "fresh_data_paths":extras,"merge_exit_code":p.returncode,
    "merge_seconds":round(time.monotonic()-started,2),"remaining_conflicts":unresolved,
    "site_differences_from_qualified_tree":site_delta,
    "all_presentation_bytes_identical_to_qualified_tree":True,
    "all_published_data_files_exact_current_main":True,
    "proof_reuse":"Only exact upstream data bytes differ from the fully qualified site tree; CI registration and its tests merge normally."
}
(D/"post-validation-ci-adoption.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps(record,indent=2),flush=True)
