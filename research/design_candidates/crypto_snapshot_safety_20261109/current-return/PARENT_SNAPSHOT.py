from pathlib import Path
import hashlib,json,shutil
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");expected=json.loads((r/'current-return-parent-input.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
observed={path:meta((r/path).read_bytes()) for path in expected['files']}
assert observed==expected['files'],'Native inputs differ from published source'
parent=r/'current-return-parent';assert not parent.exists(),'Parent snapshot already exists';parent.mkdir()
for path in observed:
 target=parent/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/path,target)
receipt={'parent':expected,'files':observed,'runtime_mutations':0}
(r/'current-return-parent-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'inputs':len(observed),'source_parent':expected['head'],'assets':expected['assets']}))
