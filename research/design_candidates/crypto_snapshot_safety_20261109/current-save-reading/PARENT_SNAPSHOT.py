from pathlib import Path
import hashlib,json
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");target=r/'current-save-reading-parent';assert not target.exists(),'Parent snapshot exists'
expected=json.loads((r/'current-save-reading-parent-input.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
files={}
for path,m in expected['files'].items():
 b=(r/path).read_bytes();actual=meta(b);assert actual==m,path;files[path]=actual
for path in expected['files']:
 out=target/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes((r/path).read_bytes());assert meta(out.read_bytes())==expected['files'][path]
(r/'current-save-reading-parent-receipt.json').write_text(json.dumps({'parent':expected,'files':files,'runtime_mutations':0},indent=2)+'\n')
print(json.dumps({'source_parent':expected['head'],'assets':expected['assets'],'inputs':len(files)}))
