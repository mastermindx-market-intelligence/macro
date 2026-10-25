"""Verify Dark Pool participation never exceeds the physical 100% bound."""
from __future__ import annotations
import argparse, hashlib, html, json, re, urllib.request
from pathlib import Path

ap=argparse.ArgumentParser()
g=ap.add_mutually_exclusive_group(required=True)
g.add_argument('--site-dir', type=Path)
g.add_argument('--base-url')
ap.add_argument('--output', type=Path)
a=ap.parse_args()

def read(rel: str) -> bytes:
    if a.site_dir is not None:
        return (a.site_dir / rel).read_bytes()
    url=a.base_url.rstrip('/')+'/'+rel
    with urllib.request.urlopen(url, timeout=30) as r:  # no auth, no interception
        if r.status != 200: raise RuntimeError(f'{url}: HTTP {r.status}')
        return r.read()

body=read('darkpool.html')
text=body.decode('utf-8')
m=re.search(r'<script[^>]+id="dp-data"[^>]*>(.*?)</script>', text, re.S)
if not m: raise SystemExit('dp-data payload missing')
rows=json.loads(html.unescape(m.group(1)))
vals=[float(r['participation']) for r in rows if r.get('participation') is not None]
bad=[{'ticker':r.get('ticker'),'asof':r.get('asof'),'participation':r.get('participation')}
     for r in rows if r.get('participation') is not None and float(r['participation']) > 1]
result={'html_sha256':hashlib.sha256(body).hexdigest(),'rows':len(rows),'participation_rows':len(vals),
        'max_participation':max(vals) if vals else None,'impossible_rows':bad,'passed':bool(rows) and not bad}
if a.site_dir is not None:
    pane=json.loads(read('darkpool_eod.json'))
    prows=list(pane.get('universe') or [])+list(pane.get('historical_rows') or [])
    ctx=json.loads((a.site_dir.parent/'data/darkpool/context/latest.json').read_text())
    result['pane_impossible']=sum(r.get('participation') is not None and float(r['participation'])>1 for r in prows)
    result['context_impossible']=sum(r.get('participation') is not None and float(r['participation'])>1 for r in ctx.get('standouts') or [])
    result['invalid_current']=ctx['coverage'].get('n_invalid_current_participation')
    result['invalid_history_filtered']=ctx['coverage'].get('n_invalid_participation_rows')
    result['passed']=result['passed'] and result['pane_impossible']==0 and result['context_impossible']==0
print(json.dumps(result,ensure_ascii=False,sort_keys=True))
if a.output:
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
raise SystemExit(0 if result['passed'] else 1)
