from pathlib import Path
import os,subprocess,time,hashlib,json,sys
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'feedback-lifetime-verified';rendered=r/'feedback-lifetime-verified-rendered'
assert not phase.exists() and not rendered.exists(),'Candidate output already exists'
expected=json.loads((r/'feedback-lifetime-parent-input.json').read_text());changes=json.loads((r/'feedback-lifetime-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in expected['files'].items():
 if path not in ['templates/crypto_intelligence_r4.js','tests/test_crypto_intelligence_r4_browser.py']:assert meta((r/path).read_bytes())==m,path
inverse={}
for path,steps in changes['source'].items():
 text=(r/path).read_text()
 for step in reversed(steps):
  assert text.count(step['after'])==step['count'],(path,'inverse occurrence',step['label'])
  text=text.replace(step['after'],step['before'])
 inverse[path]=text==(r/'feedback-lifetime-parent'/path).read_text()
assert all(inverse.values()),inverse
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text();addition=changes['test_addition'];parent_test=(r/'feedback-lifetime-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
assert test==parent_test+addition
edge=changes['handoff_test_addition'];assert addition.endswith(edge);initial_addition=addition[:-len(edge)]
for fix in reversed(changes['harness_fixes']):
 assert initial_addition.count(fix['after'])==fix['count'];initial_addition=initial_addition.replace(fix['after'],fix['before'])
assert initial_addition==changes['initial_test_addition']
assert hashlib.sha256((parent_test+initial_addition).encode()).hexdigest()==json.loads((r/'feedback-lifetime-baseline/result.json').read_text())['test_sha256']
assert hashlib.sha256(test.encode()).hexdigest()==json.loads((r/'feedback-lifetime-baseline-corrected/result.json').read_text())['test_sha256']
sys.path.insert(0,str(r))
from scripts.build_crypto_intelligence_r4 import render_view
view=json.loads((r/'site/crypto_intelligence_r4.json').read_text());render_view(view,rendered)
version=hashlib.sha256(b''.join((r/'templates'/name).read_bytes() for name in ['crypto_intelligence_r4.html.j2','crypto_intelligence_r4.css','crypto_intelligence_r4.js'])).hexdigest()[:12]
html={}
for name in ['crypto-r4.html','vector-r4.html']:
 old=(r/'feedback-lifetime-parent/site'/name).read_text();new=(rendered/name).read_text();assert old.count(expected['assets'])==2
 html[name]=new==old.replace(expected['assets'],version);assert html[name],name
assert (rendered/'crypto_intelligence_r4.json').read_bytes()==(r/'site/crypto_intelligence_r4.json').read_bytes()
assert (rendered/'crypto_intelligence_r4.css').read_bytes()==(r/'site/crypto_intelligence_r4.css').read_bytes()
for name in ['crypto-r4.html','vector-r4.html','crypto_intelligence_r4.js']:(r/'site'/name).write_bytes((rendered/name).read_bytes())
assert (r/'templates/crypto_intelligence_r4.js').read_bytes()==(r/'site/crypto_intelligence_r4.js').read_bytes()
changed={};unchanged={}
for path,m in expected['files'].items():
 current=meta((r/path).read_bytes());(unchanged if current==m else changed)[path]=current
assert len(changed)==5 and len(unchanged)==16,(list(changed),list(unchanged))
source={'source_parent':expected['head'],'assets':version,'changed':changed,'unchanged':unchanged,'product_inverse_exact':inverse,'browser_test_inverse_exact':True,'initial_baseline_test_recovered_exact':True,'same_corrected_baseline_test_bytes':True,'harness_corrections_explicit':changes['harness_fixes'],'extra_handoff_control_added':True,'retained_html_except_two_asset_refs_exact':html,'retained_view_exact':True,'retained_css_exact':True,'served_js_exact':True}
(r/'feedback-lifetime-source-receipt.json').write_text(json.dumps(source,indent=2)+'\n')
phase.mkdir();env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'),MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR=str(phase/'captures'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_feedback_retires_on_task_navigation_and_does_not_return_with_back","tests/test_crypto_intelligence_r4_browser.py::test_r4_expired_feedback_space_retires_only_when_the_task_changes","tests/test_crypto_intelligence_r4_browser.py::test_r4_close_reopen_never_resurrects_transient_feedback","tests/test_crypto_intelligence_r4_browser.py::test_r4_locale_change_retires_old_feedback_and_preserves_the_reader","tests/test_crypto_intelligence_r4_browser.py::test_r4_frozen_remove_handoff_survives_but_explicit_retry_retires_it","tests/test_crypto_intelligence_r4_browser.py::test_r4_same_url_history_traversal_retires_feedback","tests/test_crypto_intelligence_r4_browser.py::test_r4_older_apply_does_not_retire_newer_feedback_from_its_preflight","tests/test_crypto_intelligence_r4_browser.py::test_r4_superseded_preflight_cannot_clear_its_newer_navigation_result","tests/test_crypto_intelligence_r4_browser.py::test_r4_completion_navigation_retires_feedback_without_a_late_reissue","tests/test_crypto_intelligence_r4_browser.py::test_r4_remove_feedback_handoff_cannot_follow_a_retargeted_history_write","tests/test_crypto_intelligence_r4_browser.py::test_r4_retired_deadline_cannot_hide_a_new_feedback_message","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_confirmed_mutation_preserves_the_reader","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_idempotent_mutation_keeps_reading_without_another_write","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_failed_mutation_does_not_rebuild_or_replay","tests/test_crypto_intelligence_r4_browser.py::test_r4_feedback_timeout_keeps_action_geometry_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_locale_preserves_disclosure_focus_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_saved_locale_keeps_disclosure_focus_and_reading_position","tests/test_crypto_intelligence_r4_browser.py::test_r4_newer_focus_during_confirmation_survives","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_uses_fresh_reading_when_history_persistence_fails","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_reading_persistence_yields_to_a_newer_choice","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_inside_a_render_focus_callback_retains_its_new_intent","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_review_returns_to_the_same_case_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_confirmed_remove_can_be_followed_by_an_unreadable_list","tests/test_crypto_intelligence_r4_browser.py::test_r4_saved_journey_restores_the_exact_outer_horizon","tests/test_crypto_intelligence_r4_browser.py::test_r4_saved_parent_focus_callback_keeps_its_new_destination","tests/test_crypto_intelligence_r4_browser.py::test_r4_newer_feedback_inside_handoff_history_write_survives_the_older_handoff"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();run=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(run.stdout);(phase/'stderr.txt').write_text(run.stderr)
result={'command':cmd,'exit_code':run.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'runtime_asset_version':version,'test_sha256':hashlib.sha256(test.encode()).hexdigest()}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'source':source,'result':result}));print(run.stdout[-15000:]);print(run.stderr[-3000:])
