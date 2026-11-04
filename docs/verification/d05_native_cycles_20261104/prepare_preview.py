#!/usr/bin/env python3
"""Reproducible, local-only D05 preview. Run with PYTHONPATH=. from repository root.

Dependencies: Jinja2 plus the repository's i18n imports. Uses dated committed
fixtures; it never recalculates a market model, writes a forward log, or deploys.
"""
from pathlib import Path
import argparse, copy, hashlib, json, re, shutil, subprocess, tempfile
from jinja2 import Environment, FileSystemLoader
from engine import i18n
root=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description='Build a local D05 candidate from archived committed inputs; no engine run or forward-log write.')
parser.add_argument('--out', type=Path)
parser.add_argument('--scenario', choices=['archive','coherent','same-date-mismatch','mixed-series','missing-extras'], default='archive',
                    help='Synthetic scenarios exercise the real publication producer; none is live market evidence.')
args=parser.parse_args()
out=args.out or Path(tempfile.mkdtemp(prefix='d05-native-preview-'))
out.mkdir(parents=True,exist_ok=True)
source_ref='c53915f6d67078d5c0aeaf73bf85ddea1a23de03'
fixture_label='archived-source' if args.scenario=='archive' else 'synthetic-'+args.scenario
env=Environment(loader=FileSystemLoader(root/'templates'),autoescape=False)
env.globals.update(td=i18n.td,tr=i18n.tr,t=i18n.t)
for name in ['sector_central','sector_cycles']:
    html=env.get_template(name+'.html.j2').render(basket_member_syms=['SPY'])
    html=html.replace('<body ', '<body data-d05-fixture="'+fixture_label+'" ',1)
    html=html.replace('</body>','<div style="position:fixed;bottom:0;left:0;z-index:100000;background:var(--panel);color:var(--muted);padding:3px 8px;font:11px sans-serif">D05 TEST FIXTURE · '+fixture_label+' · not live</div></body>')
    (out/(name+'.html')).write_text(html)
assets=set(re.findall(r'(?:src|href)=[\'"]([^\'"?#]+)', '\n'.join((out/(n+'.html')).read_text() for n in ['sector_central','sector_cycles'])))
assets|={'sector_cycles_data.js','sector_cycles_series_data.js','sector_cycles_narr_data.js','sector_cycles_dna_data.js','sector_central_data.js'}
assets={a for a in assets if not a.startswith(('/','#','http','mailto:','data:')) and Path(a).suffix in {'.js','.css','.woff2','.svg'}}
known=set(subprocess.check_output(['git','-C',str(root),'ls-tree','-r','--name-only',source_ref,'site'],text=True).splitlines())
for a in sorted(assets):
    dst=out/a; dst.parent.mkdir(parents=True,exist_ok=True)
    src=root/'templates'/a
    if src.exists(): shutil.copy2(src,dst)
    elif 'site/'+a in known:
        dst.write_bytes(subprocess.check_output(['git','-C',str(root),'show',source_ref+':site/'+a]))
    else: print('Absent optional asset:',a)
# The page fetches these optional panels; use committed evidence when present.
for a in ['basketdata/baskets.json','marketdata/rotation_events.json','marketdata/sector_fragmentation.json']:
    if 'site/'+a in known:
        dst=out/a;dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(subprocess.check_output(['git','-C',str(root),'show',source_ref+':site/'+a]))
provenance={'fixture_only':True,'scenario':args.scenario,'source_ref':source_ref,'inputs':{}}
if args.scenario!='archive':
    from engine.leadership_rotation_context import measured_group_read
    from scripts._cycles_payload import publication_scripts, FAMILY_KEYS

    def archived(name, variable):
        raw=(out/name).read_bytes()
        provenance['inputs'][name]=hashlib.sha256(raw).hexdigest()
        text=raw.decode('utf-8').strip()
        match=re.fullmatch(r'window\.'+re.escape(variable)+r'\s*=\s*(.*?)\s*;?',text,re.S)
        if not match: raise ValueError('Expected one archived data assignment: '+name)
        return json.loads(match.group(1))

    full=archived('sector_cycles_data.js','SECTOR_CYCLES')
    series=archived('sector_cycles_series_data.js','SECTOR_CYCLES_SERIES')
    narr=archived('sector_cycles_narr_data.js','SECTOR_NARR')
    dna=archived('sector_cycles_dna_data.js','SECTOR_DNA')
    central=archived('sector_central_data.js','SECTOR_CENTRAL')
    records={row['id']:row for family in FAMILY_KEYS for row in full.get(family,[])}
    allowed={'price','osc','turns','fx','usd_record','rs_history'}
    for eid,part in series.items():
        if eid not in records or not isinstance(part,dict) or not set(part)<=allowed:
            raise ValueError('Archived split shape cannot be used for fixture reconstruction')
        records[eid].update(part)
    full['meta']['fixture_only']=True
    # These are NEW, explicitly synthetic test publications. No assertion is
    # made that the unstamped archives were originally published atomically.
    sources={kind:{'status':'available','reason':'fixture_only','records':len(value)}
             for kind,value in [('narr',narr),('dna',dna)]}
    publication=publication_scripts(full,narr,dna,sources=sources)
    central_input=full
    if args.scenario in {'same-date-mismatch','mixed-series'}:
        changed=copy.deepcopy(full)
        row=next(row for row in changed['sectors'] if row.get('price'))
        row['price'][0]['v'] += 1
        if args.scenario=='same-date-mismatch': central_input=changed
        else: publication['series']=publication_scripts(changed,narr,dna,sources=sources)['series']
    central['measured_read']=measured_group_read(central_input)
    (out/'sector_central_data.js').write_text('window.SECTOR_CENTRAL='+json.dumps(central,separators=(',',':'))+';\n')
    for kind,suffix in [('core','data'),('series','series_data'),('narr','narr_data'),('dna','dna_data')]:
        (out/('sector_cycles_'+suffix+'.js')).write_text(publication[kind])
    if args.scenario=='missing-extras': (out/'sector_cycles_narr_data.js').unlink()
(out/'fixture_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('Preview:',out,'scenario:',args.scenario,'assets:',len(assets))
