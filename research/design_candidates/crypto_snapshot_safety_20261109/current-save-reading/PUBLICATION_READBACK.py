from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");out=r/'current-save-reading-publication-receipt.json';assert not out.exists(),'Receipt already exists'
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
source=json.loads((r/'current-save-reading-source-receipt.json').read_text())
for path,m in dict(source['changed'],**source['unchanged']).items():assert meta((r/path).read_bytes())==m,path
runs={};paths=["current-save-reading-parent-input.json","current-save-reading-parent-receipt.json","current-save-reading-parent-snapshot.py","current-save-reading-source-receipt.json","current-save-reading-transforms.json","current-save-reading-test-addition.txt","current-save-reading-baseline.py","current-save-reading-final.py","current-save-reading-verified.py","current-save-reading-publication-readback.py"]
for phase in ['current-save-reading-baseline','current-save-reading-final','current-save-reading-verified']:
 root=ET.fromstring((r/phase/'junit.xml').read_text());cases={}
 for c in root.iter('testcase'):
  identity=c.get('classname','')+'::'+c.get('name','');assert identity not in cases
  outcome='failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed';cases[identity]=outcome
 result=json.loads((r/phase/'result.json').read_text());obs_path=r/phase/'observations.json'
 observations=json.loads(obs_path.read_text()) if obs_path.exists() else None
 if observations:assert observations['page_errors']==[] and observations['blocked_external_requests']==0 and observations['blocked_websockets']==0
 runs[phase]={'result':result,'observations':observations,'cases':cases,'counts':{state:list(cases.values()).count(state) for state in ['passed','failed','error','skipped']}}
 paths.extend(str(p.relative_to(r)) for p in [r/phase/n for n in ['result.json','observations.json','stdout.txt','stderr.txt','junit.xml']] if p.exists())
base=runs['current-save-reading-baseline'];selection=runs['current-save-reading-final'];final=runs['current-save-reading-verified']
assert len(base['cases'])==91 and base['counts']['failed']==19 and base['counts']['passed']==72 and base['result']['exit_code']==1
assert selection['result']['exit_code']==4 and len(selection['cases'])==0
assert set(base['cases'])==set(final['cases']) and len(final['cases'])==91 and set(final['cases'].values())=={'passed'} and final['result']['exit_code']==0
assert final['result']['runtime_asset_version']==source['assets']==selection['result']['runtime_asset_version']
assert final['result']['candidate_inputs']==selection['result']['candidate_inputs']==source['changed']
assert final['observations']['contexts']==91 and final['observations']['pages']==97
files={p:meta((r/p).read_bytes()) for p in paths}
captures=[]
for p in sorted((r/'current-save-reading-verified/captures').glob('*.png')):
 b=p.read_bytes();assert b[:8]==bytes([137,80,78,71,13,10,26,10]);width,height=struct.unpack('>II',b[16:24])
 captures.append(dict(name=p.name,path=str(p.relative_to(r)),role='Confirmed current mutation reader' if p.name.startswith('current-save-reading-') else 'Retained current-review navigation',**meta(b),width=width,height=height))
assert sum(c['name'].startswith('current-save-reading-') for c in captures)==6
receipt={'source':source,'runs':runs,'case_set_checks':{'baseline_19_failed_72_passed':True,'selection_error_no_cases_executed':True,'correction_only_runner_selector_prefix':True,'candidate_source_and_test_unchanged_for_verification':True,'final_same_91_all_passed':True},'files':files,'captures':captures,'limits':['Native isolated historical/synthetic HTTP fixture only; no hosted acceptance, current-market freshness or public-route cutover.','The existing storage write/readback contract is unchanged; Web Storage has no atomic cross-tab compare-and-swap.','Optional history persistence failure preserves the fresh visible reader but does not claim durable reading metadata.','A newer route, locale, history entry/metadata or focus choice owns the UI continuation; an already confirmed storage outcome is not replayed.','Crops show actual dialog viewport; browser assertions exercise expanded offscreen content and navigation.']}
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'assets':source['assets'],'changed':len(source['changed']),'unchanged':len(source['unchanged']),'runs':{k:v['counts'] for k,v in runs.items()},'files':len(files),'captures':[{'name':c['name'],'width':c['width'],'height':c['height']} for c in captures]}))
