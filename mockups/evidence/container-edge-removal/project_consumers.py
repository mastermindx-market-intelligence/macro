"""One-time exact-source CSS/UI projection; preserves stored market payloads."""
from pathlib import Path
import collections, hashlib, json, re, sys
from urllib.parse import unquote,urlsplit
sys.path.insert(0,str(Path(__file__).resolve().parent))
import scan_edges as scan
ROOT=Path.cwd();SITE=ROOT/'site';E=ROOT/'mockups/evidence/container-edge-removal'
catalog=json.loads((E/'consumer-projection-catalog.json').read_text())['rules']
fragments=sorted([r for r in catalog if r['kind']=='fragment'],key=lambda r:len(r['old']),reverse=True)
byselector=collections.defaultdict(list)
for r in catalog:
    if r['kind']=='rule':byselector[r['selector']].append(r)
inline=[r for r in catalog if r['kind']=='inline']
hits=collections.Counter();consumers=collections.defaultdict(set);renamed={};changed=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def norm(s):return re.sub(r'\s+',' ',re.sub(r'/\*.*?\*/','',s,flags=re.S)).strip()
def mark(r,path,n=1):hits[r['id']]+=n;consumers[r['id']].add(path)
def project(text,path):
    before=text
    for r in fragments:
        if r['old'] in text:
            n=text.count(r['old']);text=text.replace(r['old'],r['new']);mark(r,path,n)
    edits=[]
    for sel,body,a,b,*_ in scan.rules(text):
        matches=[r for r in byselector.get(sel,[]) if norm(body)==norm(r['old'])]
        targets={r['new'] for r in matches}
        if len(targets)==1:
            r=matches[0];edits.append((a,b,r['new']));mark(r,path)
        elif len(targets)>1:raise ValueError(('ambiguous exact CSS rule',path,sel))
    for a,b,new in sorted(edits,reverse=True):text=text[:a]+new+text[b:]
    return text
def local_ref(page,url):
    u=urlsplit(url)
    if u.scheme or u.netloc or not u.path:return None
    p=(SITE/unquote(u.path.lstrip('/')) if u.path.startswith('/') else page.parent/unquote(u.path)).resolve()
    try:p.relative_to(SITE)
    except ValueError:return None
    return p if p.is_file() else None
pages=[p for p in SITE.rglob('*.html') if p.name not in ('macro_edge_fixture.html','stocks_edge_fixture.html')]
assets=set()
for p in pages:
    s=p.read_text()
    for ref in re.findall(r'(?:href|src)\s*=\s*[\"\']([^\"\']+)',s,re.I):
        q=local_ref(p,ref)
        if q is not None and q.suffix in ('.css','.js'):assets.add(q)
todo=list(assets)
while todo:
    p=todo.pop()
    if p.suffix!='.css':continue
    for ref in re.findall(r'@import\s+(?:url\(\s*)?[\"\']([^\"\']+)',p.read_text()):
        q=local_ref(p,ref)
        if q is not None and q.suffix=='.css' and q not in assets:assets.add(q);todo.append(q)
for index,p in enumerate(sorted(assets)):
    rel=str(p.relative_to(ROOT));before=p.read_text();after=project(before,rel)
    if after==before:continue
    payload=after.encode();digest=sha(payload)[:8]
    if re.fullmatch('[0-9a-f]{8}',p.stem) and p.parent.name in ('css','js') and p.parent.parent.name=='assets':
        q=p.with_name(digest+p.suffix)
        if q.exists():assert q.read_bytes()==payload,(q,'hash collision')
        else:q.write_bytes(payload)
        renamed[str(p.relative_to(SITE))]=str(q.relative_to(SITE))
    else:q=p;q.write_bytes(payload)
    changed.append(dict(path=str(q.relative_to(ROOT)),from_path=rel,before_sha256=sha(before.encode()),after_sha256=sha(payload)))
    if len(changed)%25==0:print('assets_changed',len(changed),flush=True)
def inline_replace(m,path):
    quote,body=m.group(1),m.group(2)
    for r in inline:
        if '{{' not in r['old'] and '{%' not in r['old']:
            if body==r['old']:body=r['new'];mark(r,path)
        elif '{%' not in r['old']:
            pieces=re.split(r'({{.*?}})',r['old']);names=[];pat=''
            for piece in pieces:
                if piece.startswith('{{'):names.append(piece);pat+='(.+?)'
                else:pat+=re.escape(piece)
            found=re.fullmatch(pat,body)
            if found:
                new=r['new']
                for name,value in zip(names,found.groups()):new=new.replace(name,value)
                assert '{{' not in new and '{%' not in new
                body=new;mark(r,path)
    return m[0] if body==m.group(2) else 'style='+quote+body+quote
railspan=re.compile(r'<span class="(?:mc-(?:rail|arrival|stance|dest)-bar|mx-cap mx-cap--[a-z]+)" aria-hidden="true"></span>')
data_blocks=lambda s:re.findall(r'<script\b[^>]*type=[\"\']application/(?:ld\+)?json[\"\'][^>]*>(.*?)</script>',s,re.I|re.S)
for index,p in enumerate(pages):
    rel=str(p.relative_to(ROOT));before=p.read_text();after=before
    after=re.sub(r'(<style\b[^>]*>)(.*?)(</style>)',lambda m:m[1]+project(m[2],rel)+m[3],after,flags=re.I|re.S)
    def script(m):
        if re.search(r'type=[\"\']application/(?:ld\+)?json',m[1],re.I):return m[0]
        if not re.search(r'border|box-shadow|mx-cap|queue-rail|candidate-rail|mc-(?:rail|arrival|stance|dest)-bar',m[2]):return m[0]
        return m[1]+project(m[2],rel)+m[3]
    after=re.sub(r'(<script\b[^>]*>)(.*?)(</script>)',script,after,flags=re.I|re.S)
    after=re.sub(r'\bstyle\s*=\s*([\"\'])(.*?)\1',lambda m:inline_replace(m,rel),after,flags=re.S)
    after=railspan.sub('',after)
    for old,new in renamed.items():
        if old in after:
            oldhash=Path(old).stem;newhash=Path(new).stem
            after=after.replace(old,new).replace(new+'?v='+oldhash,new+'?v='+newhash)
    assert data_blocks(before)==data_blocks(after),(rel,'embedded JSON changed')
    if after!=before:
        p.write_text(after);changed.append(dict(path=rel,before_sha256=sha(before.encode()),after_sha256=sha(after.encode())))
    if index%2000==0:print('pages_scanned',index,'changed',len(changed),flush=True)
record=dict(schema='mastermind.container_edge_consumer_projection.v1',base=catalog and '65f534bdc1369d2496f8e044a90636997e223392',source='a739405d248e3e985c6215067878028f8403fad9',pages_scanned=len(pages),reachable_assets=len(assets),renamed_assets=renamed,changed=changed,rules=[dict(id=r['id'],path=r['path'],kind=r['kind'],matches=hits[r['id']],consumers=sorted(consumers[r['id']])) for r in catalog])
(E/'consumer-projection-receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(pages=len(pages),assets=len(assets),changed=len(changed),renamed=len(renamed),applied_rules=len(hits))),flush=True)
