from pathlib import Path
import os,subprocess,time,hashlib,json,sys
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");phase=r/'scenario-recovery-final';rendered=r/'scenario-recovery-rendered'
assert not phase.exists() and not rendered.exists(),'Candidate output already exists'
expected=json.loads((r/'scenario-recovery-parent-input.json').read_text());candidate=json.loads((r/'scenario-recovery-candidate-input.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for p,m in expected['files'].items():assert meta((r/p).read_bytes())==candidate.get(p,m),p
sys.path.insert(0,str(r))
from scripts.build_crypto_intelligence_r4 import render_view
view=json.loads((r/'site/crypto_intelligence_r4.json').read_text());render_view(view,rendered)
version=hashlib.sha256(b''.join((r/'templates'/n).read_bytes() for n in ['crypto_intelligence_r4.html.j2','crypto_intelligence_r4.css','crypto_intelligence_r4.js'])).hexdigest()[:12]
for name in ['crypto-r4.html','vector-r4.html']:
 text=(rendered/name).read_text();before=(r/'site'/name).read_text()
 assert text.count(version)==2 and text.replace(version,expected['assets'])==before,name
assert (rendered/'crypto_intelligence_r4.json').read_bytes()==(r/'site/crypto_intelligence_r4.json').read_bytes()
assert (rendered/'crypto_intelligence_r4.css').read_bytes()==(r/'site/crypto_intelligence_r4.css').read_bytes()
assert (rendered/'crypto_intelligence_r4.js').read_bytes()==(r/'templates/crypto_intelligence_r4.js').read_bytes()
for name in ['crypto-r4.html','vector-r4.html','crypto_intelligence_r4.js']:(r/'site'/name).write_bytes((rendered/name).read_bytes())
changed={};unchanged={}
for p,m in expected['files'].items():
 current=meta((r/p).read_bytes());(unchanged if current==m else changed)[p]=current
source={'source_parent':expected['head'],'assets':version,'changed':changed,'unchanged':unchanged,'retained_page_changes':'Only two asset-version references per page','retained_view_exact':True,'served_assets_exact':True}
(r/'scenario-recovery-source-receipt.json').write_text(json.dumps(source,indent=2)+'\n')
phase.mkdir()
env=os.environ.copy();env.update(PYTHONPATH=str(r),PYTHONDONTWRITEBYTECODE='1',MMX_CHROMIUM_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',MMX_CRYPTO_SNAPSHOT_REPORT=str(phase/'observations.json'),MMX_CRYPTO_SNAPSHOT_CAPTURE_DIR=str(phase/'captures'))
cmd=['/opt/homebrew/opt/python@3.14/bin/python3.14','-m','pytest','-q']+["tests/test_crypto_intelligence_r4_browser.py::test_r4_missing_current_case_recovers_without_borrowing_review_context","tests/test_crypto_intelligence_r4_browser.py::test_r4_generic_and_valid_current_reviews_remain_distinct","tests/test_crypto_intelligence_r4_browser.py::test_r4_unusable_saved_version_never_borrows_current_context","tests/test_crypto_intelligence_r4_browser.py::test_r4_deep_link_and_older_snapshots_fail_open_with_honest_copy"]+['--tb=short','--junitxml='+str(phase/'junit.xml'),'--basetemp='+str(phase/'pytest-temp')]
start=time.monotonic();p=subprocess.run(cmd,cwd=r,env=env,capture_output=True,text=True,timeout=120)
(phase/'stdout.txt').write_text(p.stdout);(phase/'stderr.txt').write_text(p.stderr)
result={'command':cmd,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3),'source_parent':expected['head'],'runtime_asset_version':version,'candidate_inputs':candidate}
(phase/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result));print(p.stdout);print(p.stderr)
