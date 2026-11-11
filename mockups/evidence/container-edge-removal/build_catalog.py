from pathlib import Path
import collections, difflib, hashlib, json, re
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import scan_edges as scan

root=Path.cwd()/'.tmp/source-projection'
oldroot=root/'base';newroot=Path.cwd()
envs=[Environment(loader=FileSystemLoader(str(p/'templates')),undefined=StrictUndefined,keep_trailing_newline=True) for p in (oldroot,newroot)]
catalog=[];unresolved=[]
def add(kind,path,old,new,selector=None):
    if old==new or not old.strip(): return
    item=dict(kind=kind,path=path,old=old,new=new)
    if selector is not None:item['selector']=selector
    item['id']=hashlib.sha256((kind+path+old+new).encode()).hexdigest()[:16]
    catalog.append(item)
for p in sorted((newroot/'templates').rglob('*')):
    if not p.is_file() or p.suffix not in ('.css','.js','.html','.j2'):continue
    rel=str(p.relative_to(newroot));before=oldroot/rel
    if not before.exists():continue
    if p.name=='confluence_screener.html.j2':before=oldroot/rel
    a=before.read_text();b=p.read_text()
    if a==b:continue
    if p.suffix=='.css' or p.name.endswith('.css.j2'):
        if not re.search(r'{{|{%|\$\{',a+b):add('fragment',rel,a,b)
    styles=[re.findall(r'<style\b[^>]*>(.*?)</style>',x,re.I|re.S) for x in (a,b)]
    if len(styles[0])==len(styles[1]):
        for old,new in zip(*styles):
            if old==new:continue
            try:
                old=envs[0].from_string(old).render()
                new=envs[1].from_string(new).render()
                add('fragment',rel,old,new)
            except Exception as e:
                unresolved.append(dict(path=rel,kind='style-render',reason=str(e)))
    blocks=[re.findall(r'{% block base_css %}(.*?){% endblock %}',x,re.S) for x in (a,b)]
    if len(blocks[0])==len(blocks[1]):
        for old,new in zip(*blocks):
            if not re.search(r'{{|{%|\$\{',old+new):add('fragment',rel,old,new)
    ro=[collections.defaultdict(list),collections.defaultdict(list)]
    for idx,text in enumerate((a,b)):
        for sel,body,*_ in scan.rules(text):ro[idx][sel].append(body)
    for sel,olds in ro[0].items():
        news=ro[1].get(sel,[])
        if len(olds)!=len(news):continue
        for old,new in zip(olds,news):
            if re.search(r'(?:border|box-shadow|content|padding|color|background|display|grid-template-columns|font-weight|gap|margin)\s*[-\w]*\s*:',old+new) and not re.search(r'{{|{%|\$\{',old+new):
                add('rule',rel,old,new,sel)
    attrs=[re.findall(r'\bstyle\s*=\s*([\"\'])(.*?)\1',x,re.S) for x in (a,b)]
    if len(attrs[0])==len(attrs[1]):
        for (_,old),(_,new) in zip(*attrs):
            if old!=new:add('inline',rel,old,new)
    else:unresolved.append(dict(path=rel,kind='inline-count',before=len(attrs[0]),after=len(attrs[1])))
    # Contextual static hunks carry removed/renamed selectors and emitted UI strings.
    al=a.splitlines(keepends=True);bl=b.splitlines(keepends=True)
    for group in difflib.SequenceMatcher(None,al,bl,autojunk=False).get_grouped_opcodes(2):
        old=''.join(al[group[0][1]:group[-1][2]]);new=''.join(bl[group[0][3]:group[-1][4]])
        if not re.search(r'{{|{%|{#',old+new) and re.search(r'border|box-shadow|::before|::after|mx-cap|queue-rail|candidate-rail|mc-(rail|arrival|stance|dest)-bar',old):add('fragment',rel,old,new)
seen=set();unique=[]
for r in catalog:
    key=(r['kind'],r.get('selector'),r['old'],r['new'])
    if key not in seen:unique.append(r);seen.add(key)
out=dict(base='65f534bdc1369d2496f8e044a90636997e223392',source='a739405d248e3e985c6215067878028f8403fad9',rules=unique,unresolved_source_forms=unresolved)
(Path.cwd()/'mockups/evidence/container-edge-removal/consumer-projection-catalog.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
chunks=[json.dumps(out,ensure_ascii=False)[i:i+20000] for i in range(0,len(json.dumps(out,ensure_ascii=False)),20000)]
(root/'projection_chunks').mkdir(exist_ok=True)
for i,ch in enumerate(chunks):(root/'projection_chunks'/f'{i:02}.json').write_text(json.dumps(ch))
print(json.dumps({'rules':len(unique),'kinds':dict(collections.Counter(r['kind'] for r in unique)),'chunks':len(chunks),'unresolved':unresolved},ensure_ascii=False,indent=2))
