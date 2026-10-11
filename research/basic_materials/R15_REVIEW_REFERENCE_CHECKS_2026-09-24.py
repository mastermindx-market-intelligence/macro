"""Offline R15 review checks, not a production contract parser or financial engine.

Uses Decimal over declared synthetic inputs. No network, app imports, credentials,
identity allocation, source retention, policy grants, valuation or trading actions.
The threshold convention below is an explicit hypothetical scenario assumption;
it is not a legal interpretation of undisclosed settlement terms.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

MAX_BYTES = 250_000

def text_decimal(value: str, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f'{label}: decimal_text required')
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError(f'{label}: finite required')
    if result < 0:
        raise ValueError(f'{label}: nonnegative required')
    return result

def render(value: Decimal) -> str:
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text

def stream_scenario(quantity: str, basis: str, delivered_before: str | None,
                    spot_usd_per_oz: str) -> dict[str, Any]:
    """BHP-tranche-only toy scenario; divisible deliveries and one constant spot price.

    quantity is either produced silver before this stated fixed payable factor,
    or already-payable silver. No legal settlement simulation or actual phase
    inference. Upfront capital, taxes, financing and overhead are not deducted.
    """
    if basis not in {'produced_silver_oz', 'payable_silver_oz'}:
        raise ValueError('quantity_basis is missing or unsupported')
    q = text_decimal(quantity, 'quantity')
    p = text_decimal(spot_usd_per_oz, 'spot')
    if delivered_before is None:
        return {'status':'not_computed','reason':'unknown_contract_deliveries'}
    before = text_decimal(delivered_before, 'delivered_before')
    with localcontext() as context:
        context.prec = 60
        payable = q * Decimal('0.9') if basis == 'produced_silver_oz' else q
        remaining_high = max(Decimal('0'), Decimal('100000000') - before)
        high = min(payable * Decimal('0.3375'), remaining_high)
        high_payable = high / Decimal('0.3375')
        low_payable = max(Decimal('0'), payable - high_payable)
        low = low_payable * Decimal('0.225')
        delivered = high + low
        hypothetical_proceeds = delivered * p
        purchase_payment = hypothetical_proceeds * Decimal('0.2')
        return {
            'status':'synthetic_scenario_only',
            'payable_input_oz':render(payable),
            'pre_threshold_delivered_oz':render(high),
            'post_threshold_delivered_oz':render(low),
            'delivered_oz':render(delivered),
            'ending_contract_deliveries_oz':render(before + delivered),
            'hypothetical_proceeds_usd':render(hypothetical_proceeds),
            'purchase_payment_usd':render(purchase_payment),
            'contribution_usd':render(hypothetical_proceeds-purchase_payment),
            'is_valuation':False,
            'is_actual_company_result':False,
        }

def _pairs(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError(f'duplicate key: {key}')
        result[key]=value
    return result

def read_json(path: Path) -> dict:
    data=path.read_bytes()
    if len(data)>MAX_BYTES:raise ValueError('input exceeds size limit')
    return json.loads(data,object_pairs_hook=_pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))

def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def check_worksheet(doc: dict, r14_path: Path | None = None) -> dict:
    """Check declared research consistency; no source/execution permission is granted."""
    results=[]
    def check(label, condition):
        results.append({'id':label,'passed':bool(condition)})
    cases=doc['new_cases']; terms=doc['contract_terms']
    check('three_remaining_document_cases', [c['case_ref'] for c in cases]==['R8-C02','R8-C03','R8-C04'])
    check('all_five_documents_indexed', sorted(c['case_ref'] for c in doc['selected_case_index'])==[f'R8-C0{i}' for i in range(1,6)])
    check('four_distinct_selected_subjects', set(c['subject'] for c in doc['selected_case_index'])=={'Nutrien','NOVONIX','Wheaton','Weyerhaeuser'})
    check('no_native_identity_invention', all(c['native_identity'] is None for c in cases))
    fields=['native_source_ref','curation_revision','retention_receipt','native_review_receipt','current_rights_receipt','production_generation','actual_rendered_href','live_route_proof']
    check('all_native_admission_receipts_unknown',all(c[f] is None for c in cases for f in fields))
    authority=['can_publish','can_rank','can_gate','can_size','can_originate','can_open_entry']
    check('authority_literal_false',all(c[f] is False for c in cases for f in authority))
    check('source_dates_preserved',[c['source']['document_date'] for c in cases]==['2026-09-09','2026-09-16','2026-04-01'])
    check('intraday_clocks_not_invented',all(c['source']['exact_publication_instant'] is None for c in cases))
    check('corporate_sources_not_sec_by_issuer',all(c['source']['candidate_policy_family'] is None for c in cases))
    observations={o['id']:o for c in cases for o in c['observations']}
    check('observation_ids_unique',len(observations)==sum(len(c['observations']) for c in cases))
    check('customer_test_subset',observations['Q1']['value_text']=='12' and observations['Q2']['value_text']=='14')
    check('probability_not_test_ratio',cases[0]['state']['qualification_probability'] is None)
    check('anonymous_customer_preserved',cases[0]['state']['named_customer'] is None)
    check('internal_and_customer_evidence_separate',cases[0]['state']['internal_all_parameters_met'] is True and cases[0]['state']['customer_all_parameters_met'] is False)
    check('commercial_target_is_conditional',cases[0]['state']['sales_start']['statement_mode']=='FORWARD_TARGET' and cases[0]['state']['sales_start']['window']=='H2 2027')
    check('mou_not_binding_supply_contract',cases[1]['state']['arrangement']=='NONBINDING_MOU' and cases[1]['state']['binding_sales_volume'] is None)
    check('mou_does_not_correct_qualification',cases[1]['state']['correction_of_qualification'] is False)
    check('contract_rates_match_selected_original',terms['initial_share']=='0.3375' and terms['later_share']=='0.225' and terms['fixed_payable_factor']=='0.9' and terms['ongoing_spot_fraction']=='0.2')
    check('counter_is_contract_scoped',terms['threshold_delivered_oz']=='100000000' and terms['counter_scope']=='BHP Antamina PMPA only')
    check('upfront_paid_not_recurring_expense',terms['upfront_payment_usd']=='4300000000' and terms['upfront_payment_mode']=='REPORTED_PAID')
    check('actual_phase_remains_unknown',terms['actual_cumulative_deliveries_oz'] is None and terms['actual_phase'] is None)
    check('physical_supply_not_duplicated',cases[2]['state']['additional_mine_supply'] is None and cases[2]['state']['mine_ownership_established'] is False)
    check('all_case_cards_identify_limits',all(c['card']['not_established'] and c['card']['next_evidence'] for c in cases))
    check('no_actual_stock_calls',all(c['card']['current_market_call'] is False for c in cases))
    scenario_results=[]
    for sc in doc['synthetic_scenarios']:
        got=stream_scenario(**sc['inputs'])
        expected=sc['expected']
        match=all(got[k]==v for k,v in expected.items())
        check('scenario_'+sc['id'],match)
        scenario_results.append({'id':sc['id'],'observed':got,'expected_subset':expected,'passed':match})
    check('all44_previous_requirements_preserved',doc['preserved_program']['requirement_count']==44 and doc['preserved_program']['task_ids']==[f'T{i}' for i in range(1,9)])
    check('all_holds_open_h4_partial',all(v in {'OPEN','PARTIAL'} for v in doc['preserved_program']['holds'].values()) and doc['preserved_program']['holds']['H4']=='PARTIAL')
    check('no_denied_action_retry',doc['effect_boundary']['browser_actions']==0 and doc['effect_boundary']['other_subject_identity_queries']==0)
    check('not_independent_review',doc['independent_semantic_review'] is False)
    if r14_path is not None:
        raw=r14_path.read_bytes(); inherited=read_json(r14_path)
        check('r14_exact_immutable_input',git_blob(raw)==doc['r14_input']['git_blob'])
        check('r14_subjects_not_replaced',[x['subject'] for x in inherited['cases']]==['Nutrien','Weyerhaeuser'])
        for c in inherited['cases']:
            values={m['local_claim_label']:Decimal(m['value_text']) for m in c['measurements']}
            for r in c['derived_checks']:
                args=[values[k] for k in r['inputs']]
                actual=args[0]-args[1] if r['operation']=='difference' else sum(args,Decimal('0'))
                check('inherited_'+r['id'],actual==Decimal(r['expected']))
    return {'scope':'Offline research consistency and explicit synthetic arithmetic only; not source admission, native schema, contract interpretation, model or product proof.',
            'checks':results,'passed':sum(x['passed'] for x in results),'failed':sum(not x['passed'] for x in results),
            'scenario_results':scenario_results,'independent_review':False,'native_product_tests':0,'model_answers_evaluated':0}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worksheet',required=True,type=Path)
    parser.add_argument('--r14',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=check_worksheet(read_json(args.worksheet),args.r14)
    text=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8') as target:target.write(text)
    else:print(text,end='')
    if result['failed']:raise SystemExit(1)

if __name__=='__main__':main()
