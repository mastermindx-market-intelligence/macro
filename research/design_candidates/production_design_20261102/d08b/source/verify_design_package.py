"""Verify fixture mathematics and static artifact integrity, never product behavior.

Run from any working directory. Requires Pillow only for reading screenshot sizes.
This checker makes no Paper, network, source-store or product mutation.
"""
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime
from collections import Counter
import json, math, re, sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return json.loads((ROOT / name).read_text())

checks = []
def check(name, condition, evidence):
    checks.append({'check': name, 'status': 'PASS' if condition else 'FAIL', 'evidence': evidence})

f = read('source/illustrative-fixture.json')
m = f['netGammaMillions']
totals = list(map(sum, m))
check('Matrix dimensions and row totals', len(m) == 9 and all(len(r) == 6 for r in m) and totals == [68,84,165,281,187,525,-400,-255,-155], {'rowTotalsMillions': totals})
check('Qualified known subtotal is 500M, not complete-book total', sum(totals) == f['knownNetGammaSubtotalMillions'] == 500 and f['population'] == {'reported':112,'qualified':108,'excluded':4,'marketCoverage':None}, {'knownSubtotalMillions':sum(totals),'population':f['population']})
s = f['selection']
now = s['callGammaMillions'] + s['putGammaMillions']
prev = s['priorCallGammaMillions'] + s['priorPutGammaMillions']
gross_now = abs(s['callGammaMillions']) + abs(s['putGammaMillions'])
gross_prev = abs(s['priorCallGammaMillions']) + abs(s['priorPutGammaMillions'])
check('Selected node and net/gross observed change', (now,prev,now-prev,gross_now,gross_prev,gross_now-gross_prev) == (268,224,44,532,536,-4), {'netNow':now,'netPrior':prev,'netChange':now-prev,'grossNow':gross_now,'grossPrior':gross_prev,'grossChange':gross_now-gross_prev})
dist = 100*(s['strike']-f['spot'])/f['spot']
check('Strike distance uses declared spot denominator', round(dist,2) == -0.28, {'distancePercent':dist})
v=f['volatility']
check('Missing IV points stay missing and selected expiry stays Nov 20', v['atmIvPercent'][1] is None and v['callIvPercent'][3] is None and v['selectedExpiry']=='2026-11-20' and v['atmIvPercent'][2]==17.2, {'atmIvPercent':v['atmIvPercent'],'callIvPercent':v['callIvPercent'],'selectedExpiry':v['selectedExpiry']})

c = read('source/comparison-illustrative-fixture.json')
key=lambda r:(r['expiry'],r['strike'],r['right'])
p={key(r):r['valueMillions'] for r in c['previous']}
q={key(r):r['valueMillions'] for r in c['current']}
finite=lambda x:isinstance(x,(int,float)) and math.isfinite(x)
matched={k for k in p.keys() & q.keys() if finite(p[k]) and finite(q[k])}
gained={k for k in p.keys() & q.keys() if not finite(p[k]) and finite(q[k])}
lost={k for k in p.keys() & q.keys() if finite(p[k]) and not finite(q[k])}
counts={'previousOnly':len(p.keys()-q.keys()),'currentOnly':len(q.keys()-p.keys()),'qualificationGained':len(gained),'qualificationLost':len(lost),'finiteMatched':len(matched),'previousQualified':sum(map(finite,p.values())),'currentQualified':sum(map(finite,q.values()))}
check('Nonzero cohort exclusions reconcile without contaminating matched change', counts=={'previousOnly':1,'currentOnly':1,'qualificationGained':1,'qualificationLost':1,'finiteMatched':2,'previousQualified':4,'currentQualified':4} and sum(q[k]-p[k] for k in matched)==44 and sum(abs(q[k])-abs(p[k]) for k in matched)==-4, counts)
dt=datetime.fromisoformat
allow = max(dt(c['previousAvailableAt']),dt(c['currentAvailableAt'])) <= dt(c['knowledgeCutoff'])
historical_refuses = dt(c['currentAvailableAt']) > dt('2026-11-02T16:15:00-05:00')
check('Illustrative cutoff admits current knowledge and refuses Nov 2 knowledge', allow and historical_refuses, {k:c[k] for k in ['knowledgeCutoff','cutoffMode','previousAvailableAt','currentAvailableAt']})

chain=read('source/chain-illustrative-fixture.json')
rows=chain['rows']; doi=[r['doi'] for r in rows if finite(r['doi'])]
sel=next(r for r in rows if r['expiry']=='2026-11-06' and r['strike']==750 and r['side']=='C')
check('Published chain point count, size domain and selected row', len(rows)==30 and sum(x!=0 for x in doi)==28 and sum(x==0 for x in doi)==1 and len(rows)-len(doi)==1 and max(map(abs,doi))==657 and sel['doi']==-320 and sel['oi']==7850 and chain['oiPositionSession'] is None and chain['availableAt'] is None, {'rows':len(rows),'nonzeroMarks':sum(x!=0 for x in doi),'measuredZero':sum(x==0 for x in doi),'missing':len(rows)-len(doi),'maximumAbsDoi':max(map(abs,doi)),'selected':sel})

boards=read('source/paper-compositions.json')
check('Exactly 18 unique editable board payloads', len(boards)==18 and len({b['key'] for b in boards})==18 and {b['key'] for b in boards}=={f'B{i:02d}' for i in range(18)}, {'boardCount':len(boards),'compositionFragments':sum(len(b['ops']) for b in boards)})
dims=[]
for b in boards:
    with Image.open(ROOT/'evidence'/f"{b['key']}.jpg") as im:
        dims.append({'board':b['key'],'expected':[b['width'],b['height']],'actual':list(im.size),'format':im.format})
