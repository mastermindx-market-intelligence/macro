from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
from PIL import Image
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm")
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
source=json.loads((r/'drawer-focus-source-receipt.json').read_text())
for path,m in dict(source['changed'],**source['unchanged']).items():assert meta((r/path).read_bytes())==m,path
runs={}
for name in ['drawer-focus-baseline','drawer-focus-verified','drawer-focus-final']:
 phase=r/name;cases={}
 for x in ET.parse(phase/'junit.xml').getroot().iter('testcase'):
  key=x.attrib.get('classname','')+'::'+x.attrib['name'];assert key not in cases,key
  cases[key]='failed' if x.find('failure') is not None else 'error' if x.find('error') is not None else 'skipped' if x.find('skipped') is not None else 'passed'
 runs[name]={'result':json.loads((phase/'result.json').read_text()),'observations':json.loads((phase/'observations.json').read_text()),'cases':cases}
final=runs['drawer-focus-final'];baseline=runs['drawer-focus-baseline']
assert len(final['cases'])==48 and set(final['cases'].values())=={'passed'},final['cases']
assert set(final['cases'])==set(baseline['cases'])
assert all(set(run['cases'])==set(final['cases']) and run['result']['test_sha256']==final['result']['test_sha256'] for run in runs.values())
before={x['label']:x for x in baseline['observations']['drawer_focus']}
after={x['label']:x for x in final['observations']['drawer_focus']}
assert set(before)==set(after) and len(after)==22
layout={label:all(before[label][k]==after[label][k] for k in ['layout','bodyHeight','scrollHeight','headerHeight']) for label in after}
assert all(layout.values()),layout
files=['drawer-focus-parent-input.json','drawer-focus-parent-receipt.json','drawer-focus-parent-snapshot.py','drawer-focus-source-receipt.json','drawer-focus-transforms.json','drawer-focus-test-addition.txt','drawer-focus-baseline.py','drawer-focus-verified.py','drawer-focus-publication-readback.py','drawer-focus-initial-source-receipt.json','drawer-focus-initial-transforms.json','drawer-focus-final.py']
for name in runs:
 files += [name+'/'+f for f in ['result.json','observations.json','stdout.txt','stderr.txt','junit.xml']]
captured=[]
baseline_keep=['drawer-focus-actions-en-390-expired.png','drawer-focus-current-reverse-en-390.png','drawer-focus-saved-resize-zh-320.png']
for name in runs:
 capture_dir=r/name/'captures'
 paths=sorted(capture_dir.glob('*.png')) if name=='drawer-focus-final' else [capture_dir/x for x in baseline_keep] if name=='drawer-focus-baseline' else [capture_dir/'drawer-focus-actions-en-390-expired.png']
 for path in paths:
  assert path.exists(),path
  with Image.open(path) as image:w,h=image.size
  captured.append({'name':path.name,'path':str(path.relative_to(r)),'run':name,
   'new_visual_scope':name=='drawer-focus-baseline' or name=='drawer-focus-final' and path.name.startswith('drawer-focus-'),
   'role':'Before correction' if name=='drawer-focus-baseline' else 'Initial native rounding diagnostic' if name=='drawer-focus-verified' else 'New keyboard focus proof' if path.name.startswith('drawer-focus-') else 'Retained affected regression',
   **meta(path.read_bytes()),'width':w,'height':h})
receipt={'source':source,'runs':runs,'case_set_checks':{'same_48_case_ids':True,'identical_baseline_final_test_bytes':True,'added_cases':11,'retained_cases':37,'same_all_three_case_ids_and_test_bytes':True},
 'initial_rounding_correction':{'initial_assets':'3de80c670379','initial_passed':47,'initial_failed':1,'observed_en390_clearance':7.84375,'final_requested_scroll_padding':9,'minimum_actual_clearance':8,'test_assertions_unchanged':True},'layout_conservation':layout,'files':{path:meta((r/path).read_bytes()) for path in files},'captures':captured,
 'capture_policy':{'baseline_retained':len(baseline_keep),'baseline_total_generated':len(list((r/'drawer-focus-baseline/captures').glob('*.png'))),'initial_retained':1,'initial_total_generated':len(list((r/'drawer-focus-verified/captures').glob('*.png'))),'all_final_captures_retained':len(list((r/'drawer-focus-final/captures').glob('*.png')))},
 'limits':['Native historical/synthetic fixtures, one Chrome version; not a cross-engine, assistive-technology, hosted or public-route acceptance.',
 'Focus changes remain native. The ResizeObserver only publishes the actual header height as a CSS metric; no focus/scroll/render/history/storage operation is added.',
 'Explicit preventScroll restoration retains reading. Scroll padding changes the preferred viewing region, not content dimensions or blank layout space.',
 'Current Conditions summary retains its native outline; existing action/saved-disclosure 2px+4px rings are unchanged.',
 'Other denied/uncertain and model/alert/result/receipt/release/admission boundaries remain.']}
(r/'drawer-focus-publication-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'assets':source['assets'],'changed':len(source['changed']),'unchanged':len(source['unchanged']),'runs':{name:{state:list(run['cases'].values()).count(state) for state in ['passed','failed','error','skipped']} for name,run in runs.items()},'files':len(files),'captures':len(captured),'new_visual_captures':sum(c['new_visual_scope'] for c in captured),'layout_samples_exact':len(layout)}))
