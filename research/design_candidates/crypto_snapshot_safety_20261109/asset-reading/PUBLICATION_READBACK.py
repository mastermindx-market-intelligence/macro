from pathlib import Path
import hashlib,json,struct,xml.etree.ElementTree as ET
r=Path('/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm');source=json.loads((r/'asset-reading-source-receipt.json').read_text());changes=json.loads((r/'asset-reading-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for p,m in {**source['changed'],**source['unchanged']}.items():assert meta((r/p).read_bytes())==m,p
inverse={}
for p,steps in changes['source'].items():
 s=(r/p).read_text()
 for step in reversed(steps):
  assert s.count(step['after'])==1
  s=s.replace(step['after'],step['before'])
 inverse[p]=s==(r/'asset-reading-parent'/p).read_text()
assert all(inverse.values())
s=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text();t=changes['tests'];assert s.endswith(t['addition']);s=s[:-len(t['addition'])]
for key in ('hierarchy','fixture'):
 assert s.count(t[key]['after'])==1;s=s.replace(t[key]['after'],t[key]['before'])
assert s==(r/'asset-reading-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
runs={}
for phase,expected in [('asset-reading-baseline',(21,6)),('asset-reading-final',(21,0))]:
 tests=list(ET.parse(r/phase/'junit.xml').getroot().iter('testcase'));failed=[n for n in tests if n.find('failure') is not None or n.find('error') is not None]
 assert (len(tests),len(failed))==expected
 obs=json.loads((r/phase/'observations.json').read_text());assert obs['contexts']==6 and obs['pages']==6 and not obs['page_errors'] and obs['blocked_external_requests']==0 and obs['blocked_websockets']==0
 runs[phase]={'result':json.loads((r/phase/'result.json').read_text()),'tests':len(tests),'failed':len(failed),'passed':len(tests)-len(failed),'observations':obs,'files':{n:meta((r/phase/n).read_bytes()) for n in ('result.json','stdout.txt','stderr.txt','junit.xml','observations.json')}}
captures={}
for p in sorted((r/'asset-reading-final/captures').glob('*.png')):
 b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',b[16:24]);captures[p.name]={**meta(b),'width':w,'height':h}
assert len(captures)==8
receipt={'source':source,'product_inverses_exact':inverse,'browser_test_inverse_exact':True,'runs':runs,'captures':captures,'scope':'21 affected cases:15 unchanged server-price cases +6 browser cases. Existing quote cases add hierarchy checks; two new identity journeys preserve data/search/routes/returns/comparison and ordinary coverage formatting. No complete-suite claim.'}
out=r/'asset-reading-publication-receipt.json';assert not out.exists();out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'source_paths':len(source['changed']),'unchanged_inputs':len(source['unchanged']),'inverses':inverse,'test_inverse':True,'passing':runs['asset-reading-final']['passed'],'captures':captures}))
