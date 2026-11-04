#!/usr/bin/env python3
"""Reproducible, local-only D05 preview. Run with PYTHONPATH=. from repository root.

Dependencies: Jinja2 plus the repository's i18n imports. Uses dated committed
fixtures; it never recalculates a market model, writes a forward log, or deploys.
"""
from pathlib import Path
import argparse, re, shutil, subprocess, tempfile
from jinja2 import Environment, FileSystemLoader
from engine import i18n
root=Path(__file__).resolve().parents[3]
parser=argparse.ArgumentParser(description='Build a local D05 candidate from archived committed inputs; no engine run or forward-log write.')
parser.add_argument('--out', type=Path)
args=parser.parse_args()
out=args.out or Path(tempfile.mkdtemp(prefix='d05-native-preview-'))
out.mkdir(parents=True,exist_ok=True)
source_ref='c53915f6d67078d5c0aeaf73bf85ddea1a23de03'
env=Environment(loader=FileSystemLoader(root/'templates'),autoescape=False)
env.globals.update(td=i18n.td,tr=i18n.tr,t=i18n.t)
for name in ['sector_central','sector_cycles']:
    html=env.get_template(name+'.html.j2').render(basket_member_syms=['SPY'])
    html=html.replace('<body ', '<body data-d05-fixture="archived-source" ',1)
    html=html.replace('</body>','<div style="position:fixed;bottom:0;left:0;z-index:100000;background:var(--panel);color:var(--muted);padding:3px 8px;font:11px sans-serif">D05 LOCAL CANDIDATE · archived source fixture · not live</div></body>')
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
for a in ['basketdata/baskets.json']:
    if 'site/'+a in known:
        dst=out/a;dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(subprocess.check_output(['git','-C',str(root),'show',source_ref+':site/'+a]))
print('Preview:',out,'assets:',len(assets))
