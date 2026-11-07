import pathlib,subprocess,json,hashlib,os,datetime,stat
ROOT=pathlib.Path('/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-observations-20261009-pro-003')
CACHE=pathlib.Path('/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009')
S=CACHE/'pro003-ci-main-refresh-preparation-012'
CP=ROOT/'research/theme_graph/economic_network_execution_20261009/continuation_pro_003'
PREFIX=CP.relative_to(ROOT).as_posix()+'/'
HEAD='4caf1e2b1e58e3199ba5d63ebfa6563ef098eeff'
REMOTE='cbcc5ee143400af162a252e4faac0f06c7157e37'
BRANCH='sol/web-gmi-economic-observations-20261009-pro-003'
PROTECTED='326c8469a21d7f50fc9ecb1848196bf1c6e66685'
SCRIPT=CACHE/'pro003-checkpoint-apply-runner-018.py'
OUT=CACHE/'pro003-checkpoint-apply-result-018.json'
env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def get(*a):
 p=subprocess.run(['git','--no-lazy-fetch','--no-optional-locks','-C',str(ROOT),*a],capture_output=True,env=env);assert p.returncode==0,(a,p.returncode,p.stderr.decode(errors='replace')[:300]);return p.stdout
def checked(path,size,digest):
 assert path.is_file() and not path.is_symlink(),str(path)
 b=path.read_bytes();assert len(b)==size and sha(b)==digest,str(path);return b
def cpwrite(name,b,replace=False):
 rel=pathlib.PurePosixPath(name);assert not rel.is_absolute() and '..' not in rel.parts
 p=CP/name;p.parent.mkdir(parents=True,exist_ok=True);assert p.parent.resolve().is_relative_to(CP)
 if replace:
  assert name=='README.md' and p.read_bytes()==old_readme
  temp=p.with_name('README_PUBLICATION_018.tmp');assert not temp.exists()
 else:
  assert not p.exists() and not p.is_symlink();temp=p
 fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o644)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 if replace:os.replace(temp,p)
 assert p.read_bytes()==b
 return {'path':PREFIX+name,'byte_length':len(b),'sha256':sha(b)}
def verify_pins():
 for key,count in [('source_pins',53),('owner_pins',71)]:
  assert len(pre[key])==count
  for x in pre[key]:
   p=ROOT/x['path'];b=p.read_bytes();assert not p.is_symlink() and sha(b)==x['sha256'] and get('show',HEAD+':'+x['path'])==b,x['path']
 assert len(pre['controls'])==9
 for x in pre['controls']:
  b=(ROOT/x['path']).read_bytes();expected_sha='5cc24c46e7c4ed8b0b9525366a7069e86f546b32849c72cb8518320842d860cd' if x['path']=='.github/ci/legacy-jobs.yml' else x['new_sha256'];assert get('show',HEAD+':'+x['path'])==b and get('show',REMOTE+':'+x['path'])==b and sha(b)==expected_sha,x['path']
assert not OUT.exists() and not (CP/'CI_REFRESH_PUBLICATION_MANIFEST_018.json').exists()
started=now()
assert get('rev-parse','HEAD').decode().strip()==HEAD and get('branch','--show-current').decode().strip()==BRANCH
assert not get('status','--porcelain=v1','--untracked-files=all').strip() and not get('ls-files','--others','--ignored','--exclude-standard').strip()
assert get('ls-remote','--exit-code','origin','refs/heads/'+BRANCH).decode().split()[0]==REMOTE
r=subprocess.run(['gh','api','repos/mastermindx-market-intelligence/Mastermind/branches/master'],cwd=ROOT,capture_output=True,env=env);assert r.returncode==0
protected=json.loads(r.stdout);assert protected['protected'] is True and protected['commit']['sha']==PROTECTED
pre=json.loads(checked(CACHE/'pro003-main-refresh-preflight-006.json',916286,'e3e8aa9112ccd1fd7c3ce107f83c7b2834afb6c0f5afaf8c69057de78457c6b8'))
verify_pins()
receipts=[
 ('PREPARATION_RECEIPT_012.json',4189,'5e5c461a48e3b903a658a7d5d2532c9f3e22ffc6be14b11245af78d13721bb6b'),
 ('PROCEDURE_ADDITION_RECEIPT_014.json',1258,'5db89e9b7117b225bbf219ce8cd0e2833acccaf4125d7b7a4dd3cc111084b4e8'),
 ('REVIEW_ADDITION_RECEIPT_015.json',1075,'8d5b021f16491eacfa8178b20d9fc33d9e944cf2acceb8994e2da9ee497b509a')]
