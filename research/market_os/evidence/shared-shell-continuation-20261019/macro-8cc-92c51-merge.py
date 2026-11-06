import datetime,hashlib,json,pathlib,subprocess
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27');E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
RP=E/'macro-8cc-92c51-candidates.json';R=json.loads(RP.read_text());H=R['head'];M=R['incoming'];T=R['preview_tree']
def g(*a,check=True):
 p=subprocess.run(['git','-C',str(W),*a],capture_output=True,text=True,timeout=90)
 if check and p.returncode:raise RuntimeError((a,p.returncode,p.stderr))
 return p
assert g('rev-parse','HEAD').stdout.strip()==H
assert g('symbolic-ref','--short','HEAD').stdout.strip()=='sol/market-os-shared-shell-design-20260924'
assert g('write-tree').stdout.strip()==R['prior_index']
assert not g('status','--porcelain=v1').stdout
assert g('rev-parse','-q','--verify','MERGE_HEAD',check=False).returncode!=0
assert g('ls-remote','origin','refs/heads/sol/market-os-shared-shell-design-20260924').stdout.split()[0]==H
for f in R['files']:
 raw=pathlib.Path(f['candidate']).read_bytes();assert len(raw)==f['bytes'] and hashlib.sha256(raw).hexdigest()==f['sha256']
inv={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'incoming':M,'base':R['base'],'command':['git','merge','--no-ff','--no-commit',M],'source':'original shared-shell-r27','candidate_receipt_sha256':hashlib.sha256(RP.read_bytes()).hexdigest()}
ip=E/'macro-8cc-92c51-merge-invocation.json';assert not ip.exists();ip.write_text(json.dumps(inv,indent=2)+'\n')
p=g('merge','--no-ff','--no-commit',M,check=False);lp=E/'macro-8cc-92c51-merge.log';lp.write_text(p.stdout+p.stderr)
assert p.returncode==1,(p.returncode,p.stdout,p.stderr)
assert g('rev-parse','HEAD').stdout.strip()==H and g('rev-parse','MERGE_HEAD').stdout.strip()==M
unmerged={}
for line in g('ls-files','-u').stdout.splitlines():
 lead,path=line.split('\t');mode,blob,stage=lead.split();unmerged.setdefault(path,{})[stage]=blob
assert set(unmerged)=={x['path'] for x in R['files']},unmerged
for f in R['files']:
 assert unmerged[f['path']]=={'1':f['base_blob'],'2':f['ours_blob'],'3':f['incoming_blob']},f['path']
for f in R['files']:(W/f['path']).write_bytes(pathlib.Path(f['candidate']).read_bytes())
g('add','--',*[f['path'] for f in R['files']])
assert not g('ls-files','-u').stdout and not g('diff','--name-only').stdout
tree=g('write-tree').stdout.strip()
changed=g('diff','--name-only',T,tree).stdout.splitlines();assert set(changed)=={f['path'] for f in R['files']},changed
for f in R['files']:
 raw=subprocess.check_output(['git','-C',str(W),'show',':'+f['path']]);assert hashlib.sha256(raw).hexdigest()==f['sha256']
whitespace=g('diff','--cached','--check',M,check=False)
receipt={**inv,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'merge_exit':p.returncode,'merge_log_sha256':hashlib.sha256(lp.read_bytes()).hexdigest(),'unmerged_before_resolution':unmerged,'unmerged_after_resolution':[],'index':tree,'only_two_conflicts_differ_from_preview':True,'candidate_hashes_match':True,'complete_owned_whitespace':{'argv':whitespace.args,'exit':whitespace.returncode,'stdout':whitespace.stdout,'stderr':whitespace.stderr},'commit_created':False,'push_started':False}
raw=(json.dumps(receipt,indent=2)+'\n').encode();(E/'macro-8cc-92c51-actual-merge.json').write_bytes(raw);print(raw.decode());print(json.dumps({'receipt_sha256':hashlib.sha256(raw).hexdigest()}))
assert whitespace.returncode==0
