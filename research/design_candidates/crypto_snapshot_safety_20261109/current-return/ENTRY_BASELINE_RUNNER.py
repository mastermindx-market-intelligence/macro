from pathlib import Path
import os,subprocess,time,hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'current-return-entry-baseline';assert not phase.exists()
source=json.loads((r/'current-return-pre-entry-source-receipt.json').read_text())
for path,m in dict(source['changed'],**source['unchanged']).items():
 if path!='tests/test_crypto_intelligence_r4_browser.py':assert hashlib.sha256((r/path).read_bytes()).hexdigest()==m['sha256'],path
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text();addition=(r/'current-return-entry-test-addition.txt').read_text()
assert test.endswith(addition) and hashlib.sha256(test[:-len(addition)].encode()).hexdigest()==source['changed']['tests/test_crypto_intelligence_r4_browser.py']['sha256']
phase.mkdir();env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q','tests/test_crypto_intelligence_r4_browser.py::test_r4_new_current_review_entry_starts_at_its_own_beginning','--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':source['source_parent'],'runtime_asset_version':source['assets'],'test_sha256':hashlib.sha256(test.encode()).hexdigest()}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));print(p.stdout);print(p.stderr)
