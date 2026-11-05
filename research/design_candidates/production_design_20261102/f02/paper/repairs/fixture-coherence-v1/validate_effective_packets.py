#!/usr/bin/env python3
"""Independent Decimal/HTML checks of v3 deliverables; no runtime or Paper calls."""
import hashlib,json,re
from decimal import Decimal,ROUND_HALF_UP,getcontext
from html.parser import HTMLParser
from pathlib import Path
getcontext().prec=60
HERE=Path(__file__).resolve().parent;PAPER=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
class Text(HTMLParser):
 def __init__(self):super().__init__();self.values=[]
 def handle_data(self,s):
  s=re.sub(r'\s+',' ',s).strip()
  if s:self.values.append(s)
def vals(h):p=Text();p.feed(h);return p.values
def rounded(x,places):return f'{x.quantize(Decimal(1).scaleb(-places),rounding=ROUND_HALF_UP):.{places}f}'
data=[(286,207,201),(267,189,185),(500,346,343),(177,118,116),(375,238,241),(54,33,33),(333,194,198),(0,None,None),(250,139,138),(500,261,264)]
order=[0,1,2,3,4,5,6,8,9,7]
results=[];charts=[];packets={}
for path in sorted((HERE/'effective').glob('*.json')):
 if path.name=='supplemental-wide-clone.json':continue
 o=json.loads(path.read_text());packets[path.name]=o
 for b in o.get('boards',[])+o.get('append_to_existing',[]):
  bk=b.get('key',b.get('target_board_key'))
  rows=[s for s in b['steps'] if re.fullmatch(r'sector-\d+',s['key'])]
  if len(rows)==10:
   base=min(int(s['key'].split('-')[1]) for s in rows)
   assert [int(s['key'].split('-')[1])-base for s in rows]==order,bk
   header=next(s for s in b['steps'] if s['key'] in ['table','table-header'])
   assert any('↓' in v for v in vals(header['html'])),bk
   for s in rows:
    i=int(s['key'].split('-')[1])-base;d,n,p=data[i];v=vals(s['html'])
    if d:
     current=Decimal(n)*100/Decimal(d);prior=Decimal(p)*100/Decimal(d);delta=current-prior
     rate=rounded(current,1)+'%';change=('+' if delta>0 else '')+rounded(delta,2)
     assert rate in v,(bk,s['key'],rate,v)
     assert change in v,(bk,s['key'],change,v)
     assert f'{d} / {d}' in v,(bk,s['key'],v)
    else:assert '0 / 82' in v and v.count('—')==2,(bk,v)
   results.append({'board':bk,'raw_rate_descending_energy_last':True,'visible_sort_arrow':True,'all_ten_coverage_and_rate_labels_match':True})
  for s in b['steps']:
   if s['key'] in ['chart','history-chart'] and (bk.startswith('macro-') or bk.startswith('width-') or bk=='grammar'):
    svg=re.search(r'<svg\b.*?</svg>',s['html'],re.S).group(0)
    pts=[(Decimal(x),Decimal(y)) for x,y in re.findall(r'<circle\b[^>]*cx="([0-9.]+)"[^>]*cy="([0-9.]+)"',svg)]
    assert len(pts)==7,(bk,len(pts))
    w=Decimal(re.search(r'<svg[^>]*width="([0-9.]+)"',svg).group(1))
    if bk=='grammar':x0,pw,y0,ph,lo,hi=map(Decimal,[80,1176,54,150,50,80])
    elif s['key']=='history-chart':x0,pw,y0,ph,lo,hi=map(Decimal,[44,758,16,132,40,80])
    else:x0,pw,y0,ph,lo,hi=Decimal(44),w-64,Decimal(20),Decimal(140),Decimal(40),Decimal(80)
    ns=[657,663,None,679,673,687,697,709];expected=[]
    for i,n in enumerate(ns):
     if n is not None:expected.append((x0+Decimal(i)*pw/7,y0+(hi-Decimal(n)*100/1063)/(hi-lo)*ph))
    assert all(abs(a-c)<Decimal('0.000002') and abs(b-d)<Decimal('0.000002') for (a,b),(c,d) in zip(pts,expected)),bk
    lines=re.findall(r'<line\b[^>]*stroke-width="(?:2(?:\.5)?|3)"[^>]*/>',svg)
    assert len(lines)==5,(bk,len(lines))
    # There must be no point or segment spanning the missing third session.
    gap_x=x0+2*pw/7
    for line in lines:
     x1=Decimal(re.search(r'x1="([0-9.]+)"',line).group(1));x2=Decimal(re.search(r'x2="([0-9.]+)"',line).group(1))
     assert not min(x1,x2)<gap_x<max(x1,x2),bk
    charts.append({'board':bk,'points':7,'data_segments':5,'gap_date':'23 Oct','coordinates_match_integer_counts':True})

manifest=json.loads((HERE/'packet-manifest.json').read_text())
assert all(sha((PAPER/p['original_packet']).read_bytes())==p['original_sha256'] for p in manifest['packets'])
assert all(sha((HERE/p['effective_packet']).read_bytes())==p['effective_sha256'] for p in manifest['packets'])
original_core=json.loads((PAPER/'core-supplement-inputs.json').read_text())
original_mobile=json.loads((PAPER/'mobile-inputs/mobile-state-boards.json').read_text())
for name,original,effective in [('options-full-row-evidence-320',original_core,packets['core-supplement-inputs.json']),('company-eps-overlay-320',original_mobile,packets['mobile-state-boards.json']),('company-dividend-overlay-320',original_mobile,packets['mobile-state-boards.json'])]:
 assert next(b for b in original['boards'] if b['key']==name)==next(b for b in effective['boards'] if b['key']==name)
universe=Decimal(709)*100/1063;prior=Decimal(697)*100/1063
assert [rounded(universe,2),rounded(prior,2),rounded(universe-prior,2),rounded((universe-prior)*100,0),rounded((universe/prior-1)*100,2)]==['66.70','65.57','1.13','113','1.72']
communication=Decimal(118)*100/177;comm_prior=Decimal(116)*100/177
assert [rounded(communication,2),rounded(comm_prior,2),rounded(communication-comm_prior,2)]==['66.67','65.54','1.13']
for name,o in packets.items():
 for b in o.get('boards',[])+o.get('append_to_existing',[]):
  bk=b.get('key',b.get('target_board_key'))
  if bk.startswith('macro-') or bk.startswith('width-'):
   assert 'f02.fixture.v2/macro/' not in json.dumps(b,ensure_ascii=False)
report={'schema':'f02.fixture-effective-validation.v1','status':'SOURCE_CHECKS_PASS_NATIVE_EFFECTS_NOT_ASSERTED','method':'Independent Decimal arithmetic from integer tuples plus actual effective HTML labels/order/point coordinates; no import of the generator.',
 'table_boards':results,'chart_boards':charts,'original_source_hashes_unchanged':True,'effective_hashes_match_manifest':True,'company320_and_options320_subtrees_unchanged':True,'universe_and_communication_rounding_distinct':True,'core_math':{'it':'742/1000=74.20%;721/1000=72.10%;+2.10pp;coverage1000/1006','utilities':'132/250=52.80%;133/250=53.20%;-0.40pp;coverage250/250'},'paper_calls':0,'browser_calls':0}
out=HERE/'independent-source-validation.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'table_boards':len(results),'charts':len(charts),'sha256':sha(out.read_bytes())},indent=2))
