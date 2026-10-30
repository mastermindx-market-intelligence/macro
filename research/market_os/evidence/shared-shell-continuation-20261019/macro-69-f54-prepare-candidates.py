import ast,datetime,hashlib,json,pathlib,re,subprocess
import yaml
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27')
E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
R=json.loads((E/'macro-69-newmain-0415-reconcile.json').read_text())
H=R['head']; M=R['incoming_main']; B=R['merge_base']; T=R['preview'].splitlines()[0]
def g(*a): return subprocess.check_output(['git','-C',str(W),*a])
def show(ref,path): return g('show',ref+':'+path).decode()
assert g('rev-parse','HEAD').decode().strip()==H
assert not g('status','--porcelain','--untracked-files=no').strip()
assert g('write-tree').decode().strip()==R['index']
pat=re.compile(r'^<<<<<<< '+H+r'\n(.*?)^=======\n(.*?)^>>>>>>> '+M+r'\n',re.M|re.S)
manifest_path='.github/ci/legacy-jobs.yml'
p=show(T,manifest_path); hunks=list(pat.finditer(p)); assert len(hunks)==10
allowed_ours={'lib/shared_shell.py','lib/site_assets.py'}
allowed_theirs={'engine/guidance_source_evidence.py','engine/guidance_source_context.py','collectors/sec_document_spine.py','collectors/sec_request_pacer.py','engine/fundamental_forensics/sec_document_spine.py'}
def join_paths(match):
 left,right=match.groups()
 for block,allowed in ((left,allowed_ours),(right,allowed_theirs)):
  lines=block.splitlines(); vals=[]
  for line in lines:
   m=re.fullmatch(r'      - "([^"]+)"',line); assert m,line; vals.append(m.group(1))
  assert set(vals)<=allowed and len(vals)==len(set(vals)),vals
 assert not set(left.splitlines())&set(right.splitlines())
 return left+right
manifest=pat.sub(join_paths,p); assert '<<<<<<<' not in manifest
b,o,t,c=[yaml.safe_load(x) for x in (show(B,manifest_path),show(H,manifest_path),show(M,manifest_path),manifest)]
assert list(c)==list(o)==list(t)==list(b)
assert list(c['jobs'])==list(o['jobs'])==list(t['jobs'])==list(b['jobs'])
both_paths=[]; checked=[]
def subseq(small,big):
 it=iter(big); return all(any(x==y for y in it) for x in small)
def check_union(b,o,t,c,path):
 if o==b: assert c==t,path
 elif t==b: assert c==o,path
 elif o==t: assert c==o,path
 elif isinstance(b,dict) and isinstance(o,dict) and isinstance(t,dict) and isinstance(c,dict):
  assert set(b)==set(o)==set(t)==set(c),path
  for k in b: check_union(b[k],o[k],t[k],c[k],path+[str(k)])
 elif path[-1]=='paths' and all(isinstance(x,list) for x in (b,o,t,c)):
  assert set(b)<=set(o) and set(b)<=set(t),path
  assert set(c)==set(o)|set(t) and len(c)==len(set(c)),path
  assert subseq(o,c) and subseq(t,c),path
  both_paths.append({'path':'.'.join(path),'ours_added':sorted(set(o)-set(b)),'incoming_added':sorted(set(t)-set(b))})
 else: raise AssertionError(('unclassified simultaneous change',path))
 checked.append('.'.join(path))
check_union(b,o,t,c,[])
caddy_path='app/deploy/Caddyfile'
bc,oc,tc=[show(x,caddy_path) for x in (B,H,M)]
assert tc.count(' /help_refresh.js')==4 and tc.replace(' /help_refresh.js','')==bc
assert ' /help_refresh.js' not in oc
assert oc.count(' /theme.js ')==4
cc=oc.replace(' /theme.js ',' /theme.js /help_refresh.js ')
assert cc.replace(' /help_refresh.js','')==oc
test_path='tests/test_ci_pack.py'
pt=show(T,test_path); th=list(pat.finditer(pt)); assert len(th)==2
def join_test(match):
 left,right=match.groups()
 if 'scripts/build_free_content.py' in left:
  assert '5_649' in left and '5_661' in right
  return right
 assert left.startswith('    Shared Shell composition') and right.startswith('    SPR page JODI')
 return left+'\n'+right
ct=pat.sub(join_test,pt); assert '<<<<<<<' not in ct
# Preserve incoming executable semantics exactly, plus the previously approved
# Shared Shell test source changes outside the overlapping budget/history.
ot=show(H,test_path);bt=show(B,test_path);tt=show(M,test_path)
def strip_docs(tree):
 for n in ast.walk(tree):
  if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str): n.body=n.body[1:]
 return tree
# Original Shared Shell test change relative to B only changed the one budget and docstring.
norm_o=ot.replace('("scripts/build_free_content.py", 134, 5_649)','("scripts/build_free_content.py", 134, 5_642)')
assert ast.dump(strip_docs(ast.parse(norm_o)))==ast.dump(strip_docs(ast.parse(bt)))
assert ast.dump(strip_docs(ast.parse(ct)))==ast.dump(strip_docs(ast.parse(tt)))
files=[]
for path,data in ((manifest_path,manifest),(caddy_path,cc),(test_path,ct)):
 raw=data.encode(); dest=E/('macro-69-f54-candidate-'+path.replace('/','_'))
 dest.write_bytes(raw); files.append({'path':path,'candidate':str(dest),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'base_blob':g('rev-parse',B+':'+path).decode().strip(),'ours_blob':g('rev-parse',H+':'+path).decode().strip(),'incoming_blob':g('rev-parse',M+':'+path).decode().strip()})
receipt={'schema':'mastermind.attended.threeway_candidate.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':H,'incoming':M,'base':B,'preview_tree':T,'files':files,'manifest_jobs':len(c['jobs']),'manifest_conflicts_resolved':len(hunks),'manifest_all_fields_verified':True,'manifest_simultaneous_path_changes':both_paths,'manifest_checked_nodes':len(checked),'test_incoming_executable_ast_preserved':True,'test_both_histories_preserved':True,'test_incoming_weight_ceiling_retained_pending_measurement':5661,'caddy_incoming_exact_four_insertions':True,'caddy_ours_other_bytes_preserved':True,'working_source_edited':False,'index_unchanged':g('write-tree').decode().strip()==R['index']}
raw=(json.dumps(receipt,indent=2)+'\n').encode();(E/'macro-69-f54-candidates.json').write_bytes(raw)
print(raw.decode());print(json.dumps({'receipt_sha256':hashlib.sha256(raw).hexdigest()}))
