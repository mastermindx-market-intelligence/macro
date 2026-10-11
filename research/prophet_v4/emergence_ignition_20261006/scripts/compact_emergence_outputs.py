#!/usr/bin/env python3
"""Make compact publication tables from full reproducible emergence outputs."""
import argparse,csv,json,shutil,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--boards-source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
def csvrows(path):return list(csv.DictReader(path.open()))
def writecsv(name,rows):
    if not rows:return
    with (a.out/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for name in ('parent_window_latest','extended_window_latest','extended_window_first'):
    summary=json.loads((a.source/(name+'_summary.json')).read_text())
    for v in summary['matched'].values():v.pop('records',None)
    (a.out/(name+'_summary.json')).write_text(json.dumps(summary,indent=2,sort_keys=True))
    for suffix in ('_exposed_baselines.csv','_outcomes.csv'):shutil.copyfile(a.source/(name+suffix),a.out/(name+suffix))
    pairs=[r for r in csvrows(a.source/(name+'_matched_pairs.csv')) if r['horizon']=='12' and r['mode']=='valid']
    writecsv(name+'_h12_matched_pairs.csv',pairs)
    used={(r['date'],r['control_ticker']) for r in pairs}
    writecsv(name+'_h12_control_baselines.csv',[r for r in csvrows(a.source/(name+'_control_baselines.csv')) if (r['as_of'],r['ticker']) in used])
for name in ['b1_emergence_relations.csv','b1_rp1_source_manifest.csv','b1_rp1_coverage_summary.json','emergence_price_control_sensitivity.json','emergence_price_match_pairs.csv','reproduction_environment.json']:
    shutil.copyfile(a.source/name,a.out/name)
writecsv('b03_selected_pool_b1_relations.csv',[r for r in csvrows(a.source/'b03_pool_b1_relations.csv') if r['as_of'] in ('2026-09-04','2026-10-02','2026-10-05')])
pairs=csvrows(a.source/'emergence_price_match_pairs.csv')
keys={(r['date'],r['control_ticker']) for r in pairs}|{(r['date'],r['exposed_ticker']) for r in pairs}
seen=set();rows=[]
for r in csvrows(a.source/'emergence_price_controls_used.csv'):
    k=(r['as_of'],r['ticker'])
    if k in keys and k not in seen:rows.append(r);seen.add(k)
writecsv('emergence_matched_price_controls.csv',rows)
for n in ['board_source_manifest.json','extraction_summary.json']:shutil.copyfile(a.boards_source/n,a.out/n)
manifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(a.out.iterdir()) if p.is_file() and p.name!='EMERGENCE_ARTIFACT_DIGESTS.json'}
(a.out/'EMERGENCE_ARTIFACT_DIGESTS.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'files':len(manifest),'bytes':sum(r['bytes'] for r in manifest.values())}))

