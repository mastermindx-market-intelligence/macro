from pathlib import Path
import sys,subprocess,json,hashlib,datetime,time,ast
import pytest,yaml
root=Path.cwd();sys.path.insert(0,str(root))
from scripts import ci_scope_dependencies as d
from scripts import run_ci_pack as c
from engine.neuralweb import response_eval as ev
p=Path('/Volumes/Mastermind/evidence/intelligence-evaluation-os-20261012-01a1333d/integration')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();assert head=='8453d2a9051956a9dca49babe5db75201fa00666'
inv=p/'t6-fourth-tracked.bin';d.write_tracked_path_inventory(inv,head,root=root);started=time.monotonic()
with d.planner_tracked_path_inventory(inv,head,root=root):
 import xml.etree.ElementTree as ET
 suites=list(ET.parse(p/'t6-fourth-ci-tests.xml').getroot().iter('testsuite'))
 assert sum(int(x.get('tests',0)) for x in suites)==3
 assert not any(int(x.get(k,0)) for x in suites for k in ('failures','errors','skipped'))
 previous=(p/'t6-fourth-scope.log').read_text()
 assert 'CURATED_MISSES {}' in previous
 assert hashlib.sha256((root/'.github/ci/legacy-jobs.yml').read_bytes()).hexdigest()=='668e716e16f0a307d1a1acf6714904e9dc4df3659a1795f21d5cae18983ba7ea'
 rc=0;misses={}
 print('Reuse completed3focusedPASS and exact-head zero-miss closure; fix local verifier Iterable[str] argument only',flush=True)
 jobs={j.job_id:j for j in c.load_legacy_jobs(root/'.github/ci/legacy-jobs.yml')}
 cases=json.loads((p/'t6-fourth-source-adjudication.json').read_text())['cases'];sel={}
 for case in cases:
  for path in ['engine/neuralweb/eval/benchmark_'+case['benchmark_id']+'.json',case['source_path']]:
   assert c._job_diff_match(jobs['eval-os-a1'],[path]),path
   selected,reason=c.select_jobs([jobs['eval-os-a1']],[path]);assert [j.job_id for j in selected]==['eval-os-a1'],path;sel[path]=reason
 rows=c.packing_probe_measurements(root/'.github/ci/legacy-jobs.yml',[('templates/index.html',135,5803),('scripts/build_free_content.py',134,5600),('engine/prophet/plan_book.py',129,5600)],max_packs=10);breaches=c.packing_probe_breaches(rows)
 assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
 report={'schema':'eval_os.t6_fourth_scope_validation.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':head,'inventory_sha256':hashlib.sha256(inv.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((root/'.github/ci/legacy-jobs.yml').read_bytes()).hexdigest(),'pytest_exit':int(rc),'closure_misses':misses,'new_inputs_select_owner':sel,'strict_pre9228_probe_rows':rows,'strict_pre9228_breaches':breaches,'elapsed_seconds':round(time.monotonic()-started,2),'retained_partial_log_sha256':hashlib.sha256((p/'t6-fourth-scope.log').read_bytes()).hexdigest(),'verifier_correction':'_job_diff_match expects Iterable[str], not a string; exact-head3PASS and completed full closure reused, selection and packing continued with [path]. No product source repair required.','scope':'Exact committed source/local static and test proof only; no hosted CI, merge, model reasoning or production acceptance.'}
 (p/'t6-fourth-scope-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['strict_pre9228_probe_rows','new_inputs_select_owner']}),flush=True)
raise SystemExit(int(rc) or int(bool(misses) or bool(breaches)))
