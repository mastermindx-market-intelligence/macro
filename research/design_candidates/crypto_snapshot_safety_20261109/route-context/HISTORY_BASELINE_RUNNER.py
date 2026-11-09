from pathlib import Path
import os,subprocess,time,hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'route-context-history-baseline'
assert not phase.exists(),'Baseline already exists'
expected=json.loads((r/'route-context-parent-input.json').read_text())
for p,m in expected['files'].items():
 b=(r/p).read_bytes();sha="29c022d2c6f83d98adb7d013856047bd2c628f858a9543a3676653ce82038265" if p=='tests/test_crypto_intelligence_r4_browser.py' else m['sha256']
 assert hashlib.sha256(b).hexdigest()==sha,p
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_route_focus_handoff_yields_to_a_newer_choice[replace]","tests/test_crypto_intelligence_r4_browser.py::test_r4_route_focus_handoff_yields_to_a_newer_choice[push]"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'test_sha256':"29c022d2c6f83d98adb7d013856047bd2c628f858a9543a3676653ce82038265"}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(p.stdout);print(p.stderr)
