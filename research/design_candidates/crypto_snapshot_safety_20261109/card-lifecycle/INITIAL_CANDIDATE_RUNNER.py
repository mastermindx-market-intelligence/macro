from pathlib import Path
import os,subprocess,time,hashlib,json,sys,re
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'card-lifecycle-final';rendered=r/'card-lifecycle-rendered'
assert not phase.exists() and not rendered.exists(),'Candidate output already exists'
expected=json.loads((r/'card-lifecycle-parent-input.json').read_text())
candidate=json.loads((r/'card-lifecycle-candidate-input.json').read_text())
changes=json.loads((r/'card-lifecycle-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in expected['files'].items():assert meta((r/path).read_bytes())==candidate.get(path,m),path
inverse={}
for path,steps in changes['source'].items():
 text=(r/path).read_text()
 for step in reversed(steps):
  assert text.count(step['after'])==1,(path,'inverse occurrence')
  text=text.replace(step['after'],step['before'])
 inverse[path]=text==(r/'card-lifecycle-parent'/path).read_text()
assert all(inverse.values()),inverse
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text()
assert test.endswith(changes['test_addition'])
assert test[:-len(changes['test_addition'])]==(r/'card-lifecycle-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
sys.path.insert(0,str(r))
from scripts.build_crypto_intelligence_r4 import render_view
view=json.loads((r/'site/crypto_intelligence_r4.json').read_text());render_view(view,rendered)
version=hashlib.sha256(b''.join((r/'templates'/name).read_bytes() for name in ['crypto_intelligence_r4.html.j2','crypto_intelligence_r4.css','crypto_intelligence_r4.js'])).hexdigest()[:12]
card=re.compile(r'<button class="cri-path"[^>]*>.*?</button>|<article class="cri-panel cri-case"[^>]*>.*?</article>',re.S)
outside={};identities={};leading={}
for name in ['crypto-r4.html','vector-r4.html']:
 text=(rendered/name).read_text();before=(r/'site'/name).read_text()
 old=card.findall(before);new=card.findall(text)
 assert len(old)==len(new)==14,(name,len(old),len(new))
 identity=lambda blocks:[re.findall(r'data-open="scenario:([^"]+)"',block) for block in blocks]
 assert identity(old)==identity(new),(name,'case identity/order')
 assert text.count(version)==2
 left=card.sub('<scenario-card/>',text.replace(version,expected['assets'])).lstrip('\n')
 right=card.sub('<scenario-card/>',before).lstrip('\n')
 outside[name]=left==right;assert outside[name],name
 identities[name]=identity(new)
 leading[name]={'before':len(before)-len(before.lstrip('\n')),'after':len(text)-len(text.lstrip('\n'))}
assert (rendered/'crypto_intelligence_r4.json').read_bytes()==(r/'site/crypto_intelligence_r4.json').read_bytes()
for name in ['crypto_intelligence_r4.css','crypto_intelligence_r4.js']:
 assert (rendered/name).read_bytes()==(r/'templates'/name).read_bytes()
for name in ['crypto-r4.html','vector-r4.html','crypto_intelligence_r4.js','crypto_intelligence_r4.css']:
 (r/'site'/name).write_bytes((rendered/name).read_bytes())
changed={};unchanged={}
for path,m in expected['files'].items():
 current=meta((r/path).read_bytes());(unchanged if current==m else changed)[path]=current
source={'source_parent':expected['head'],'runtime_parent':expected['runtime_checkpoint'],'assets':version,
 'changed':changed,'unchanged':unchanged,'product_inverse_exact':inverse,'browser_test_inverse_exact':True,
 'retained_page_outside_14_cards_exact':outside,'case_identity_order':identities,
 'leading_template_newlines':leading,'retained_view_exact':True,'served_assets_exact':True}
(r/'card-lifecycle-source-receipt.json').write_text(json.dumps(source,indent=2)+'\n')
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'),MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR=str(phase/'captures'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_card_expiry_uses_the_complete_utc_expiry_day","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_instances_keep_their_own_horizon_and_readable_layout","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_unqualified_dates_keep_recorded_instructions","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_supplied_text_and_evidence_are_qualified_independently","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_static_reading_is_time_neutral_and_typed","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_refresh_keeps_focus_and_inspects_the_original_case","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_empty_input_preserves_the_existing_empty_branch","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_scenario_retains_its_existing_reading_order","tests/test_crypto_intelligence_r4_browser.py::test_r4_frozen_expiry_is_distinct_from_original_progress"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),
 'source_parent':expected['head'],'runtime_asset_version':version,'candidate_inputs':candidate}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(p.stdout);print(p.stderr)
