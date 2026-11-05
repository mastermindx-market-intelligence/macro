import sys,json,ast,hashlib,subprocess,time
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import yaml
from scripts import run_ci_pack as R
start=time.monotonic();manifest=Path('.github/ci/legacy-jobs.yml');source=yaml.safe_load(manifest.read_text());base=yaml.safe_load(subprocess.check_output(['git','show','52abe2e:.github/ci/legacy-jobs.yml'],text=True));review=yaml.safe_load(subprocess.check_output(['git','show','ed2529fc:.github/ci/legacy-jobs.yml'],text=True))
changed=[k for k,v in source['jobs'].items() if v!=base['jobs'].get(k)]
assert changed==['research-record-claims','site20-s4-chart-brief-js'],changed
assert set(source['jobs'])==set(base['jobs'])
assert all(source['jobs'][k]==review['jobs'][k] for k in changed)
assert {k:v for k,v in source.items() if k!='jobs'}=={k:v for k,v in base.items() if k!='jobs'}
jobs,note=R.infer_job_scopes(R.load_legacy_jobs(manifest))
routing={}
for p in ['templates/stock_seasonality.js','site/stock_seasonality.js','tests/js/test_stock_seasonality_selection.cjs','templates/history.html.j2','tests/test_history_provenance_copy.py']:
 selected,reason=R.select_jobs(jobs,[p]);ids=[j.job_id for j in selected];wanted='research-record-claims' if 'history' in p else 'site20-s4-chart-brief-js';assert wanted in ids,(p,wanted,ids);routing[p]={'selected':ids,'owner':wanted}
tree=ast.parse(Path('tests/test_ci_pack.py').read_text());constants={}
for n in tree.body:
 if isinstance(n,ast.Assign):
  for t in n.targets:
   if isinstance(t,ast.Name) and t.id in ['PACKING_PROBES','PACKING_PROBE_MAX_PACKS']: constants[t.id]=ast.literal_eval(n.value)
rows=[]
for p,maxjobs,maxweight in constants['PACKING_PROBES']:
 selected,reason=R.select_jobs(jobs,[p]);weight=sum(j.weight for j in selected);packs=max(1,min(12,-(-weight//R.PACK_TARGET_SECONDS)));assert len(selected)<=maxjobs and weight<=maxweight and packs<=constants['PACKING_PROBE_MAX_PACKS'],(p,len(selected),weight,packs)
 rows.append({'probe':p,'jobs':len(selected),'weight':weight,'packs':packs,'ceilings':[maxjobs,maxweight,constants['PACKING_PROBE_MAX_PACKS']],'job_ids':sorted(j.job_id for j in selected)})
result={'base':'52abe2e183833a216267942a99513e6c9cbe062f','reviewed_calendar_history':'ed2529fc91d580a479ec797d5c31ed62053d6541','changed_jobs_only':changed,'both_jobs_exact_reviewed_postimages':True,'all_other_jobs_and_top_level_exact_base':True,'routing':routing,'packing':rows,'breaches':[],'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'elapsed':time.monotonic()-start}
p=Path('/Volumes/Mastermind/evidence/accepted-products-p12t2s5-20261103/s14-s3-routing-packing.json');p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'changed_jobs':changed,'packing':[{k:v for k,v in x.items() if k!='job_ids'} for x in rows],'elapsed':result['elapsed']}))
