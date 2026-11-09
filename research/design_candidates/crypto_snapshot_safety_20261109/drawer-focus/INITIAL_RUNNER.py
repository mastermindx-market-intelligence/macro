from pathlib import Path
import os,subprocess,time,hashlib,json,sys
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'drawer-focus-verified';rendered=r/'drawer-focus-verified-rendered'
assert not phase.exists() and not rendered.exists(),'Candidate output already exists'
expected=json.loads((r/'drawer-focus-parent-input.json').read_text());changes=json.loads((r/'drawer-focus-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in expected['files'].items():
 if path not in ['templates/crypto_intelligence_r4.js','templates/crypto_intelligence_r4.css','tests/test_crypto_intelligence_r4_browser.py']:assert meta((r/path).read_bytes())==m,path
inverse={}
for path,steps in changes['source'].items():
 text=(r/path).read_text()
 for step in reversed(steps):
  assert text.count(step['after'])==step['count'],(path,'inverse occurrence',step['label'])
  text=text.replace(step['after'],step['before'])
 inverse[path]=text==(r/'drawer-focus-parent'/path).read_text()
assert all(inverse.values()),inverse
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text();addition=changes['test_addition']
assert test.endswith(addition) and test[:-len(addition)]==(r/'drawer-focus-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
assert hashlib.sha256(test.encode()).hexdigest()==json.loads((r/'drawer-focus-baseline/result.json').read_text())['test_sha256']
sys.path.insert(0,str(r))
from scripts.build_crypto_intelligence_r4 import render_view
view=json.loads((r/'site/crypto_intelligence_r4.json').read_text());render_view(view,rendered)
version=hashlib.sha256(b''.join((r/'templates'/name).read_bytes() for name in ['crypto_intelligence_r4.html.j2','crypto_intelligence_r4.css','crypto_intelligence_r4.js'])).hexdigest()[:12]
html={}
for name in ['crypto-r4.html','vector-r4.html']:
 old=(r/'drawer-focus-parent/site'/name).read_text();new=(rendered/name).read_text()
 assert old.count(expected['assets'])==2
 html[name]=new==old.replace(expected['assets'],version);assert html[name],name
assert (rendered/'crypto_intelligence_r4.json').read_bytes()==(r/'site/crypto_intelligence_r4.json').read_bytes()
for name in ['crypto-r4.html','vector-r4.html','crypto_intelligence_r4.js','crypto_intelligence_r4.css']:(r/'site'/name).write_bytes((rendered/name).read_bytes())
assert (r/'templates/crypto_intelligence_r4.js').read_bytes()==(r/'site/crypto_intelligence_r4.js').read_bytes()
assert (r/'templates/crypto_intelligence_r4.css').read_bytes()==(r/'site/crypto_intelligence_r4.css').read_bytes()
changed={};unchanged={}
for path,m in expected['files'].items():
 current=meta((r/path).read_bytes());(unchanged if current==m else changed)[path]=current
assert len(changed)==7 and len(unchanged)==14,(list(changed),list(unchanged))
source={'source_parent':expected['head'],'assets':version,'changed':changed,'unchanged':unchanged,'product_inverse_exact':inverse,'browser_test_inverse_exact':True,'same_baseline_test_bytes':True,'retained_html_except_two_asset_refs_exact':html,'retained_view_exact':True,'served_assets_exact':True}
(r/'drawer-focus-source-receipt.json').write_text(json.dumps(source,indent=2)+'\n')
phase.mkdir();env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'),MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR=str(phase/'captures'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_keyboard_current_action_ring_clears_drawer_edge","tests/test_crypto_intelligence_r4_browser.py::test_r4_reverse_tab_reveals_current_summary_below_sticky_header","tests/test_crypto_intelligence_r4_browser.py::test_r4_reverse_tab_respects_wrapped_saved_header_after_resize","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_actions_wrap_with_separate_touch_targets","tests/test_crypto_intelligence_r4_browser.py::test_r4_disabled_current_save_is_distinct_and_inert","tests/test_crypto_intelligence_r4_browser.py::test_r4_feedback_timeout_keeps_action_geometry_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_confirmed_mutation_preserves_the_reader","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_failed_mutation_does_not_rebuild_or_replay","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_uses_fresh_reading_when_history_persistence_fails","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_reading_persistence_yields_to_a_newer_choice","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_review_returns_to_the_same_case_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_locale_preserves_disclosure_focus_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_saved_locale_keeps_disclosure_focus_and_reading_position","tests/test_crypto_intelligence_r4_browser.py::test_r4_newer_focus_during_confirmation_survives","tests/test_crypto_intelligence_r4_browser.py::test_r4_completion_focus_callbacks_keep_their_new_panel","tests/test_crypto_intelligence_r4_browser.py::test_r4_programmatic_save_preserves_unrelated_focus_and_stale_save_stays_safe"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();run=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(run.stdout);(phase/'stderr.txt').write_text(run.stderr)
result={'command':cmd,'exit_code':run.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'runtime_asset_version':version,'test_sha256':hashlib.sha256(test.encode()).hexdigest()}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'source':source,'result':result}));print(run.stdout[-15000:]);print(run.stderr[-3000:])
