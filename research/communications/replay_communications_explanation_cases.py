"""Check fixed, author-annotated Communications explanation examples offline.

This is NOT a product composer, source selector, access-control implementation,
parser, canonical schema, or financial engine. Tokens are research annotations;
false annotations can pass. No network, model, private data, native owner, or
watchlist is accessed. Only an explicit --output path is written.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any

ROSTER = ['Meta', 'Alphabet', 'The Trade Desk', 'Magnite']
# Frozen displayed inputs from the Phase11 study, rechecked against selected Q2 tables.
FROZEN = {
 'E01.revenue': ('60801','47516','USD million','issuer consolidated','M2Q'),
 'E01.profit': ('18775','20441','USD million','issuer consolidated','M2Q'),
 'E02.search': ('63271','54190','USD million','Google Search & other','G2Q'),
 'E02.network': ('7303','7354','USD million','Google Network','G2Q'),
 'E03.revenue': ('715057','694039','USD thousand','issuer consolidated','T2Q'),
 'E03.profit': ('101577','116777','USD thousand','issuer consolidated','T2Q'),
 'E04.contribution': ('189595','161956','USD thousand','issuer-defined contribution','MG2Q'),
 'E04.gross_profit': ('130785','108379','USD thousand','issuer consolidated','MG2Q'),
}
NUMERIC_FIELDS=('current_printed','prior_printed','source_unit','reporting_scope','source_id')
COPY_FIELDS=('economic_role','headline','interpretation','limitation','next_observation')

def require(ok: bool, message: str) -> None:
    if not ok: raise ValueError(message)

def emissions(pack: dict[str, Any], tokens: set[str], *, denied: bool=False) -> set[str]:
    """Replay a supplied prerequisite truth table; do not infer source meaning."""
    if denied: return set()
    return {claim for claim, needed in pack['research_claim_prerequisites'].items()
            if set(needed) <= tokens}

def check_copy(value: Any) -> None:
    require(isinstance(value,dict) and set(value)=={'en','zh'},'bilingual fields missing')
    require(all(isinstance(x,str) and x.strip() for x in value.values()),'bilingual copy empty')
    require(all(len(x)<=240 for x in value.values()),'copy exceeds 240 characters')

def evaluate(pack: dict[str, Any]) -> dict[str, Any]:
    require(pack.get('format')=='communications-explanation-reference-v1','not the fixed research format')
    require(pack.get('production_schema') is None,'must not name a production schema')
    require(pack.get('fixed_roster')==ROSTER,'fixed public example roster changed')
    panels=pack.get('panels',[])
    require([p.get('company_label') for p in panels]==ROSTER,'four-company roster/order changed')
    sources={s['id']:s for s in pack['source_register']}
    require(len(sources)==7,'source register changed')
    require(all(s.get('native_retention_ref') is None for s in sources.values()),'fabricated retention receipt')
    measure_ids=[]
    for panel in panels:
        require(panel.get('native_issuer_id') is None and panel.get('native_security_ids')==[]
                and panel.get('verified_company_route') is None,'native identity/route in research pack')
        require(panel.get('production_admission') is False,'research must not claim admission')
        require(panel.get('investment_action') is None,'no investment action permitted')
        require(set(panel['authority'])=={'can_rank','can_gate','can_size','can_originate','can_open_entry'}
                and all(v is False for v in panel['authority'].values()),'authority must be all false')
        for f in COPY_FIELDS: check_copy(panel[f])
        require(panel['report_period_end']=='2026-06-30','report period drift')
        exp=panel['expectation']
        require(exp['question']=='original company outlook delivery','wrong expectation question')
        require(exp['final_pre_result_history']=='unqualified' and exp['analyst_consensus']=='unqualified',
                'unqualified history/consensus promoted')
        guide=exp['guide_source_id']; require(guide is None or guide in sources,'guide source missing')
        require((panel['company_label']=='Alphabet') == (guide is None),'Alphabet guide fabricated or peer guide lost')
        require(len(panel['headline_measures'])==2,'two decisive measures required')
        for m in panel['headline_measures']:
            mid=m['id'];measure_ids.append(mid)
            require(mid in FROZEN and tuple(m[f] for f in NUMERIC_FIELDS)==FROZEN[mid],
                    'frozen numeric or scope input changed: '+mid)
            require(m['current_period']==['2026-04-01','2026-06-30'] and
                    m['prior_period']==['2025-04-01','2025-06-30'],'period comparison changed')
            require(m['source_rounding_method'] is None,'source precision invented')
            require(m['native_evidence_id'] is None and m['native_definition_id'] is None,'native identity invented')
            for f in ['current_printed','prior_printed']:
                try: v=Decimal(m[f])
                except (InvalidOperation,TypeError): raise ValueError('not a finite printed decimal') from None
                require(v.is_finite(),'nonfinite printed input')
            check_copy(m['label'])
    require(len(measure_ids)==len(set(measure_ids))==8,'duplicate/missing measure')
    for value in pack['state_copy'].values(): check_copy(value)
    scenarios=pack['scenarios'];require(len(scenarios)==20,'scenario roster changed')
    require(len({s['id'] for s in scenarios})==20,'duplicate scenario ID')
    results=[]; expectation_checks=0
    for s in scenarios:
        tokens=(set(pack['baseline_tokens'])-set(s['remove_inputs']))|set(s['add_inputs'])
        emitted=emissions(pack,tokens,denied=s['global_entitlement_denied'])
        for item in s['must_not_emit']:
            expectation_checks+=1;require(item not in emitted,s['id']+' emitted prohibited '+item)
        for item in s['must_retain']:
            expectation_checks+=1;require(item in emitted,s['id']+' lost supported '+item)
        require(bool(s['maps_to_crv']) and all(type(x) is int and 1<=x<=60 for x in s['maps_to_crv']),
                'not mapped to existing CRV requirements')
        results.append({'id':s['id'],'emitted':sorted(emitted),'expectations':'pass'})
    return {'status':'reference_checks_passed','panels_checked':4,'scenarios_checked':20,
            'scenario_expectations_checked':expectation_checks,'bilingual_state_messages':len(pack['state_copy']),
            'frozen_printed_measure_pairs':8,'production_tests':0,'source_extraction_validated':False,
            'rights_enforcement_proved':False,'native_admission_proved':False,'results':results,
            'limitations':'Author annotations and a fixed local dependency table; not a native consumer or semantic proof.'}

def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases',type=Path,default=Path(__file__).with_name('COMMUNICATIONS_A1_EXPLANATION_SCENARIOS_2026-09-24.json'))
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        pack=json.loads(args.cases.read_text(encoding='utf-8'),parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))
        result=evaluate(pack)
        body=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
        if args.output: args.output.write_text(body,encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(1,f'Reference check failed: {exc}\n')
if __name__=='__main__': main()
