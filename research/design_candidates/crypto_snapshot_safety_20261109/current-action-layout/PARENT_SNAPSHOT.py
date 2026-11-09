from pathlib import Path
import hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");out=r/'current-action-layout-parent';assert not out.exists(),'Parent snapshot already exists'
expected=json.loads((r/'current-action-layout-parent-input.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
for path,m in expected['files'].items():assert meta((r/path).read_bytes())==m,path
for path in expected['files']:
 target=out/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((r/path).read_bytes())
receipt={'source_parent':expected['head'],'tree':expected['tree'],'assets':expected['assets'],'files':expected['files'],'copied_inputs':len(expected['files']),'runtime_changes':0}
(r/'current-action-layout-parent-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'source_parent':expected['head'],'assets':expected['assets'],'copied_inputs':len(expected['files']),'runtime_changes':0}))
