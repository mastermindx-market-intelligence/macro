"""Bind integrated consumers, preserve upstream data, and carry byte-identical proof."""
from pathlib import Path
import ast,collections,functools,hashlib,json,re,subprocess,sys
R=Path.cwd();E=R/'mockups/evidence/container-edge-removal';I=E/'integration'
MAIN='c58c69bf42786f29c8857550bdb244d08da35240';HEAD='97abae6fa8f17bdb71f8670d59d1ba43497e3ae7';BASE='65f534bdc1369d2496f8e044a90636997e223392'
sys.path.insert(0,str(E));import scan_edges as scan
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def git(*args):return subprocess.check_output(['git',*args])
def tree(ref):
 out={}
 for row in git('ls-tree','-r','-z',ref,'--','site').split(b'\0'):
  if row:
   meta,path=row.split(b'\t',1);out[path.decode()]=meta.split()[2].decode()
 return out
main_blobs=tree(MAIN)
changes=git('diff','--no-renames','--name-only',MAIN).decode().splitlines()
data_changes=[p for p in changes if p.startswith('data/') or (p.startswith('site/') and (Path(p).suffix in ('.json','.jsonl','.parquet','.csv','.tsv') or Path(p).name.endswith('_data.js')))]
# Pure existing projection functions only: no module-level file mutation is executed.
catalog=json.loads((E/'consumer-projection-catalog.json').read_text())['rules']
selectors=collections.defaultdict(list)
for r in catalog:
 if r['kind']=='rule':selectors[r['selector']].append(r)
