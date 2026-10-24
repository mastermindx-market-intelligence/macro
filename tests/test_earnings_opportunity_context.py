"""Synthetic/native-corpus contract tests; never real live acceptance."""
from copy import deepcopy
import pytest
from tests.test_earnings_opportunity_qualification import inputs
from engine.company_intelligence import opportunity_context as ec
from lib import opportunity_case as oc, opportunity_evidence as oe, evidence_foundation as ef


def evidence(inputs):
    return {k:v for k,v in ec.compose_candidate_evidence(**inputs,composed_at='2026-10-07T14:01:00Z').items() if k!='candidate_context_binding'}


def test_native_context_composes_substantive_case_without_live_or_surprise(inputs):
    ev=evidence(inputs); v=ev['vector']; assert oe.validate_vector(v)==[]
    case=oc.compose_case(**ev)
    assert oc.validate_case(case)==case
    assert case['company_context']['state']=='partial'
    assert case['company_context']['block_ids']
    assert case['company_context']['owner_slots'][0]['value_or_null']=={'value':1234,'unit':'usd_millions','basis':'reported','period':'2026Q3'}
    assert case['evidence_binding']['state']=='exact_owner_native_event'
    assert case['permitted_consumers']==['research_session']
    assert case['research_state']=='partial'
    assert case['subject']['subject_type']=='earnings_cik'
    assert case['market_incorporation']['denominator']['included']==0
    assert case['entry_availability']['entry_signal']['state']=='unknown'
    assert not any(case['authority'].values())
    assert all(x is None for k,x in case['calibrated'].items() if k!='state')
    assert ec.compose_candidate_case(**inputs,composed_at='2026-10-07T14:01:00Z')==case


@pytest.mark.parametrize('mutation',['live','wrong_subject','ticker_subject','generation','digest','value','source_clock','known_clock','build_clock','extra_slot','missing_link','foreign_link','consumer'])
def test_rehashed_vector_mutations_fail_closed(inputs,mutation):
    v=evidence(inputs)['vector']; s=v['slots'][0]
    if mutation=='live':v['asof']['t0_mode']='live'
    elif mutation=='wrong_subject':v['subject']['value']='0000320193'
    elif mutation=='ticker_subject':v['subject'].update(subject_type='us_listing_symbol',value='MU')
    elif mutation=='generation':s['earnings_context']['generation_id']='2'*24
    elif mutation=='digest':s['earnings_context']['workspace_sha256']='b'*64
    elif mutation=='value':s['value_or_null']['value']+=1
    elif mutation=='source_clock':s['earnings_context']['source_available_at']='2026-10-06T19:59:00Z'
    elif mutation=='known_clock':s['earnings_context']['observed_at']='2026-10-08T00:00:00Z'
    elif mutation=='build_clock':s['earnings_context']['generated_at']='2026-10-08T00:00:00Z'
    elif mutation=='extra_slot':v['slots'].append(deepcopy(s))
    elif mutation=='missing_link':del s['earnings_context']
    elif mutation=='foreign_link':s['construct']='sue_surprise'
    elif mutation=='consumer':v['permitted_consumers'].append('prophet')
    v['content_sha256']=oe.compute_content_sha256(v)
    assert oe.validate_vector(v)


@pytest.mark.parametrize('mutation',['reference_digest','reference_subject','slot_reference','mapping','secondary_subject'])
def test_k5_cross_contract_mismatches_refuse_after_rehash(inputs,mutation):
    ev=evidence(inputs);rid,ref=next(iter(ev['references'].items())); recipe=ev['recipe']
    if mutation=='slot_reference':ev['vector']['slots'][0]['owner_ref']['evidence_ref_id']=None
    elif mutation=='mapping':
        recipe['block_specs'][0]['output_fields']=['transmission'];recipe['output_mappings'][0]['output_field']='transmission'
        recipe['recipe_id']=ef.compute_recipe_id(recipe)
    else:
        if mutation=='reference_digest':ref['native_digest']['sha256']='b'*64
        elif mutation=='reference_subject':ref['subject']['key']='0000320193'
        elif mutation=='secondary_subject':ref['secondary_subjects']=[{'key_type':'cik','key':'0000320193'}]
        new=ef.compute_reference_id(ref);ref['reference_id']=new;ev['references']={new:ref}
        ev['blocks'][0]['reference_ids']=[new]
        for clock in ev['blocks'][0]['clock_summary']['entries']:clock['reference_id']=new
        ev['blocks'][0]['evidence_block_id']=ef.compute_block_id(ev['blocks'][0])
        ev['vector']['slots'][0]['owner_ref']['evidence_ref_id']=new
    ev['vector']['content_sha256']=oe.compute_content_sha256(ev['vector'])
    with pytest.raises(oc.OpportunityCaseError):oc.compose_case(**ev)


def test_event_case_identity_stable_across_native_generation_and_cutoff(inputs):
    first=ec.compose_candidate_case(**inputs,composed_at='2026-10-07T14:01:00Z')
    inputs['revisions'][0]['generation_id']='2'*24
    inputs['revisions'][0]['workspace']['generation_id']='2'*24
    from tests.test_earnings_opportunity_qualification import revision
    inputs['revisions']=[revision(inputs['revisions'][0]['workspace'])]
    second=ec.compose_candidate_case(**inputs,composed_at='2026-10-07T14:01:00Z')
    assert first['case_id']==second['case_id'] and first['content_sha256']!=second['content_sha256']


@pytest.mark.parametrize('mutation',['prior_quarter','workspace_quarter','unknown_end','other_end','segment_only'])
def test_owner_fact_period_and_whole_company_scope_do_not_get_inferred(inputs,mutation):
    body=inputs['revisions'][0]['workspace']
    if mutation=='prior_quarter':body['facts'][0]['period']='2026Q2'
    elif mutation=='workspace_quarter':body['fiscal_period']['quarter']=2
    elif mutation=='unknown_end':body['facts'][0]['period']='2026-06-27'
    elif mutation=='other_end':
        body['facts'][0]['period']='2026-06-27';body['fiscal_period']['calendar_end']='2026-06-28'
    else:body['facts'][0]['metric']='rms_segment_revenue'
    from engine.company_intelligence.opportunity_qualification import EarningsQualificationError
    with pytest.raises(EarningsQualificationError):ec.compose_candidate_case(**inputs,composed_at='2026-10-07T14:01:00Z')


def test_exact_native_calendar_end_is_accepted_without_calendar_quarter_guess(inputs):
    body=inputs['revisions'][0]['workspace'];body['facts'][0]['period']='2026-06-27'
    body['fiscal_period']['calendar_end']='2026-06-27'
    assert ec.compose_candidate_case(**inputs,composed_at='2026-10-07T14:01:00Z')['company_context']['state']=='partial'
