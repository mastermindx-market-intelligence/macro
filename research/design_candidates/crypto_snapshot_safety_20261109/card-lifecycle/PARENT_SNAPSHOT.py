from pathlib import Path
import hashlib,json,shutil,sys
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");expected=json.loads((r/'card-lifecycle-parent-input.json').read_text())
def meta(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'blob':hashlib.sha1(('blob '+str(len(b))+'\0').encode()+b).hexdigest()}
parent=r/'card-lifecycle-parent';assert not parent.exists(),'Parent snapshot already exists'
observed={p:meta((r/p).read_bytes()) for p in expected['files']}
assert observed==expected['files'],'Native inputs differ from published source'
parent.mkdir()
for p in observed:
 dest=parent/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/p,dest)
sys.path.insert(0,str(r))
from scripts.build_crypto_intelligence_r4 import render_view
out=r/'card-lifecycle-parent-render';assert not out.exists(),'Parent render exists'
view=json.loads((r/'site/crypto_intelligence_r4.json').read_text());render_view(view,out)
reproduced={name:(out/name).read_bytes()==(r/'site'/name).read_bytes() for name in ['crypto-r4.html','vector-r4.html','crypto_intelligence_r4.js','crypto_intelligence_r4.css','crypto_intelligence_r4.json']}
assert all(reproduced.values()),reproduced
receipt={'parent':expected,'files':observed,'retained_render_exact':reproduced,'runtime_mutations':0}
(r/'card-lifecycle-parent-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'inputs':len(observed),'source_parent':expected['head'],'retained_render_exact':reproduced}))
