"""One direct foreground child; atomically retain wait truth before validation."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,subprocess,time,tempfile
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
now=lambda:datetime.now(timezone.utc).isoformat()
def dirsync():
 fd=os.open(E,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)
def save(p,value):
 fd,tmp=tempfile.mkstemp(prefix='.'+p.name+'.control-',dir=str(E))
 with os.fdopen(fd,'w') as f:
  json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.link(tmp,p);dirsync();Path(tmp).unlink();dirsync()
 # Any failure before success leaves exact temp/final evidence; no overwrite or blind retry.
def notify(value):
 try:print(json.dumps(value),flush=True)
 except (OSError,ValueError):pass
assert os.environ.get('CODEX_THREAD_ID')==ROOT and sys.flags.optimize==0 and len(sys.argv)==3
packet=E/sys.argv[1];assert packet.parent==E and sha(packet)==sys.argv[2]
p=json.loads(packet.read_text());assert p['schema']=='tiingo.single_finite_foreground_stage_launch_packet/v1' and p['root']==ROOT
assert p['wrapper_sha256']==sha(__file__) and p['mode'] in {'preflight','qualify','coverage'} and p['prefix'] in {'01','03'}
source=E/p['source_file'];assert source.parent==E and sha(source)==p['source_sha256']
for n,h in p['frozen_input_sha256'].items():assert (E/n).parent==E and sha(E/n)==h
assert p['provider_requests']==0 and p['credentials_read'] is False and p['automatic_retry'] is False
log=E/p['exclusive_log_file'];intent=E/p['exclusive_launch_intent_file'];childid=E/p['exclusive_child_identity_file'];waitp=E/p['exclusive_observed_wait_file'];validation=E/p['exclusive_validation_file']
outputs=[E/n for n in p['new_output_files']];allpaths=[log,intent,childid,waitp,validation,*outputs]
assert len(set(allpaths))==len(allpaths) and not set(allpaths)&{packet,source,*(E/n for n in p['frozen_input_sha256'])}
for f in allpaths:assert f.parent==E and not f.exists()
command=[sys.executable,'-E',str(source),p['mode'],p['prefix']]
command_sha=hashlib.sha256(json.dumps(command,separators=(',',':')).encode()).hexdigest()
save(intent,{'schema':'tiingo.single_foreground_exclusive_launch_intent/v1','recorded_at_utc':now(),'root':ROOT,'run_id':p['run_id'],'prefix':p['prefix'],'mode':p['mode'],'packet_sha256':sha(packet),'wrapper_sha256':sha(__file__),'source_sha256':sha(source),'command_sha256':command_sha,'command':command,'frozen_input_sha256':p['frozen_input_sha256'],'new_output_files':p['new_output_files'],'exclusive_log_file':log.name,'automatic_retry':False,'daemon':False,'child_started_claimed':False})
control_errors=[]
with log.open('x') as out:
 child=subprocess.Popen(command,stdout=out,stderr=subprocess.STDOUT)
 try:save(childid,{'schema':'tiingo.direct_Popen_child_handle_identity/v1','observed_spawn_at_utc':now(),'observed_spawn_monotonic':time.monotonic(),'root':ROOT,'launch_intent_sha256':sha(intent),'child_pid':child.pid,'parent_wrapper_pid':os.getpid(),'command_sha256':command_sha,'identity_basis':'Actual direct Popen handle observed by this wrapper; no OS birth-time or later PID-reuse inference','stdout_stderr_same_exclusive_log':True})
 except Exception as error:control_errors.append({'phase':'child_identity_publication','error_type':type(error).__name__})
 notify({'phase':'foreground_child_started','child_pid':child.pid,'mode':p['mode'],'prefix':p['prefix']})
 rc=child.wait()
 # Preserve wait truth unconditionally before syncing, hashing or validating child outputs/inputs.
 save(waitp,{'schema':'tiingo.direct_foreground_wrapper_observed_wait_return/v1','recorded_at_utc':now(),'root':ROOT,'run_id':p['run_id'],'prefix':p['prefix'],'mode':p['mode'],'observed_direct_child_pid':child.pid,'observed_subprocess_wait_return_code':rc,'command_sha256':command_sha,'packet_sha256_at_launch':sys.argv[2],'wrapper_observed_wait_return':True,'actual_Codex_tool_terminal_consumed_claimed':False,'missing_original_terminal_reconstructed':False,'pre_wait_control_record_errors':control_errors,'validation_completed_claimed':False,'automatic_retry':False})
 validation_errors=list(control_errors);hashes={};log_sha=None
 try:
  out.flush();os.fsync(out.fileno());log_sha=sha(log)
  for n,h in p['frozen_input_sha256'].items():assert sha(E/n)==h
  assert sha(source)==p['source_sha256'] and sha(packet)==sys.argv[2]
  hashes={f.name:sha(f) for f in outputs if f.exists()}
  if rc==0:assert len(hashes)==len(outputs),'Successful subprocess lacks planned outputs'
 except Exception as error:validation_errors.append({'phase':'post_wait_validation','error_type':type(error).__name__})
 save(validation,{'schema':'tiingo.direct_foreground_wrapper_post_wait_validation/v1','recorded_at_utc':now(),'root':ROOT,'run_id':p['run_id'],'prefix':p['prefix'],'mode':p['mode'],'observed_wait_receipt_sha256':sha(waitp),'packet_sha256_at_launch':sys.argv[2],'wrapper_sha256':sha(__file__),'source_sha256_at_launch':p['source_sha256'],'observed_subprocess_wait_return_code':rc,'log_sha256':log_sha,'output_sha256':hashes,'post_wait_validation_passed':not bool(validation_errors),'validation_errors':validation_errors,'actual_Codex_tool_terminal_consumed_claimed':False,'missing_original_terminal_reconstructed':False,'automatic_retry':False,'provider_requests':0,'credentials_read':False})
 notify({'phase':'foreground_child_wait_and_validation_recorded','child_exit_code':rc,'observed_wait_receipt_sha256':sha(waitp),'validation_passed':not bool(validation_errors),'validation_receipt_sha256':sha(validation)})
raise SystemExit(rc if not validation_errors else 74)
