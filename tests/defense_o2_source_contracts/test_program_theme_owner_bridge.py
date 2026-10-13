"""Portable theme bridge regressions; frozen fixtures, no live owner reads.

Synthetic basket/terms check structure only. The frozen GD native owner checks
its reported category/literal. Neither fixture is production source admission.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import pytest
from engine.government_revenue import program_theme_context as t
from engine.government_revenue import program_theme_reviewed_builder as b
from engine.government_revenue import program_theme_disclosure as d
from engine.government_revenue.defense_economics import defense_economics_content_id
from test_program_theme_context import owners as legacy_owners

HERE=Path(__file__).parent
# Existing shared frozen fixture stays the base; no machine-specific paths.
BASE=HERE/'accepted_quartet_economics.json'
NOW='2026-10-13T08:00:00+00:00'


def snapshot(kind,payload):
 raw=json.dumps(payload).encode()
 return t.OwnerSnapshot(kind,raw,NOW,'test_fixture_not_production','qualified_public_display')


def basket_payload():
 p=json.loads(BASE.read_bytes());p['generated_at']=NOW;profile=p['profiles'][0]
 refs=[]
 for label in ('membership','pulse','baskets'):
  digest=sha256(label.encode()).hexdigest();key=f'group_pulse:defense:{label}:{digest}:LMT';refs.append(key)
  p['source_bindings'][key]=dict(sha256=digest,content_id='fixture:'+label,contract='group_pulse.v1' if label=='pulse' else 'basket_current_snapshot',owner_family='group_reads',issuer_id=profile['issuer_id'],security_id=profile['security_id'],periods=['2026-10-09'],observed_at='2026-10-13T05:30:00+00:00',owner_admission_ref='synthetic:'+label)
 profile['axes']['participation']=dict(state='stale',summary_en='Synthetic defense basket: 1/3 active, 3/3 covered; market 2026-10-09, membership 2026-08-07, assembled 2026-10-13T05:00:00Z.',summary_zh='合成测试国防篮子：1/3活跃，3/3覆盖；市场2026-10-09，成员2026-08-07，原来源生成2026-10-13T05:00:00Z。',owner_ref=refs[1],evidence_refs=refs,observed_at='2026-10-13T05:30:00+00:00',fiscal_period=None,facts=[],reason_code='current_basket_market_participation',limitations=['basket_context_not_issuer_alpha','current_membership_not_historical_first_seen','activity_not_capital_flow','capital_concentration_not_measured','no_scientific_or_rights_reclassification'])
 p['content_id']=defense_economics_content_id(p);return p


def basket_assignment(payload):
 ref=dict(owner_key='economic',pointer='/profiles/0/axes/participation',row_id=payload['profiles'][0]['issuer_id'])
 return {theme:{'market_context':dict(state='stale',reason_code='shared_defense_basket_not_theme_portfolio',references=[ref])} for theme in t.THEMES}


def compose(assignments,owners):
 return t.compose_program_theme_context(assignments,owners=owners,generated_at=NOW,as_of=NOW)


def test_shared_context_keeps_six_theme_missingness_and_native_scope():
 payload=basket_payload();owner=snapshot('defense_economics',payload);p=compose(basket_assignment(payload),{'economic':owner})
 display=d.disclose_program_themes(p,owners={'economic':owner},current_owner_receipts={'economic':dict(state='available',sha256=sha256(owner.raw_bytes).hexdigest(),owner_alias_state='unchanged')})
 assert all(row['research_state']=='EVIDENCE_INSUFFICIENT' for row in display['themes'])
 assert all('not a theme-specific portfolio' in row['known_en'] and 'membership and returns remain unqualified' in row['missing_en'] for row in display['themes'])
 assert all(row['rail_states']['market_context']=='stale' for row in display['themes'])


@pytest.mark.parametrize('mutation',['supported','stale_to_partial','wrong_reason','missing_limit','duplicate_source_kind','wrong_subject'])
def test_basket_scope_provenance_or_freshness_cannot_be_promoted(mutation):
 payload=basket_payload();assignment=basket_assignment(payload);axis=payload['profiles'][0]['axes']['participation']
 if mutation=='supported':assignment['space']['market_context']['state']='supported'
 if mutation=='stale_to_partial':assignment['space']['market_context']['state']='partial'
 if mutation=='wrong_reason':assignment['space']['market_context']['reason_code']='theme_portfolio_ready'
 if mutation=='missing_limit':axis['limitations'].remove('current_membership_not_historical_first_seen')
 if mutation=='duplicate_source_kind':axis['evidence_refs'][0]=axis['evidence_refs'][1]
 if mutation=='wrong_subject':payload['source_bindings'][axis['owner_ref']]['issuer_id']='cik:wrong'
 payload['content_id']=defense_economics_content_id(payload)
 with pytest.raises(ValueError):compose(assignment,{'economic':snapshot('defense_economics',payload)})


def fingerprint(payload):
 ref=basket_assignment(payload)['space']['market_context']['references'][0]
 return b.reference_fingerprint(ref,'market_context',snapshot('defense_economics',payload),NOW)


def test_only_replay_read_observation_clock_is_transport_identity():
 payload=basket_payload();original=fingerprint(payload);axis=payload['profiles'][0]['axes']['participation']
 axis['observed_at']='2026-10-13T05:40:00+00:00'
 for ref in axis['evidence_refs']:payload['source_bindings'][ref]['observed_at']=axis['observed_at']
 payload['content_id']=defense_economics_content_id(payload)
 assert fingerprint(payload)==original


@pytest.mark.parametrize('field',['native_assembly','membership','denominator','source_hash','state'])
def test_native_owner_observations_remain_material_fingerprint_dependencies(field):
 payload=basket_payload();original=fingerprint(payload);axis=payload['profiles'][0]['axes']['participation']
 if field=='native_assembly':axis['summary_en']=axis['summary_en'].replace('05:00:00Z','05:01:00Z')
 if field=='membership':axis['summary_en']=axis['summary_en'].replace('2026-08-07','2026-08-08')
 if field=='denominator':axis['summary_en']=axis['summary_en'].replace('3/3','3/4')
 if field=='source_hash':payload['source_bindings'][axis['evidence_refs'][0]]['sha256']='a'*64
 if field=='state':axis['state']='partial'
 payload['content_id']=defense_economics_content_id(payload)
 assert fingerprint(payload)!=original


@pytest.mark.parametrize('kind',['fms','program_dossier'])
def test_preexisting_contrary_owner_contract_is_preserved(kind):
 owners=legacy_owners();key='fms' if kind=='fms' else 'dossier';payload=owners[key].payload()
 if kind=='fms':
  row=payload['cases'][0];pointer='/cases/0';row_id=row['case_key']
 else:
  row=payload['dossiers'][0]['participants']['rows'][0];pointer='/dossiers/0/participants/rows/0';row_id=row['entity_id']
 ref=dict(owner_key=key,pointer=pointer,row_id=row_id)
 p=compose({'nato_fms_demand':{'contrary_case':dict(state='partial',reason_code='existing_owner_context',references=[ref])}},owners)
 assert p['themes'][3]['rails']['contrary_case']['references']==[ref]
 bad=deepcopy(ref);bad['row_id']='invented'
 with pytest.raises(ValueError):compose({'nato_fms_demand':{'contrary_case':dict(state='partial',reason_code='existing_owner_context',references=[bad])}},owners)


def financial_owners():
 payload=json.loads(BASE.read_bytes());payload['generated_at']=NOW
 terms=json.loads((HERE/'fixtures/theme_bridge_synthetic_shareholder_terms.json').read_bytes())
 payload['profiles'][3]['axes']['economics']['facts']+=terms['facts'];payload['source_bindings'].update(terms['source_bindings']);payload['content_id']=defense_economics_content_id(payload)
 gd=json.loads((HERE/'fixtures/gd_theme_backlog_owner.json').read_bytes())
 return {'economic':snapshot('defense_economics',payload),'gd':snapshot('company_intelligence',gd)}


def financial_assignments(owners):
 return {'space':{'contrary_case':dict(state='partial',reason_code='reported_space_ownership_change',references=[t.financial_fact_reference('economic',owners['economic'],'evt_cik0000202058_2026q2_results:'+suffix) for suffix in ('space_business_sale_completed_terms','space_business_sale_retained_scope')])},'shipbuilding':{'contrary_case':dict(state='partial',reason_code='reported_unfunded_backlog_category',references=[t.financial_fact_reference('gd',owners['gd'],'evt_cik0000040533_2026q2_results:marine_unfunded_backlog')])}}


def test_exact_financial_contrary_fact_owners_are_additive_partial_context():
 owners=financial_owners();p=compose(financial_assignments(owners),owners)
 assert p['themes'][2]['rails']['contrary_case']['state']=='partial'
 assert p['themes'][5]['rails']['contrary_case']['state']=='partial'
 assert all(row['research_state']=='EVIDENCE_INSUFFICIENT' for row in p['themes'])


@pytest.mark.parametrize('mutation',['wrong_theme','supported','wrong_reason','narrative'])
def test_financial_contrary_cannot_be_theme_promotion_or_profile_narrative(mutation):
 owners=financial_owners();assignment=financial_assignments(owners)
 if mutation=='wrong_theme':assignment['golden_dome']=assignment.pop('space')
 if mutation=='supported':assignment['space']['contrary_case']['state']='supported'
 if mutation=='wrong_reason':assignment['shipbuilding']['contrary_case']['reason_code']='funded_order_capture'
 if mutation=='narrative':
  ref=assignment['shipbuilding']['contrary_case']['references'][0];ref['pointer']='/issuer';ref['row_id']=owners['gd'].payload()['issuer']['company_id']
 with pytest.raises(ValueError):compose(assignment,owners)


def test_legacy_defense_profile_context_is_preserved_without_new_fact_claim():
 payload=json.loads(BASE.read_bytes());owner=snapshot('defense_economics',payload)
 ref=dict(owner_key='economic',pointer='/profiles/0/contrary_case',row_id=payload['profiles'][0]['issuer_id'])
 p=compose({'space':{'contrary_case':dict(state='partial',reason_code='existing_owner_context',references=[ref])}},{'economic':owner})
 display=d.disclose_program_themes(p,owners={'economic':owner},current_owner_receipts={'economic':dict(state='available',sha256=sha256(owner.raw_bytes).hexdigest(),owner_alias_state='unchanged')})
 assert payload['profiles'][0]['contrary_case'] in display['themes'][2]['known_en']


def test_new_named_financial_case_requires_exact_full_fact_namespace():
 owners=financial_owners();assignment=financial_assignments(owners);ref=assignment['space']['contrary_case']['references'][0]
 body=owners['economic'].payload();node,_=t._pointer(body,ref['pointer'])
 node['fact_id']='evt_cik0000936468_2026q2_results:space_business_sale_completed_terms';ref['row_id']=node['fact_id']
 body['content_id']=defense_economics_content_id(body);owners['economic']=snapshot('defense_economics',body)
 with pytest.raises(ValueError,match='theme_contrary_fact_scope_invalid'):compose(assignment,owners)


def milestone_case():
 owners=legacy_owners();graph=owners['ontology'].payload();index=next(i for i,row in enumerate(graph['milestones']) if row['id']=='prog-milestone:a904b5338b54')
 row=graph['milestones'][index];ref=dict(owner_key='ontology',pointer=f'/milestones/{index}',row_id=row['id'])
 return owners,{'shipbuilding':{'next_event':dict(state='partial',reason_code='reviewed_future_milestone_window',references=[ref])}}


def test_reviewed_future_window_is_partial_source_context_not_committed_delivery():
 owners,assignment=milestone_case();p=compose(assignment,owners)
 receipts={key:dict(state='available',sha256=sha256(owner.raw_bytes).hexdigest(),owner_alias_state='unchanged') for key,owner in owners.items()}
 display=d.disclose_program_themes(p,owners=owners,current_owner_receipts=receipts);ship=display['themes'][5]
 assert ship['rail_states']['next_event']=='partial' and ship['research_state']=='EVIDENCE_INSUFFICIENT'
 assert 'FY2032' in ship['next_en'] and 'owning milestone estimate' in ship['next_en']
 assert any(source['url']=='https://crsreports.congress.gov/product/pdf/RL/RL32418' for source in ship['sources'])


def test_program_or_role_cannot_be_relabelled_as_next_milestone():
 owners,assignment=milestone_case();role=owners['ontology'].payload()['role_assertions'][0]
 ref=assignment['shipbuilding']['next_event']['references'][0];ref.update(pointer='/role_assertions/0',row_id=role['id'])
 with pytest.raises(ValueError,match='milestone_reference_required'):compose(assignment,owners)


def test_past_window_cannot_remain_a_next_event_after_valid_native_id_rebuild():
 from engine.government_revenue import program_ontology as po
 owners,assignment=milestone_case();graph=owners['ontology'].payload();row=graph['milestones'][0]
 row['window']={'from':'2024-10-01','to':'2025-09-30'}
 row['id']=po.milestone_id(program_id=row['program_id'],kind=row['kind'],title=row['title'],temporal_kind=row['temporal_kind'],date_value=row.get('date'),window=row['window'],revision=row['revision'])
 old=owners['ontology'];owners['ontology']=t.OwnerSnapshot(old.owner_kind,json.dumps(graph).encode(),old.available_at,old.admission_ref,old.rights_state)
 assert owners['ontology'].payload()
 assignment['shipbuilding']['next_event']['references'][0]['row_id']=row['id']
 with pytest.raises(ValueError,match='past_milestone_as_next_event'):compose(assignment,owners)
