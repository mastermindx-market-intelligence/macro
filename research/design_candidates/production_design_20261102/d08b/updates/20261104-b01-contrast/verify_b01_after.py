from pathlib import Path
import json, re, math, hashlib
import xml.etree.ElementTree as ET
from collections import Counter
from PIL import Image

BASE = Path(__file__).resolve().parent
PAYLOAD = BASE.parents[1] / 'source' / 'paper-compositions.json'

def svg_root(text, root_id=None):
    blocks = re.findall(r'<svg\b.*?</svg>', text, re.S)
    if root_id:
        blocks = [b for b in blocks if f'id="{root_id}"' in b.split('>',1)[0]]
    assert len(blocks) == 1, (root_id, len(blocks))
    cleaned = re.sub(r'\sstyle=\{\{.*?\}\}', '', blocks[0], flags=re.S)
    return ET.fromstring(cleaned)

def local_tag(n):
    return n.tag.split('}')[-1]

def text_value(n):
    t = ''.join(n.itertext()).strip()
    if t.startswith('{') and t.endswith('}'):
        return json.loads(t[1:-1])
    return t

def num_attr(n, name, default=None):
    name2 = {'font-size':'fontSize','stroke-width':'strokeWidth','fill-opacity':'fillOpacity'}.get(name,name)
    v = n.attrib.get(name,n.attrib.get(name2,default))
    return float(v) if v is not None else None

def cells(root):
    children = list(root)
    out = []
    for a,b in zip(children,children[1:]):
        if local_tag(a) != 'rect' or local_tag(b) != 'text':
            continue
        t = text_value(b)
        if not re.fullmatch(r'[+\-−]\d+',t):
            continue
        fill = a.attrib['fill'].upper()
        alpha = int(fill[7:9],16)/255 if len(fill)==9 else num_attr(a,'fill-opacity',1)
        out.append({
            'value':t,'fg':b.attrib['fill'].upper(),'fillRGB':fill[:7],
            'alphaByte':int(fill[7:9],16) if len(fill)==9 else math.floor(alpha*255+0.5),
            'sourceAlpha':alpha,
            **{k:num_attr(a,k) for k in ['x','y','width','height','rx']},
            'textX':num_attr(b,'x'),'textY':num_attr(b,'y'),'fontSize':num_attr(b,'font-size'),
            'stroke':a.attrib.get('stroke','none').upper(),'strokeWidth':num_attr(a,'stroke-width',0),
            '_rect':a,'_text':b
        })
    return out

def srgb_linear(x):
    return x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4

def rgb(h):
    return [int(h[i:i+2],16)/255 for i in (1,3,5)]

def luminance(v):
    return sum(w*srgb_linear(x) for w,x in zip((0.2126,0.7152,0.0722),v))

def ratio(fg, fill, alpha, panel='#181B21'):
    bg=[s*alpha+d*(1-alpha) for s,d in zip(rgb(fill),rgb(panel))]
    a,b=luminance(rgb(fg)),luminance(bg)
    return (max(a,b)+0.05)/(min(a,b)+0.05)

def serializable(c):
    return {k:v for k,v in c.items() if not k.startswith('_')}

def canonical(n, ignore_cell_ink=False, cell_text_ids=None):
    attrs={k:v for k,v in n.attrib.items() if k!='id'}
    if ignore_cell_ink and id(n) in cell_text_ids: attrs.pop('fill',None)
    return [local_tag(n),sorted(attrs.items()),(n.text or '').strip(),[canonical(c,ignore_cell_ink,cell_text_ids) for c in n]]

board = next(b for b in json.loads(PAYLOAD.read_text()) if b['key']=='B01')
expected_svg = svg_root(next(op['html'] for op in board['ops'] if op['name']=='matrix'))
actual_svg = svg_root((BASE/'B01-after-1NZL-0.jsx').read_text(),'1SDU-0')
before_svg = svg_root((BASE/'B01-matrix-1ONW-0.jsx').read_text())
expected, actual, before = cells(expected_svg), cells(actual_svg), cells(before_svg)
assert len(expected)==len(actual)==len(before)==54
fields_exact=['value','fg','fillRGB','alphaByte','stroke']
fields_numeric=['x','y','width','height','rx','textX','textY','fontSize','strokeWidth']
differences=[]
for i,(a,e) in enumerate(zip(actual,expected)):
    errors={k:[a[k],e[k]] for k in fields_exact if a[k]!=e[k]}
    for k in fields_numeric:
        if a[k] is None or e[k] is None:
            if a[k]!=e[k]: errors[k]=[a[k],e[k]]
        elif abs(a[k]-e[k])>0.00051: errors[k]=[a[k],e[k]]
    if errors:differences.append({'cellIndex':i,'errors':errors})
contrast=[]
for i,a in enumerate(actual):
    contrast.append({'cellIndex':i,**serializable(a),'contrast':ratio(a['fg'],a['fillRGB'],a['alphaByte']/255)})
before_after_preserved = canonical(before_svg,True,{id(c['_text']) for c in before})==canonical(actual_svg,True,{id(c['_text']) for c in actual})
changed_ink=[{'cellIndex':i,'value':a['value'],'before':b['fg'],'after':a['fg']} for i,(b,a) in enumerate(zip(before,actual)) if a['fg']!=b['fg']]
hashes={}
for name in ['B01-live-before-repair.jpg','B01-live-after-repair.jpg','B01-after-1NZL-0.jsx']:
    data=(BASE/name).read_bytes()
    hashes[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
with Image.open(BASE/'B01-live-after-repair.jpg') as im:
    dimensions=list(im.size)
result={
    'fileId':'01M3NSZGE8JWN2EZCSF0DT05RM','artboardId':'1NZL-0','matrixId':'1ONW-0','svgId':'1SDU-0',
    'actualCells':len(actual),'expectedCells':len(expected),'differentCells':len(differences),'differences':differences,
    'foregroundCounts':dict(Counter(c['fg'] for c in actual)),
    'allOtherNativeSvgContentUnchanged':before_after_preserved,
    'foregroundChanges':changed_ink,
    'contrastMethod':'WCAG relative luminance; actual native 8-bit RGBA alpha composited over #181B21 in sRGB, then linearized. Label foreground is native JSX.',
    'minimum':min(contrast,key=lambda c:c['contrast']),
    'below4_5':[c for c in contrast if c['contrast']<4.5],
    'cellResults':contrast,'screenshotDimensions':dimensions,'hashes':hashes,
    'scope':'Native Paper B01 matrix postcondition only; not browser or production acceptance'
}
(BASE/'B01-after-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['cellResults','foregroundChanges']},indent=2))
assert not differences
assert before_after_preserved
assert not result['below4_5']

