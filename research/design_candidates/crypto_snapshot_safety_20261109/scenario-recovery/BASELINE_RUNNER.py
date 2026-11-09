from pathlib import Path
import os,subprocess,time,hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'scenario-recovery-baseline'
assert not phase.exists(),'Baseline directory already exists'
expected=json.loads((r/'scenario-recovery-parent-input.json').read_text())
for p,m in expected['files'].items():
 b=(r/p).read_bytes()
 if p=='tests/test_crypto_intelligence_r4_browser.py':
  assert hashlib.sha256(b).hexdigest()=="93ace94b0401a1bb2ea872cad16fc1adefa869c147812874dd31cab6c2c95a81"
 else:assert hashlib.sha256(b).hexdigest()==m['sha256'],p
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_missing_current_case_recovers_without_borrowing_review_context","tests/test_crypto_intelligence_r4_browser.py::test_r4_generic_and_valid_current_reviews_remain_distinct","tests/test_crypto_intelligence_r4_browser.py::test_r4_unusable_saved_version_never_borrows_current_context","tests/test_crypto_intelligence_r4_browser.py::test_r4_deep_link_and_older_snapshots_fail_open_with_honest_copy"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'test_sha256':"93ace94b0401a1bb2ea872cad16fc1adefa869c147812874dd31cab6c2c95a81"}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(p.stdout);print(p.stderr)
