"""Check planning artifacts and arithmetic, never native admission/product behavior.

Run: python research/mining/check_mining_plan.py (checkout) or
     python check_mining_plan.py (portable packet).
Standard library only. Reads the preserved specification plus the plan, qualification
and trace; writes one local receipt. No network, native objects, cloud or trade effects.
"""
from __future__ import annotations
import ast
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
SPEC_NAME = '2026-09-24-mining-shared-foundation-economic-dossier-design.md'
PLAN_NAME = '2026-09-24-mining-economic-dossier-implementation.md'
QUAL_NAME = 'MINING_WITNESS_INPUT_QUALIFICATION_2026-09-24.md'
TRACE_NAME = 'MINING_IMPLEMENTATION_TRACE_2026-09-24.json'
RECEIPT_NAME = 'MINING_IMPLEMENTATION_PLAN_CHECKS_2026-09-24.json'
SPEC_HASH = '0925e376bc7504aa5e191cfc1795415ecbfe2b7128d6d2bc06ecd5d6d361530e'


def resolve(name: str, kind: str) -> Path:
    candidate = REPO / 'docs' / 'superpowers' / kind / name
    return candidate if candidate.is_file() else ROOT / name


def digest(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {'bytes': len(raw), 'words': len(raw.decode('utf-8').split()),
            'sha256': hashlib.sha256(raw).hexdigest(),
            'git_blob_sha1': hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}


def evaluate(spec: str, plan: str, qual: str, trace: dict) -> dict[str, bool]:
    spec_rows = [(a, b.strip(), c.strip()) for a,b,c in
        re.findall(r'^\| (MGD-\d{2}) \| ([^|]+) \| (.+) \|$', spec, re.M)]
    rows = trace.get('requirements', [])
    actual_rows = [(r['id'], r['family'], r['requirement']) for r in rows]
    tasks = re.findall(r'^## \d+\. Task (T\d{2}) ', plan, re.M)
    expected_tasks = [f'T{i:02d}' for i in range(1,9)]
    blocks = re.findall(r'```python\n(.*?)\n```', plan, re.S)
    valid_syntax = True
    for block in blocks:
        try:
            ast.parse(block)
        except SyntaxError:
            valid_syntax = False
    c, r = trace['witness_vectors']['W-C'], trace['witness_vectors']['W-R']
    d = Decimal
    with localcontext() as ctx:
        ctx.prec = 40
        fcx_sales = d(c['sales_actual_mlb'])-d(c['sales_estimate_mlb'])
        fcx_cost = d(c['cost_actual_usd_lb'])-d(c['cost_estimate_usd_lb'])
        mp_sum = d(r['materials_revenue'])+d(r['magnetics_revenue'])+d(r['intercompany_elimination'])
    tests = [row['test'] for row in rows]
    return {
      'preserved_spec_hash': hashlib.sha256(spec.encode()).hexdigest() == SPEC_HASH,
      'forty_verbatim_obligations': len(rows) == 40 and actual_rows == spec_rows,
      'eight_sequential_tasks': tasks == expected_tasks == trace['task_ids'],
      'every_obligation_has_real_plan_task': all(row['task'] in tasks for row in rows),
      'every_trace_test_listed_in_plan': len(set(tests)) == 40 and all(t in plan for t in tests),
      'future_tests_not_claimed_run': all(row['execution']=='NOT_RUN' and row['phase']=='future_product_test' for row in rows),
      'all_admission_gates_remain_unclosed': set(trace['admission_gates'])=={f'G{i}' for i in range(1,8)} and set(trace['admission_gates'].values())=={'NOT_CLOSED_BY_THIS_PLAN'},
      'python_plan_examples_parse': len(blocks) == 7 and valid_syntax,
      'no_unresolved_placeholder_tokens': re.search(r'\b(?:TODO|TBD|FIXME)\b', plan) is None,
      'two_correct_source_filers': c['cik']=='0000831259' and r['cik']=='0001801368',
      'same_quarter_comparison_scope': c['reporting_period']==r['reporting_period']=='2026Q2' and r['unit']=='USD thousands',
      'fcx_selected_arithmetic': fcx_sales==d('20') and fcx_cost==d('-0.27'),
      'mp_segment_reconciliation': mp_sum==d(r['consolidated_revenue'])==d('108490'),
      'mp_ppa_not_gaap_revenue': d(r['consolidated_revenue'])+d(r['ppa_income'])==d('126070') and d(r['consolidated_revenue'])!=d('126070'),
      'signed_gaap_loss_preserved': d(r['gaap_net_loss'])==d('-20296') and d(r['adjusted_ebitda'])==d('28493'),
      'native_receipts_not_fabricated': all(v[k] is None for v in (c,r) for k in ('native_span_receipt','native_identity_bridge','native_derivation_receipt')),
      'shared_economic_gate_acknowledged': 'reported_economic_context' in plan and 'prior/actual/later-outlook triple' in plan,
      'no_fixture_task_cycle': 'created and frozen in T01 before T02 consumes it' in plan,
      'source_retention_limit_disclosed': 'native retained-body hash, byte offsets' in qual and 'could not resolve' in qual,
      'release_and_mission_held': 'PLAN_PROPOSED / PREPARED_ADMISSION_HELD' in plan and 'MISSION_COMPLETE: false' in plan,
    }


def main() -> None:
    paths={'spec':resolve(SPEC_NAME,'specs'),'plan':resolve(PLAN_NAME,'plans'),
           'qualification':ROOT/QUAL_NAME,'trace':ROOT/TRACE_NAME}
    spec,plan,qual=(paths[key].read_text(encoding='utf-8') for key in ('spec','plan','qualification'))
    trace=json.loads(paths['trace'].read_text())
    checks=evaluate(spec,plan,qual,trace)
    mutations={}
    changed=deepcopy(trace); changed['requirements'].pop()
    mutations['missing_obligation']=not evaluate(spec,plan,qual,changed)['forty_verbatim_obligations']
    changed=deepcopy(trace); changed['witness_vectors']['W-R']['reporting_period']='2026H1'
    mutations['wrong_reporting_period']=not evaluate(spec,plan,qual,changed)['same_quarter_comparison_scope']
    changed=deepcopy(trace); changed['witness_vectors']['W-R']['gaap_net_loss']='20296'
    mutations['lost_financial_sign']=not evaluate(spec,plan,qual,changed)['signed_gaap_loss_preserved']
    changed=deepcopy(trace); changed['witness_vectors']['W-R']['consolidated_revenue']='126070'
    mutations['ppa_laundered_into_revenue']=not evaluate(spec,plan,qual,changed)['mp_segment_reconciliation']
    changed=deepcopy(trace); changed['witness_vectors']['W-C']['native_span_receipt']='invented'
    mutations['fabricated_native_receipt']=not evaluate(spec,plan,qual,changed)['native_receipts_not_fabricated']
    changed=deepcopy(trace); changed['admission_gates']['G5']='CLOSED'
    mutations['false_live_admission']=not evaluate(spec,plan,qual,changed)['all_admission_gates_remain_unclosed']
    receipt={
      'operation':trace['operation'], 'classification':'OFFLINE_PLAN_TRACE_SYNTAX_AND_RESEARCH_ARITHMETIC_ONLY',
      'run_utc':datetime.now(timezone.utc).isoformat(),
      'command':'python research/mining/check_mining_plan.py' if paths['plan'].parent.name=='plans' else 'python check_mining_plan.py',
      'documents':{p.name:digest(p) for p in paths.values()}, 'checker':digest(Path(__file__)),
      'checks':checks, 'total':len(checks),'passed':sum(checks.values()),'failed':sum(not v for v in checks.values()),
      'changed_artifact_traps':mutations,
      'self_review':[
        'Initial checker expected six Python examples; AST inspection found seven valid blocks (one interface block and six tests). Corrected the count to seven without changing the plan or weakening syntax validation.',
        'Shared response has a closed Semiconductor slice enum; exact owner-controlled generic extraction is a gated proposal, not an already-callable Mining API.',
        'Shared economics currently needs a guidance triple; the plan specifies a separate closed reported-context policy and preserves legacy witness requirements.',
        'Initial draft placed the shared case helper under T02 while T01 consumed it; moved helper creation to T01 and made T02 a consumer before publication.',
        'Primary section locators and source values are confirmed; exact retained original bodies, native spans and live identity/financial objects remain unearned.',
        'Native extraction profiles do not imply safe public discovery enrollment; public defaults remain unchanged without their separate owner admission.',
        'Optional derived percentages are withheld without native receipts; both required real economic tasks must still be populated.',
        'All forty spec conditions retain exact text and future-test identity; the old domain corpus remains evidence with explicit later capability obligations.'
      ],
      'not_claimed':['executed product tests','upstream module execution','native source or identity admission','actual formula receipts','current CI','independent review','browser proof','design or plan acceptance','worker dispatch','deployment','investment validation']
    }
    (ROOT/RECEIPT_NAME).write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'total':receipt['total'],'passed':receipt['passed'],'failed':receipt['failed'],'changed_artifact_traps':mutations,'plan':receipt['documents'][PLAN_NAME],'checker_git_blob':receipt['checker']['git_blob_sha1']},indent=2))
    if not all(checks.values()) or not all(mutations.values()):
        raise SystemExit(1)


if __name__=='__main__':
    main()
