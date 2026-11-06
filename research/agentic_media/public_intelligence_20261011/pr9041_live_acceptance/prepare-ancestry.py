"""Build a portable ancestry witness for an exact observed installed HEAD."""
import base64,hashlib,json,pathlib,re,subprocess,sys
release,head,repo=sys.argv[1:]
assert re.fullmatch('[0-9a-f]{40}',release) and re.fullmatch('[0-9a-f]{40}',head)
subprocess.run(['git','-C',repo,'merge-base','--is-ancestor',release,head],check=True)
chain=[];oid=head
while True:
 raw=subprocess.check_output(['git','-C',repo,'cat-file','commit',oid])
 assert hashlib.sha1(b'commit '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==oid
 chain.append({'oid':oid,'raw_base64':base64.b64encode(raw).decode()})
 if oid==release:break
 parents=[l.split()[1].decode() for l in raw.split(b'\n\n',1)[0].splitlines() if l.startswith(b'parent ')]
 assert parents and len(chain)<200
 oid=parents[0]
proof={'schema':'mastermind.git.exact_installed_ancestry.v1','head':head,'release':release,'chain':chain}
from mmx_ancestry import verify_proof
verify_proof(proof,release)
pathlib.Path(__file__).with_name('mmx-9041-installed-ancestry.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps({'release':release,'installed_head':head,'verified_commit_objects':len(chain)}))