check('Native Paper screenshots match exact board dimensions', all(x['actual']==x['expected'] and x['format']=='JPEG' for x in dims), dims)

class FirstTag(HTMLParser):
    def __init__(self):super().__init__();self.attrs=None
    def handle_starttag(self,tag,attrs):
        if self.attrs is None:self.attrs=dict(attrs)
bounds=[];outside=[]
for b in boards:
    for o in b['ops']:
        if o.get('target'):continue
        p=FirstTag();p.feed(o['html']);style=p.attrs.get('style','')
        css={k.strip():v.strip() for k,v in re.findall(r'([\w-]+)\s*:\s*([^;]+)',style)}
        if css.get('position')!='absolute':continue
        def px(k):return float(css[k].removesuffix('px'))
        x,y,w,h=[px(k) for k in ['left','top','width','height']]
        r={'board':b['key'],'fragment':o['name'],'box':[x,y,w,h]}
        bounds.append(r)
        if min(x,y)<0 or x+w>b['width']+.01 or y+h>b['height']+.01:outside.append(r)
check('Declared top-level composition boxes stay inside artboards', not outside, {'checked':len(bounds),'outside':outside,'limit':'Does not measure nested text overflow, browser layout or reflow.'})

D={'bg':'#0F1115','panel':'#181B21','raised':'#1E222A','text':'#D7DCE3','muted':'#A5ACB8','blue':'#7AA7E0','pos':'#65CCD2','neg':'#D1A1E4','gold':'#E6BE68'}
L={'bg':'#F7F8FA','panel':'#FFFFFF','raised':'#EEF1F6','text':'#1C2430','muted':'#5D6B7E','blue':'#2758E6','pos':'#14676E','neg':'#794A91','gold':'#865D13'}
def rgb(h):return [int(h[i:i+2],16)/255 for i in (1,3,5)]
def lum(x):return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for w,v in zip([.2126,.7152,.0722],rgb(x) if isinstance(x,str) else x))
def contrast(a,b):
    x,y=sorted([lum(a),lum(b)]);return (y+.05)/(x+.05)
ratios=[]
for name,t in [('dark',D),('light',L)]:
    for fg in ['text','muted','blue','pos','neg','gold']:
        for bg in ['bg','panel','raised']:
            ratios.append({'theme':name,'foreground':fg,'background':bg,'ratio':contrast(t[fg],t[bg])})
check('Named text palette pairs meet 4.5 to 1', min(x['ratio'] for x in ratios)>=4.5, {'minimum':min(ratios,key=lambda x:x['ratio']),'pairCount':len(ratios),'limit':'Calculated sRGB color pairs only; no complete WCAG claim.'})
cells=[]
for name,t in [('dark',D),('light',L)]:
    for r in m:
        for val in r:
            exact_op=.12+.65*math.sqrt(abs(val)/268)
            color=t['pos'] if val>=0 else t['neg']
            exact_bg=[a*exact_op+b*(1-exact_op) for a,b in zip(rgb(color),rgb(t['panel']))]
            fg=max(['#FFFFFF','#000000'],key=lambda x:contrast(x,exact_bg))
            op=round(exact_op,3)
            bg=[a*op+b*(1-op) for a,b in zip(rgb(color),rgb(t['panel']))]
            cells.append({'theme':name,'value':val,'foreground':fg,'ratio':contrast(fg,bg)})
check('Heatmap label contrast uses actual rounded alpha', min(x['ratio'] for x in cells)>=4.5, {'minimum':min(cells,key=lambda x:x['ratio']),'cellThemeCases':len(cells)})

widths=[]
for w in [320,390,768,1024,1280,1440,1600]:
    rail=224 if w>=1200 else 196 if w>860 else 0
    gutter=16 if w<=600 else 20 if w<1200 else 24
    content=w-rail-2*gutter
    dock=320 if content>=984 else 0
    widths.append({'viewport':w,'rail':rail,'gutterEach':gutter,'content':content,'inspector':dock,'primary':content-dock-(24 if dock else 0)})
check('Useful widths match candidate.4 geometry', [x['content'] for x in widths]==[288,358,728,788,1008,1168,1328] and all(not x['inspector'] or x['primary']>=640 for x in widths), widths)

ledger=read('CAPABILITY_LEDGER.json')
check('Retention ledger contains 60 distinct records', len(ledger['items'])==60 and len({x['id'] for x in ledger['items']})==60 and dict(Counter(x['disposition'] for x in ledger['items']))=={k:v for k,v in ledger['counts'].items() if v}, {'declaredCounts':ledger['counts'],'itemCount':len(ledger['items'])})
missing=[]
for path in ROOT.glob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)',path.read_text()):
        target=target.split('#',1)[0]
        if not target or re.match(r'^[a-zA-Z]+:',target):continue
        if not (path.parent/target).exists():missing.append({'file':path.name,'target':target})
check('Local Markdown artifact links resolve', not missing, {'missing':missing})

result={'scope':'D08B static design artifact verification; no product runtime validation','status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL','checks':checks,'unverified':['Browser functionality of the candidate','Keyboard, touch, screen reader and focus implementation','200% text and 400% browser reflow','Actual backend schema/cache/data guarantees beyond audited source','Formal admitted RIG approval','F01/F02 foundation release','Production implementation and deployment']}
(ROOT/'VERIFICATION_RESULTS.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[c for c in checks if c['status']=='FAIL']},ensure_ascii=False))
sys.exit(0 if result['status']=='PASS' else 1)
