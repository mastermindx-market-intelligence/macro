"""Finite root-owned attended preflight -> consumed proof -> writer -> census."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1')
CORE=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1/tiingo-wave15-continuation04-disposition-pipeline-bound01.py')
CORE_SHA='f4a3c65db22325f9755b7ebaa6d425819f41aefdc916f0733341f35f06727ccc'
ROOT='01a12ab6-92cb-7c42-a711-42673ebb6b50'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def emit(v):print(json.dumps(v),flush=True)
def save(p,v):
 with os.fdopen(os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'w') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def check():
 assert sys.flags.optimize==0 and sha(CORE)==CORE_SHA
 assert os.environ.get('CODEX_THREAD_ID')==ROOT
 assert sha(E/'eod-wave15-original-unadmitted-continuation04-20261013-01a12ab6-scope.json')=='1ec636d0f27fe20e81dfc72a0853980e91c8af6522507d19269d67eea36eeb28'
def stage(mode,prefix):
 check();log=E/f'eod-wave15-unadmitted-continuation04-prefix{prefix}-two-stage-{mode}-original.log'
 started=now()
 with log.open('x') as f:r=subprocess.run([sys.executable,'-E',str(CORE),mode,prefix],stdout=f,stderr=subprocess.STDOUT)
 assert r.returncode==0,f'{mode} failed at prefix {prefix}; preserve this exact stage, no replacement'
 return started,now(),log
check()
FIRST=int(sys.argv[1]);assert 1<=FIRST<=92;LAST=FIRST+7
for i in range(FIRST,LAST+1):
 for suffix in ['disposition-preflight','preflight-parent-consumption','qualified']:
  assert not (E/f'eod-wave15-unadmitted-continuation04-prefix{i:02d}-{suffix}.json').exists()
 assert not (E/f'eod-qualified-catalogue-coverage-wave15-unadmitted-continuation04-prefix{i:02d}-delta.json').exists()
emit({'phase':'attended_disposition_window_started','started_at_utc':now(),'controller_sha256':sha(__file__),'core_sha256':CORE_SHA,'root':ROOT,'first_prefix':f'{FIRST:02d}','last_possible_prefix':f'{LAST:02d}','new_start_deadline_seconds':900,'already_started_stage_settles_before_exit':True,'archive_payload_repair':False,'provider_requests':0,'credentials_read':False})
deadline=time.monotonic()+900;next_prefix=FIRST;completed=[]
while time.monotonic()<deadline and next_prefix<=LAST:
 check()
 progress=json.loads(subprocess.check_output([sys.executable,'-E',str(CORE),'progress'],text=True));emit({'phase':'owned_progress','progress':progress})
 assert progress['next_prefix']==f'{next_prefix:02d}'
 if time.monotonic()>=deadline:break
 if progress['new_unqualified_responses']>=200 or (progress['settlement_file_observed'] and progress['new_unqualified_responses']>0):
  prefix=f'{next_prefix:02d}';emit({'phase':'preflight_started','prefix':prefix})
  started,settled,log=stage('preflight',prefix)
  pfpath=E/f'eod-wave15-unadmitted-continuation04-prefix{prefix}-disposition-preflight.json';pf=json.loads(pfpath.read_text())
  assert pf['method_sha256']==CORE_SHA and pf['prefix']==prefix and pf['all_normalizer_inputs_verified'] and pf['source_payload_modified'] is False and pf['archive_writes']==0
  assert pf['selected_responses']==pf['valid_count']+pf['quality_count']==len(pf['records'])
  save(E/f'eod-wave15-unadmitted-continuation04-prefix{prefix}-preflight-parent-consumption.json',{'schema':'tiingo.attended_original_preflight_actual_parent_consumption/v1','recorded_at_utc':now(),'root':ROOT,'controller_sha256':sha(__file__),'method_sha256':CORE_SHA,'prefix':prefix,'actual_preflight_return_consumed':True,'original_preflight_exit_code':0,'original_started_at_utc':started,'original_terminal_return_at_utc':settled,'original_preflight_log_sha256':sha(log),'preflight_sha256':sha(pfpath),'provider_requests':0,'credentials_read':False})
  emit({'phase':'successful_preflight_consumed','prefix':prefix,'valid':pf['valid_count'],'whole_quality_quarantines':pf['quality_count']})
  if time.monotonic()>=deadline:
   emit({'phase':'consumed_preflight_preserved_writer_not_admitted_deadline','prefix':prefix,'preflight_sha256':sha(pfpath),'archive_writer_started':False});break
  stage('qualify',prefix);qpath=E/f'eod-wave15-unadmitted-continuation04-prefix{prefix}-qualified.json';q=json.loads(qpath.read_text());assert q['all_completed_response_dispositions_verified'] and q['method_sha256']==CORE_SHA
  stage('coverage',prefix);cpath=E/f'eod-qualified-catalogue-coverage-wave15-unadmitted-continuation04-prefix{prefix}-delta.json';c=json.loads(cpath.read_text());assert c['accepted_qualification_files'][qpath.name]==sha(qpath) and c['method_sha256']==CORE_SHA
  emit({'phase':'original_disposition_and_census_returns_consumed','prefix':prefix,'qualification_sha256':sha(qpath),'coverage_sha256':sha(cpath),'valid_responses':q['selected_receipts'],'whole_quality_quarantines':len(q['quality_quarantines']),'histories':c['accepted_nonempty_ticker_histories'],'bars':c['accepted_distinct_bars']})
  completed.append(prefix);next_prefix+=1
 elif progress['settlement_file_observed'] and progress['new_unqualified_responses']==0:break
 if time.monotonic()<deadline and next_prefix<=LAST:time.sleep(30)
emit({'phase':'attended_disposition_window_settled','settled_at_utc':now(),'completed_prefixes':completed,'next_unstarted_prefix':f'{next_prefix:02d}','original_capture_terminal_return_consumed':False,'original_capture_complete_claimed':False,'closure_requires_actual_original_terminal_return':True})
