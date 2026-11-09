from pathlib import Path
import os,subprocess,time,hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'route-context-baseline'
assert not phase.exists(),'Baseline already exists'
expected=json.loads((r/'route-context-parent-input.json').read_text())
for p,m in expected['files'].items():
 b=(r/p).read_bytes();sha="6bedde77dc7b3ca68413fe49525db47a73d8084ce2a0e8652fb0aac65f352f02" if p=='tests/test_crypto_intelligence_r4_browser.py' else m['sha256']
 assert hashlib.sha256(b).hexdigest()==sha,p
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_native_route_destinations_match_ordinary_context","tests/test_crypto_intelligence_r4_browser.py::test_r4_in_section_keyboard_route_keeps_a_visible_focus_owner","tests/test_crypto_intelligence_r4_browser.py::test_r4_route_focus_handoff_yields_to_a_newer_choice","tests/test_crypto_intelligence_r4_browser.py::test_r4_consumed_or_modified_route_click_is_not_replayed_by_app","tests/test_crypto_intelligence_r4_browser.py::test_r4_horizon_deep_link_drawer_history_and_chart_window","tests/test_crypto_intelligence_r4_browser.py::test_r4_missing_current_case_recovers_without_borrowing_review_context"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'test_sha256':"6bedde77dc7b3ca68413fe49525db47a73d8084ce2a0e8652fb0aac65f352f02"}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(p.stdout);print(p.stderr)
