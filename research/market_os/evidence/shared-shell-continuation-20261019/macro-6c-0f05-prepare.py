import collections,datetime,hashlib,json,pathlib,re,subprocess,sys
import yaml
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27')
E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
B='f54eeb09f3473e091ea55416a8dcad9196603e60';H='6c0f54d2a5acabaf3df7a01aa3f604c9edf22e36';M='0f058428717ac7c96c11e5a3ebc960db6a61edab';T='73c503c20659bad5e08a74311bdb590f401ca03b'
def g(*a):return subprocess.check_output(['git','-C',str(W),*a])
def show(ref,p):return g('show',ref+':'+p)
def sha(b):return hashlib.sha256(b).hexdigest()
assert g('rev-parse','HEAD').decode().strip()==H
assert not g('status','--porcelain','--untracked-files=no').strip()
I=g('write-tree').decode().strip();assert I=='4bac8f078fc9d922be955e1b02b4f0bfa603e77d'
assert g('merge-base',H,M).decode().strip()==B
sys.path.insert(0,str(W))
from lib.shared_shell import inject_shared_shell_text,BLOCK
files=[]
def save(p,c,proof):
 assert not re.search(rb'(?m)^(<<<<<<< |=======|>>>>>>> )',c)
 d=E/('macro-6c-0f05-candidate-'+p.replace('/','_'));d.write_bytes(c)
 files.append({'path':p,'candidate':str(d),'bytes':len(c),'sha256':sha(c),**{k+'_blob':g('rev-parse',r+':'+p).decode().strip() for k,r in [('base',B),('ours',H),('incoming',M)]},**proof})
p='.github/ci/legacy-jobs.yml'
pat=re.compile(r'^<<<<<<< '+H+r'\n(.*?)^=======\n(.*?)^>>>>>>> '+M+r'\n',re.M|re.S)
s=show(T,p).decode();hunks=list(pat.finditer(s));assert len(hunks)==1
left,right=hunks[0].groups()
assert left=='      - "lib/shared_shell.py"\n      - "lib/site_assets.py"\n'
expected=['engine/local_projection_research_card.py','engine/local_projections.py','engine/seasonality/contracts.py','engine/seasonality/event_study.py','engine/seasonality/multiplicity.py','research/local_projections/ALFRED_CPI_PAYROLL_V1_SOURCE_REFUSAL.json','research/local_projections/ALFRED_CPI_PAYROLL_V1_STUDY_SPEC.json','research/local_projections/ALFRED_CPI_PAYROLL_V2_APPENDIX.md','research/local_projections/ALFRED_CPI_PAYROLL_V2_STUDY_SPEC.json','research/local_projections/reproduce_alfred_cpi_payroll_v2.py','scripts/local_projection_alfred_panel.py','scripts/run_local_projections.py']
assert right.splitlines()[0]=='      # Native LP card import/source closure, measured after consumer adoption.'
assert right.splitlines()[1:]==['      - "'+x+'"' for x in expected]
c=pat.sub(lambda m:m[1]+m[2],s)
b,o,t,j=[yaml.safe_load(x) for x in (show(B,p),show(H,p),show(M,p),c)]
assert list(j)==list(o)==list(t)==list(b)
assert list(j['jobs'])==list(o['jobs'])==list(t['jobs'])==list(b['jobs'])
both=[];checked=[]
def subseq(a,z):
 it=iter(z);return all(any(x==y for y in it) for x in a)
def verify(b,o,t,c,path):
 if o==b:assert c==t,path
 elif t==b:assert c==o,path
 elif o==t:assert c==o,path
 elif all(isinstance(x,dict) for x in (b,o,t,c)):
  assert set(b)==set(o)==set(t)==set(c),path
  for k in b:verify(b[k],o[k],t[k],c[k],path+[str(k)])
 elif path[-1]=='paths' and all(isinstance(x,list) for x in (b,o,t,c)):
  assert set(b)<=set(o) and set(b)<=set(t),path
  assert not (set(o)-set(b)) & (set(t)-set(b)),path
  assert collections.Counter(c)==collections.Counter(b)+(collections.Counter(o)-collections.Counter(b))+(collections.Counter(t)-collections.Counter(b)),path
  assert subseq(o,c) and subseq(t,c),path
  both.append({'path':'.'.join(path),'ours_added':sorted(set(o)-set(b)),'incoming_added':sorted(set(t)-set(b))})
 else:raise AssertionError(('unclassified simultaneous change',path))
 checked.append('.'.join(path))
