import ast,collections,datetime,hashlib,json,pathlib,re,subprocess,yaml
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27');E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
B='92c51f1ff800b36fc63e7869243945996ac7315c';H='e2d10f933587f58be8716505529a37f8839901f7';M='42c859546ececa797b400db0adeb8c5a22f96832'
g=['git','--no-optional-locks','-C',str(W)]
out=E/'macro-e2d-42c-ci-resolution.json';assert not out.exists()
def show(ref,p):return subprocess.check_output(g+['show',ref+':'+p]).decode()
assert subprocess.check_output(g+['rev-parse','HEAD'],text=True).strip()==H
assert subprocess.check_output(g+['rev-parse','MERGE_HEAD'],text=True).strip()==M
rx=re.compile(r'^<<<<<<< HEAD\n(.*?)^=======\n(.*?)^>>>>>>> '+M+r'\n',re.M|re.S)
path='.github/ci/legacy-jobs.yml';original=(W/path).read_text();matches=list(rx.finditer(original));assert len(matches)==12,len(matches)
for m in matches:
 assert all(line.strip() in ['- "lib/shared_shell.py"','- "lib/site_assets.py"'] for line in m[1].splitlines())
 assert all(line.strip().startswith(('- "', '#')) for line in m[2].splitlines())
candidate=rx.sub(lambda m:m[1]+m[2],original);assert '<<<<<<<' not in candidate
b,h,m,c=[yaml.safe_load(s) for s in (show(B,path),show(H,path),show(M,path),candidate)]
assert list(c)==list(m)
assert {k:v for k,v in c.items() if k!='jobs'}=={k:v for k,v in m.items() if k!='jobs'}
assert list(c['jobs'])==list(m['jobs']) and len(c['jobs'])==330
def subseq(a,b):
 it=iter(b);return all(any(x==y for y in it) for x in a)
path_rows=[]
for key,cv in c['jobs'].items():
 if key not in b['jobs']:
  assert key not in h['jobs'] and cv==m['jobs'][key];continue
 bv=b['jobs'][key];hv=h['jobs'][key];mv=m['jobs'][key]
 assert set(cv)==set(hv)|set(mv)
 for field in set(cv)|set(bv)|set(hv)|set(mv):
  absent=object();v0=bv.get(field,absent);vh=hv.get(field,absent);vm=mv.get(field,absent);vc=cv.get(field,absent)
  if field=='paths' and isinstance(vh,list) and isinstance(vm,list):
   assert subseq(vh,vc) and subseq(vm,vc),(key,'parent order')
   c0=collections.Counter(v0);ch=collections.Counter(vh);cm=collections.Counter(vm)
   expected=c0+((ch-c0)|(cm-c0))
   assert collections.Counter(vc)==expected,(key,'multiplicity')
   if vh!=v0 or vm!=v0:path_rows.append({'job':key,'base':len(v0),'head':len(vh),'main':len(vm),'combined':len(vc)})
  elif vh==v0:assert vc==vm,(key,field,'main')
  elif vm==v0:assert vc==vh,(key,field,'head')
  else:assert vh==vm==vc,(key,field,'ambiguous concurrent nonpath change')
path2='tests/test_ci_pack.py';original2=(W/path2).read_text();matches2=list(rx.finditer(original2));assert len(matches2)==2,len(matches2)
assert '"templates/index.html", 136, 5_803' in matches2[0][1] and '"templates/index.html", 136, 5_822' in matches2[0][2]
assert 'Shared Shell/current-main92c51 composition' in matches2[1][1] and 'SPR JODI trend and gold vintage' in matches2[1][2]
ordinal=[0]
def resolve_test(mt):
 n=ordinal[0];ordinal[0]+=1
 return mt[2] if n==0 else mt[1]+'\n'+mt[2]
candidate2=rx.sub(resolve_test,original2);assert '<<<<<<<' not in candidate2
def no_docs(s):
 tree=ast.parse(s)
 for node in ast.walk(tree):
  if isinstance(node,(ast.Module,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str):node.body[0].value.value=''
 return ast.dump(tree,include_attributes=False)
assert no_docs(candidate2)==no_docs(show(M,path2)),'test executable AST changed'
for p,s in [(path,candidate),(path2,candidate2)]:(W/p).write_text(s)
p=subprocess.run(g+['add','--',path,path2],capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stderr
p=subprocess.run(g+['diff','--cached','--check','--',path,path2],capture_output=True,text=True,timeout=30);assert p.returncode==0,p.stdout+p.stderr
r={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'base':B,'head':H,'incoming':M,'manifest_conflicts_resolved':12,'manifest_jobs':len(c['jobs']),'new_jobs':[k for k in c['jobs'] if k not in h['jobs']],'parent_ids_order_and_fields_preserved':True,'paths_both_parent_order_and_exact_multiplicity':True,'changed_path_lists':path_rows,'test_conflicts_resolved':2,'test_executable_AST_identical_to_incoming':True,'retained_incoming_ceilings':{'templates/index.html':[136,5822,10],'scripts/build_free_content.py':[134,5697,10],'engine/prophet/plan_book.py':[130,5600,10]},'all_both_parent_histories_preserved':True,'fresh_selector_or_test_run':False,'files':[{'path':p,'bytes':len(s.encode()),'sha256':hashlib.sha256(s.encode()).hexdigest()} for p,s in [(path,candidate),(path2,candidate2)]]}
with out.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2));print(json.dumps({'receipt':str(out),'bytes':out.stat().st_size,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()}))