env=dict(re=re,scan=scan,fragments=sorted([r for r in catalog if r['kind']=='fragment'],key=lambda r:len(r['old']),reverse=True),byselector=selectors,inline=[r for r in catalog if r['kind']=='inline'],mark=lambda *a,**kw:None)
nodes=[n for n in ast.parse((E/'project_consumers.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name in ('norm','project','inline_replace')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'approved_projection_functions','exec'),env)
rail=re.compile(r'<span class="(?:mc-(?:rail|arrival|stance|dest)-bar|mx-cap mx-cap--[a-z]+)" aria-hidden="true"></span>')
@functools.lru_cache(None)
def approved_script(body):
 s=env['project'](body.decode(),'read-only-preservation-check')
 s=re.sub(r'\bstyle\s*=\s*(["\'])(.*?)\1',lambda m:env['inline_replace'](m,'read-only-preservation-check'),s,flags=re.S)
 return rail.sub('',s).encode()
script_re=re.compile(rb'<script\b([^>]*)>(.*?)</script\s*>',re.I|re.S)
def scripts(b):
 typed=[];executable=[]
 for attrs,body in script_re.findall(b):
  if re.search(rb'type=["\']application/(?:ld\+)?json["\']',attrs,re.I):typed.append(body)
  elif body.strip():executable.append(body)
 return typed,executable
batch=subprocess.Popen(['git','cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
def read_obj(ref):
 batch.stdin.write((ref+'\n').encode());batch.stdin.flush()
 header=batch.stdout.readline().split()
 assert len(header)==3 and header[1]==b'blob',(ref,header)
 b=batch.stdout.read(int(header[2]));assert batch.stdout.read(1)==b'\n';return b
typed_mismatches=[];unknown=[];approved_deltas=[];approved_structures=[];checked=0;same=0;script_pairs=0
history_cache={}
try:
 for i,p in enumerate(sorted((R/'site').rglob('*.html'))):
  rel=str(p.relative_to(R));current=p.read_bytes();expected=main_blobs.get(rel)
  if expected is None:continue
  if blob(current)==expected:same+=1;continue
  previous=read_obj(expected);pt,pe=scripts(previous);ct,ce=scripts(current);checked+=1
  if pt!=ct:typed_mismatches.append(rel)
  if len(pe)!=len(ce):
   old=scripts(read_obj(BASE+':'+rel))[1];accepted=scripts(read_obj(HEAD+':'+rel))[1]
   row={'path':rel,'main_count':len(pe),'current_count':len(ce),'main_script_sha256':[sha(x) for x in pe],'current_script_sha256':[sha(x) for x in ce]}
   if pe==old and ce==accepted:
    row['reason']='accepted script structure carried byte-identically; upstream script structure and bodies unchanged from original base';approved_structures.append(row)
   else:row['reason']='nonempty executable script count differs without byte-bound historical explanation';unknown.append(row)
   continue
  for index,(a,b) in enumerate(zip(pe,ce)):
   script_pairs+=1
   if a==b:continue
   row={'path':rel,'script_index':index,'main_sha256':sha(a),'current_sha256':sha(b),'main_bytes':len(a),'current_bytes':len(b)}
   if approved_script(a)==b:row['reason']='exact approved static UI transformation';approved_deltas.append(row);continue
   if rel not in history_cache:
    history_cache[rel]=(scripts(read_obj(BASE+':'+rel))[1],scripts(read_obj(HEAD+':'+rel))[1])
   old,accepted=history_cache[rel]
   if index<len(old) and index<len(accepted) and a==old[index] and b==accepted[index]:
    row['reason']='accepted script carried byte-identically; upstream script unchanged from original base';approved_deltas.append(row)
   else:row['reason']='requires investigation';unknown.append(row)
  if i%3000==0:print(json.dumps({'html_visited':i,'typed_mismatches':len(typed_mismatches),'unknown_scripts':len(unknown)}),flush=True)
finally:
 batch.stdin.close();batch.stdout.close();batch.wait()
ew=json.loads((R/'research/evidence/ew_p4_descriptive_ui_20261031/receipt.json').read_text())
ew_rows=[]
for row in ew['pr_source_equivalence']['render_files']:
 actual=blob((R/row['path']).read_bytes());ew_rows.append({'path':row['path'],'actual_blob':actual,'expected_blob':row['blob_at_source_revision'],'equal':actual==row['blob_at_source_revision']})
product_paths=['site/products/mastermind-ai.html','site/products/market-dashboards.html','site/products/market-terminal.html','site/scene-motion.css','site/scene-motion.js']
product_rows=[]
for path in product_paths:
 a=git('show',HEAD+':'+path);b=(R/path).read_bytes();product_rows.append({'path':path,'sha256':sha(b),'equal_to_accepted':a==b})
report={'schema':'mastermind.container_edge_integration_preservation.v1','main':MAIN,'accepted_reference':HEAD,'unchanged_html_files':same,'changed_html_files_checked':checked,'executable_script_pairs_checked':script_pairs,'published_data_file_differences':data_changes,'typed_json_mismatches':typed_mismatches,'approved_executable_script_differences':approved_deltas,'historical_script_structure_differences':approved_structures,'unexplained_executable_script_differences':unknown,'ew_render_inputs':ew_rows,'product_presentation_inputs':product_rows}
(I/'preservation-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
old=json.loads((E/'input-bindings.json').read_text());bound=[]
for row in old['files']:
 p=R/row['path']
 if p.exists():
  b=p.read_bytes();bound.append({'path':row['path'],'sha256':sha(b),'bytes':len(b),'equal_to_historical':sha(b)==row['sha256']})
(I/'input-bindings.json').write_text(json.dumps({'schema':'mastermind.container_edge_input_bindings.v1','baseline':MAIN,'nearest_head':HEAD,'honesty':'Current integrated working-tree bytes after the main merge and approved finite projection. Historical captures are not relabeled.','files':bound},indent=2)+'\n')
print(json.dumps({'data_differences':len(data_changes),'typed_json_mismatches':len(typed_mismatches),'approved_script_differences':len(approved_deltas),'historical_structure_differences':len(approved_structures),'unexplained_scripts':unknown,'ew_equal':sum(r['equal'] for r in ew_rows),'ew_inputs':len(ew_rows),'product_inputs_equal':all(r['equal_to_accepted'] for r in product_rows),'bound_files':len(bound),'unchanged_bound_files':sum(r['equal_to_historical'] for r in bound)}),flush=True)
assert not data_changes and not typed_mismatches and not unknown, 'upstream data/payload preservation failed'
assert all(r['equal'] for r in ew_rows) and all(r['equal_to_accepted'] for r in product_rows),'historical presentation closure changed'
