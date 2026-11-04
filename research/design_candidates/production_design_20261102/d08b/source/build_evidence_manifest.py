"""Freeze local artifact hashes; Git commit supplies immutable review identity."""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
targets=json.loads((ROOT/'source/paper-targets.json').read_text())
boards=json.loads((ROOT/'source/paper-compositions.json').read_text())
def digest(path):
    raw=path.read_bytes()
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'gitBlobSha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
inventory=[]
for p in sorted(ROOT.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts or p.name=='EVIDENCE_MANIFEST.json':continue
    if p.suffix not in {'.md','.json','.py','.jpg'}:continue
    inventory.append({'path':str(p.relative_to(ROOT)),**digest(p)})
artboards=[]
for b in sorted(boards,key=lambda b:b['key']):
    p=ROOT/'evidence'/f"{b['key']}.jpg"
    with Image.open(p) as im:size=list(im.size)
    captures=[x for x in targets['captureReceipts'] if x['key']==b['key']]
    artboards.append({'key':b['key'],'nodeId':targets['boardRoots'][b['key']],'pageId':'p-14-0' if b['key']=='B00' else 'p-12-0','name':b['name'],'width':b['width'],'height':b['height'],'theme':b['theme'],'locale':b['locale'],'evidence':str(p.relative_to(ROOT)),'screenshotDimensions':size,**digest(p),'captureReceipt':captures[-1] if captures else {'sessionDate':'2026-11-04','exactTimestamp':None,'note':'Final native screenshot after this board’s last content change, reviewed in this session. No exact timestamp retained in compact capture record.'}})
manifest={'schema':'d08b.design_evidence/v1','status':'reviewable_candidate_rig_draft','artifactDate':'2026-11-04','immutability':'This manifest and its files are frozen by the containing Git commit. Live Paper URLs and snapshot guards are mutable, not approval identities.','file':{k:targets[k] for k in ['fileId','fileName','pages']},'pins':targets['sourcePins'],'catalog':targets['catalog'],'artboards':artboards,'evidenceClasses':{'candidate':'evidence/B00.jpg through B17.jpg are actual native Paper screenshots of labeled illustrative fixtures.','incumbentPaper':['evidence/before_exposure.jpg','evidence/before_vol.jpg','evidence/before_3d.jpg','evidence/before-exposure-r2-phone.jpg'],'servedBrowserBaseline':['evidence/production-matrix-settled.jpg','evidence/production-volatility-read-failure.jpg']},'readLimit':'An optional concurrent recapture yielded an image only for B00; no-image responses are not evidence. Final affected captures were obtained sequentially; unchanged reviewed screenshots were retained.','inventory':inventory,'selfHashExcluded':True}
(ROOT/'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'artboards':len(artboards),'inventoryFiles':len(inventory),'bytes':sum(x['bytes'] for x in inventory)}))
