import datetime,hashlib,json,pathlib,subprocess
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27')
E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
B='92c51f1ff800b36fc63e7869243945996ac7315c';H='e2d10f933587f58be8716505529a37f8839901f7';M='42c859546ececa797b400db0adeb8c5a22f96832'
g=['git','--no-optional-locks','-C',str(W)]
out=E/'macro-e2d-42c-deploy-resolution.json';assert not out.exists()
def show(ref,path):return subprocess.check_output(g+['show',ref+':'+path]).decode()
assert subprocess.check_output(g+['rev-parse','HEAD'],text=True).strip()==H
assert subprocess.check_output(g+['rev-parse','MERGE_HEAD'],text=True).strip()==M
paths=['app/deploy/Caddyfile','app/deploy/update.sh'];cand={};records=[]
for path in paths:
 b,h,m=(show(x,path) for x in (B,H,M))
 assert show(':2',path)==h and show(':3',path)==m
 if path.endswith('Caddyfile'):
  old=' /mm_brain.js ';new=' /mm_brain.js /mm_brain_visuals.js /mm_brain_visuals.css '
  assert b.count(old)==4 and h.count(old)==4
  assert b.replace(old,new)==m,'incoming Caddy delta differs from reviewed four asset additions'
  c=h.replace(old,new)
  assert c.count('/shared_shell_bridge.js /shared_shell.css')==4
  assert 'beta.mastermind-x.com {' in c and 'reverse_proxy 127.0.0.1:3001' in c
  assert 'Content-Security-Policy "base-uri \'self\'; object-src \'none\'; frame-ancestors https://beta.mastermind-x.com"' in c
 else:
  old='ask_brain|cortex|brain_gateway|';new='ask_brain|cortex|brain_gateway|brain_visuals|'
  assert b.count(old)==1 and h.count(old)==1
  assert b.replace(old,new)==m,'incoming updater delta differs from reviewed brain_visuals restart addition'
  c=h.replace(old,new)
  assert 'shared_shell' in c
 assert '<<<<<<<' not in c and '>>>>>>>' not in c
 cand[path]=c
 records.append({'path':path,'base_sha256':hashlib.sha256(b.encode()).hexdigest(),'head_sha256':hashlib.sha256(h.encode()).hexdigest(),'main_sha256':hashlib.sha256(m.encode()).hexdigest(),'result_sha256':hashlib.sha256(c.encode()).hexdigest(),'result_bytes':len(c.encode()),'main_delta_exactly_verified':True,'head_other_bytes_preserved':True})
for path,c in cand.items():(W/path).write_text(c)
p=subprocess.run(g+['add','--']+paths,capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr
q=subprocess.run(g+['diff','--cached','--check','--']+paths,capture_output=True,text=True,timeout=30);assert q.returncode==0,q.stdout+q.stderr
r={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':B,'head':H,'incoming':M,'resolution':'exact union of independent asset allowlist and API restart additions; other H bytes preserved','files':records,'staged_paths':paths,'focused_diff_check_exit':q.returncode}
with out.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
print(json.dumps({'receipt':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
for path in ['.github/ci/legacy-jobs.yml','tests/test_ci_pack.py']:
 t=(W/path).read_text();lines=t.splitlines();spans=[];a=None
 for i,line in enumerate(lines):
  if line.startswith('<<<<<<<'):a=max(0,i-3)
  if a is not None and line.startswith('>>>>>>>'):spans.append({'line':a+1,'text':'\n'.join(lines[a:i+4])});a=None
 hdiff=subprocess.check_output(g+['diff',B,H,'--',path],text=True)
 print(json.dumps({'inspect_path':path,'conflicts':spans,'head_delta':hdiff}))
