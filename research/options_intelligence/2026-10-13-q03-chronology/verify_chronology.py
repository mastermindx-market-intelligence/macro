"""Synthetic validation only; runs no study and consumes no market observations."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
import argparse,ast,hashlib,importlib.util,json,random,shutil,subprocess,sys,tempfile
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--candidate', type=Path, required=True)
parser.add_argument('--tests', type=Path, required=True)
parser.add_argument('--baseline', type=Path, required=True,
                    help='Exact original adapter; no automatic retrieval is performed.')
parser.add_argument('--output', type=Path, required=True)
args=parser.parse_args()
candidate=args.candidate.resolve(strict=True)
test=args.tests.resolve(strict=True)
baseline=args.baseline.resolve(strict=True)
raw_baseline=baseline.read_bytes()
expected_baseline='b52c55c7838d83e7c966da394eed4afa7381698bc628cbb50c84fb826529dd8d'
if hashlib.sha256(raw_baseline).hexdigest()!=expected_baseline:
    raise SystemExit('BASELINE_IDENTITY_MISMATCH')
if args.output.exists():
    raise SystemExit('OUTPUT_ALREADY_EXISTS')
spec=importlib.util.spec_from_file_location('chronology_property_subject',candidate)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rng=random.Random(20261013);base=datetime(2026,10,1,12,tzinfo=timezone.utc)
checked=0
for _ in range(2000):
    begin=base+timedelta(seconds=rng.randrange(-86400,86400))
    end=begin+timedelta(minutes=30)
    cutoff=begin+timedelta(seconds=rng.randrange(-1200,7200))
    validation=cutoff+timedelta(seconds=rng.randrange(1,7200))
    mature=begin+timedelta(seconds=rng.randrange(-1200,10800))
    def represent(t):
        return t.astimezone(timezone(timedelta(minutes=rng.choice([-660,-300,-240,0,330,345,570,840]))))
    row={'pilot':'P1','decision_at':represent(begin),'label_mature_at':represent(mature)}
    expected=end<=cutoff and end<=mature<=cutoff and end<validation
    kept,purged=m.purge_training_rows([row],training_cutoff=represent(cutoff),validation_start=represent(validation),sessions=[])
    assert bool(kept)==expected and len(kept)+len(purged)==1
    checked+=1
source=candidate.read_text();original=raw_baseline.decode('utf-8')
def replace_function(text,name,replacement):
    node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==name)
    lines=text.splitlines(keepends=True)
    return ''.join(lines[:node.lineno-1])+replacement.rstrip()+'\n'+''.join(lines[node.end_lineno:])
original_node=next(n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name=='purge_training_rows')
old_purge='\n'.join(original.splitlines()[original_node.lineno-1:original_node.end_lineno])
mutants={
 'trust_maturity_instead_of_actual_endpoint':replace_function(source,'purge_training_rows',old_purge),
 'allow_duplicate_or_unsorted_calendar':replace_function(source,'_validated_sessions','def _validated_sessions(sessions):\n    return tuple(sessions)'),
 'remove_clock_validation_and_utc_normalization':replace_function(source,'_aware_utc','def _aware_utc(value, name):\n    return value'),
 'compute_elapsed_horizon_in_local_wall_time':source.replace('start = _aware_utc(row.get("decision_at"), "P1 decision_at")','_aware_utc(row.get("decision_at"), "P1 decision_at")\n        start = row["decision_at"]'),
 'consume_generator_again_for_every_row':source.replace('if frozen_sessions is None:', 'if True:'),
}
results=[]
for name,text in mutants.items():
    assert text!=source;ast.parse(text)
    with tempfile.TemporaryDirectory(prefix='q03-mutation-') as folder:
        root=Path(folder);(root/'scripts').mkdir();(root/'tests').mkdir()
        (root/'scripts/options_pilot_study_adapter.py').write_text(text)
        shutil.copyfile(test,root/'tests/test_options_pilot_chronology.py')
        r=subprocess.run([sys.executable,str(root/'tests/test_options_pilot_chronology.py')],capture_output=True,text=True,timeout=20)
        assert r.returncode!=0, name+' survived'
        assert 'SyntaxError' not in r.stderr and 'ModuleNotFoundError' not in r.stderr
        summary=next((line for line in reversed(r.stderr.splitlines()) if line.startswith('FAILED (')),'unclassified')
        results.append({'mutation':name,'killed':True,'exit_code':r.returncode,'test_summary':summary})
receipt={'schema':'options.q03.chronology_validation.v1','synthetic_only':True,'seed':20261013,'property_cases':checked,'new_regression_tests':28,'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest(),'test_sha256':hashlib.sha256(test.read_bytes()).hexdigest(),'mutations':results,'empirical_acceptance':False,'independent_model_review':'NOT_STARTED_DISPATCH_REFUSED','scope_limit':'P3 remains day-granular; calendar venue/completeness and exact session-close/consumer receipts not certified.'}
with args.output.open('x',encoding='utf-8') as destination:
    destination.write(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
