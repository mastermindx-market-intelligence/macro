from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");source=json.loads((r/'route-context-source-receipt.json').read_text());changes=json.loads((r/'route-context-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for p,m in {**source['changed'],**source['unchanged']}.items():assert meta((r/p).read_bytes())==m,p
inverse={}
for p,steps in changes['source'].items():
 text=(r/p).read_text()
 for step in reversed(steps):
  assert text.count(step['after'])==1
  text=text.replace(step['after'],step['before'])
 inverse[p]=text==(r/'route-context-parent'/p).read_text()
assert all(inverse.values())
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text()
assert test.endswith(changes['test_addition'])
assert test[:-len(changes['test_addition'])]==(r/'route-context-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
runs={};identities={}
for name,wanted in [('route-context-baseline',(21,10,21,21)),('route-context-history-baseline',(2,2,2,2)),('route-context-final',(23,0,23,25))]:
 cases=list(ET.parse(r/name/'junit.xml').getroot().iter('testcase'));failures=[n for n in cases if n.find('failure') is not None or n.find('error') is not None]
 assert not any(n.find('skipped') is not None for n in cases)
 obs=json.loads((r/name/'observations.json').read_text())
 assert (len(cases),len(failures),obs['contexts'],obs['pages'])==wanted,(name,len(cases),len(failures),obs)
 assert not obs['page_errors'] and obs['blocked_external_requests']==0 and obs['blocked_websockets']==0
 identities[name]={(n.attrib.get('classname'),n.attrib['name']) for n in cases}
 runs[name]={'result':json.loads((r/name/'result.json').read_text()),'tests':len(cases),'failed':len(failures),'passed':len(cases)-len(failures),'observations':obs,'files':{f:meta((r/name/f).read_bytes()) for f in ['result.json','stdout.txt','stderr.txt','junit.xml','observations.json']}}
assert identities['route-context-baseline']|identities['route-context-history-baseline']==identities['route-context-final']
old={"scenario-recovery-memory-en-390.png":{"bytes":16968,"sha256":"9454c6c97044132c5d0d8d380b3295f1caa0ec20df022064e8e3762da76d9629","blob":"bf477db74ec17a8964ff3f8d11ee972becea78a0","width":390,"height":764},"scenario-recovery-memory-zh-320.png":{"bytes":15297,"sha256":"6d2105669347f8e1609e65ff21e11344bf82abd9ef33c51b83f61bf33336147d","blob":"7e99702a9b80dd60b69e056197c238ff59daea75","width":320,"height":764},"scenario-recovery-scenario-en-390.png":{"bytes":16968,"sha256":"9454c6c97044132c5d0d8d380b3295f1caa0ec20df022064e8e3762da76d9629","blob":"bf477db74ec17a8964ff3f8d11ee972becea78a0","width":390,"height":764},"scenario-recovery-scenario-zh-320.png":{"bytes":15297,"sha256":"6d2105669347f8e1609e65ff21e11344bf82abd9ef33c51b83f61bf33336147d","blob":"7e99702a9b80dd60b69e056197c238ff59daea75","width":320,"height":764}}
captures={}
for p in sorted((r/'route-context-final/captures').glob('*.png')):
 b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',b[16:24]);m={**meta(b),'width':w,'height':h}
 captures[p.name]={**m,'prior_capture_exact':m==old[p.name] if p.name in old else None}
assert len(captures)==6
result={'source':source,'product_inverse_exact':inverse,'browser_test_inverse_exact':True,'runs':runs,'baseline_case_union_matches_final':True,'captures':captures,'scope':'23 affected cases in one candidate run: native href/context/new-tab parity; in-section and persistent keyboard focus; six newer-choice callbacks; six consumed/modified click probes; existing horizon/drawer and six missing-case recovery paths. Native Meta-click opens two additional pages. No complete-suite claim.'}
(r/'route-context-publication-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'state':'qualified','assets':source['assets'],'changed':len(source['changed']),'unchanged':len(source['unchanged']),'candidate_tests':23,'contexts':23,'pages':25,'new_captures':[k for k,v in captures.items() if v['prior_capture_exact'] is None],'prior_captures_exact':{k:v['prior_capture_exact'] for k,v in captures.items() if v['prior_capture_exact'] is not None}}))
