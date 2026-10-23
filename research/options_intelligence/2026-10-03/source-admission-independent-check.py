#!/usr/bin/env python3
"""Portable preservation of the executed independent synthetic reference review.

The 47-case construction/assertion block is unchanged from the actually executed
/tmp/source-admission-independent-review.py (SHA-256
3ad5c9d8340bb85a015c279da29e5ec181cdcaad9205c60e52d12deba96fe516).
This portable edition changes path/output plumbing, requires exact reviewed input
hashes, and faithfully adds the six previously executed CLI payloads. CLI checks
now call the same main() with in-memory stdio instead of launching subprocesses.
No network, external process, provider, source write, or output-file operation.
This checks a synthetic research reference and grants no production authority.
"""
import copy
import contextlib
import io
import sys
import hashlib
import json
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parent
source = (ROOT / 'source-admission-reference.py').read_bytes()
fixture_bytes = (ROOT / 'source-admission-fixtures.json').read_bytes()
EXPECTED_REFERENCE_SHA256 = 'c935d56729043c20692e6bc0bfddb9592cbde07328932d750fd36a945b72441c'
EXPECTED_FIXTURES_SHA256 = '2e5fc497bb0ffb13625ae4661365ee0ce5252e7cae10a0f5b1468950f407b8eb'
if hashlib.sha256(source).hexdigest() != EXPECTED_REFERENCE_SHA256:
    raise SystemExit('Refused: reference bytes differ from independently reviewed input')
if hashlib.sha256(fixture_bytes).hexdigest() != EXPECTED_FIXTURES_SHA256:
    raise SystemExit('Refused: fixture bytes differ from independently reviewed input')
m = types.ModuleType('independent_exact_snapshot')
m.__file__ = str(ROOT / 'source-admission-reference.py')
exec(compile(source, m.__file__, 'exec'), m.__dict__)
bundle = json.loads(fixture_bytes)
base, policy = bundle['base_evidence'], bundle['policy']
checks = []

def setpath(e, path, value):
    keys=path.split('.')
    for key in keys[:-1]: e=e[int(key)] if isinstance(e,list) else e[key]
    e[int(keys[-1]) if isinstance(e,list) else keys[-1]]=copy.deepcopy(value)

def getpath(e, path):
    for key in path.split('.'):e=e[int(key)] if isinstance(e,list) else e[key]
    return e

def check(name, changes, expected, evidence=None, policy_changes=None):
    e=copy.deepcopy(base if evidence is None else evidence);p=copy.deepcopy(policy)
    for key,value in changes.items():setpath(e,key,value)
    for key,value in (policy_changes or {}).items():setpath(p,key,value)
    before=copy.deepcopy(e),copy.deepcopy(p)
    got=m.evaluate(e,p)
    assertions={'source_certified_accepted':False,'reference_scope':'research_fixture_only',**expected}
    failures=[]
    for key,want in assertions.items():
        value=getpath(got,key)
        if value!=want or type(value)!=type(want):failures.append({'path':key,'expected':want,'actual':value})
    if before!=(e,p):failures.append({'path':'input_immutability'})
    if m.evaluate(e,p)!=got:failures.append({'path':'determinism'})
    checks.append({'case':name,'changes':changes,'expected':assertions,'failures':failures,'acceptance':got['acceptance']})
    return got

