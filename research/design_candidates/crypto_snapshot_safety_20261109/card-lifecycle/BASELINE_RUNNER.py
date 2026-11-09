from pathlib import Path
import os,subprocess,time,hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'card-lifecycle-baseline'
assert not phase.exists(),'Baseline already exists'
expected=json.loads((r/'card-lifecycle-parent-input.json').read_text())
for path,m in expected['files'].items():
 b=(r/path).read_bytes();sha="5f274464ff6e3bb91a8a18ce903f6939f22c38ede63f74141df788edb96a1608" if path=='tests/test_crypto_intelligence_r4_browser.py' else m['sha256']
 assert hashlib.sha256(b).hexdigest()==sha,path
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_card_expiry_uses_the_complete_utc_expiry_day","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_instances_keep_their_own_horizon_and_readable_layout","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_unqualified_dates_keep_recorded_instructions","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_supplied_text_and_evidence_are_qualified_independently","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_static_reading_is_time_neutral_and_typed","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_refresh_keeps_focus_and_inspects_the_original_case","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_empty_input_preserves_the_existing_empty_branch","tests/test_crypto_intelligence_r4_browser.py::test_r4_current_scenario_retains_its_existing_reading_order","tests/test_crypto_intelligence_r4_browser.py::test_r4_frozen_expiry_is_distinct_from_original_progress"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'test_sha256':"5f274464ff6e3bb91a8a18ce903f6939f22c38ede63f74141df788edb96a1608"}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(p.stdout);print(p.stderr)
