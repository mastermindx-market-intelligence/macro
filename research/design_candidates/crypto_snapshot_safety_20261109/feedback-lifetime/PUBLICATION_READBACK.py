from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
from PIL import Image
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm")
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
source=json.loads((r/'feedback-lifetime-source-receipt.json').read_text())
for path,m in dict(source['changed'],**source['unchanged']).items():assert meta((r/path).read_bytes())==m,path
runs={}
for name in ['feedback-lifetime-baseline','feedback-lifetime-baseline-corrected','feedback-lifetime-verified']:
 phase=r/name;cases={}
 for x in ET.parse(phase/'junit.xml').getroot().iter('testcase'):
  key=x.attrib.get('classname','')+'::'+x.attrib['name'];assert key not in cases,key
  cases[key]='failed' if x.find('failure') is not None else 'error' if x.find('error') is not None else 'skipped' if x.find('skipped') is not None else 'passed'
 runs[name]={'result':json.loads((phase/'result.json').read_text()),'observations':json.loads((phase/'observations.json').read_text()),'cases':cases}
initial=runs['feedback-lifetime-baseline'];corrected=runs['feedback-lifetime-baseline-corrected'];final=runs['feedback-lifetime-verified']
assert len(initial['cases'])==66 and len(corrected['cases'])==30 and len(final['cases'])==67
assert set(final['cases'].values())=={'passed'}
assert set(final['cases'])==set(initial['cases'])|set(corrected['cases'])
assert set(corrected['cases']).issubset(final['cases'])
assert final['result']['test_sha256']==corrected['result']['test_sha256']
assert len(set(final['cases'])-set(corrected['cases']))==37
assert all(initial['cases'][key]=='passed' for key in set(final['cases'])-set(corrected['cases']))
for run in runs.values():
 obs=run['observations'];assert obs['page_errors']==[] and obs['blocked_external_requests']==0 and obs['blocked_websockets']==0
files=['feedback-lifetime-parent-input.json','feedback-lifetime-parent-receipt.json','feedback-lifetime-parent-snapshot.py','feedback-lifetime-source-receipt.json','feedback-lifetime-transforms.json','feedback-lifetime-initial-test-addition.txt','feedback-lifetime-handoff-test-addition.txt','feedback-lifetime-test-fixes.json','feedback-lifetime-test-addition.txt','feedback-lifetime-baseline.py','feedback-lifetime-baseline-corrected.py','feedback-lifetime-verified.py','feedback-lifetime-publication-readback.py']
for name in runs:files += [name+'/'+f for f in ['result.json','observations.json','stdout.txt','stderr.txt','junit.xml']]
baseline_keep=['feedback-task-review-success-en-390.png','feedback-task-review-failure-zh-320.png']
captures=[]
for name in ['feedback-lifetime-baseline-corrected','feedback-lifetime-verified']:
 directory=r/name/'captures';paths=sorted(directory.glob('*.png')) if name=='feedback-lifetime-verified' else [directory/n for n in baseline_keep]
 for path in paths:
  assert path.exists(),path
  with Image.open(path) as im:w,h=im.size
  captures.append({'name':path.name,'path':str(path.relative_to(r)),'run':name,'new_visual_scope':name=='feedback-lifetime-baseline-corrected' or path.name.startswith('feedback-'),
   'role':'Parent feedback leakage' if name=='feedback-lifetime-baseline-corrected' else 'New task/Retry feedback proof' if path.name.startswith('feedback-') else 'Retained mutation/navigation regression',
   **meta(path.read_bytes()),'width':w,'height':h})
receipt={'source':source,'runs':runs,'case_set_checks':{'initial_cases':66,'corrected_baseline_cases':30,'final_cases':67,'new_cases':30,'retained_cases':37,'final_equals_baseline_union':True,'same_corrected_baseline_final_test_bytes':True,'initial_test_module_exactly_recoverable':True},
 'harness_corrections':['Return no unbound native Storage method from Playwright evaluate; the assignment itself remains the intended restoration.','Select the displayed30-day source in a reentrant opener instead of its hidden7-day duplicate.','Add one separate control for a newer feedback result inside the handoff history write before apply starts.'],
 'files':{path:meta((r/path).read_bytes()) for path in files},'captures':captures,
 'capture_policy':{'baseline_retained':len(baseline_keep),'corrected_baseline_total_generated':len(list((r/'feedback-lifetime-baseline-corrected/captures').glob('*.png'))),'all_final_captures_retained':len(list((r/'feedback-lifetime-verified/captures').glob('*.png')))},
 'limits':['Native historical/synthetic fixtures only; not hosted/public-route, market freshness, personal-data, cross-engine or new assistive-technology acceptance.',
 'The existing single status node, five-second timer, text, role and live markup remain. Timeout retains space within its task; explicit retirement cancels the timer and empties only its owned old message.',
 'A frozen Remove handoff may preserve or retire only its supplied witness. If a newer message replaced it before apply, that newer message is left alone.',
 'No extra route/history/store/notification owner, timer or replay is introduced. Model/alert/receipt/result/release/admission boundaries remain.']}
(r/'feedback-lifetime-publication-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'assets':source['assets'],'changed':len(source['changed']),'unchanged':len(source['unchanged']),'runs':{name:{state:list(run['cases'].values()).count(state) for state in ['passed','failed','error','skipped']} for name,run in runs.items()},'files':len(files),'captures':len(captures),'new_visual_captures':sum(c['new_visual_scope'] for c in captures)}))
