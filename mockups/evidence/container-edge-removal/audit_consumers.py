from pathlib import Path
import functools,hashlib,importlib.util,json,os,re,sys,collections
from urllib.parse import urlsplit,unquote
R=Path.cwd();S=R/'site';E=R/'mockups/evidence/container-edge-removal'
spec=importlib.util.spec_from_file_location('edge_guard',R/'tests/test_container_edge_stripes.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
functional_left=tuple(x for v in g._FUNCTIONAL_LEFT.values() for x in v)
functional_pseudo=tuple(x for v in g._FUNCTIONAL_PSEUDO.values() for x in v)
functional_shadow={x[1] for x in g.GUARD2_ALLOWED}
groups={};known=collections.Counter();seen_blocks={};assets=set();missing=set();superseded=set()
renamed=json.loads((E/'consumer-projection-receipt.json').read_text())['renamed_assets']
def record(path,selector,kind,body):
 key=(selector,kind,body.strip())
 if key not in groups:groups[key]=dict(selector=selector,kind=kind,body=body.strip(),count=0,examples=[])
 row=groups[key];row['count']+=1
 if len(row['examples'])<8:row['examples'].append(path)
def inspect(text,path):
 digest=hashlib.sha256(text.encode()).hexdigest()
 if digest in seen_blocks:
  for sel,kind,body in seen_blocks[digest]:record(path,sel,kind,body)
  return
 out=[]
 for sel,body in g._estate_rules(text):
  if g._left_accent(body):
   if any(x in sel for x in functional_left):known['functional_left']+=1
   else:out.append((sel,'left',body))
  if g._estate_inset_stripe(body):
   if sel in functional_shadow:known['functional_shadow']+=1
   else:out.append((sel,'shadow',body))
  if re.search(r'::?(before|after)\b',sel) and g._estate_pseudo_bar(body):
   if any(x in sel for x in functional_pseudo):known['functional_pseudo']+=1
   else:out.append((sel,'pseudo',body))
 if re.search(r'\.style\.(?:borderLeft|borderInlineStart)(?:Color|Width)?\s*=',g._clean_source(text)):
  out.append(('runtime setter','runtime','side-border assignment'))
 seen_blocks[digest]=out
 for sel,kind,body in out:record(path,sel,kind,body)
@functools.lru_cache(None)
def resolve(directory,url):
 u=urlsplit(url)
 if u.scheme or u.netloc or not u.path or any(x in url for x in ('${','{{','{%','<','>','}',' ','\n','\t')):return None
 q=Path(os.path.normpath(str(S/u.path.lstrip('/') if u.path.startswith('/') else Path(directory)/unquote(u.path))))
 try:q.relative_to(S)
 except ValueError:return None
 return q
pages=[p for p in S.rglob('*.html') if p.name not in ('macro_edge_fixture.html','stocks_edge_fixture.html')]
for i,p in enumerate(pages):
 text=p.read_text();rel=str(p.relative_to(R))
 for ref in re.findall(r"""(?<![\w-])(?:href|src)\s*=\s*["']([^"']+)""",text,re.I):
  q=resolve(str(p.parent),ref)
  if q is not None and q.suffix in ('.css','.js'):
   if q.is_file():assets.add(q)
   else:missing.add(str(q.relative_to(R)))
   if str(q.relative_to(S)) in renamed:superseded.add(str(q.relative_to(S)))
 for block in re.findall(r'<style\b[^>]*>(.*?)</style>',text,re.I|re.S):inspect(block,rel)
 for attrs,block in re.findall(r'<script\b([^>]*)>(.*?)</script>',text,re.I|re.S):
  if 'application/' not in attrs and re.search(r'border-left|border-inline-start|borderLeft|box-shadow|::before|::after',block):inspect(block,rel)
 for match in re.finditer(r"""\bstyle\s*=\s*(["'])(.*?)\1""",g._clean_source(text),re.S):
  if g._left_accent(match[2]) or g._estate_inset_stripe(match[2]):record(rel,'inline','inline',match[2])
 for m in re.finditer(r'<span class="(?:mc-(?:rail|arrival|stance|dest)-bar|mx-cap mx-cap--[a-z]+)" aria-hidden="true"></span>',text):record(rel,'retired span','markup',m[0])
 if i%3000==0:print('audited_pages',i,'unique_residuals',len(groups),flush=True)
todo=list(assets)
while todo:
 p=todo.pop();rel=str(p.relative_to(R));text=p.read_text()
 if p.suffix=='.css':
  for ref in re.findall(r"""@import\s+(?:url\(\s*)?["']([^"']+)""",text):
   q=resolve(str(p.parent),ref)
   if q is not None:
    if q.is_file() and q not in assets:assets.add(q);todo.append(q)
    elif not q.is_file():missing.add(str(q.relative_to(R)))
    if str(q.relative_to(S)) in renamed:superseded.add(str(q.relative_to(S)))
 if p.name.endswith('.min.js') or p.name.startswith(('plotly','lightweight-charts')) or 'vendor' in p.parts:continue
 inspect(text,rel)
report=dict(schema='mastermind.container_edge_consumer_audit.v1',pages=len(pages),reachable_assets=len(assets),unique_blocks=len(seen_blocks),functional=dict(known),missing_assets=sorted(missing),superseded_references=sorted(superseded),residuals=list(groups.values()))
(E/'consumer-residual-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='residuals'}|{'unique_residuals':len(groups)}),flush=True)
