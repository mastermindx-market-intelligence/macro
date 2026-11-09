from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");out=r/'current-action-layout-publication-receipt.json';assert not out.exists(),'Publication receipt exists'
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
source=json.loads((r/'current-action-layout-source-receipt.json').read_text())
for path,m in dict(source['changed'],**source['unchanged']).items():assert meta((r/path).read_bytes())==m,path
runs={};paths=["current-action-layout-parent-input.json","current-action-layout-parent-receipt.json","current-action-layout-parent-snapshot.py","current-action-layout-initial-source-receipt.json","current-action-layout-source-receipt.json","current-action-layout-initial-transforms.json","current-action-layout-transforms.json","current-action-layout-test-addition.txt","current-action-layout-baseline.py","current-action-layout-final.py","current-action-layout-verified.py","current-action-layout-launch-error.json","current-action-layout-publication-readback.py"]
for phase in ['current-action-layout-baseline','current-action-layout-final','current-action-layout-verified']:
 tree=ET.fromstring((r/phase/'junit.xml').read_text());cases={}
 for c in tree.iter('testcase'):
  identity=c.get('classname','')+'::'+c.get('name','');assert identity not in cases
  outcome='failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed';cases[identity]=outcome
 result=json.loads((r/phase/'result.json').read_text());observations=json.loads((r/phase/'observations.json').read_text())
 assert observations['page_errors']==[] and observations['blocked_external_requests']==0 and observations['blocked_websockets']==0
 runs[phase]={'result':result,'observations':observations,'cases':cases,'counts':{state:list(cases.values()).count(state) for state in ['passed','failed','error','skipped']}}
 paths.extend(phase+'/'+n for n in ['result.json','observations.json','stdout.txt','stderr.txt','junit.xml'])
base=runs['current-action-layout-baseline'];initial=runs['current-action-layout-final'];final=runs['current-action-layout-verified']
assert len(base['cases'])==75 and base['counts']['failed']==21 and base['counts']['passed']==54 and base['result']['exit_code']==1
assert len(initial['cases'])==75 and initial['counts']['failed']==3 and initial['counts']['passed']==72 and initial['result']['exit_code']==1
assert set(base['cases'])==set(initial['cases'])==set(final['cases']) and len(final['cases'])==75 and set(final['cases'].values())=={'passed'} and final['result']['exit_code']==0
assert final['result']['runtime_asset_version']==source['assets']
assert final['observations']['contexts']==75 and final['observations']['pages']==81
launch=json.loads((r/'current-action-layout-launch-error.json').read_text());assert launch['exit_code']==127
files={p:meta((r/p).read_bytes()) for p in paths}
captures=[]
for p in sorted((r/'current-action-layout-verified/captures').glob('*.png')):
 b=p.read_bytes();assert b[:8]==bytes([137,80,78,71,13,10,26,10]);width,height=struct.unpack('>II',b[16:24])
 new=p.name.startswith('current-actions-') or p.name.startswith('current-feedback-')
 captures.append(dict(name=p.name,path=str(p.relative_to(r)),role='Current action and feedback UI' if new else 'Retained mutation, navigation or intent regression',new_visual_scope=new,**meta(b),width=width,height=height))
assert sum(c['new_visual_scope'] for c in captures)==13
receipt={'source':source,'runs':runs,'case_set_checks':{'baseline_21_failed_54_passed':True,'initial_3_failed_72_passed':True,'same_75_case_identities':True,'final_75_passed':True,'assertion_changes_recorded_not_claimed_identical_tests':True},'launch_error':launch,'files':files,'captures':captures,'limits':['Native isolated historical/synthetic fixtures only; no hosted or public-route production acceptance.','Two existing test functions have explicit scoped updates: visible failure feedback and actual nested-action starting scroll. Their originals are recoverable from the transforms.','Confirmed outcomes keep their reading; owned failures may move the existing drawer only enough to reveal actionable feedback while preserving body and focus.','Retaining the hidden message box prevents timeout-induced clamping; it does not guarantee constant geometry across differently sized later messages.','Existing status/live markup is retained; native browser checks are not assistive-technology announcement certification.','No storage retry, independent scroll container, status node, timer or history owner is introduced.']}
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'assets':source['assets'],'changed':len(source['changed']),'unchanged':len(source['unchanged']),'runs':{k:v['counts'] for k,v in runs.items()},'files':len(files),'captures':len(captures),'new_visual_captures':sum(c['new_visual_scope'] for c in captures)}))
