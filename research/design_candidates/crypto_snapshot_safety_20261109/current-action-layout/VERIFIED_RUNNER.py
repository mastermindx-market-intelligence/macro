from pathlib import Path
import os,subprocess,time,hashlib,json,sys
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'current-action-layout-verified';rendered=r/'current-action-layout-verified-rendered'
assert not phase.exists() and not rendered.exists(),'Candidate output already exists'
expected=json.loads((r/'current-action-layout-parent-input.json').read_text());changes=json.loads((r/'current-action-layout-transforms.json').read_text());previous=json.loads((r/'current-action-layout-initial-source-receipt.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in dict(previous['changed'],**previous['unchanged']).items():
 if path not in ['tests/test_crypto_intelligence_r4_browser.py','templates/crypto_intelligence_r4.js']:assert meta((r/path).read_bytes())==m,path
inverse={}
for path,steps in changes['source'].items():
 text=(r/path).read_text()
 for step in reversed(steps):
  assert text.count(step['after'])==step['count'],(path,'inverse occurrence',step['label'])
  text=text.replace(step['after'],step['before'])
 inverse[path]=text==(r/'current-action-layout-parent'/path).read_text()
assert all(inverse.values()),inverse
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text();prior=test
for step in reversed(changes['existing_test_changes']):
 assert prior.count(step['after'])==step['count'];prior=prior.replace(step['after'],step['before'])
addition=changes['test_addition'];assert prior.endswith(addition) and prior[:-len(addition)]==(r/'current-action-layout-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
assert hashlib.sha256(prior.encode()).hexdigest()==json.loads((r/'current-action-layout-baseline/result.json').read_text())['test_sha256']
sys.path.insert(0,str(r))
from scripts.build_crypto_intelligence_r4 import render_view
view=json.loads((r/'site/crypto_intelligence_r4.json').read_text());render_view(view,rendered)
version=hashlib.sha256(b''.join((r/'templates'/name).read_bytes() for name in ['crypto_intelligence_r4.html.j2','crypto_intelligence_r4.css','crypto_intelligence_r4.js'])).hexdigest()[:12]
html={}
for name in ['crypto-r4.html','vector-r4.html']:
 text=(rendered/name).read_text();assert text.count(version)==2
 html[name]=text.replace(version,expected['assets'])==(r/'current-action-layout-parent/site'/name).read_text();assert html[name],name
assert (rendered/'crypto_intelligence_r4.json').read_bytes()==(r/'site/crypto_intelligence_r4.json').read_bytes()
for name in ['crypto_intelligence_r4.css','crypto_intelligence_r4.js']:assert (rendered/name).read_bytes()==(r/'templates'/name).read_bytes()
for name in ['crypto-r4.html','vector-r4.html','crypto_intelligence_r4.css','crypto_intelligence_r4.js']:(r/'site'/name).write_bytes((rendered/name).read_bytes())
changed={};unchanged={}
for path,m in expected['files'].items():
 current=meta((r/path).read_bytes());(unchanged if current==m else changed)[path]=current
assert len(changed)==7 and len(unchanged)==14,(list(changed),list(unchanged))
source={'source_parent':expected['head'],'assets':version,'changed':changed,'unchanged':unchanged,'product_inverse_exact':inverse,'browser_test_inverse_exact':True,'existing_failure_acceptance_change_explicit':changes['acceptance_rationale'],'baseline_test_recovered_exact':True,'initial_candidate_correction':changes['initial_candidate_correction'],'retained_html_except_two_asset_refs_exact':html,'retained_view_exact':True,'served_assets_exact':True}
(r/'current-action-layout-source-receipt.json').write_text(json.dumps(source,indent=2)+'\n')
phase.mkdir();env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'),MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR=str(phase/'captures'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_current_actions_wrap_with_separate_touch_targets","tests/test_crypto_intelligence_r4_browser.py::test_r4_disabled_current_save_is_distinct_and_inert","tests/test_crypto_intelligence_r4_browser.py::test_r4_mutation_feedback_never_covers_controls","tests/test_crypto_intelligence_r4_browser.py::test_r4_feedback_timeout_keeps_action_geometry_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_failure_feedback_does_not_scroll_when_it_already_fits","tests/test_crypto_intelligence_r4_browser.py::test_r4_saved_remove_failure_feedback_is_visible_without_rebuilding","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_confirmed_mutation_preserves_the_reader","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_idempotent_mutation_keeps_reading_without_another_write","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_failed_mutation_does_not_rebuild_or_replay","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_uses_fresh_reading_when_history_persistence_fails","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_reading_persistence_yields_to_a_newer_choice","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_expired_remove_heading_callback_keeps_its_new_destination","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_inside_a_render_focus_callback_retains_its_new_intent","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_yields_its_ui_when_storage_observes_a_new_history_entry","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_mutation_with_unqualified_reading_still_reconciles_controls","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_review_returns_to_the_same_case_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_locale_preserves_disclosure_focus_and_reading","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_scenario_retains_its_existing_reading_order","tests/test_crypto_intelligence_r4_browser.py::test_r4_newer_focus_during_confirmation_survives","tests/test_crypto_intelligence_r4_browser.py::test_r4_completion_focus_callbacks_keep_their_new_panel","tests/test_crypto_intelligence_r4_browser.py::test_r4_programmatic_save_preserves_unrelated_focus_and_stale_save_stays_safe","tests/test_crypto_intelligence_r4_browser.py::test_r4_snapshot_buttons_keep_their_visible_intent_across_tabs","tests/test_crypto_intelligence_r4_browser.py::test_r4_confirmed_remove_can_be_followed_by_an_unreadable_list","tests/test_crypto_intelligence_r4_browser.py::test_r4_frozen_remove_keeps_semantic_focus_across_locale","tests/test_crypto_intelligence_r4_browser.py::test_r4_saved_locale_keeps_disclosure_focus_and_reading_position","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_return_survives_unreadable_saved_storage"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'runtime_asset_version':version,'candidate_inputs':changed}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['command','candidate_inputs']}));print(p.stdout[-10500:]);print(p.stderr)
