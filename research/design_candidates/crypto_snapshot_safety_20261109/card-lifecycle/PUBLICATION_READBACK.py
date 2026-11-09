from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm")
source=json.loads((r/'card-lifecycle-source-receipt-final.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in {**source['changed'],**source['unchanged']}.items():assert meta((r/path).read_bytes())==m,path
assert len(source['changed'])==8 and len(source['unchanged'])==13
runs={};identities={};failures={}
for name,wanted in [('card-lifecycle-baseline',(45,40,45,45)),('card-lifecycle-final',(45,5,45,45)),('card-lifecycle-harness-final',(5,0,5,5))]:
 cases=list(ET.parse(r/name/'junit.xml').getroot().iter('testcase'))
 failed=[node for node in cases if node.find('failure') is not None or node.find('error') is not None]
 assert not any(node.find('skipped') is not None for node in cases)
 obs=json.loads((r/name/'observations.json').read_text())
 assert (len(cases),len(failed),obs['contexts'],obs['pages'])==wanted,(name,len(cases),len(failed),obs)
 assert not obs['page_errors'] and obs['blocked_external_requests']==0 and obs['blocked_websockets']==0
 identities[name]={(node.attrib.get('classname'),node.attrib['name']) for node in cases}
 failures[name]={(node.attrib.get('classname'),node.attrib['name']) for node in failed}
 runs[name]={'result':json.loads((r/name/'result.json').read_text()),'tests':len(cases),'failed':len(failed),
 'passed':len(cases)-len(failed),'observations':obs,
 'failed_cases':[{'name':node.attrib['name'],'type':(node.find('failure') if node.find('failure') is not None else node.find('error')).attrib.get('type'),
 'message':(node.find('failure') if node.find('failure') is not None else node.find('error')).attrib.get('message')} for node in failed],
 'files':{f:meta((r/name/f).read_bytes()) for f in ['result.json','stdout.txt','stderr.txt','junit.xml','observations.json']}}
assert identities['card-lifecycle-baseline']==identities['card-lifecycle-final']
assert failures['card-lifecycle-final']==identities['card-lifecycle-harness-final']
assert len((identities['card-lifecycle-final']-failures['card-lifecycle-final'])|identities['card-lifecycle-harness-final'])==45
captures={};all_captures={}
for folder in ['card-lifecycle-final','card-lifecycle-harness-final']:
 for path in sorted((r/folder/'captures').glob('*.png')):
  b=path.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n'
  w,h=struct.unpack('>II',b[16:24]);record={**meta(b),'width':w,'height':h,'native_path':str(path)}
  all_captures[str(path.relative_to(r))]=record
  if path.name in captures:record['prior_capture_exact']=captures[path.name]['sha256']==record['sha256']
  captures[path.name]=record
assert len(captures)==6,(len(captures),list(captures))
result={'source':source,'runs':runs,'baseline_and_candidate_case_identity_exact':True,
 'correction_cases_exactly_initial_failures':True,'unique_affected_passing_cases':45,
 'verification_scope':'40 initial candidate passes plus five corrected affected passes; not a single 45-pass run. Runtime unchanged during correction.',
 'captures':captures,'all_native_captures':all_captures,
 'parent_snapshot':json.loads((r/'card-lifecycle-parent-receipt.json').read_text())}
out=r/'card-lifecycle-publication-receipt.json';assert not out.exists(),'Publication receipt already exists'
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'changed':len(source['changed']),'unchanged':len(source['unchanged']),'assets':source['assets'],
 'runs':{k:{'tests':v['tests'],'failed':v['failed'],'passed':v['passed']} for k,v in runs.items()},
 'captures':{k:{'bytes':v['bytes'],'width':v['width'],'height':v['height'],'prior_capture_exact':v.get('prior_capture_exact')} for k,v in captures.items()},
 'unique_affected_passing_cases':45}))
