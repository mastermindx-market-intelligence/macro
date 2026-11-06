"""Execute hypothetical R12 semantic witnesses, not Mastermind product code.

No repository imports, native ID minting, upstream source admission, network,
credentials, private storage or runtime writes. This is a research decision
oracle, NOT the proposed native v1.1 implementation. It deliberately checks only
its small closed witness notation. Native compatibility/integration stays owed.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

DECIMAL = re.compile(r'-?(?:0|[1-9][0-9]{0,29})(?:\.[0-9]{1,12})?\Z', re.ASCII)

class Refusal(ValueError):
    pass

def require(condition: bool, code: str) -> None:
    if not condition:
        raise Refusal(code)

def exact(value: Any) -> Decimal:
    require(isinstance(value, str) and DECIMAL.fullmatch(value) is not None, 'decimal_lexeme')
    return Decimal(value)

def rendered(value: Decimal) -> str:
    if value == 0:
        return '0'
    text = format(value, 'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text

def closed(obj: Any, keys: set[str]) -> None:
    require(isinstance(obj, dict) and set(obj) == keys, 'closed_shape')

def measurement(row: dict[str, Any]) -> dict[str, Any]:
    require(isinstance(row, dict), 'closed_shape')
    if row.get('kind') == 'non_numeric':
        closed(row, {'kind','state','source_text'})
        require(row['state'] in {'not_disclosed','qualitative','not_applicable','source_missing'}, 'non_numeric_state')
        require(isinstance(row['source_text'],str) and bool(row['source_text'].strip()), 'source_text_required')
        return {'valid': True}
    closed(row, {'kind','measure_class','value','unit','unit_label','currency','scale','basis','origin','source_text'})
    require(row['kind']=='numeric','observation_kind')
    cls=row['measure_class']
    require(cls in {'physical_count','physical_quantity','financial_amount','financial_change','ratio_level','ratio_change','unit_price','royalty_rate'},'measure_class')
    val=row['value']
    require(isinstance(val,dict),'closed_shape')
    if val.get('kind')=='point':
        closed(val, {'kind','decimal'}); values=[exact(val['decimal'])]
    else:
        closed(val, {'kind','low','high','low_inclusive','high_inclusive'})
        require(val['kind']=='interval','value_kind')
        values=[exact(val['low']),exact(val['high'])]
        require(type(val['low_inclusive']) is bool and type(val['high_inclusive']) is bool,'interval_bounds')
        require(values[0] <= values[1], 'interval_order')
        require(values[0] != values[1] or (val['low_inclusive'] and val['high_inclusive']),'empty_interval')
    if cls in {'physical_count','physical_quantity'}:
        require(all(v>=0 for v in values),'negative_physical')
    if cls=='physical_count':
        require(all(v==v.to_integral_value() for v in values),'fractional_count')
    if cls=='royalty_rate':
        require(all(0<=v<=100 for v in values),'royalty_rate_range')
    allowed_units={
        'physical_count':{'count'},'physical_quantity':{'quantity'},
        'financial_amount':{'currency'},'financial_change':{'currency','percent','percentage_point'},
        'ratio_level':{'ratio','percent'},'ratio_change':{'ratio','percent','percentage_point'},
        'unit_price':{'currency'},'royalty_rate':{'percent'}}
    require(row['unit'] in allowed_units[cls], 'unit_class_mismatch')
    require(isinstance(row['unit_label'],str) and bool(row['unit_label'].strip()),'unit_label_required')
    require(type(row['scale']) is int and row['scale'] in {0,3,6,9},'scale')
    if row['unit']=='currency':
        require(isinstance(row['currency'],str) and re.fullmatch('[A-Z]{3}',row['currency']) is not None,'currency_required')
    else:
        require(row['currency'] is None and row['scale']==0,'noncurrency_scale')
    basis=row['basis']; closed(basis,{'metric','entity_scope','period','denominator','gross_net','stock_flow'})
    require(basis['gross_net'] in {None,'gross','net'},'gross_net_enum')
    require(basis['stock_flow'] in {None,'stock','flow'},'stock_flow_enum')
    for name in ('metric','entity_scope','period'):
        require(isinstance(basis[name],str) and bool(basis[name].strip()),'basis_required')
    require(basis['denominator'] is None or (isinstance(basis['denominator'],str) and bool(basis['denominator'].strip())),'denominator_shape')
    if cls in {'royalty_rate','unit_price','ratio_level','ratio_change'} or row['unit'] in {'percent','percentage_point'}:
        require(bool(basis['denominator']), 'denominator_required')
    require(row['origin'] in {'reported','derived','target'},'origin_enum')
    require(isinstance(row['source_text'],str) and bool(row['source_text'].strip()),'source_text_required')
    return {'valid':True}

def evaluate(op: str, inp: dict[str, Any]) -> dict[str, Any]:
    try:
        with localcontext() as ctx:
            ctx.prec=96
            if op=='measurement':
                return measurement(inp)
            if op=='rate_change':
                old,new=exact(inp['old']),exact(inp['new'])
                require(old!=0,'zero_relative_base')
                return {'percentage_points':rendered(new-old),'relative_percent':rendered((new-old)/old*100)}
            if op=='revenue_change':
                v,p=exact(inp['volume_percent']),exact(inp['price_percent'])
                require(v>=-100 and p>=-100,'invalid_growth_factor')
                return {'revenue_percent':rendered(((1+v/100)*(1+p/100)-1)*100)}
            if op=='waterfall':
                require(inp['royalty_rate_percent'] is not None,'rate_not_disclosed')
                require(inp['royalty_base']=='net_sales','royalty_base_mismatch')
                gross,deductions,cost=map(exact,(inp['gross_sales'],inp['deductions'],inp['cash_operating_cost']))
                royalty_rate,share=map(exact,(inp['royalty_rate_percent'],inp['profit_share_percent']))
                require(0<=royalty_rate<=100 and 0<=share<=100,'rate_range')
                require(gross>=deductions>=0 and cost>=0,'waterfall_basis')
                net=gross-deductions; royalty=net*royalty_rate/100
                profit=net-cost-royalty
                require(profit>=0,'loss_allocation_unproven')
                partner=profit*share/100
                return {k:rendered(v) for k,v in {'net_sales':net,'royalty':royalty,'profit_before_share':profit,'partner_share':partner,'commercializer_residual':profit-partner}.items()}
            if op=='loss_share':
                profit,share=exact(inp['profit']),exact(inp['share_percent'])
                require(0<=share<=100,'rate_range')
                require(profit>=0 or inp['loss_sharing']=='included','loss_allocation_unproven')
                return {'allocation':rendered(profit*share/100)}
            if op=='tiered_royalty':
                require(inp['mode'] in {'marginal','whole_base'},'tier_method_unproven')
                sales,threshold,lo,hi=map(exact,(inp['sales'],inp['threshold'],inp['lower_percent'],inp['upper_percent']))
                require(sales>=0 and threshold>=0 and 0<=lo<=100 and 0<=hi<=100,'tier_basis')
                if inp['mode']=='marginal':
                    payout=min(sales,threshold)*lo/100+max(sales-threshold,Decimal(0))*hi/100
                else:
                    payout=sales*(lo if sales<=threshold else hi)/100
                return {'royalty':rendered(payout)}
            if op=='supply':
                rows=inp['rows']; require(type(inp['complete']) is bool,'coverage_boolean')
                require(inp['source_freshness'] in {'fresh','stale','unknown'},'freshness')
                require(all(r['jurisdiction']=='US' for r in rows),'jurisdiction_mismatch')
                if not inp['complete']:
                    status='CANDIDATE_NOT_ELIGIBLE'
                else:
                    statuses={r['regulator_status'] for r in rows}
                    if not statuses: status='EMPTY_OBSERVATION'
                    elif statuses=={'Current'}: status='CURRENT'
                    elif 'Current' in statuses: status='MIXED_WITH_CURRENT'
                    elif statuses=={'Resolved'}: status='RESOLVED_IN_SCOPE'
                    elif statuses=={'Discontinued'}: status='DISCONTINUED_IN_SCOPE'
                    else: status='UNKNOWN_STATUS'
                return {'status':status,'coverage':'COMPLETE_INTERVAL' if inp['complete'] else 'INCOMPLETE','freshness':inp['source_freshness'],'economic_conclusion':'NOT_ESTABLISHED'}
            if op=='version_boundary':
                version=inp['wire_schema']
                require(version in {'theme_graph.curation_assertion.v1','theme_graph.curation_assertion.v1.1'},'unsupported_version')
                require(version!='theme_graph.curation_assertion.v1' or inp['uses_extension'] is False,'new_meaning_in_legacy_version')
                return {'selection':'unchanged_shared_v1_branch' if version.endswith('.v1') else 'shared_v1_1_branch_candidate'}
            if op=='profile_boundary':
                require(not (inp['request_profile']=='healthcare' and inp['response_schema']=='semiconductor_theme_research.v1'),'profile_mismatch')
                return {'valid':True}
            raise Refusal('unsupported_witness_operation')
    except Refusal as exc:
        return {'error':str(exc)}

def check_packet(doc: dict[str,Any]) -> dict[str,Any]:
    require(doc['native_application_execution']=='NOT_EXECUTED','application_state')
    for k in ('native_schema_implemented','independent_review_accepted','healthcare_worker_started'):
        require(doc[k] is False,'false_acceptance')
    require(len(doc['inherited_application_case_ids'])==60 and len(set(doc['inherited_application_case_ids']))==60,'inherited_case_coverage')
    require(len(doc['coverage_family_ids'])==12 and len(set(doc['coverage_family_ids']))==12,'family_coverage')
    ids=[x['id'] for x in doc['cases']]
    require(len(ids)==len(set(ids)),'duplicate_witness')
    results=[]
    for case in doc['cases']:
        require(case['native_application_execution']=='NOT_EXECUTED','application_state')
        original=copy.deepcopy(case['input'])
        result=evaluate(case['operation'],case['input'])
        require(case['input']==original,'input_mutated')
        require(result==case['expected'],f"witness_mismatch:{case['id']}:{result}")
        results.append({'id':case['id'],'local_witness':'PASS','result':result,'native_application_execution':'NOT_EXECUTED'})
    return {'case_count':len(results),'operations':dict(Counter(x['operation'] for x in doc['cases'])),'results':results}


# These are authored synthetic examples, not collected company records.
def number(v, cls='financial_amount', unit='currency', denominator=None, **kw):
    obj={'kind':'numeric','measure_class':cls,'value':{'kind':'point','decimal':v},'unit':unit,'unit_label':{'count':'procedure','quantity':'kilogram','currency':'USD','percent':'percent','percentage_point':'percentage point','ratio':'dimensionless ratio'}[unit],'currency':'USD' if unit=='currency' else None,'scale':6 if unit=='currency' else 0,'basis':{'metric':'synthetic_measure','entity_scope':'hypothetical business only','period':'hypothetical quarter','denominator':denominator,'gross_net':None,'stock_flow':None},'origin':'reported','source_text':'Invented witness; not a company observation.'}
    obj.update(kw);return obj

def non_numeric(state='not_disclosed'):
    return {'kind':'non_numeric','state':state,'source_text':'A royalty exists but its numerical terms are undisclosed (invented example).'}

cases=[]
def add(label,op,data,expected):
    cases.append({'id':f'R12-W{len(cases)+1:02d}','label':label,'operation':op,'input':data,'expected':expected,'native_application_execution':'NOT_EXECUTED'})

def valid(label,v):add(label,'measurement',v,{'valid':True})
def bad(label,v,code):add(label,'measurement',v,{'error':code})
valid('Signed financial level survives',number('-19.102'))
valid('Signed financial change survives',number('-2.0','financial_change','percent','prior-period comparable revenue'))
valid('Physical count is non-negative',number('4','physical_count','count',currency=None,scale=0))
bad('Negative physical count rejected',number('-4','physical_count','count',currency=None,scale=0),'negative_physical')
bad('Fractional count is not an integer count',number('2.5','physical_count','count',currency=None,scale=0),'fractional_count')
valid('Fractional physical quantity is explicit',number('2.5','physical_quantity','quantity','per batch',currency=None,scale=0))
valid('Unknown royalty remains a fact without a number',non_numeric())
v=non_numeric();v['value']={'kind':'point','decimal':'0'};bad('Missing rate cannot carry zero',v,'closed_shape')
bad('Boolean is not an exact decimal',number(True),'decimal_lexeme')
bad('Binary float is not an exact source decimal',number(0.1),'decimal_lexeme')
bad('NaN refused',number('NaN'),'decimal_lexeme')
bad('Exponent notation refused by bounded canonical witness',number('1e1000000'),'decimal_lexeme')
bad('Oversized decimal refused',number('9'*31),'decimal_lexeme')
bad('Whitespace cannot silently normalize',number(' 5 '),'decimal_lexeme')
v=number('5','royalty_rate','percent','net product sales');valid('Exact rate has an economic denominator',v)
bad('Undenominated rate rejected',number('5','royalty_rate','percent'),'denominator_required')
bad('Royalty rate outside first-release range rejected',number('101','royalty_rate','percent','net product sales'),'royalty_rate_range')
v=number('5');v['basis']['gross_net']='net_sales';bad('net_sales is a base, not a gross/net enum',v,'gross_net_enum')
v=number('5');v['origin']='not_disclosed';bad('Disclosure state is not estimation provenance',v,'origin_enum')
v=number('5');v['value']={'kind':'interval','low':'5','high':'8','low_inclusive':True,'high_inclusive':True};valid('A documented interval remains an interval',v)
v=copy.deepcopy(v);v['value']['low']='9';bad('Reversed interval rejected',v,'interval_order')
v=number('3','ratio_change','percentage_point','rate level');valid('Percentage-point change has its own unit',v)
add('Rate levels yield both pp and relative change without confusion','rate_change',{'old':'10','new':'12'},{'percentage_points':'2','relative_percent':'20'})
add('Volume and price multiply, not add','revenue_change',{'volume_percent':'20','price_percent':'-10'},{'revenue_percent':'8'})
add('Sales-to-profit waterfall has distinct bases','waterfall',{'gross_sales':'1000','deductions':'200','cash_operating_cost':'600','royalty_rate_percent':'5','royalty_base':'net_sales','profit_share_percent':'25'},{'net_sales':'800','royalty':'40','profit_before_share':'160','partner_share':'40','commercializer_residual':'120'})
add('Wrong royalty denominator is refused, not silently substituted','waterfall',{'gross_sales':'1000','deductions':'200','cash_operating_cost':'600','royalty_rate_percent':'5','royalty_base':'gross_sales','profit_share_percent':'25'},{'error':'royalty_base_mismatch'})
add('Unknown rate produces no payout estimate','waterfall',{'gross_sales':'1000','deductions':'200','cash_operating_cost':'600','royalty_rate_percent':None,'royalty_base':'net_sales','profit_share_percent':'25'},{'error':'rate_not_disclosed'})
add('Loss allocation requires loss-sharing evidence','loss_share',{'profit':'-40','share_percent':'25','loss_sharing':'unknown'},{'error':'loss_allocation_unproven'})
add('Explicit loss sharing preserves negative allocation','loss_share',{'profit':'-40','share_percent':'25','loss_sharing':'included'},{'allocation':'-10'})
add('Graduated tiers do not apply the top rate to all sales','tiered_royalty',{'sales':'800','threshold':'100','lower_percent':'5','upper_percent':'8','mode':'marginal'},{'royalty':'61'})
add('Whole-base tier has different economics','tiered_royalty',{'sales':'800','threshold':'100','lower_percent':'5','upper_percent':'8','mode':'whole_base'},{'royalty':'64'})
add('Unspecified tier method cannot generate payout','tiered_royalty',{'sales':'800','threshold':'100','lower_percent':'5','upper_percent':'8','mode':'unknown'},{'error':'tier_method_unproven'})

def row(status,availability='Available',jurisdiction='US',product='Product Alpha'):
    return {'regulator_status':status,'manufacturer_availability':availability,'jurisdiction':jurisdiction,'product':product}
add('Current plus available remains current','supply',{'rows':[row('Current')],'complete':True,'source_freshness':'fresh'},{'status':'CURRENT','coverage':'COMPLETE_INTERVAL','freshness':'fresh','economic_conclusion':'NOT_ESTABLISHED'})
add('Different products cannot create a false all-clear','supply',{'rows':[row('Current'),row('Resolved',product='Product Beta')],'complete':True,'source_freshness':'fresh'},{'status':'MIXED_WITH_CURRENT','coverage':'COMPLETE_INTERVAL','freshness':'fresh','economic_conclusion':'NOT_ESTABLISHED'})
add('Resolved does not establish a glut','supply',{'rows':[row('Resolved')],'complete':True,'source_freshness':'fresh'},{'status':'RESOLVED_IN_SCOPE','coverage':'COMPLETE_INTERVAL','freshness':'fresh','economic_conclusion':'NOT_ESTABLISHED'})
add('Discontinuation is not resolution','supply',{'rows':[row('Discontinued')],'complete':True,'source_freshness':'fresh'},{'status':'DISCONTINUED_IN_SCOPE','coverage':'COMPLETE_INTERVAL','freshness':'fresh','economic_conclusion':'NOT_ESTABLISHED'})
add('Empty complete result stays explicitly empty','supply',{'rows':[],'complete':True,'source_freshness':'fresh'},{'status':'EMPTY_OBSERVATION','coverage':'COMPLETE_INTERVAL','freshness':'fresh','economic_conclusion':'NOT_ESTABLISHED'})
add('Incomplete candidate is ineligible, not empty success','supply',{'rows':[row('Resolved')],'complete':False,'source_freshness':'fresh'},{'status':'CANDIDATE_NOT_ELIGIBLE','coverage':'INCOMPLETE','freshness':'fresh','economic_conclusion':'NOT_ESTABLISHED'})
add('A fresh fetch cannot fill missing source freshness','supply',{'rows':[row('Current')],'complete':True,'source_freshness':'unknown'},{'status':'CURRENT','coverage':'COMPLETE_INTERVAL','freshness':'unknown','economic_conclusion':'NOT_ESTABLISHED'})
add('Unknown source status is not a negative claim','supply',{'rows':[row('Unrecognized')],'complete':True,'source_freshness':'fresh'},{'status':'UNKNOWN_STATUS','coverage':'COMPLETE_INTERVAL','freshness':'fresh','economic_conclusion':'NOT_ESTABLISHED'})
add('Jurisdiction mixing refuses a national aggregate','supply',{'rows':[row('Resolved'),row('Current',jurisdiction='EU')],'complete':True,'source_freshness':'fresh'},{'error':'jurisdiction_mismatch'})
add('Old encoded body remains valid only on the legacy version','version_boundary',{'wire_schema':'theme_graph.curation_assertion.v1','uses_extension':True},{'error':'new_meaning_in_legacy_version'})
add('Extension gets explicit version without rewriting old records','version_boundary',{'wire_schema':'theme_graph.curation_assertion.v1.1','uses_extension':True},{'selection':'shared_v1_1_branch_candidate'})
add('Unknown native version refuses','version_boundary',{'wire_schema':'theme_graph.curation_assertion.v99','uses_extension':False},{'error':'unsupported_version'})
add('Shared URL alone cannot claim Healthcare profile','profile_boundary',{'request_profile':'healthcare','response_schema':'semiconductor_theme_research.v1'},{'error':'profile_mismatch'})
add('Generic legacy work stays with shared v1 branch','version_boundary',{'wire_schema':'theme_graph.curation_assertion.v1','uses_extension':False},{'selection':'unchanged_shared_v1_branch'})


INHERITED_APPLICATION_IDS = ['R8-A01', 'R8-A02', 'R8-A03', 'R8-A04', 'R8-A05', 'R8-A06', 'R8-A07', 'R8-A08', 'R8-A09', 'R8-A10', 'R8-A11', 'R8-A12', 'R8-A13', 'R8-A14', 'R8-A15', 'R8-A16', 'R8-A17', 'R8-A18', 'R8-A19', 'R8-A20', 'R8-A21', 'R8-A22', 'R8-A23', 'R8-A24', 'R8-A25', 'R8-A26', 'R8-A27', 'R8-A28', 'R8-A29', 'R8-A30', 'R8-A31', 'R8-A32', 'R8-A33', 'R8-A34', 'R8-A35', 'R8-A36', 'R8-A37', 'R8-A38', 'R8-A39', 'R8-A40', 'R8-A41', 'R9-A01', 'R9-A02', 'R9-A03', 'R9-A04', 'R9-A05', 'R9-A06', 'R9-A07', 'R10-A01', 'R10-A02', 'R10-A03', 'R10-A04', 'R10-A05', 'R10-A06', 'R10-A07', 'R10-A08', 'R10-A09', 'R10-A10', 'R10-A11', 'R10-A12']
COVERAGE_FAMILY_IDS = ['R8-F01', 'R8-F02', 'R8-F03', 'R8-F04', 'R8-F05', 'R8-F06', 'R8-F07', 'R8-F08', 'R8-F09', 'R8-F10', 'R8-F11', 'R8-F12']

def candidate_payloads() -> list[dict[str, Any]]:
    """Complete candidate envelopes; unstamped, synthetic, NOT native-validity proof."""
    common = {
        'schema':'theme_graph.curation_assertion.v1.1','curation_revision':None,
        'review':{'disposition':'held','reviewed_at':'2026-09-24T00:02:00Z','reviewer':'synthetic-design-only','review_due_at':None},
        'source':{'publisher':'Hypothetical issuer','source_uri':'https://example.invalid/synthetic','locator':'Invented paragraph','published_at':None,'published_at_grain':'unknown','observed_at':'2026-09-24T00:00:00Z','retained_at':'2026-09-24T00:00:00Z','retention_ref':None,'native_digest':None},
        'subject':{'company_node_id':None,'source_business_label':'Hypothetical Developer','source_product_label':'Program Alpha','source_platform_label':None,'configuration':None},
        'object':{'source_product_label':'Program Alpha','configuration':None},
        'predicate':'REPORTED_ECONOMIC_RIGHT','statement_mode':'REPORTED_FACT',
        'scope':{'canonical_theme_id':'glp1_obesity','application':'hypothetical metabolic program','technology_facet':None,'region':'source-described worldwide scope','period':None,'denominator':None},
        'observation':{'kind':'non_numeric','state':'not_applicable','source_text':'The primary assertion is a contractual relationship, not a single aggregate measurement.'},
        'temporal':{'business_valid_from':None,'business_valid_to':None},
        'limitations':{'establishes':['Shape of an invented research example only'],'does_not_establish':['Actual contract','Native schema validity','Source retention','Security identity','Investment conclusion'],'coverage':'synthetic','source_dependence':'invented','expiry_trigger':None},
        'correction':{'predecessor_revision':None,'reason':None},
        'authority':{'can_rank':False,'can_gate':False,'can_size':False,'can_originate':False,'can_open_entry':False}}
    right = copy.deepcopy(common)
    right['economic_right'] = {
        'parties':[{'selector':'developer','source_label':'Hypothetical Developer','company_node_id':None},{'selector':'licensor','source_label':'Hypothetical Licensor','company_node_id':None}],
        'grantor':'licensor','grantee':'developer','asset_label':'Program Alpha','indication_label':None,'territory_label':'worldwide',
        'activities':['development','commercialization'],'arrangement_state':'operative_reported','change_basis':'reported_terms',
        'components':[{'selector':'royalty_a','kind':'royalty','payer':'developer','recipient':'licensor','payment_base':'net product sales','term':non_numeric('qualitative'),'tier_method':'unknown','cost_responsibility':None,'loss_participation':'unknown','conditions':['Numerical rate and tier schedule not disclosed in this invented example.'],'valid_from':None,'valid_to':None}],
        'unknowns':['Exact numerical terms','Deduction definition','Actual economic materiality']}
    supply=copy.deepcopy(common)
    supply['predicate']='REPORTED_SUPPLY_STATUS'
    supply['subject']['source_business_label']=None
    supply['scope']['region']='US'
    supply['source']['publisher']='Synthetic supply-source owner'
    supply['source']['observed_at']='2026-09-24T00:01:00Z'
    supply['source']['retained_at']='2026-09-24T00:01:00Z'
    supply['supply_status']={
        'status_authority':'Synthetic regulator','jurisdiction':'US','source_record_key':{'value':None,'strength':'content_scoped_only'},
        'product_label':'Program Alpha','presentation_label':'Hypothetical presentation',
        'regulator_status':{'raw':'Current','normalized':'current'},
        'manufacturer_availability':{'raw':'Available','normalized':'available'},
        'capture':{'started_at':'2026-09-24T00:00:00Z','completed_at':'2026-09-24T00:01:00Z','completeness':'complete_interval','atomic_snapshot_proven':False,'source_generation':None,'source_generation_freshness':'unknown','native_receipt_ref':None},
        'unknowns':['No actual upstream observation or native acquisition receipt exists.']}
    return [right,supply]

def packet() -> dict[str, Any]:
    return {'artifact_kind':'healthcare_r12_synthetic_semantic_witnesses','date':'2026-09-24',
            'scope':'Original hypothetical decision/arithmetic witnesses, not a native validator, registry, production contract or source facts.',
            'inherited_application_case_ids':INHERITED_APPLICATION_IDS,
            'coverage_family_ids':COVERAGE_FAMILY_IDS,
            'native_application_execution':'NOT_EXECUTED','native_schema_implemented':False,
            'independent_review_accepted':False,'healthcare_worker_started':False,
            'candidate_native_payloads':candidate_payloads(),'cases':cases}

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--emit-dir',type=Path,help='Optional local research outputs; never a native admission.')
    args=p.parse_args()
    doc=packet()
    report=check_packet(doc)
    for candidate in doc['candidate_native_payloads']:
        require(candidate['schema']=='theme_graph.curation_assertion.v1.1','candidate_schema')
        require(candidate['curation_revision'] is None and candidate['review']['disposition']=='held','candidate_not_admitted')
        require(all(v is False for v in candidate['authority'].values()),'candidate_authority')
        require(candidate['subject']['company_node_id'] is None,'candidate_unbound')
    report.update({'scope':'Local synthetic arithmetic and selected semantic witness checks only; full native schema/modules not executed.',
                   'native_application_tests_run':0,'candidate_native_payload_count':2,
                   'candidate_native_validation':'NOT_EXECUTED','inherited_application_cases':60,
                   'mutation_checks':[]})
    mutations=[('invented_native_pass',lambda d:d.update(native_application_execution='PASS')),
               ('invented_independent_review',lambda d:d.update(independent_review_accepted=True)),
               ('duplicate_witness',lambda d:d['cases'].append(copy.deepcopy(d['cases'][0]))),
               ('lost_original_case',lambda d:d['inherited_application_case_ids'].pop()),
               ('lost_family',lambda d:d['coverage_family_ids'].pop()),
               ('wrong_positive_expected',lambda d:d['cases'][0].update(expected={'valid':False})),
               ('wrong_negative_expected',lambda d:d['cases'][3].update(expected={'valid':True})),
               ('invented_worker',lambda d:d.update(healthcare_worker_started=True))]
    for name,change in mutations:
        candidate=copy.deepcopy(doc);change(candidate)
        try:check_packet(candidate)
        except Refusal:report['mutation_checks'].append({'id':name,'result':'REJECTED'})
        else:raise AssertionError('Mutation survived: '+name)
    raw=(json.dumps(doc,ensure_ascii=False,indent=2)+'\n').encode()
    report['packet_sha256']=hashlib.sha256(raw).hexdigest()
    if args.emit_dir:
        args.emit_dir.mkdir(parents=True,exist_ok=True)
        (args.emit_dir/'HEALTHCARE_R12_SEMANTIC_WITNESSES_2026-09-24.json').write_bytes(raw)
        (args.emit_dir/'LOCAL_WITNESS_RESULTS_2026-09-24.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False))

if __name__=='__main__':main()
