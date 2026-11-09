from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm")
source=json.loads((r/'scenario-recovery-source-receipt.json').read_text());changes=json.loads((r/'scenario-recovery-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for p,m in {**source['changed'],**source['unchanged']}.items():assert meta((r/p).read_bytes())==m,p
inverse={}
for p,steps in changes['source'].items():
 text=(r/p).read_text()
 for step in reversed(steps):
  assert text.count(step['after'])==1
  text=text.replace(step['after'],step['before'])
 inverse[p]=text==(r/'scenario-recovery-parent'/p).read_text()
assert all(inverse.values())
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text();addition=changes['test_addition']
assert test.endswith(addition)
assert test[:-len(addition)]==(r/'scenario-recovery-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
runs={}
for name,wanted in [('scenario-recovery-baseline',(17,6)),('scenario-recovery-final',(17,0))]:
 cases=list(ET.parse(r/name/'junit.xml').getroot().iter('testcase'))
 failed=[n for n in cases if n.find('failure') is not None or n.find('error') is not None]
 assert (len(cases),len(failed))==wanted
 assert not any(n.find('skipped') is not None for n in cases)
 obs=json.loads((r/name/'observations.json').read_text())
 assert obs['contexts']==17 and obs['pages']==17
 assert not obs['page_errors'] and obs['blocked_external_requests']==0 and obs['blocked_websockets']==0
 runs[name]={'result':json.loads((r/name/'result.json').read_text()),'tests':len(cases),'failed':len(failed),'passed':len(cases)-len(failed),'observations':obs,'files':{p.name:meta(p.read_bytes()) for p in [r/name/f for f in ['result.json','stdout.txt','stderr.txt','junit.xml','observations.json']]}}
captures={}
for p in sorted((r/'scenario-recovery-final/captures').glob('*.png')):
 b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',b[16:24]);captures[p.name]={**meta(b),'width':w,'height':h}
assert len(captures)==4
result={'source':source,'product_inverse_exact':inverse,'browser_test_inverse_exact':True,'runs':runs,'captures':captures,'scope':'17 browser cases: six missing/malformed current-case recovery cases; four generic/valid review controls; six existing unusable-saved cases; one existing missing-current/legacy-saved path. No complete-suite claim.'}
(r/'scenario-recovery-publication-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'state':'qualified','changed':len(source['changed']),'unchanged':len(source['unchanged']),'assets':source['assets'],'runs':{k:{'tests':v['tests'],'failed':v['failed'],'contexts':v['observations']['contexts']} for k,v in runs.items()},'captures':len(captures)}))
