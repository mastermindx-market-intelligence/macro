"""One bounded new-input research canary through the unchanged installed selector."""
import hashlib,json,os,subprocess
from pathlib import Path
from datetime import datetime,timezone
E=Path('/Users/chriswong/.codex/visualizations/2026/10/11/01a12ab6-92cb-7c42-a711-42673ebb6b50/tiingo-phase1');R=Path('/Volumes/Mastermind/market-data/tiingo');LAUNCH=Path('/Users/chriswong/.local/bin/mmx-data-workspace')
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,d):
 with p.open('x') as f:json.dump(d,f,indent=2);f.write('\n')
assert os.environ.get('CODEX_THREAD_ID')=='01a12ab6-92cb-7c42-a711-42673ebb6b50'
assert h(LAUNCH)=='381f3b12c4d80313acd518ac2d5571fe09bf3286009645a00dd15af64e5a809c'
qp=E/'eod-wave15-prefix02-qualified.json';assert h(qp)=='280bf20a6e22223dde64dc1bf0b79484568eef91ec86aea1c996917b77a5e1a6'
parent=load(E/'tiingo-wave15-disposition-window02-actual-parent-consumption.json');assert parent['actual_original_terminal_return_consumed'] and parent['qualification_sha256'][qp.name]==h(qp)
row=next(r for r in load(qp)['receipts'] if r['symbol']=='SAPIF');assert row['projection_lineage_verified'] and row['split_events']==1 and row['dividend_events']==69 and row['projected_rows']==4787
rp=R/row['receipt_file'];assert h(rp)==row['receipt_file_sha256'];rec=load(rp);day=row['observed_at_utc'][:10];raw=R/'manifests/eod-bars'/day/(row['raw_sha256']+'.json');identity=R/'manifests/eod-bars'/day/(row['receipt_id']+'.json');mf=identity if identity.exists() else raw;meta=load(mf)
assert meta['source_receipt_id']==row['receipt_id'] and meta['source_sha256']==row['raw_sha256'];pf=R/meta['output_path'];assert h(pf)==meta['output_sha256']
ref='tiingo:'+meta['output_path'];source_before={str(p.relative_to(R)):h(p) for p in [rp,mf,pf]}
scope={'schema':'tiingo.new_qualified_input_existing_installed_lab_canary_scope/v1','started_at_utc':datetime.now(timezone.utc).isoformat(),'method_sha256':h(__file__),'launcher_sha256':h(LAUNCH),'accepted_qualification_sha256':h(qp),'qualified_receipt_id':row['receipt_id'],'vendor_symbol':'SAPIF','source_before_sha256':source_before,'one_trial_declared_budget':1,'research_only':True,'production_trial_ledger_requested':False,'archive_writes_requested':False,'selector_or_runtime_change_requested':False,'provider_requests':0,'credentials_read':False}
scopepath=E/'tiingo-wave15-new-history-installed-lab-canary-scope.json';save(scopepath,scope)
def invoke(label,request):
 req=E/f'tiingo-wave15-new-history-installed-{label}-request.json';out=E/f'tiingo-wave15-new-history-installed-{label}-original-result.json';save(req,request)
 with req.open('rb') as i,out.open('xb') as o:r=subprocess.run([str(LAUNCH)],stdin=i,stdout=o,stderr=subprocess.PIPE)
 assert r.returncode==0,f'{label} failed; preserve original artifact, no replay'
 d=load(out);assert d['implementation_revision']=='0b204cde017b88a9fec03ddb583f6b5e02ea4886'
 return out,d
out,description=invoke('describe',{'action':'describe','ref':ref});version=description['source']['file_version']
request={'action':'lab_run','bar_frequency':'daily','column_map':{'close':'close_tradj','high':'high_tradj','low':'low_tradj','volume':'volume_vendor_adjusted'},'start':row['first_date'],'end':row['last_date'],'expected_versions':{ref:version},'request':{'cost_bps':5,'horizon_bars':21,'n_configs_searched':1,'refs':[ref],'signal_id':'golden_cross_7_35'},'time_column':'market_date'}
resultpath,result=invoke('lab',request)
assert result['research_only'] and result['result']['production_ledger_written'] is False
run=result['run'];assert run['state']=='SUCCEEDED' and run['exit_code']==0 and run['production_ledger_written'] is False
assert result['result']['sources'][0]['loaded_rows']==4787 and result['result']['sources'][0]['ref']==ref and result['result']['sources'][0]['file_version']==version
for rel,digest in source_before.items():assert h(R/rel)==digest
proof={'schema':'tiingo.new_history_actual_installed_research_lab_canary/v1','settled_at_utc':datetime.now(timezone.utc).isoformat(),'scope_sha256':h(scopepath),'launcher_sha256':h(LAUNCH),'implementation_revision':result['implementation_revision'],'qualified_vendor_symbol':'SAPIF','qualified_source_receipt_id':row['receipt_id'],'actual_adjusted_history_rows':4787,'source_window':[row['first_date'],row['last_date']],'original_describe_result_sha256':h(out),'original_lab_result_sha256':h(resultpath),'source_ref':ref,'source_file_version':version,'run':run,'source_before_after_hashes_unchanged':True,'trial_budget':1,'metrics_or_market_rows_copied_to_acceptance':False,'raw_adjusted_and_action_evidence_from_qualified_source':{'split_events':1,'dividend_events':69,'raw_adjusted_different_dates':row['raw_adjusted_different_dates']},'production_trial_ledger_written':False,'research_only':True,'canonical_identity_admitted':False,'pit_backtest_eligible':False,'selector_or_runtime_changed':False,'provider_requests':0,'credentials_read':False,'programme_acceptance_claimed':False}
save(E/'tiingo-wave15-new-history-installed-lab-canary-actual-reader-result.json',proof);print(json.dumps(proof),flush=True)