verify(b,o,t,j,[])
save(p,c.encode(),{'all_329_job_fields_order_and_multiplicities_verified':len(j['jobs'])==329,'simultaneous_path_changes':both,'checked_nodes':len(checked)})
auth="try{ window.MDXAuth.open('signin'); }catch(e){ location.href = 'plans.html'; }"
rules={
 'site/etfs.html':[(auth,"if (window.MMXSharedShell) { window.MMXSharedShell.openAuth('signin'); return; } "+auth,1)],
 'site/us_stocks.html':[
 ("location.href = 'stock.html#' + encodeURIComponent(tk);","var _d = 'stock.html#' + encodeURIComponent(tk); var _ss = window.MMXSharedShell; if (_ss) { _ss.navigate(_d, 'push'); } else { location.href = _d; }",1),
 ("    window.addEventListener('hashchange', fromHash);","    window.addEventListener('hashchange', fromHash);\n    window.addEventListener('mmx:shell-location', fromHash);",1),
 ("          try{ window.MDXAuth.open('signin'); }catch(e2){ location.href = 'plans.html'; }","          if(window.MMXSharedShell){ window.MMXSharedShell.openAuth('signin'); return; }\n          try{ window.MDXAuth.open('signin'); }catch(e2){ location.href = 'plans.html'; }",1)]}
for p,ops in rules.items():
 b,o,t=[show(r,p) for r in (B,H,M)]
 def forward(s):
  for before,after,n in ops:
   assert s.count(before)==n,(p,before,s.count(before));s=s.replace(before,after)
  return inject_shared_shell_text(s,version='048314d5',css_version='b1918cca')
 assert forward(b.decode()).encode()==o,('base/ours reconstruction',p)
 c=forward(t.decode());assert len(BLOCK.findall(c))==1
 inverse=BLOCK.sub('',c,count=1)
 for before,after,n in reversed(ops):
  assert inverse.count(after)==n;(inverse:=inverse.replace(after,before))
 assert inverse.encode()==t
 assert inject_shared_shell_text(c,version='048314d5',css_version='b1918cca')==c
 save(p,c.encode(),{'base_to_ours_exact':True,'inverse_recovers_incoming_exact':True,'injector_idempotent':True,'owned_adapters':len(ops),'incoming_sha256':sha(t)})
bound=['app/deploy/Caddyfile','app/deploy/update.sh','config/site_access.yml','tests/test_site_access_boundary.py','lib/shared_shell.py','templates/shared_shell_bridge.js','templates/shared_shell.css','site/shared_shell_bridge.js','site/shared_shell.css','templates/sector_central.html.j2','templates/sector_central_china.html.j2']
carry=[]
for p in bound:
 assert show(B,p)==show(M,p),('incoming changed bound source',p)
 assert show(T,p)==show(H,p),('preview changed ours bound source',p)
 carry.append({'path':p,'sha256':sha(show(H,p)),'incoming_delta_none':True,'preview_equals_ours':True})
r={'schema':'mastermind.attended.threeway_candidate.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'incoming':M,'base':B,'preview_tree':T,'prior_index':I,'files':files,'carry_forward_source_bindings':carry,'existing_ceiling':5661,'final_weight_not_yet_measured':True,'source_effect':False}
assert g('write-tree').decode().strip()==I and not g('status','--porcelain','--untracked-files=no').strip()
raw=(json.dumps(r,indent=2)+'\n').encode();(E/'macro-6c-0f05-candidates.json').write_bytes(raw)
print(raw.decode());print(json.dumps({'receipt_sha256':sha(raw)}))
