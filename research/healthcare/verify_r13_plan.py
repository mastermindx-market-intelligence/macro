"""Check a research plan's consistency. No product or native application tests."""
from __future__ import annotations
import argparse, ast, copy, hashlib, json, os, re, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class PlanRefusal(ValueError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlanRefusal(message)

def blob(data: bytes) -> str:
    return hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()

def check(text: str, reference: dict) -> dict:
    checks = []
    def must(condition: bool, name: str) -> None:
        require(condition, name); checks.append(name)
    must(text.startswith('# Healthcare Theme Intelligence Implementation Plan'), 'plan_header')
    must('**Status:** REVIEW_PENDING.' in text, 'review_not_accepted')
    must('NEW Healthcare-specific Fable CEO session' in text, 'new_healthcare_receiver')
    must('NOT the Healthcare build receiver' in text, 'semiconductor_not_receiver')
    must('No manual startup prompt is being issued as a live assignment' in text, 'manual_activation_not_issued')
    must('in-place consolidation of the existing plan' in text, 'one_operative_plan')
    must('9b06712b56450b38f952d4bc30bfcd2dcfb91e0f' in text and 'f58970d627a6334905bd42fa5994a25a2b00956a' in text, 'historical_original_pin')
    tasks = re.findall(r'^## Task (T\d\d)\b',text,re.M)
    must(tasks == [f'T{i:02d}' for i in range(1,9)], 'eight_ordered_tasks')
    for task in tasks:
        section=text.split(f'## Task {task} ',1)[1].split('\n## ',1)[0]
        must(re.findall(r'^- \[ \] \*\*Step (\d)',section,re.M)==list('12345'), f'{task}_five_steps')
    rows=[]
    for line in text.splitlines():
        if re.match(r'^\| R(?:8|9|10)-A\d\d \|',line):
            cells=[c.strip() for c in line.split('|')[1:-1]]
            require(len(cells)==4,'case_row_shape')
            rows.append({'id':cells[0],'task':cells[1],'required_result':cells[2],'execution':cells[3]})
    expected=[{k:c[k] for k in ('id','task','required_result','execution')} for c in reference['cases']]
    must(rows==expected,'all_60_exact_requirements_and_assignments')
    must(len(rows)==60 and len({c['id'] for c in rows})==60,'unique_case_denominator')
    families=re.findall(r'^\| (R8-F\d\d) \| ([^|]+) \|',text,re.M)
    must([(a,b.strip()) for a,b in families]==[(f['id'],f['name']) for f in reference['coverage_families']],'all_12_exact_families')
    must('All 60 IDs' in text and 'NOT_EXECUTED' in text, 'unexecuted_application_scope')
    must('D1 does not wait for v1.1' in text and 'dependency-closed tests' in text,'d1_independent_release')
    must('Source-rights withdrawal' in text and '86400 seconds' in text,'separate_rights_entitlement')
    must('known-existing key' in text and 'nonexistent-key 404' in text,'noncircular_private_proof')
    must('Preserve existing v1 input bytes' in text and 'unknown schemas refuse' in text.lower(),'legacy_versions_preserved')
    must('unknown version' in text.lower() and 'No new exported hash or mint' in text,'single_native_identity')
    must('profile="healthcare"' in text and 'healthcare_theme_research.v1' in text,'typed_healthcare_profile')
    must('unsupported Healthcare' in text and 'No arbitrary module imports' in text,'no_profile_fallback')
    must('factual inputs/original analysis, excerpts, entire expressive documents and third-party attachments separately' in text,'representation_rights_scope')
    must('without the SEC\'s permission' in text and 'government sites can contain protected privately authored material' in text,'rights_counterevidence_retained')
    must('all twelve research families' in text and 'Valuation layer V1' in text and 'Evaluation V2' in text,'ambition_retained')
    codes = re.findall(r'```python\n(.*?)```',text,re.S)
    for code in codes:
        tree=ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                require('/api/themes/glp1_obesity/research/v1' not in node.value,'obsolete_get_test')
            if isinstance(node,ast.FunctionDef):
                require(node.name not in {'revision_from_material','revision_material','promote_verified_selector'},'obsolete_native_fork')
    must(len(codes)==7,'seven_syntax_checked_examples')
    must('def revision_from_material' not in text and 'b"gmi-curation-v1' not in text,'no_obsolete_hash_recipe')
    must('GET /api/themes/{theme_id}/research/v1' not in text,'no_obsolete_get_recipe')
    must('def promote_verified_selector' not in text,'no_parallel_selector_recipe')
    must('"gross_net_basis": "net_sales"' not in text and '"estimate_status": "not_disclosed"' not in text,'no_misplaced_enums')
    must(not re.search(r'\b(?:TBD|TODO)\b|fill in details|implement later',text),'no_placeholder_markers')
    return {'status':'PASS','planning_checks':len(checks),'checks':checks,'tasks':8,'steps':40,
            'preserved_application_cases':len(rows),'coverage_families':len(families),
            'python_examples_syntax_checked':len(codes),'application_tests_executed':0,
            'independent_review_accepted':False,'healthcare_worker_started':False}

def build_reference(root: Path) -> dict:
    """Rebuild the R11 review matrix from R8, R9 and R10. No separate matrix file."""
    r8=json.loads((root/'HEALTHCARE_R8_ACCEPTANCE_REVIEW_2026-09-23.json').read_text())
    r9=json.loads((root/'HEALTHCARE_R9_TRACEABILITY_2026-09-23.json').read_text())
    r10=(root/'HEALTHCARE_R10_SHARED_COMPATIBILITY_REVIEW_2026-09-24.md').read_text()
    by_id={c['id']:c for c in r8['acceptance_cases']}
    cases=[]
    for row in r9['r8_acceptance_cases']:
        src=by_id[row['id']]
        cases.append({'id':row['id'],'task':row['implementation_task'],'required_result':src['intended_result'],'execution':row['execution']})
    for row in r9['new_acceptance_cases']:
        cases.append({'id':row['id'],'task':row['implementation_task'],'required_result':row['intended_result'],'execution':row['execution']})
    for line in r10.splitlines():
        if re.match(r'^\| R10-A\d\d \|', line):
            cells=[c.strip() for c in line.split('|')[1:-1]]
            require(len(cells)==3,'r10_case_row_shape')
            cases.append({'id':cells[0],'task':cells[1],'required_result':cells[2],'execution':'NOT_EXECUTED'})
    families=[{'id':f['id'],'name':f['name']} for f in r8['coverage_families']]
    require(len(cases)==60 and len({c['id'] for c in cases})==60,'rebuilt_reference_case_count')
    require(len(families)==12,'rebuilt_reference_family_count')
    return {'cases':cases,'coverage_families':families,'source':'R8 acceptance + R9 task map + R10 table'}

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument('--plan',type=Path,default=None)
    p.add_argument('--reference',type=Path,default=None,help='Optional matrix. Omit to rebuild from R8/R9/R10.')
    p.add_argument('--output',type=Path,default=None,help='Receipt path. Default is $TMPDIR/r13_plan_verification.json.')
    args=p.parse_args()
    plan=args.plan or (ROOT/'HEALTHCARE_IMPLEMENTATION_PLAN_R9_2026-09-23.md')
    raw=plan.read_bytes(); text=raw.decode()
    if args.reference is not None:
        ref_bytes=args.reference.read_bytes(); ref=json.loads(ref_bytes); reference_origin=str(args.reference)
    else:
        ref=build_reference(ROOT)
        ref_bytes=json.dumps(ref,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        reference_origin='in-process:R8/R9/R10'
    result=check(text,ref)
    mutants={
      'drop_case':text.replace(next(l for l in text.splitlines() if l.startswith('| R8-A05 |'))+'\n',''),
      'wrong_task':text.replace('| R8-A05 | T06 |','| R8-A05 | T03 |'),
      'claimed_pass':text.replace('| R8-A05 | T06 | Preserve parties, scope and denominator; do not label profit-sharing or manufacturing. | NOT_EXECUTED |','| R8-A05 | T06 | Preserve parties, scope and denominator; do not label profit-sharing or manufacturing. | PASS |'),
      'old_fable_receiver':text.replace('NOT the Healthcare build receiver','the Healthcare build receiver'),
      'auto_activation':text.replace('No manual startup prompt is being issued as a live assignment','A manual startup prompt is issued as a live assignment'),
      'review_inflation':text.replace('**Status:** REVIEW_PENDING.','**Status:** ACCEPTED.'),
      'drop_family':text.replace(next(l for l in text.splitlines() if l.startswith('| R8-F12 |'))+'\n',''),
      'hash_fork':text+'\n```python\ndef revision_from_material(body):\n    return body\n```\n',
      'remove_rights_counterevidence':text.replace('government sites can contain protected privately authored material','government sites are always unrestricted'),
      'd1_future_dependency':text.replace('D1 does not wait for v1.1','D1 must wait for v1.1'),
    }
    rejected={}
    for name,mutant in mutants.items():
        require(mutant!=text,f'mutant_no_change:{name}')
        try:check(mutant,ref)
        except (PlanRefusal,SyntaxError) as exc:rejected[name]=str(exc)
        else:raise PlanRefusal(f'mutant_survived:{name}')
    output=args.output
    if output is None:
        output=Path(os.environ.get('TMPDIR') or tempfile.gettempdir())/'r13_plan_verification.json'
    result.update({'plan_git_blob':blob(raw),'plan_sha256':hashlib.sha256(raw).hexdigest(),'plan_bytes':len(raw),
                   'reference_sha256':hashlib.sha256(ref_bytes).hexdigest(),'reference_origin':reference_origin,
                   'rejected_corruptions':rejected,'scope':'Planning consistency and syntax only; no native or product execution.'})
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'checks','rejected_corruptions'}},indent=2))
    print('rejected_corruptions',len(rejected))
    print('output',output)

if __name__=='__main__':main()
