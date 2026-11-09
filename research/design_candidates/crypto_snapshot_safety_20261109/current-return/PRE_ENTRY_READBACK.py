from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");out=r/'current-return-publication-receipt.json'
assert not out.exists(),'Publication receipt already exists'
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
source=json.loads((r/'current-return-source-receipt.json').read_text())
for path,m in dict(source['changed'],**source['unchanged']).items():assert meta((r/path).read_bytes())==m,path
runs={}
for phase in ['current-return-baseline','current-return-final','current-return-harness-final','current-return-verified']:
 root=ET.fromstring((r/phase/'junit.xml').read_text());cases={}
 for c in root.iter('testcase'):
  identity=c.get('classname')+'::'+c.get('name');assert identity not in cases
  outcome='failed' if c.find('failure') is not None else 'error' if c.find('error') is not None else 'skipped' if c.find('skipped') is not None else 'passed'
  cases[identity]=outcome
 result=json.loads((r/phase/'result.json').read_text());observations=json.loads((r/phase/'observations.json').read_text())
 assert observations['page_errors']==[] and observations['blocked_external_requests']==0 and observations['blocked_websockets']==0
 runs[phase]={'result':result,'observations':observations,'cases':cases,'counts':{state:list(cases.values()).count(state) for state in ['passed','failed','error','skipped']}}
base=runs['current-return-baseline']['cases'];initial=runs['current-return-final']['cases'];correction=runs['current-return-harness-final']['cases'];final=runs['current-return-verified']['cases']
assert set(base)==set(initial) and len(base)==57
assert set(correction)=={k for k,v in initial.items() if v=='failed'} and set(correction.values())=={'passed'}
assert len(final)==59 and set(final.values())=={'passed'} and set(initial).issubset(final)
assert all('current_review_locale_does_not_restart_existing_reading' in k for k in set(final)-set(initial))
assert runs['current-return-verified']['result']['exit_code']==0
assert runs['current-return-verified']['result']['runtime_asset_version']==source['assets']
files={p:meta((r/p).read_bytes()) for p in ["current-return-parent-input.json","current-return-parent-receipt.json","current-return-parent-snapshot.py","current-return-initial-source-receipt.json","current-return-pre-visual-source-receipt.json","current-return-source-receipt.json","current-return-initial-transforms.json","current-return-pre-visual-transforms.json","current-return-transforms.json","current-return-baseline.py","current-return-candidate.py","current-return-harness-correction.py","current-return-verified.py","current-return-injection-diagnostic.py","current-return-injection-diagnostic.json","current-return-baseline/result.json","current-return-baseline/observations.json","current-return-baseline/stdout.txt","current-return-baseline/stderr.txt","current-return-baseline/junit.xml","current-return-final/result.json","current-return-final/observations.json","current-return-final/stdout.txt","current-return-final/stderr.txt","current-return-final/junit.xml","current-return-harness-final/result.json","current-return-harness-final/observations.json","current-return-harness-final/stdout.txt","current-return-harness-final/stderr.txt","current-return-harness-final/junit.xml","current-return-verified/result.json","current-return-verified/observations.json","current-return-verified/stdout.txt","current-return-verified/stderr.txt","current-return-verified/junit.xml"]}
files['current-return-publication-readback.py']=meta((r/'current-return-publication-readback.py').read_bytes())
captures=[]
for entry in [{"name":"current-return-review-en-390.png","path":"current-return-verified/captures/current-return-review-en-390.png","role":"Final verified UI"},{"name":"current-return-review-zh-320.png","path":"current-return-verified/captures/current-return-review-zh-320.png","role":"Final verified UI"},{"name":"current-return-details-en-390.png","path":"current-return-verified/captures/current-return-details-en-390.png","role":"Final verified UI"},{"name":"current-return-details-zh-320.png","path":"current-return-verified/captures/current-return-details-zh-320.png","role":"Final verified UI"},{"name":"current-return-detached-en-390.png","path":"current-return-verified/captures/current-return-detached-en-390.png","role":"Final verified UI"},{"name":"current-return-detached-zh-320.png","path":"current-return-verified/captures/current-return-detached-zh-320.png","role":"Final verified UI"},{"name":"initial-current-return-review-en-390.png","path":"current-return-final/captures/current-return-review-en-390.png","role":"Initial candidate before first-reading correction"},{"name":"initial-current-return-review-zh-320.png","path":"current-return-final/captures/current-return-review-zh-320.png","role":"Initial candidate before first-reading correction"}]:
 b=(r/entry['path']).read_bytes();assert b[:8]==bytes([137,80,78,71,13,10,26,10]);width,height=struct.unpack('>II',b[16:24]);captures.append(dict(entry,**meta(b),width=width,height=height))
receipt={'source':source,'runs':runs,'case_set_checks':{'baseline_equals_initial_57':True,'initial_two_failures_equal_corrected_cases':True,'verified_all_59_pass':True,'only_two_locale_cases_added':True},'diagnostic':json.loads((r/'current-return-injection-diagnostic.json').read_text()),'files':files,'captures':captures,'limits':['Native isolated HTTP fixture only; no hosted acceptance or public-route cutover.','Current scope uses supplied revision/cutoff/horizon; no historical results or forecast calibration are created.','Capture crops show the actual dialog viewport; offscreen content is exercised by browser assertions.']}
out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'assets':source['assets'],'changed':len(source['changed']),'unchanged':len(source['unchanged']),'runs':{k:v['counts'] for k,v in runs.items()},'files':len(files),'captures':len(captures),'capture_dimensions':[(c['name'],c['width'],c['height']) for c in captures]}))
