import datetime,hashlib,json,pathlib,subprocess,sys,time
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27');E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
R=json.loads((E/'macro-0f05-budget-repair.json').read_text())
def g(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
assert g('rev-parse','HEAD')==R['head'] and g('rev-parse','MERGE_HEAD')==R['incoming'] and g('write-tree')==R['after_index']
assert not g('diff','--name-only') and not g('ls-files','-u')
paths=['.github/ci/legacy-jobs.yml','tests/test_ci_pack.py','app/deploy/Caddyfile','config/site_access.yml']
hashes={p:hashlib.sha256((W/p).read_bytes()).hexdigest() for p in paths}
temp=E/'macro-0f05-packing-after-tmp';assert not temp.exists()
a=['/opt/homebrew/bin/python3.12','-m','pytest','-q','--tb=short','--basetemp',str(temp),'tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs']
start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
inv={'started_at':start,'head':R['head'],'incoming':R['incoming'],'index':R['after_index'],'command':a,'source_sha256':hashes,'scope':'packing node after minimal measured literal/history change; prior three scope passes remain bound to unchanged manifest'}
(E/'macro-0f05-packing-after-invocation.json').write_text(json.dumps(inv,indent=2)+'\n')
p=subprocess.run(a,cwd=W,capture_output=True,timeout=900);raw=p.stdout+p.stderr;(E/'macro-0f05-packing-after.log').write_bytes(raw)
assert g('write-tree')==R['after_index'] and not g('diff','--name-only')
assert hashes=={p:hashlib.sha256((W/p).read_bytes()).hexdigest() for p in paths}
receipt={**inv,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-tick,3),'exit':p.returncode,'log_sha256':hashlib.sha256(raw).hexdigest(),'source_and_index_unchanged':True}
(E/'macro-0f05-packing-after.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(raw.decode());print(json.dumps(receipt,indent=2));raise SystemExit(p.returncode)
