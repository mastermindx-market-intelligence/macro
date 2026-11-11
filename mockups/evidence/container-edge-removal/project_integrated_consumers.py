"""Resume the exact approved projection; reuse only byte-bound reachable proof."""
from pathlib import Path
import json, subprocess, hashlib
R=Path.cwd(); E=R/'mockups/evidence/container-edge-removal'; I=E/'integration'
MAIN='c58c69bf42786f29c8857550bdb244d08da35240'
HEAD='97abae6fa8f17bdb71f8670d59d1ba43497e3ae7'
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==HEAD
assert not subprocess.check_output(['git','diff','--name-only','--diff-filter=U'],text=True).strip()
partial=json.loads((I/'partial-projection-checkpoint.json').read_text())
assert subprocess.check_output(['git','write-tree'],text=True).strip()==partial['input_tree']
code=(E/'project_consumers.py').read_text()
def patch(old,new):
 global code
 assert code.count(old)==1,(old[:70],code.count(old))
 code=code.replace(old,new)
patch('import collections, hashlib, json, re, sys','import collections, hashlib, json, re, sys, functools, subprocess')
patch("sys.path.insert(0,str(Path(__file__).resolve().parent))","sys.path.insert(0,str(Path.cwd()/'mockups/evidence/container-edge-removal'))")
patch("hits=collections.Counter();consumers=collections.defaultdict(set);renamed={};changed=[]", """hits=collections.Counter();consumers=collections.defaultdict(set);renamed={};changed=[]
accepted_blobs={}
for item in subprocess.check_output(['git','ls-tree','-r','-z','97abae6fa8f17bdb71f8670d59d1ba43497e3ae7','--','site']).split(b'\\0'):
    if not item:continue
    meta,path=item.split(b'\\t',1);accepted_blobs[path.decode()]=meta.split()[2].decode()
def blob(text):
    b=text.encode();return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\\0'+b).hexdigest()
accepted_pages=set();accepted_reachable={};reused_assets=[];reused_pages=0
""")
patch('def project(text,path):','def uncached_project(text,path):')
patch('def local_ref(page,url):',"""project_cache={}
def project(text,path):
    if text in project_cache:
        after,delta=project_cache[text]
        for key,n in delta.items():hits[key]+=n;consumers[key].add(path)
        return after
    before=hits.copy();after=uncached_project(text,path)
    project_cache[text]=(after,{key:n-before[key] for key,n in hits.items() if n!=before[key]})
    return after
@functools.lru_cache(None)
def local_ref(directory,url):""")
patch('else page.parent/unquote(u.path)',"else Path(directory)/unquote(u.path)")
code=code.replace('local_ref(p,ref)','local_ref(str(p.parent),ref)')
patch("    s=p.read_text()\n    for ref in re.findall", "    s=p.read_text();rel=str(p.relative_to(ROOT));accepted=blob(s)==accepted_blobs.get(rel)\n    if accepted:accepted_pages.add(rel)\n    for ref in re.findall")
patch("        q=local_ref(str(p.parent),ref)\n        if q is not None and q.suffix in ('.css','.js'):assets.add(q)", """        if not urlsplit(ref).path.lower().endswith(('.css','.js')):continue
        q=local_ref(str(p.parent),ref)
        if q is not None and q.suffix in ('.css','.js'):
            assets.add(q)
            if accepted:accepted_reachable.setdefault(q,rel)""")
patch("    rel=str(p.relative_to(ROOT));before=p.read_text();after=project(before,rel)", """    rel=str(p.relative_to(ROOT));before=p.read_text()
    if p in accepted_reachable and blob(before)==accepted_blobs.get(rel):
        reused_assets.append(dict(path=rel,blob=accepted_blobs[rel],witness_page=accepted_reachable[p]));continue
    after=project(before,rel)""")
patch('def inline_replace(m,path):','def uncached_inline_replace(m,path):')
patch('railspan=re.compile(', """inline_cache={}
def inline_replace(m,path):
    key=m[0]
    if key in inline_cache:
        after,delta=inline_cache[key]
        for rid,n in delta.items():hits[rid]+=n;consumers[rid].add(path)
        return after
    before=hits.copy();after=uncached_inline_replace(m,path)
    inline_cache[key]=(after,{rid:n-before[rid] for rid,n in hits.items() if n!=before[rid]})
    return after
railspan=re.compile(""")
patch("    rel=str(p.relative_to(ROOT));before=p.read_text();after=before", """    rel=str(p.relative_to(ROOT));before=p.read_text();after=before
    if rel in accepted_pages and not any(old in before for old in renamed):
        reused_pages+=1;continue""")
patch("    assert data_blocks(before)==data_blocks(after),(rel,'embedded JSON changed')","    if after!=before:assert data_blocks(before)==data_blocks(after),(rel,'embedded JSON changed')")
patch("base=catalog and '65f534bdc1369d2496f8e044a90636997e223392',source='a739405d248e3e985c6215067878028f8403fad9'","base='"+MAIN+"',source='"+HEAD+"'")
patch("(E/'consumer-projection-receipt.json').write_text", """record['prepared_input_tree']='"""+partial['input_tree']+"""'
record['historical_catalog_sha256']=sha((E/'consumer-projection-catalog.json').read_bytes())
record['accepted_pages_reused']=reused_pages
record['accepted_asset_bindings']=reused_assets
record['rule_accounting']='Matches and changed entries cover this resumed pass only. Seven earlier page mutations are separately byte-bound in partial-projection-checkpoint.json; no interrupted-run rule totals are asserted.'
record['partial_projection_checkpoint']='partial-projection-checkpoint.json'
(E/'integration/consumer-projection-receipt.json').write_text""")
exec(compile(code,str(E/'project_consumers.py'),'exec'),{'__name__':'__main__','__file__':str(E/'project_consumers.py')})
