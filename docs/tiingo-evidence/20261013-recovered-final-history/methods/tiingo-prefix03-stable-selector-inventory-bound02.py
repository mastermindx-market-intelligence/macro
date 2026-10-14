"""Stable exact-selector inventory after read-only interrupted-writer reconciliation."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,subprocess,sys,re,stat,tempfile
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo')
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
RECON='tiingo-prefix03-original91287-partial-effect-readonly-reconciliation.json'
RECON_SHA='77b8699971806bc63f839fec280e2ba41d1d3bda669087acfa3c1f293cce7254'
def directory_identity(p):
 st=p.lstat();assert stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode),'Symlink/non-directory ancestor'
 return st.st_dev,st.st_ino
def check_ancestors(p):
 return {str(a):directory_identity(a) for a in reversed((p.parent,*p.parent.parents))}
def regular_state(p):
 ancestors=check_ancestors(p)
 try:before=p.lstat()
 except FileNotFoundError:return None,ancestors
 assert stat.S_ISREG(before.st_mode) and not stat.S_ISLNK(before.st_mode),'Symlink/non-regular leaf'
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 with os.fdopen(fd,'rb') as f:
  opened=os.fstat(f.fileno());assert (opened.st_dev,opened.st_ino)==(before.st_dev,before.st_ino) and stat.S_ISREG(opened.st_mode)
  h=hashlib.sha256()
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 after=p.lstat();assert (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns)==(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
 assert check_ancestors(p)==ancestors
 return h.hexdigest(),ancestors
def sha(p):
 digest,_=regular_state(Path(p));assert digest is not None,'Required file truly absent';return digest
load=lambda p:json.loads(Path(p).read_text())
SELF_SHA=sha(Path(__file__))
assert sys.flags.optimize==0 and os.environ.get('CODEX_THREAD_ID')==ROOT
assert sha(E/RECON)==RECON_SHA
r=load(E/RECON);assert r['method_sha256']=='497ac9a15d4e0fef4027a4b5e12b49574b7abc6690eafb75c347ade420a242e2' and r['root']==ROOT and r['original_tool_session']==91287 and r['original_tool_exit_code'] is None and r['actual_original_terminal_return_consumed'] is False
assert r['all862_raw_scalar_window_identity_and_success_ledger_bounds_verified'] and r['all_existing_current_reader_rows_equal_raw_normalization'] and r['all_observed_and_protected_artifact_hashes_unchanged'] and r['selected_responses']==862 and r['complete_current_projections']+r['absent_current_projections']==862
pins={'tiingo-prefix03-readonly52142-completed-actual-parent-acceptance.json':'86c4b2662826a7df698aea904bed0238259fb346b8b2d3e9af7e349734863c68','tiingo-prefix03-original91287-retained-native-launch-call.json':'6f33a7d295a4bc4ce712e34d618c13817e3114c0d2060373a26c196caec61cc9','tiingo-prefix03-original91287-retained-native-launch-return.json':'c440304f2ba2ec08df43c374cb9ec6f4346f80541a3cbd9307b16d1374243b27','tiingo-wave15-continuation04-settled-success-prefix03-bound01.py':'49c3e277752add221fa1a6848cee0ffdea88ed057d224f5859e22c8a09884a64','eod-wave15-unadmitted-continuation04-prefix03-preflight-parent-consumption.json':'fb2ef7fda589d824ed72d97462278cb554ca09cd1ab9d600e2e5229f28783170'}
for n,h in pins.items():assert sha(E/n)==h
accepted=load(E/'tiingo-prefix03-readonly52142-completed-actual-parent-acceptance.json')
assert accepted['root']==ROOT and accepted['actual_readonly_tool_session']==52142 and accepted['actual_readonly_native_exit_code']==0 and accepted['actual_readonly_native_terminal_consumed'] is True and accepted['readonly_reconciliation_sha256']==RECON_SHA
launch=load(E/'tiingo-prefix03-original91287-retained-native-launch-call.json');returned=load(E/'tiingo-prefix03-original91287-retained-native-launch-return.json')
assert launch['payload']['call_id']==returned['payload']['call_id']=='call_OMxasq0OcwsNay5xETIzv5Xy'
commands=[json.loads(x) for x in re.findall(r'cmd:("(?:\\.|[^"\\])*")',launch['payload']['input'])]
writer=[x for x in commands if "p=Path('eod-wave15-unadmitted-continuation04-prefix03-settled-success-qualify-original.log')" in x]
assert len(writer)==1
command=writer[0];assert "with p.open('x') as f:" in command and "subprocess.run([sys.executable,'-E','tiingo-wave15-continuation04-settled-success-prefix03-bound01.py','qualify','03'],stdout=f,stderr=subprocess.STDOUT)" in command
assert '91287' in json.dumps(returned) and '1efd51' in json.dumps(returned)
log=E/'eod-wave15-unadmitted-continuation04-prefix03-settled-success-qualify-original.log'
def no_holder():
 c=subprocess.run(['lsof','-nP',str(log)],text=True,capture_output=True)
 assert c.returncode==1 and c.stdout=='' and c.stderr=='','Exact original log still held or holder check unavailable'
no_holder()
assert sha(log)==r['original_exclusive_log_sha256']
assert regular_state(E/'eod-wave15-unadmitted-continuation04-prefix03-qualified.json')[0] is None and regular_state(E/'eod-qualified-catalogue-coverage-wave15-unadmitted-continuation04-prefix03-delta.json')[0] is None
proof=load(E/'eod-wave15-unadmitted-continuation04-prefix03-disposition-preflight.json');items={x['receipt_id']:x for x in proof['records']};assert len(items)==862 and set(items)=={x['receipt_id'] for x in r['footprint']}
paths={};directories=set()
for f in r['footprint']:
 item=items[f['receipt_id']];assert item['symbol']==f['symbol'] and item['request_path']==f['request_path'] and item['receipt_file_sha256']==f['receipt_file_sha256']==sha(R/f['receipt_file'])
 day=item['observed_at_utc'][:10]
 for selector in dict.fromkeys([item['receipt_id'],item['raw_sha256']]):
  for directory,suffix in [('manifests','.json'),('normalized','.parquet')]:
   rel=f'{directory}/eod-bars/{day}/{selector}{suffix}';expected=f['artifact_sha256'].get(rel)
   assert rel not in paths or paths[rel]==expected;paths[rel]=expected;directories.add(R/directory/'eod-bars'/day)
def inventory():
 state={};ancestor_state={}
 for rel,h in paths.items():
  actual,ancestors=regular_state(R/rel);assert actual==h,'Occupied/changed/unclassified selector'
  state[rel]=actual
  for path,identity in ancestors.items():assert path not in ancestor_state or ancestor_state[path]==identity;ancestor_state[path]=identity
 temps={}
 for d in directories:
  directory_identity(d);check_ancestors(d)
  for pattern in ['.parquet-*','.incoming-*']:
   for p in d.glob(pattern):
    st=p.lstat();assert stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode),'Temporary symlink/non-regular entry'
    check_ancestors(p)
    temps[str(p.relative_to(R))]={'size_bytes':st.st_size,'sha256':sha(p) if st.st_size<=256*1024**2 else None,'dev':st.st_dev,'ino':st.st_ino,'unclassified_and_preserved':True}
 return state,temps,ancestor_state
frozen=dict(r['frozen_input_sha256'])
def pin(path,h):
 path=str(path);assert path not in frozen or frozen[path]==h;frozen[path]=h
pin(Path(__file__),SELF_SHA);pin(E/RECON,RECON_SHA)
for n,h in pins.items():pin(E/n,h)
def freeze_check():
 for path,h in frozen.items():assert sha(path)==h
freeze_check();no_holder();before,temps_before,ancestors_before=inventory()
after,temps_after,ancestors_after=inventory()
assert before==after and temps_before==temps_after and ancestors_before==ancestors_after
freeze_check();no_holder()
assert sha(log)==r['original_exclusive_log_sha256'] and regular_state(E/'eod-wave15-unadmitted-continuation04-prefix03-qualified.json')[0] is None and regular_state(E/'eod-qualified-catalogue-coverage-wave15-unadmitted-continuation04-prefix03-delta.json')[0] is None
out={'schema':'tiingo.interrupted_qualification_stable_exact_selector_inventory_and_launch_descriptor_binding/v1','recorded_at_utc':datetime.now(timezone.utc).isoformat(),'root':ROOT,'method_sha256':SELF_SHA,'readonly_reconciliation_sha256':RECON_SHA,'original_tool_session':91287,'original_exit_code':None,'actual_original_terminal_return_consumed':False,'native_launch_call_sha256':pins['tiingo-prefix03-original91287-retained-native-launch-call.json'],'native_launch_return_sha256':pins['tiingo-prefix03-original91287-retained-native-launch-return.json'],'original_launch_command_sha256':hashlib.sha256(command.encode()).hexdigest(),'original_wrapper_held_exclusive_log_while_waiting_for_direct_child':True,'direct_child_stdout_and_stderr_inherit_same_log':True,'scoped_original_log_no_holder_before_and_after':True,'universal_writer_absence_claimed':False,'original_frozen_selection':862,'complete_current_projections':r['complete_current_projections'],'absent_current_projections':r['absent_current_projections'],'all_identity_and_raw_selectors_stable_including_absent_paths':True,'selector_path_state':after,'ancestor_directory_identity':ancestors_after,'frozen_input_sha256':frozen,'actual_readonly52142_parent_sha256':pins['tiingo-prefix03-readonly52142-completed-actual-parent-acceptance.json'],'lstat_regular_file_and_true_absence_and_no_symlink_ancestors_both_passes':True,'unexpected_temporary_artifact_sha256':temps_after,'unexpected_temporary_artifact_count':len(temps_after),'no_temporary_cleanup':True,'same_prefix_continuation_stable_footprint_qualified':not bool(temps_after),'provider_requests':0,'archive_writes':0,'credentials_read':False}
p=E/'tiingo-prefix03-original91287-stable-selector-and-launch-descriptor-proof.json'
fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.control-',dir=str(E))
with os.fdopen(fd,'w') as f:json.dump(out,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
os.link(tmp,p);dirfd=os.open(E,os.O_RDONLY);os.fsync(dirfd);os.close(dirfd);Path(tmp).unlink()
print(json.dumps({k:v for k,v in out.items() if k not in {'selector_path_state','ancestor_directory_identity','frozen_input_sha256'}},indent=2),flush=True)
