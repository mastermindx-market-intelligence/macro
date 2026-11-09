from pathlib import Path
import os,subprocess,time,hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'current-return-harness-final'
assert not phase.exists(),'Correction output already exists'
source=json.loads((r/'current-return-source-receipt.json').read_text());changes=json.loads((r/'current-return-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in dict(source['changed'],**source['unchanged']).items():
 if path!='tests/test_crypto_intelligence_r4_browser.py':assert meta((r/path).read_bytes())==m,path
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text();addition=changes['test_addition']
assert test.endswith(addition) and test[:-len(addition)]==(r/'current-return-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
original=test
for step in reversed(changes['test_corrections']):
 assert original.count(step['after'])==step['count'];original=original.replace(step['after'],step['before'])
assert hashlib.sha256(original.encode()).hexdigest()==source['changed']['tests/test_crypto_intelligence_r4_browser.py']['sha256']
(r/'current-return-initial-source-receipt.json').write_text(json.dumps(source,indent=2)+'\n')
source['changed']['tests/test_crypto_intelligence_r4_browser.py']=meta(test.encode())
source['test_injection_correction_inverse_exact']=True
(r/'current-return-source-receipt.json').write_text(json.dumps(source,indent=2)+'\n')
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q','tests/test_crypto_intelligence_r4_browser.py::test_r4_current_return_rejects_stale_reading_identity','--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':source['source_parent'],'runtime_asset_version':source['assets'],'test_inputs':source['changed']['tests/test_crypto_intelligence_r4_browser.py'],'runtime_unchanged_from_initial_candidate':True}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));print(p.stdout);print(p.stderr)
