from pathlib import Path
import os,subprocess,time,hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'card-lifecycle-harness-final'
assert not phase.exists(),'Correction output already exists'
source=json.loads((r/'card-lifecycle-source-receipt.json').read_text())
candidate=json.loads((r/'card-lifecycle-corrected-input.json').read_text())
changes=json.loads((r/'card-lifecycle-corrected-transforms.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in {**source['changed'],**source['unchanged']}.items():
 assert meta((r/path).read_bytes())==(candidate[path] if path=='tests/test_crypto_intelligence_r4_browser.py' else m),path
test=(r/'tests/test_crypto_intelligence_r4_browser.py').read_text()
assert test.endswith(changes['test_addition'])
assert test[:-len(changes['test_addition'])]==(r/'card-lifecycle-parent/tests/test_crypto_intelligence_r4_browser.py').read_text()
initial=changes['test_addition']
for step in reversed(changes['harness_corrections']):
 assert initial.count(step['after'])==1
 initial=initial.replace(step['after'],step['before'])
assert initial==changes['initial_test_addition']
source['changed']['tests/test_crypto_intelligence_r4_browser.py']=candidate['tests/test_crypto_intelligence_r4_browser.py']
source['runtime_unchanged_after_initial_candidate']=True
source['test_harness_correction_inverse_exact']=True
(r/'card-lifecycle-source-receipt-final.json').write_text(json.dumps(source,indent=2)+'\n')
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'),MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR=str(phase/'captures'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_card_instances_keep_their_own_horizon_and_readable_layout[en-390]","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_unqualified_dates_keep_recorded_instructions[missing-expiry-zh-320]","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_unqualified_dates_keep_recorded_instructions[future-en-390]","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_static_reading_is_time_neutral_and_typed[retained-en-390]","tests/test_crypto_intelligence_r4_browser.py::test_r4_card_static_reading_is_time_neutral_and_typed[progress-object-en-390]"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':source['source_parent'],
 'runtime_asset_version':source['assets'],'runtime_unchanged':True,'test_sha256':candidate['tests/test_crypto_intelligence_r4_browser.py']['sha256']}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(p.stdout);print(p.stderr)
