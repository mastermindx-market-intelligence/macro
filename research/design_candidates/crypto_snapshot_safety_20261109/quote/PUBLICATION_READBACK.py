from pathlib import Path
import ast,hashlib,json,re,struct,xml.etree.ElementTree as ET
r=Path('/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm')
spec=json.loads((r/'quote-clarity-publication-input.json').read_text())
parent=json.loads((r/'quote-clarity-parent-manifest.json').read_text())
def meta(b):
 return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
changed={};unchanged={}
for p,m in parent['files'].items():
 actual=meta((r/p).read_bytes());expected=spec['changed'].get(p,m)
 assert actual==expected,(p,actual,expected)
 (changed if p in spec['changed'] else unchanged)[p]=actual
assert len(changed)==9 and len(unchanged)==12
inverses={}
for p,changes in spec['source_transforms'].items():
 text=(r/p).read_text()
 for step in reversed(changes):
  assert text.count(step['after'])==1,p
  text=text.replace(step['after'],step['before'])
 inverses[p]=text==(r/'quote-clarity-parent'/p).read_text()
assert all(inverses.values())
t=spec['test_transforms']
text=(r/'tests/test_crypto_intelligence_r4.py').read_text()
for addition in (t['context_addition'],t['contract_addition']):
 assert text.endswith(addition)
 text=text[:-len(addition)]
assert text.count(t['contract_import']['after'])==1
text=text.replace(t['contract_import']['after'],t['contract_import']['before'])
contract_inverse=text==(r/'quote-clarity-parent/tests/test_crypto_intelligence_r4.py').read_text()
text=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text()
assert text.endswith(t['browser_addition'])
text=text[:-len(t['browser_addition'])]
assert text.count(t['browser_fixture']['after'])==1
text=text.replace(t['browser_fixture']['after'],t['browser_fixture']['before'])
browser_inverse=text==(r/'quote-clarity-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
assert contract_inverse and browser_inverse
def money_ast(p):
 return ast.dump(next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='money'),include_attributes=False)
assert money_ast(r/'scripts/build_crypto_intelligence_r4.py')==money_ast(r/'quote-clarity-parent/scripts/build_crypto_intelligence_r4.py')
for name in ('crypto-r4.html','vector-r4.html'):
 a=(r/'site'/name).read_text();b=(r/'quote-clarity-parent/site'/name).read_text()
 assert a.count(spec['assets'])==2 and a.replace(spec['assets'],parent['runtime_version'])==b
assert (r/'site/crypto_intelligence_r4.js').read_bytes()==(r/'templates/crypto_intelligence_r4.js').read_bytes()
version=hashlib.sha256(b''.join((r/'templates'/n).read_bytes() for n in ('crypto_intelligence_r4.html.j2','crypto_intelligence_r4.css','crypto_intelligence_r4.js'))).hexdigest()[:12]
assert version==spec['assets']
runs={};passing=set()
for phase,expected in [('quote-clarity-baseline',(37,18)),('quote-clarity-final',(108,0)),('quote-clarity-context-baseline',(2,2)),('quote-clarity-context-final',(17,0))]:
 suite=ET.parse(r/phase/'junit.xml').getroot();cases=list(suite.iter('testcase'));failures=[n for n in cases if n.find('failure') is not None or n.find('error') is not None]
 assert (len(cases),len(failures))==expected,(phase,len(cases),len(failures))
 if phase.endswith('final'):
  passing.update((n.attrib.get('classname'),n.attrib['name']) for n in cases if n not in failures)
 runs[phase]={'result':json.loads((r/phase/'result.json').read_text()),'tests':len(cases),'failed':len(failures),'passed':len(cases)-len(failures),'proof_files':{n:meta((r/phase/n).read_bytes()) for n in ('result.json','stdout.txt','stderr.txt','junit.xml')}}
assert len(passing)==110
observations=json.loads((r/'quote-clarity-final/observations.json').read_text())
assert observations['contexts']==8 and observations['pages']==8 and not observations['page_errors'] and observations['blocked_external_requests']==0 and observations['blocked_websockets']==0
captures={}
for p in sorted((r/'quote-clarity-final/captures').glob('*.png')):
 b=p.read_bytes();assert b[:8]==b'\x89PNG\r\n\x1a\n';w,h=struct.unpack('>II',b[16:24]);captures[p.name]={**meta(b),'width':w,'height':h}
assert len(captures)==6
receipt={'source_parent':spec['parent'],'runtime_asset_version':version,'source':{'changed':changed,'unchanged':unchanged,'product_inverse_exact':inverses,'contract_test_inverse_exact':contract_inverse,'browser_test_inverse_exact':browser_inverse,'generic_money_ast_exact':True,'retained_pages_only_two_asset_version_references_changed':True,'retained_view_and_css_exact':True,'served_js_exact':True},'runs':runs,'unique_passing_cases':110,'passing_scope':'102 contract + 8 browser across initial108 and focused17; 15 overlap. Frontend unchanged by Decimal-context refinement; not a complete browser-suite rerun.','observations':observations,'captures':captures}
out=r/'quote-clarity-publication-receipt.json';assert not out.exists();out.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'changed':len(changed),'unchanged':len(unchanged),'inverses':inverses,'test_inverses':[contract_inverse,browser_inverse],'unique_passing':len(passing),'captures':captures,'receipt':str(out)}))