payload={};receipt_bytes={}
for name,size,digest in receipts:
 b=checked(S/name,size,digest);receipt_bytes[name]=b
 for x in json.loads(b)['direct_files']:
  name2=x['path'];assert name2 not in payload
  payload[name2]=checked(S/name2,x['byte_length'],x['sha256'])
assert len(payload)==23 and 'README.md' in payload
recon_bytes=checked(CACHE/'pro003-checkpoint-preflight-reconciliation-017.json',5803,'515ece36b9c2e8167422e1c256ae8d630df8aa6d9ac479c0b6bf29fb91defe92')
recon=json.loads(recon_bytes);assert recon['prior140_files_exact'] and recon['all9_control_bytes_match_both_own_candidate_commits']
payload['ci_main_refresh_012/FAILED_CHECKPOINT_PREFLIGHT_RUNNER_016.py.txt']=checked(CACHE/'pro003-checkpoint-apply-runner-016.py',8034,'ead8d9eda63549ffb5bdd2ea68f1842b5d9f39ce8173a8c7e0afb83cbb9de76f')
tb=(CACHE/'pro003-checkpoint-preflight-tool-completion-016.json').read_bytes();assert sha(tb)=='c419dc1ce2503f54e7bf962db04ac93f57bf3343488e00225184622b8b92712b'
payload['ci_main_refresh_012/FAILED_CHECKPOINT_PREFLIGHT_TOOL_COMPLETION_016.json']=tb
payload['ci_main_refresh_012/CHECKPOINT_PREFLIGHT_RECONCILIATION_017.json']=recon_bytes
payload['ci_main_refresh_012/PUBLICATION_PREFLIGHT_CORRECTION_018.md']=b"""# Publication preflight correction

Apply runner 016 failed at its control preflight, PID 8024, exit 1 in 14.38 seconds. It compared the branch's existing CI enrollment to the upstream-only manifest. No checkpoint file was written. Read-only reconciliation 017 subsequently verified the clean index/worktree, all 140 prior checkpoint files, 53 source pins, 71 owner pins and every control against both reviewed own candidates cbcc5ee143400af162a252e4faac0f06c7157e37 and 4caf1e2b1e58e3199ba5d63ebfa6563ef098eeff.

The accepted-upstream legacy-jobs.yml is 1,249,172 bytes, SHA-256 3aa5275a608bb9fe9b4c3b98ee42efdf2b06cfd806949752afc8f53dd5506668. The branch's already reviewed observation enrollment is 1,249,336 bytes, SHA-256 5cc24c46e7c4ed8b0b9525366a7069e86f546b32849c72cb8518320842d860cd. These are intentionally different artifacts. The other eight controls equal both upstream and the reviewed branch.

Runner 018 corrects that comparison by retaining the exact reviewed branch hash and requiring equality to both own commits for all nine controls. It changes no CI file, release policy or application source. The original failed runner and terminal tool-result value are preserved separately. The latter is an exact JSON-value serialization of the observed connector result, not a claim about wire-level response bytes. The failed attempt remains failed; the new application outcome is recorded only by its own actual receipt.

No test, provider request, authority promotion, Git reset, force operation or policy waiver accompanies this correction.
"""
assert len(payload)==27

prior=json.loads(payload['ci_main_refresh_012/PRIOR_CHECKPOINT_INVENTORY_012.json'])
assert len(prior['files'])==140
observed=[]
for p in sorted(CP.rglob('*')):
 assert not p.is_symlink()
 if p.is_file():observed.append({'path':p.relative_to(ROOT).as_posix(),'byte_length':p.stat().st_size,'sha256':sha(p.read_bytes())})