PASS={'acceptance.synthetic_contract_pass':True}
FAIL={'acceptance.synthetic_contract_pass':False}
check('baseline_literal_money',{},dict(PASS,**{'nbbo.source_premium_usd':'200','nbbo.at_ask_share':'1','inferred.signed_premium_usd':'200','side_proxy.ask_share_proxy':'0.8'}))
check('midpoint_observed_zero_not_unknown_location',{'records.0.quote.ask':'2.2'},dict(PASS,**{'nbbo.at_ask_share':'0','nbbo.inside_share':'1','inferred.signed_premium_usd':None,'inferred.unknown_premium_usd':'200'}))
check('inside_upper_half_inferred',{'records.0.price':'1.95'},dict(PASS,**{'nbbo.inside_share':'1','nbbo.at_ask_share':'0','inferred.signed_premium_usd':'195'}))
check('outside_location_abstains',{'records.0.price':'2.1'},dict(PASS,**{'nbbo.outside_share':'1','inferred.signed_premium_usd':None,'inferred.unknown_premium_usd':'210'}))
check('producer_before_trade',{'clocks.producer_classified_at':'2026-10-02T11:59:00.000Z'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('producer_before_input_available',{'clocks.producer_classified_at':'2026-10-02T12:00:00.075Z'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('producer_equal_available_boundary',{'clocks.producer_classified_at':'2026-10-02T12:00:00.100Z'},PASS)
check('contract_ref_after_classifier',{'records.0.contract_reference.available_at':'2026-10-02T12:00:00.175Z'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('offset_minute_99_rejected',{'records.0.quote.quote_timestamp':'2026-10-02T13:38:59.500+00:99'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('valid_offset_equivalent',{'records.0.quote.quote_timestamp':'2026-10-02T13:29:59.500+01:30'},dict(PASS,**{'nbbo.valid_print_count':1}))
check('submillisecond_rejected',{'records.0.quote.quote_timestamp':'2026-10-02T11:59:59.5000009Z'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('future_quote_rejected',{'records.0.quote.quote_timestamp':'2026-10-02T12:00:00.001Z'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('equal_quote_rejected',{'records.0.quote.quote_timestamp':'2026-10-02T12:00:00.000Z'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('stale_boundary_kept',{'records.0.quote.quote_timestamp':'2026-10-02T11:59:59.000Z'},PASS)
check('stale_beyond_rejected',{'records.0.quote.quote_timestamp':'2026-10-02T11:59:58.999Z'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('locked_rejected',{'records.0.quote.bid':'2'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('crossed_rejected',{'records.0.quote.bid':'2.01'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('zero_size_rejected',{'records.0.quote.bid_size':0},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('wrong_quote_contract',{'records.0.quote.contract_id':'SYN:OTHER:2026-10-16:C:100'},dict(FAIL,**{'nbbo.valid_print_count':0}))
check('unretained_contract_reference',{'records.0.contract_reference.original_receipt_retained':False},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('publication_after_consumer',{'publication_receipt.published_at':'2026-10-02T12:00:00.500Z'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('consumer_after_decision',{'consumer_receipt.admitted_at':'2026-10-02T12:00:01.001Z'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('revision_mismatch',{'consumer_receipt.revision':'other'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('reconstructed_not_captured',{'provenance.mode':'reconstructed_history'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('real_unqualified_refused',{'input_origin':'real_unqualified'},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))
check('boolean_quantity_not_integer',{'records.0.contracts':True},dict(FAIL,**{'nbbo.source_premium_usd':None,'nbbo.premium_coverage':None}))
check('deliverable_mismatch',{'records.0.contract_reference.underlying_units':'100'},dict(FAIL,**{'nbbo.source_premium_usd':None}))
check('unicode_sequence_refused',{'records.0.source_sequence':'٧'},dict(FAIL,**{'nbbo.source_premium_complete':False,'nbbo.source_premium_usd':None}))

def pair():
    e=copy.deepcopy(base);r=copy.deepcopy(e['records'][0]);r['record_id']='independent-r2';r['input_receipt']['record_id']='independent-r2';r['source_sequence']='8';e['records'].append(r);return e

e=pair();e['records'][1]['contracts']=6;e['records'][1]['quote']=None
check('unequal_missing_quote_preserves_denominator',{},dict(PASS,**{'nbbo.source_premium_usd':'800','nbbo.covered_premium_usd':'200','nbbo.print_coverage':'0.5','nbbo.premium_coverage':'0.25','nbbo.at_ask_share':'1','inferred.unknown_premium_usd':'600'}),e)
e=pair();e['records'][1]['contracts']=6;e['records'][1]['quote']['bid']='2';e['records'][1]['quote']['ask']='2.2'
check('unequal_signed_premiums_literal',{},dict(PASS,**{'nbbo.source_premium_usd':'800','nbbo.at_ask_share':'0.25','nbbo.at_bid_share':'0.75','inferred.signed_premium_usd':'-400'}),e)
e=pair();e['records'][1]['price']='NaN'
check('one_unknown_premium_blocks_complete_denominator',{},dict(FAIL,**{'nbbo.source_premium_usd':None,'nbbo.known_record_premium_usd':'200','nbbo.premium_coverage':None}),e)
e=pair();e['records'][1]['correction_status']='unresolved'
check('one_unresolved_correction_blocks_cohort',{},dict(FAIL,**{'acceptance.captured_pit_eligible':False,'nbbo.source_premium_usd':None}),e)
e=pair();e['records'][1]['source_sequence']='7'
check('same_source_identity_different_record_id',{},dict(FAIL,**{'acceptance.captured_pit_eligible':False,'nbbo.source_premium_usd':None}),e)
e=pair();e['records'][1]['source_sequence']='07'
check('leading_zero_sequence_cannot_double_denominator',{},dict(FAIL,**{'acceptance.captured_pit_eligible':False,'nbbo.source_premium_usd':None}),e)
e=pair();e['records'][1]['sequence_scope']='unqualified'
check('mixed_unknown_sequence_scope_blocks_cohort',{},dict(FAIL,**{'nbbo.source_premium_usd':None}),e)
e=pair();e['input_basis']='source_side_category_proxy';e['requested_claim']='legacy_side_proxy';e['records'][1]['quote_multiplier']=None
check('proxy_unknown_premium_not_hidden',{},dict(FAIL,**{'nbbo.source_premium_usd':None,'side_proxy.category_premium_coverage':None}),e)
check('honest_proxy_separate',{'input_basis':'source_side_category_proxy','requested_claim':'legacy_side_proxy','records.0.quote':None},dict(PASS,**{'nbbo.at_ask_share':None,'side_proxy.ask_share_proxy':'0.8'}))
check('proxy_cannot_be_measured',{'input_basis':'source_side_category_proxy'},FAIL)
check('selected_cannot_be_marketwide',{'requested_coverage_scope':'market_wide'},FAIL)

g=next(c for c in bundle['cases'] if c['id']=='complete_greek_reference_only')['changes']['additional_input_refs']
g=copy.deepcopy(g);g[0]['available_at']='2026-10-02T12:00:00.175Z'
check('feature_only_greek_after_classifier_before_feature',{'additional_input_refs':g},PASS)
g[0]['available_at']='2026-10-02T12:00:00.201Z'
check('greek_after_feature_rejected',{'additional_input_refs':g},dict(FAIL,**{'acceptance.captured_pit_eligible':False}))

left={'as_of':'2026-10-01','artifact_revision':'rev1','population_ref':'pop1','row_count':69}
right=copy.deepcopy(left);right['row_count']=62
check('same_date_only_row_count_collision',{'join_request':{'left':left,'right':right}},dict(FAIL,**{'join_identity.compatible':False}))
right=copy.deepcopy(left);right['artifact_revision']='rev2'
check('same_count_only_revision_collision',{'join_request':{'left':left,'right':right}},dict(FAIL,**{'join_identity.compatible':False}))
check('exact_identity_control',{'join_request':{'left':left,'right':left}},dict(PASS,**{'join_identity.compatible':True}))

label={'label_id':'label1','label_revision':'v1','matures_at':'2026-10-02T12:01:00.000Z','available_at':'2026-10-02T12:01:00.100Z','evaluation_at':'2026-10-02T12:01:00.099Z','value':'0'}
check('outcome_unavailable_until_actual_availability',{'outcome_reference':label},dict(PASS,**{'outcome.status':'pending','outcome.value':None}))
label['evaluation_at']='2026-10-02T12:01:00.100Z'
check('outcome_available_zero_preserved',{'outcome_reference':label},dict(PASS,**{'outcome.status':'available','outcome.value':'0'}))
label['label_id']=123
check('numeric_outcome_identity_unavailable',{'outcome_reference':label},dict(PASS,**{'outcome.status':'unavailable','outcome.value':None}))

literal=m.run_fixtures(bundle)
mutations=m.run_mutations(bundle)
post=m.run_fixtures(bundle)
# These exact payloads/expected return values were first executed via subprocess
# in the independent review. Reuse the CLI parser/main here without a process.
valid_packet=json.dumps({'evidence':base,'policy':policy})
cli_cases=[
    ('valid',valid_packet,0,True),
    ('duplicate_key','{"evidence":{},"evidence":{},"policy":{}}',2,False),
    ('nonfinite','{"evidence":NaN,"policy":{}}',2,False),
    ('extra_envelope_key','{"evidence":{},"policy":{},"candidate_id":"x"}',2,False),
    ('wrong_envelope_type','[]',2,False),
    ('malformed_json','{',2,False),
]
cli_results=[]
for name,packet,want_rc,want_accepted in cli_cases:
    saved_argv,saved_stdin=sys.argv,sys.stdin
    stdout,stderr=io.StringIO(),io.StringIO()
    try:
        sys.argv=[m.__file__,'--validate-stdin']
        sys.stdin=io.StringIO(packet)
        with contextlib.redirect_stdout(stdout),contextlib.redirect_stderr(stderr):
            returncode=m.main()
    finally:
        sys.argv,sys.stdin=saved_argv,saved_stdin
    output=json.loads(stdout.getvalue())
    failure=(returncode!=want_rc
             or output['acceptance']['synthetic_contract_pass'] is not want_accepted
             or output['source_certified_accepted'] is not False
             or stderr.getvalue()!='')
    cli_results.append({'case':name,'returncode':returncode,
                        'expected_returncode':want_rc,'failed':failure,
                        'acceptance':output['acceptance'],'stderr':stderr.getvalue()})

result={'code_sha256':hashlib.sha256(source).hexdigest(),
        'fixture_sha256':hashlib.sha256(fixture_bytes).hexdigest(),
        'independent_cases':len(checks),
        'independent_failures':[c for c in checks if c['failures']],
        'checks':checks,'author_literal_count':len(bundle['cases']),
        'author_literal_failures':literal,'mutation_results':mutations,
        'mutation_survivors':sum(not x['killed'] for x in mutations),
        'post_mutation_failures':post,'cli_cases':len(cli_results),
        'cli_results':cli_results,'cli_failures':[c for c in cli_results if c['failed']]}
print(json.dumps(result,indent=2))
failed=(result['independent_failures'] or literal or post
        or result['mutation_survivors'] or result['cli_failures'])
raise SystemExit(1 if failed else 0)
