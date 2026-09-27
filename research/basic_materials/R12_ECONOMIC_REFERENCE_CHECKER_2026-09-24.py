"""Offline Materials research answer-checker; not production financial/identity code.

Reads an explicit local case file; no app imports, network, credentials, storage
admission, arbitrary expressions, predictions, ranks, or live decision effects.
Expected answers are specified separately. Comparisons below are deliberately
narrow examples, not a global financial-metric or economic-state authority.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import hashlib
import json
from pathlib import Path
import re
from typing import Any

MAX_BYTES=256*1024
DECIMAL_TEXT=re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z')
BASIS_FIELDS=('scope','unit','currency','period','ownership')
NO_AUTHORITY=('native_admission','can_rank','can_gate','can_size','can_originate','can_open_entry')
class Refusal(ValueError):
    pass

def decimal(value: Any) -> Decimal:
    if value is None:
        raise Refusal('value_unavailable')
    if not isinstance(value,str):
        raise Refusal('decimal_text_required')
    if len(value)>80 or DECIMAL_TEXT.fullmatch(value) is None:
        raise Refusal('invalid_decimal')
    return Decimal(value)

def render(value: Decimal, rounded: bool=False) -> str:
    if rounded:
        value=value.quantize(Decimal('0.000000000001'),rounding=ROUND_HALF_EVEN)
    if value==0:
        return '0'
    text=format(value,'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text

def domain_value(row: dict) -> Decimal:
    value=decimal(row['value']);domain=row['domain']
    if domain not in {'signed','physical_count','nonnegative_quantity'}:
        raise Refusal('unknown_domain')
    if domain!='signed' and value<0:
        raise Refusal('negative_quantity')
    if domain=='physical_count' and value!=value.to_integral_value():
        raise Refusal('fractional_count')
    return value

def compatible(a: dict,b: dict) -> None:
    for field in BASIS_FIELDS:
        av=a['basis'].get(field);bv=b['basis'].get(field)
        if av is None or av=='' or bv is None or bv=='':
            raise Refusal('unknown_basis:'+field)
        if av!=bv:
            raise Refusal('incompatible:'+field)

def instant(value: Any) -> datetime:
    if not isinstance(value,str) or 'T' not in value:
        raise Refusal('instant_not_established')
    try:
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError as exc:
        raise Refusal('instant_not_established') from exc
    if parsed.tzinfo is None:
        raise Refusal('instant_not_established')
    return parsed

def answer(**values: Any) -> dict:
    return {'state':'answer','values':values}

def _calculate(case: dict) -> dict:
    x=case['input'];kind=case['kind']
    if kind=='margin_bridge':
        p0,c0,p1,c1=(decimal(x[k]) for k in ('p0','c0','p1','c1'))
        old=p0-c0;new=p1-c1;change=new-old
        return answer(prior_margin=render(old),current_margin=render(new),price_change=render(p1-p0),cost_change=render(c1-c0),margin_change=render(change),level='positive' if new>0 else ('negative' if new<0 else 'zero'),direction='improving' if change>0 else ('deteriorating' if change<0 else 'unchanged'))
    if kind=='difference':
        a,b=x['a'],x['b'];compatible(a,b)
        return answer(value=render(domain_value(a)-domain_value(b)))
    if kind=='quantity':
        return answer(value=render(domain_value(x)))
    if kind=='cash_bridge':
        if x['starting_basis']!='reported_CFO':
            raise Refusal('starting_basis_not_supported')
        if x['subtract_working_capital_again'] is not False:
            raise Refusal('working_capital_already_in_CFO')
        c,cap,a=(decimal(x[k]) for k in ('operating_cash','capex_outflow','issuer_adjustment'))
        if cap<0:
            raise Refusal('capex_outflow_magnitude_required')
        return answer(after_capex=render(c-cap),issuer_adjusted=render(c-cap+a))
    if kind=='ratio_change':
        p,c=decimal(x['prior']),decimal(x['current'])
        if p<=0:
            raise Refusal('nonpositive_base')
        return answer(change_percent=render((c/p-1)*100,True))
    if kind=='qualification':
        met,total=x['met'],x['total']
        if type(met) is not int or type(total) is not int or not (0<=met<=total and total>0):
            raise Refusal('invalid_parameter_counts')
        accepted=x['customer_acceptance_documented'];shipped=x['shipments_documented']
        if type(accepted) is not bool or type(shipped) is not bool:
            raise Refusal('invalid_evidence_flags')
        if shipped and not accepted:
            raise Refusal('receipt_scope_requires_review')
        return answer(specification_state='parameters_met' if met==total else 'some_parameters_unmet',commercial_state='shipment_documented' if shipped else ('accepted_not_shipped' if accepted else 'not_established'),success_probability=None)
    if kind=='proposition':
        if not all(type(x[k]) is bool for k in ('same_subject','same_proposition','explicit_correction_link')):
            raise Refusal('invalid_evidence_flags')
        if not x['same_subject'] or not x['same_proposition']:
            relationship='separate_proposition'
        elif x['explicit_correction_link']:
            relationship='correction_with_history'
        else:
            relationship='same_proposition_relationship_unresolved'
        return answer(relation=relationship,overwrites_prior=False)
    if kind=='contract':
        initial,later,payable,payment,q,p=(decimal(x[k]) for k in ('initial_share','later_share','payable_factor','payment_fraction','hypothetical_output_oz','hypothetical_price'))
        if not all(0<=v<=1 for v in (initial,later,payable,payment)) or q<0 or p<0:
            raise Refusal('invalid_scenario_terms')
        a=q*payable*initial;b=q*payable*later
        # Deliberately do not infer current phase or value the upfront investment.
        if x['threshold_remaining'] is not None:
            raise Refusal('current_phase_not_in_this_recipe')
        return answer(initial_delivery=render(a),later_delivery=render(b),initial_contribution=render(a*p*(1-payment)),later_contribution=render(b*p*(1-payment)),current_phase='unknown',mine_ownership_inferred=False,additional_physical_supply=False)
    if kind=='demand_mix':
        u0,u1,s0,s1,c0,c1,i=(decimal(x[k]) for k in ('units0','units1','size0','size1','chemistry0','chemistry1','intensity'))
        if min(u0,u1,s0,s1,i)<0 or not (0<=c0<=1 and 0<=c1<=1):
            raise Refusal('invalid_scenario_terms')
        e0=u0*s0;e1=u1*s1;m0=e0*c0*i;m1=e1*c1*i
        if m0<=0:raise Refusal('nonpositive_base')
        return answer(energy0=render(e0),energy1=render(e1),material0=render(m0),material1=render(m1),material_change_percent=render((m1/m0-1)*100,True))
    if kind=='growth_translation':
        g,l=decimal(x['application_growth']),decimal(x['loading_change'])
        if g<-1 or l<-1:raise Refusal('invalid_scenario_terms')
        return answer(material_change_percent=render(((1+g)*(1+l)-1)*100))
    if kind=='pass_through':
        r,c,p=(decimal(x[k]) for k in ('revenue','cost','reimbursed_increase'))
        return answer(contribution0=render(r-c),contribution1=render((r+p)-(c+p)))
    if kind=='inventory':
        opening,receipts,sales=(decimal(x[k]) for k in ('opening','receipts','sell_through'))
        if min(opening,receipts,sales)<0 or opening+receipts-sales<0:
            raise Refusal('invalid_inventory_scenario')
        return answer(closing=render(opening+receipts-sales),inventory_change=render(receipts-sales))
    if kind=='funding':
        v,d,s,e,p=(decimal(x[k]) for k in ('operating_value','new_debt','old_shares','equity_raise','issue_price'))
        if min(v,d,s,e,p)<0 or s==0 or p==0:raise Refusal('invalid_funding_scenario')
        new=e/p
        return answer(post_equity_value=render(v-d),new_shares=render(new,True),per_share=render((v-d)/(s+new),True))
    if kind=='time':
        if x['available'] is None:raise Refusal('availability_unknown')
        available=instant(x['available']);cutoff=instant(x['cutoff']);instant(x['published'])
        if x['mode']=='source_history':eligible=available<=cutoff
        elif x['mode']=='system_replay':
            if x['recorded'] is None:raise Refusal('recording_unknown')
            eligible=available<=cutoff and instant(x['recorded'])<=cutoff
        else:raise Refusal('unknown_time_mode')
        return answer(eligible=eligible,mode=x['mode'])
    if kind=='expectation':
        old=(decimal(x['old_low'])+decimal(x['old_high']))/2
        new=(decimal(x['new_low'])+decimal(x['new_high']))/2
        # Inputs are explicitly same-definition/same-period hypothetical cases.
        return answer(management_midpoint_change=render(new-old),guidance_vs_supplied_consensus=None if x['consensus'] is None else render(new-decimal(x['consensus'])))
    raise Refusal('unsupported_recipe')

def calculate_case(case: dict) -> dict:
    try:
        with localcontext() as ctx:
            ctx.prec=512
            return _calculate(case)
    except Refusal as exc:
        return {'state':'refuse','reason':str(exc)}

def strict_equal(a: Any,b: Any) -> bool:
    return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)

def load_json(path: Path) -> dict:
    with path.open('rb') as f:data=f.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:raise ValueError('research input exceeds size limit')
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError('duplicate JSON key: '+key)
            result[key]=value
        return result
    def constant(value):raise ValueError('non-finite JSON constant: '+value)
    result=json.loads(data,object_pairs_hook=pairs,parse_constant=constant)
    if not isinstance(result,dict):raise ValueError('research input must be an object')
    return result

def run(path: Path) -> dict:
    corpus=load_json(path)
    for flag in NO_AUTHORITY:
        if corpus.get(flag) is not False:raise ValueError('research must retain false '+flag)
    sources={s['source_id'] for s in corpus['sources']}
    cases=corpus['cases'];ids=[c['id'] for c in cases]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate case id')
    rows=[];outputs={}
    for case in cases:
        if not set(case['source_ids'])<=sources:raise ValueError('unknown source reference')
        outputs[case['id']]=calculate_case(case)
        rows.append({'id':case['id'],'kind':case['kind'],'observed':outputs[case['id']],'expected_match':strict_equal(outputs[case['id']],case['expected'])})
    mutations=[]
    for m in corpus['mutations']:
        altered=copy.deepcopy(outputs[m['case']]);target=altered
        parts=m['field'].split('.')
        for key in parts[:-1]:target=target[key]
        target[parts[-1]]=m['replacement']
        expected=next(c['expected'] for c in cases if c['id']==m['case'])
        mutations.append({'id':m['id'],'reason':m['reason'],'detected':not strict_equal(altered,expected)})
    report={'scope':'Offline reference calculations and supplied-premise classifications, NOT native product/LLM/prediction performance.',
      'input_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'checker_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'case_count':len(rows),'expected_matches':sum(r['expected_match'] for r in rows),
      'refusals':sum(r['observed']['state']=='refuse' for r in rows),'cases':rows,
      'output_corruption_canaries':mutations,'canaries_detected':sum(m['detected'] for m in mutations),
      'native_product_tests':0,'model_answers_evaluated':0,'forecast_outcomes_scored':0,
      'limitations':['Semantic descriptions are principal reference decisions, not independently reviewed labels.',
      'Premise flags are synthetic or manually annotated; this utility does not extract evidence or prove native identity/rights.',
      'Corruption canaries test answer-comparison sensitivity, not mutation testing of a production model.',
      'Final four-company workflow and shared-contract acceptance remain unproved.']}
    if not all(r['expected_match'] for r in rows) or not all(m['detected'] for m in mutations):
        raise AssertionError(json.dumps(report,indent=2))
    return report

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=Path,default=Path(__file__).with_name('R12_ECONOMIC_REFERENCE_CASES_2026-09-24.json'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args();report=run(args.cases)
    text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.output:
        with args.output.open('x',encoding='utf-8') as f:f.write(text)
    else:print(text,end='')
if __name__=='__main__':main()
