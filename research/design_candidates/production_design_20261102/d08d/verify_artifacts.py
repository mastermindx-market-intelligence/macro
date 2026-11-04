"""Check D08D source-artifact integrity, never product/market behavior.

Run with --freeze to write a local check receipt and a new artifact manifest.
Run without flags to verify the current immutable manifest. No network access.
"""
from pathlib import Path
import ast
import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / 'evidence/artifact-manifest.json'
RECEIPT = ROOT / 'evidence/artifact-verification.json'
checks = []

def require(condition, name, detail):
    if not condition:
        raise AssertionError(name + ': ' + str(detail))
    checks.append({'check': name, 'result': 'PASS', 'detail': detail})

def digest(path):
    b = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(b),
            'sha256': hashlib.sha256(b).hexdigest(),
            'gitBlobSha1': hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}

jsons = list(ROOT.rglob('*.json'))
for p in jsons:
    json.loads(p.read_text())
require(True, 'JSON parseability', len(jsons))

source = json.loads((ROOT/'evidence/source-manifest.json').read_text())
require(len(source) == 31 and len({e['path'] for e in source}) == 31,
        'Audited source manifest', '31 unique observed source paths')
require(all(e['observed'] and e['commit']=='2ded360882b9c721e690907ff363b553781fb920'
            and re.fullmatch('[a-f0-9]{40}',e['blobSha']) for e in source),
        'Source identities', 'All31 bind the same Terminal commit and an exact blob SHA')

ledger = json.loads((ROOT/'evidence/feature-ledger.json').read_text())
counts = {}
for e in ledger['entries']:
    counts[e['disposition']] = counts.get(e['disposition'],0)+1
require(len(ledger['entries'])==52 and counts==ledger['counts'] and counts.get('REMOVE',0)==0,
        'Capability ledger', counts)
md_ids = re.findall(r'^\| ([FEJP][0-9]{2}) \|', (ROOT/'FEATURE_LEDGER.md').read_text(), re.M)
require(set(md_ids)=={e['id'] for e in ledger['entries']} and len(md_ids)==52,
        'Ledger table agrees with JSON', '52 identical IDs')

case_ids = re.findall(r'^\| ([JQAFETUS][0-9]{2}) \|', (ROOT/'ACCEPTANCE_TESTS.md').read_text(), re.M)
require(len(case_ids)==76 and len(set(case_ids))==76,
        'Acceptance specification identifiers', '76 unique future cases; NOT_RUN')
scenarios = re.findall(r'^  Scenario:', (ROOT/'acceptance.feature').read_text(), re.M)
require(len(scenarios)==16, 'Gherkin specification', '16 scenarios; no executed steps')

freeze = json.loads((ROOT/'review-input/first-pass-artifacts.json').read_text())
for e in freeze['files']:
    d = digest(ROOT/'review-input'/e['file'])
    require(d['sha256']==e['sha256'] and d['bytes']==e['bytes'],
            'Frozen first-pass image', e['file'])
require(len(freeze['files'])==9, 'First-pass input count', 9)

study_names = json.loads((ROOT/'studies/study-manifest.json').read_text())['files']
require(len(study_names)==14, 'Supporting study count', 14)
dimensions=[]
for folder in ['studies','review-input']:
    for svg in sorted((ROOT/folder).glob('*.svg')):
        node=ET.parse(svg).getroot()
        expected=(int(node.attrib['width']),int(node.attrib['height']))
        png=svg.with_suffix('.png'); b=png.read_bytes()
        actual=struct.unpack('>II',b[16:24])
        require(b[:8]==b'\x89PNG\r\n\x1a\n' and actual==expected,
                'SVG/PNG rendered dimensions', {'file':str(png.relative_to(ROOT)),'pixels':list(actual)})
        dimensions.append({'file':str(png.relative_to(ROOT)),'width':actual[0],'height':actual[1]})

link_count=0
for md in ROOT.rglob('*.md'):
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',md.read_text()):
        if target.startswith(('https://','http://','sandbox:','#','mailto:')):
            continue
        target=target.split('#',1)[0]
        require((md.parent/target).exists(),'Relative Markdown target',str(md.relative_to(ROOT))+': '+target)
        link_count+=1
for target in re.findall(r'(?:href|src)="([^"]+)"',(ROOT/'studies/index.html').read_text()):
    require((ROOT/'studies'/target).exists(),'Gallery target',target)
for p in ROOT.rglob('*.py'):
    ast.parse(p.read_text())
require(True,'Supporting Python syntax','Static source helpers only; no product code')

if '--freeze' in sys.argv:
    receipt={'scope':'Local source-artifact checks only; no production, native Paper, accessibility or formal review acceptance',
             'dateUTC':'2026-11-04','result':'PASS','checkCount':len(checks),'checks':checks,
             'studyCount':14,'firstPassCount':9,'sourceCount':31,'ledgerCount':52,
             'acceptanceCases':76,'acceptanceExecutionStatus':'NOT_RUN','gherkinScenarios':16,
             'dimensions':dimensions,'localMarkdownLinks':link_count,
             'visualInspection':'Root inspected rendered study captures and repaired observed issues; no independent final reference approval'}
    RECEIPT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    entries=[digest(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=MANIFEST and '__pycache__' not in p.parts]
    manifest={'artifact':'D08D source/specification and illustrative study freeze',
              'canonicalIdentity':'The enclosing Git commit; this manifest is not a RIG approval',
              'excludes':['evidence/artifact-manifest.json (self digest)'],
              'files':entries,'fileCountExcludingManifest':len(entries)}
    MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
else:
    manifest=json.loads(MANIFEST.read_text())
    for e in manifest['files']:
        require(digest(ROOT/e['path'])==e,'Committed artifact digest',e['path'])
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and p!=MANIFEST and '__pycache__' not in p.parts}
    require(actual=={e['path'] for e in manifest['files']},'Manifest membership','No unlisted artifact files')
print(json.dumps({'result':'PASS','scope':'artifact integrity only','checks':len(checks),
                  'studies':14,'firstPassUnchanged':9,'sources':31,'ledger':52,'futureCasesNotRun':76,
                  'packageFiles':sum(1 for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts)},ensure_ascii=False))