assert observed==prior['files']
old_readme=checked(CP/'README.md',3103,'04eb1bd05bd75a735aa13b003f617fa71add527deadc6856e5842f1311047732')
assert payload['ci_main_refresh_012/README_PRE_REFRESH_012.md']==old_readme
historic=json.loads((CP/'CI_REFRESH_CHECKPOINT_MANIFEST_004.json').read_bytes());assert len(historic['files'])==139
for x in historic['files']:checked(ROOT/x['path'],x['byte_length'],x['sha256'])
for name in payload:
 if name!='README.md':assert not (CP/name).exists() and not (CP/name).is_symlink(),name
script_bytes=SCRIPT.read_bytes();assert __file__==str(SCRIPT) and not SCRIPT.is_symlink()
direct=[]
for name in sorted(payload):direct.append(cpwrite(name,payload[name],replace=name=='README.md'))
for name,b in receipt_bytes.items():direct.append(cpwrite('ci_main_refresh_012/'+name,b))
direct.append(cpwrite('ci_main_refresh_012/CHECKPOINT_APPLY_RUNNER_018.py',script_bytes))
for x in prior['files']:
 path=CP/'ci_main_refresh_012/README_PRE_REFRESH_012.md' if x['path']==PREFIX+'README.md' else ROOT/x['path']
 checked(path,x['byte_length'],x['sha256'])
verify_pins()
assert get('rev-parse','HEAD').decode().strip()==HEAD and not get('diff','--cached','--name-only').strip()
assert get('diff','--name-only').decode().splitlines()==[PREFIX+'README.md']
assert not get('ls-files','--others','--ignored','--exclude-standard').strip()
untracked=get('ls-files','--others','--exclude-standard').decode().splitlines()
assert set(untracked)=={x['path'] for x in direct if x['path']!=PREFIX+'README.md'}
record={'schema':'economic_network.checkpoint_apply/v1','status':'APPLIED_AND_VERIFIED_NOT_COMMITTED','started_at':started,'finished_at':now(),'candidate_before':HEAD,'prior_remote_candidate':REMOTE,'protected_revision':PROTECTED,'all_53_source_pins_preserved':True,'all_71_owner_pins_preserved':True,'all_9_controls_preserved':True,'prior_checkpoint_files_verified':140,'historic_manifest004_entries_verified':139,'sole_replaced_path':PREFIX+'README.md','exact_original_index_alias':PREFIX+'ci_main_refresh_012/README_PRE_REFRESH_012.md','source_or_ci_or_registry_mutation':False,'native_tests_or_archived_programs_executed':False,'commit_push_or_merge_executed':False,'direct_files_before_this_receipt':direct}
rb=(json.dumps(record,indent=2,sort_keys=True)+'\n').encode();direct.append(cpwrite('ci_main_refresh_012/CHECKPOINT_APPLY_RECEIPT_018.json',rb))
files=[]
for p in sorted(CP.rglob('*')):
 assert not p.is_symlink()
 if p.is_file():
  b=p.read_bytes();files.append({'path':p.relative_to(ROOT).as_posix(),'byte_length':len(b),'sha256':sha(b)})
manifest={'schema':'economic_network.checkpoint_publication_inventory/v1','candidate_before':HEAD,'protected_revision':PROTECTED,'self_excluded':PREFIX+'CI_REFRESH_PUBLICATION_MANIFEST_018.json','historical_manifests_are_immutable_records':True,'prior_index_alias':record['exact_original_index_alias'],'prior_files_preserved':140,'files':files,'file_count':len(files)}
mb=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode();direct.append(cpwrite('CI_REFRESH_PUBLICATION_MANIFEST_018.json',mb))
result={'status':record['status'],'head':HEAD,'direct_file_count':len(direct),'total_checkpoint_files':len(files)+1,'manifest_sha256':sha(mb),'manifest_bytes':len(mb),'receipt_sha256':sha(rb),'receipt_bytes':len(rb),'direct_files':direct,'finished_at':now()}
ob=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode()
with OUT.open('xb') as f:f.write(ob)
print(json.dumps({k:result[k] for k in ['status','head','direct_file_count','total_checkpoint_files','manifest_sha256','manifest_bytes','receipt_sha256','receipt_bytes']}|{'result_path':str(OUT),'result_bytes':len(ob),'result_sha256':sha(ob)}),flush=True)
