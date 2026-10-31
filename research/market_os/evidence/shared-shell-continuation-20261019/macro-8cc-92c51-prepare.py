import ast,collections,datetime,hashlib,json,pathlib,re,subprocess
import yaml
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27')
E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
B='0f058428717ac7c96c11e5a3ebc960db6a61edab';H='8ccfa5ddba6770cef48f2f162c08474d023e094e';M='92c51f1ff800b36fc63e7869243945996ac7315c';T='b750bc4f1a9fec2d48e2e9eb66e09f8e669263d8'
def g(*a):return subprocess.check_output(['git','-C',str(W),*a])
def show(ref,p):return g('show',ref+':'+p)
def sha(b):return hashlib.sha256(b).hexdigest()
assert g('rev-parse','HEAD').decode().strip()==H
assert not g('status','--porcelain=v1').strip()
I=g('write-tree').decode().strip();assert I=='12f10c410682befb243f26add961b975137bea75'
assert g('merge-base',H,M).decode().strip()==B
pat=re.compile(r'^<<<<<<< '+H+r'\n(.*?)^=======\n(.*?)^>>>>>>> '+M+r'\n',re.M|re.S)
files=[]
def save(p,c,proof):
 assert not re.search(rb'(?m)^(<<<<<<< |=======|>>>>>>> )',c)
 d=E/('macro-8cc-92c51-candidate-'+p.replace('/','_'));assert not d.exists();d.write_bytes(c)
 files.append({'path':p,'candidate':str(d),'bytes':len(c),'sha256':sha(c),**{k+'_blob':g('rev-parse',r+':'+p).decode().strip() for k,r in [('base',B),('ours',H),('incoming',M)]},**proof})
p='.github/ci/legacy-jobs.yml';s=show(T,p).decode();hunks=list(pat.finditer(s));assert len(hunks)==3
expected=[['lib/dataos/sec_filing_identity.py'],['engine/bond_issue_parser.py','engine/bond_issue_terms.py','lib/dataos/sec_filing_identity.py'],['engine/bond_issue_parser.py','engine/bond_issue_terms.py','lib/dataos/sec_filing_identity.py']]
for h,paths in zip(hunks,expected):
 left,right=h.groups();assert left=='      - "lib/shared_shell.py"\n'
 assert right.splitlines()==['      - "'+x+'"' for x in paths]
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
save(p,c.encode(),{'jobs':len(j['jobs']),'all_fields_order_and_multiplicities_verified':True,'simultaneous_path_changes':both,'checked_nodes':len(checked),'resolved_hunks':3})
p='tests/test_ci_pack.py';s=show(T,p).decode();hunks=list(pat.finditer(s));assert len(hunks)==2
assert '5_668' in hunks[0][1] and '5_664' in hunks[0][2]
assert hunks[1][1].startswith('    Shared Shell/current-main composition') and hunks[1][2].startswith('    The S&P Vector scorecard basis')
n=0
def resolve(m):
 global n
 n+=1
 return m[2] if n==1 else m[1]+'\n'+m[2]
c=pat.sub(resolve,s)
class StripDoc(ast.NodeTransformer):
 def visit_FunctionDef(self,node):
  self.generic_visit(node)
  if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str):node.body=node.body[1:]
  return node
assert ast.dump(StripDoc().visit(ast.parse(c)),include_attributes=False)==ast.dump(StripDoc().visit(ast.parse(show(M,p))),include_attributes=False)
save(p,c.encode(),{'incoming_executable_AST_exact':True,'incoming_ceiling':5664,'both_historical_notes_retained':True,'resolved_hunks':2})
bound=['app/deploy/Caddyfile','app/deploy/update.sh','config/site_access.yml','tests/test_site_access_boundary.py','lib/shared_shell.py','templates/shared_shell_bridge.js','templates/shared_shell.css','site/shared_shell_bridge.js','site/shared_shell.css','templates/sector_central.html.j2','templates/sector_central_china.html.j2','scripts/inject_shared_shell.py','lib/pages.py','scripts/optimize_assets.py','lib/config.py','scripts/check_template_site_sync.py']
carry=[]
for p in bound:
 assert g('ls-tree',B,'--',p)==g('ls-tree',M,'--',p),('incoming changed bound source or presence',p)
 assert show(T,p)==show(H,p),('preview changed ours bound source',p)
 carry.append({'path':p,'sha256':sha(show(H,p)),'incoming_delta_none':True,'preview_equals_ours':True})
r={'schema':'mastermind.attended.threeway_candidate.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'incoming':M,'base':B,'preview_tree':T,'prior_index':I,'files':files,'carry_forward_source_bindings':carry,'existing_ceiling':5664,'final_weight_not_yet_measured':True,'source_effect':False}
assert g('write-tree').decode().strip()==I and not g('status','--porcelain=v1').strip()
raw=(json.dumps(r,indent=2)+'\n').encode();dest=E/'macro-8cc-92c51-candidates.json';assert not dest.exists();dest.write_bytes(raw)
print(raw.decode());print(json.dumps({'receipt_sha256':sha(raw)}))
