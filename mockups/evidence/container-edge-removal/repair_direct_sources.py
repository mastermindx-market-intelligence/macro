from pathlib import Path
import hashlib,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import scan_edges as scan
R=Path.cwd();S=R/'site';E=R/'mockups/evidence/container-edge-removal'
record=[];rename={}
def write(p,new):
 old=p.read_text()
 if new!=old:
  p.write_text(new);record.append(dict(path=str(p.relative_to(R)),before=hashlib.sha256(old.encode()).hexdigest(),after=hashlib.sha256(new.encode()).hexdigest()))
def rules(text,fn):
 edits=[]
 for sel,body,a,b,*_ in scan.rules(text):
  new=fn(sel,body)
  if new is not None and new!=body:edits.append((a,b,new))
 for a,b,new in sorted(edits,reverse=True):text=text[:a]+new+text[b:]
 return text
def prod(sel,b):
 if sel in ('.chap-x.on::after','.md-tile::before','.mt-system-card::before'):return 'content:none;'
 if sel=='.callout':return b.replace('border-left:3px solid var(--q-gold);','')
 if sel=='.chap-x.on' and 'font-weight' not in b:return b.rstrip(';')+';font-weight:800;'
 if sel=='.mt-wl .r.sel':return b.replace('inset 2px 0 0 var(--pl-ac)','inset 0 0 0 1px var(--pl-hr)')
 return b
for name in ['mastermind-ai.html','market-dashboards.html','market-terminal.html']:
 p=S/'products'/name;s=rules(p.read_text(),prod)
 if name=='market-terminal.html':
  s=s.replace('.mt-wl .r.sel{','.mt-wl .r.sel .sy{font-weight:800}\n.mt-wl .r.sel{',1)
 write(p,s)
p=S/'scene-motion.css';s=p.read_text().replace('inset 2px 0 0 var(--pl-ac),0 0 0 2px rgba(89,128,255,.11)','inset 0 0 0 1px var(--pl-hr),0 0 0 2px rgba(89,128,255,.11)');write(p,s)
p=S/'radar_panel.js';s=p.read_text().replace('border-left:2px solid;border-radius:0 4px 4px 0','border:1px solid var(--line);border-radius:4px').replace('border-left-color:', 'color:');write(p,s)
p=S/'cycle.css';s=p.read_text()
s=s.replace('border-left: 2px solid color-mix(in srgb, var(--warn) 60%, transparent);\n  padding-left: 11px;','border:1px solid var(--line); background:var(--panel2,var(--panel)); border-radius:var(--r-ctl,8px);\n  padding:8px 11px;')
s=s.replace('border-left: 3px solid var(--c); padding-left: 12px;','padding-left:0;')
s=rules(s,lambda sel,b:'content:none;' if sel=='.cyc-card::before' else b);write(p,s)
def start(sel,b):
 if sel=='.acc::before' or (sel=='.gd-isl .body::after' and 'height:2.5px' in b):return 'content:none;'
 return b
p=R/'scripts/build_vector.py';write(p,rules(p.read_text(),start))
# Exact source-backed and retained direct-source stylesheet repairs.
for h in ['3ba1e7fa','9a7074ed','a8e92904','665fc434','0a22a76e','4697ea5f']:
 p=S/'assets/css'/f'{h}.css';s=p.read_text()
 if h=='3ba1e7fa':s=rules(s,lambda sel,b:'content:none;' if re.fullmatch(r'\.tile(?:\.t-[\w-]+)?::before',sel) else b)
 if h=='9a7074ed':
  def learn(sel,b):
   if sel=='.rail a':
    b=re.sub(r'border-(?:left|bottom)(?:-color)?\s*:[^;]+;?','',b)
    b=b.replace('margin-left:-1px','').replace('padding:7px 0 7px 16px','padding:7px 10px')
    return b.rstrip(';')+';border:1px solid transparent;border-radius:8px;'
   if sel=='.rail a.on':
    b=re.sub(r'border-(?:left|bottom)(?:-color)?\s*:[^;]+;?','',b)
    return b.rstrip(';')+';border-color:var(--hair);background:var(--squall);font-weight:600;'
   return b
  s=rules(s,learn)
 if h=='a8e92904':
  current=next(b for sel,b,*_ in scan.rules((R/'templates/fund_dossier.html.j2').read_text()) if sel=='.lean-hero')
  s=rules(s,lambda sel,b:current if sel=='.lean-hero' else b)
 if h=='665fc434':
  s=s.replace('border-left: 3px solid var(--ok);','border:1px solid var(--line);').replace('border-radius: 0 var(--radius-sm) var(--radius-sm) 0;','border-radius:var(--radius-sm);').replace('border-left-color: var(--warn);','')
  s=rules(s,lambda sel,b:b+' color:var(--ok);' if sel=='.verdict strong' else b)
  s+='\n.verdict.none strong { color:var(--warn); }\n'
 if h=='0a22a76e':s=rules(s,start)
 if h=='4697ea5f':s=rules(s,lambda sel,b:'content:none;' if sel=='.card::before' else b)
 assert s!=p.read_text(),h
 newh=hashlib.sha256(s.encode()).hexdigest()[:8];q=p.with_name(newh+'.css')
 if q.exists():assert q.read_text()==s
 else:q.write_text(s)
 rename[h]=newh;record.append(dict(path=str(q.relative_to(R)),from_path=str(p.relative_to(R)),before=hashlib.sha256(p.read_bytes()).hexdigest(),after=hashlib.sha256(s.encode()).hexdigest()))
for folder in [S,R/'templates']:
 for p in folder.rglob('*.html'):
  s=p.read_text();new=s
  for old,h in rename.items():new=new.replace('/'+old+'.css','/'+h+'.css').replace(h+'.css?v='+old,h+'.css?v='+h)
  write(p,new)
(E/'direct-source-edge-repairs.json').write_text(json.dumps(dict(changes=record,renamed=rename,preserved_functional=['product stage sequence','AI entry-point connectors','Intraday Flow center axis','dashboard branching and engine-bus connectors','cycle column separators','odds grouped-table separator','start-page mobile hit area']),indent=2)+'\n')
print(json.dumps(dict(files=len(record),renamed=rename)),flush=True)
