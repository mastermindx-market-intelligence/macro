import json,pathlib,re,sys
ROOT=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'macro_snapshot')
def blank(m): return ''.join('\n' if c=='\n' else ' ' for c in m.group())
def mask(text):
    text=re.sub(r'/\*.*?\*/|\{#.*?#\}|<!--.*?-->',blank,text,flags=re.S)
    return re.sub(r'\{\{.*?\}\}|\{%.*?%\}|\$\{[^{}]*\}',blank,text,flags=re.S)
DECL=re.compile(r'(?<![-\w])(?P<prop>border-(?:left|right|top|bottom|inline-start|inline-end|block-start|block-end)(?:-(?:color|width|style))?|box-shadow)\s*:\s*(?P<value>[^;]+)')
RULE=re.compile(r'\{([^{}]*)\}')
def rules(text):
    clean=mask(text)
    for m in RULE.finditer(clean):
        previous=max(clean.rfind('{',0,m.start()),clean.rfind('}',0,m.start()))+1
        prefix=clean[previous:m.start()]
        selector=prefix.strip().splitlines()[-1].strip() if prefix.strip() else ''
        selector=re.sub(r"^[\s+'\"]+",'',selector)
        if selector.startswith(('if ','function ','for ','return ','const ','let ','var ')): continue
        yield selector,text[m.start(1):m.end(1)],m.start(1),m.end(1),previous,m.end()
def decl(body,prop):
    m=re.search(r'(?<![-\w])'+re.escape(prop)+r'\s*:\s*([^;]+)',mask(body))
    return m.group(1).strip() if m else ''
def px(v):
    m=re.fullmatch(r'([.\d]+)px',v or '')
    return float(m.group(1)) if m else None
def pseudo_bar(sel,body):
    if not re.search(r'::?(before|after)\b',sel): return False
    w,h=px(decl(body,'width')),px(decl(body,'height'))
    if not any(x is not None and 0<x<=6 for x in (w,h)): return False
    bg=decl(body,'background') or decl(body,'background-color')
    if not bg or bg in {'none','transparent'}: return False
    pos=decl(body,'position')
    e={k:decl(body,k) for k in ('top','right','bottom','left')}
    ins=decl(body,'inset').split()
    if 0<len(ins)<=4:
        vals={1:ins*4,2:ins*2,3:ins+ins[1:2],4:ins}[len(ins)]
        for k,v in zip(e,vals): e[k]=e[k] or v
    zero=lambda x:x in {'0','0px'}
    if pos in {'absolute','fixed'}:
        vert=w is not None and w<=6 and (zero(e['left']) or zero(e['right'])) and ((zero(e['top']) and zero(e['bottom'])) or decl(body,'height')=='100%')
        hori=h is not None and h<=6 and (zero(e['top']) or zero(e['bottom'])) and ((zero(e['left']) and zero(e['right'])) or decl(body,'width')=='100%')
        return vert or hori
    return (h is not None and h<=6 and decl(body,'width') in {'','100%','auto'} and decl(body,'display') in {'block','flex',''}) or (w is not None and w<=6 and decl(body,'height')=='100%')
def scan():
    out=[]
    for directory in ['templates','engine','app','scripts']:
      for p in sorted((ROOT/directory).rglob('*')):
        if not p.is_file() or p.suffix not in {'.j2','.html','.css','.js','.py','.ts','.tsx'} or p.name.endswith('.min.js') or p.name.startswith(('plotly-','lightweight-charts')): continue
        text=p.read_text(errors='replace'); clean=mask(text)
        blocks=list(rules(text))
        for sel,body,start,end,rs,re_ in blocks:
            if pseudo_bar(sel,body): out.append({'file':str(p.relative_to(ROOT)),'kind':'pseudo','line':text.count('\n',0,start)+1,'selector':sel,'body':body,'start':start,'end':end,'rule_start':rs,'rule_end':re_})
            for m in DECL.finditer(mask(body)):
                prop=m['prop']; val=body[m.start('value'):m.end('value')].strip()
                if prop=='box-shadow' and not re.search(r'inset\s+-?[2-9](?:\.\d+)?px\s+(?:0(?:px)?\s+0|-[2-9](?:\.\d+)?px)',val) and not re.search(r'inset\s+0(?:px)?\s+-?[2-9](?:\.\d+)?px\s+0',val): continue
                out.append({'file':str(p.relative_to(ROOT)),'kind':'rule','line':text.count('\n',0,start+m.start())+1,'selector':sel,'property':prop,'value':val,'start':start+m.start(),'end':start+m.end(),'body':body})
        for m in re.finditer(r'''\bstyle\s*=\s*(["'])(.*?)\1''',text,re.S):
            body=m.group(2)
            for d in DECL.finditer(mask(body)):
                prop=d['prop'];val=body[d.start('value'):d.end('value')].strip()
                if prop=='box-shadow' and not re.search(r'inset\s+-?[2-9]',val):continue
                out.append({'file':str(p.relative_to(ROOT)),'kind':'inline','line':text.count('\n',0,m.start(2)+d.start())+1,'selector':'inline','property':prop,'value':val,'start':m.start(2)+d.start(),'end':m.start(2)+d.end(),'body':body})
    return out
if __name__=='__main__':
    hits=scan(); dest=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else 'edge_scan.json');dest.write_text(json.dumps(hits,indent=2))
    from collections import Counter
    print(json.dumps({'records':len(hits),'files':len(set(x['file'] for x in hits)),'kinds':dict(Counter(x['kind'] for x in hits)),'output':str(dest)}))
