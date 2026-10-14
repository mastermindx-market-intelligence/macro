from pathlib import Path
import sys,json,dataclasses,hashlib,subprocess,yaml
C=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/pr-9066-e4ea65fadb39fb56');D=Path(__file__).resolve().parent;sys.path.insert(0,str(C))
from scripts import run_ci_pack as p
manifest=C/'.github/ci/legacy-jobs.yml';jobs=p.load_legacy_jobs(manifest);selected=[j for j in jobs if 'engine/company_intelligence/defense_cash_profiles.py' in j.paths];assert len(selected)==16
inferred,_=p.infer_job_scopes([dataclasses.replace(j,exclusive=False) for j in selected]);lookup={j.job_id:j for j in inferred};rows=[]
for j in selected:
 closure=[v for v in lookup[j.job_id].paths if '*' not in v];assert closure,j.job_id
 missing=[v for v in closure if not p._matches_any(j.paths,v)];rows.append({'job':j.job_id,'exclusive':j.exclusive,'derived_paths':len(closure),'missing':missing});assert not missing,(j.job_id,missing)
assert hashlib.sha256(manifest.read_bytes()).hexdigest()=='5914726e9f69eee450546976b86c0d727bc4d1cb4cf0324db5ccf6c0290441d8', 'standalone manifest differs from qualified delta'
r={'scope':'All16 existing explicit cash-profile import scopes; unchanged other jobs and ceilings','manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'new_module_sha256':hashlib.sha256((C/'engine/company_intelligence/defense_space_profiles.py').read_bytes()).hexdigest(),'jobs':rows,'no_uncovered_paths':True,'unintended_job_or_ceiling_changes':False};(D/'STANDALONE_CI_CLOSURE.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'jobs':len(rows),'uncovered_paths':0,'no_unintended_job_changes':True}))
