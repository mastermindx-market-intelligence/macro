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


def selected_case():
 owners=financial_owners();ref=financial_assignments(owners)['space']['contrary_case']['references'][0]
 payload=owners['economic'].payload();node,_=t._pointer(payload,ref['pointer'])
 return owners,ref,payload,node


def version_fingerprint(payload,ref,version='1.2.0',rail='contrary_case'):
 payload['content_id']=defense_economics_content_id(payload)
 return b.reference_fingerprint(ref,rail,snapshot('defense_economics',payload),NOW,version=version)


def test_explicit_selected_fact_version_ignores_only_unconsumed_sibling_context():
 owners,ref,payload,node=selected_case();legacy=version_fingerprint(payload,ref,'1.1.0');selected=version_fingerprint(payload,ref)
 payload['source_bindings'][node['owner_ref']]['periods'].append('2026H1')
 payload['profiles'][3]['contrary_case']+=' Unrelated newly qualified cash interpretation.'
 payload['profiles'][3]['next_condition']+=' Unrelated company cash condition.'
 assert version_fingerprint(payload,ref)==selected
 assert version_fingerprint(payload,ref,'1.1.0')!=legacy
 assert b.reference_fingerprint(ref,'contrary_case',owners['economic'],NOW)==legacy
 assert selected!=legacy  # Version domain separation prevents silent compatibility.


@pytest.mark.parametrize('mutation',['value','unit','basis','class','period','document','source_span_hash','source_url','source_clock','available_clock','subject','axis_state','axis_qualification','identity','rights','admission'])
def test_selected_fact_material_dependencies_cannot_survive_version_two(mutation):
 owners,ref,payload,node=selected_case();expected=version_fingerprint(payload,ref);binding=payload['source_bindings'][node['owner_ref']];profile=payload['profiles'][3]
 if mutation=='value':node['value']+=' Changed literal.'
 if mutation=='unit':node['unit']='changed unit'
 if mutation=='basis':node['accounting_basis']='changed basis'
 if mutation=='class':node['fact_class']='reported_guidance'
 if mutation=='period':node['period']='2026H1';binding['periods'].append('2026H1')
 if mutation=='document':node['source_span']['document_id']+='changed'
 if mutation=='source_span_hash':node['source_span']['text_sha256']='a'*64
 if mutation=='source_url':node['source_span']['source_url']='https://example.invalid/changed'
 if mutation=='source_clock':binding['observed_at']='2026-10-13T06:00:00+00:00'
 if mutation=='available_clock':binding['source_available_at']='2026-07-29T01:00:00+00:00'
 if mutation=='subject':binding['issuer_id']='cik:changed'
 if mutation=='axis_state':profile['axes']['economics']['state']='stale'
 if mutation=='axis_qualification':profile['axes']['economics']['reason_code']='changed_qualification'
 if mutation=='identity':profile['identity_mode']='changed'
 payload['content_id']=defense_economics_content_id(payload)
 owner=snapshot('defense_economics',payload)
 if mutation in ('rights','admission'):
  owner=t.OwnerSnapshot(owner.owner_kind,owner.raw_bytes,owner.available_at,'changed_admission' if mutation=='admission' else owner.admission_ref,'unknown' if mutation=='rights' else owner.rights_state)
 try:actual=b.reference_fingerprint(ref,'contrary_case',owner,NOW,version='1.2.0')
 except ValueError:return  # A closed owner validation rejection is stronger than staling.
 assert actual!=expected


def test_selected_period_must_remain_in_qualified_source_inventory():
 owners,ref,payload,node=selected_case()
 payload['source_bindings'][node['owner_ref']]['periods'].remove(node['period'])
 with pytest.raises(ValueError):version_fingerprint(payload,ref)


def test_legacy_profile_text_still_binds_consumed_narrative_in_version_two():
 owners,_,payload,_=selected_case();profile=payload['profiles'][3]
 ref=dict(owner_key='economic',pointer='/profiles/3/contrary_case',row_id=profile['issuer_id'])
 expected=version_fingerprint(payload,ref);profile['contrary_case']+=' Changed consumed profile text.'
 assert version_fingerprint(payload,ref)!=expected


def migration_fixture():
 owners,ref,payload,node=selected_case()
 review=dict(contract=t.THEME_REVIEW_CONTRACT,schema_version='1.1.0',reviewed_at=NOW,reviewer='portable prior reviewer',owners={'economic':dict(owner_kind='defense_economics',path='data/government_revenue/defense_economics.json',sha256=sha256(owners['economic'].raw_bytes).hexdigest(),available_at=NOW,admission_ref=owners['economic'].admission_ref,rights_state=owners['economic'].rights_state)},assignments={'space':{'contrary_case':dict(state='partial',reason_code='reported_space_ownership_change',references=[ref])}})
 review=b.make_reviewed_leaf_config(review,owners,as_of=NOW)
 return review,owners,ref,payload,node


def test_explicit_migration_proves_old_approval_and_semantic_equality():
 review,prior,ref,payload,node=migration_fixture();payload['source_bindings'][node['owner_ref']]['periods'].append('2026H1');payload['profiles'][3]['contrary_case']+=' New unconsumed cash narrative.';payload['content_id']=defense_economics_content_id(payload)
 current={'economic':snapshot('defense_economics',payload)}
 result=b.migrate_reviewed_leaf_config(review,prior,current,as_of=NOW,reviewed_at=NOW,reviewer='explicit semantic adjudication')
 assert review['schema_version']=='1.1.0' and result['schema_version']=='1.2.0'
 assert result['reference_fingerprints']['space/contrary_case/0']==version_fingerprint(payload,ref)
 assert result['assignments']['space']['contrary_case']['state']=='partial'


@pytest.mark.parametrize('mutation',['prior_fingerprint','selected_value','selected_period','selected_document','source_clock','inventory'])
def test_migration_never_restamps_changed_selected_dependencies(mutation):
 review,prior,ref,payload,node=migration_fixture()
 if mutation=='prior_fingerprint':review['reference_fingerprints']['space/contrary_case/0']='a'*64
 if mutation=='selected_value':node['value']+=' Changed literal.'
 if mutation=='selected_period':node['period']='2026H1';payload['source_bindings'][node['owner_ref']]['periods'].append('2026H1')
 if mutation=='selected_document':node['source_span']['document_id']+='changed'
 if mutation=='source_clock':payload['source_bindings'][node['owner_ref']]['observed_at']='2026-10-13T06:00:00+00:00'
 if mutation=='inventory':review['reference_fingerprints']['space/contrary_case/1']='b'*64
 payload['content_id']=defense_economics_content_id(payload)
 with pytest.raises(ValueError,match='migration_|inventory'):
  b.migrate_reviewed_leaf_config(review,prior,{'economic':snapshot('defense_economics',payload)},as_of=NOW,reviewed_at=NOW,reviewer='explicit semantic adjudication')


def test_loader_cannot_silently_use_new_algorithm_for_existing_version(tmp_path):
 from test_program_theme_reviewed_builder import reviewed
 review,path=reviewed(tmp_path);_,_,owners=b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)
 newer=b.make_reviewed_leaf_config(review,owners,as_of=NOW,version='1.2.0');newer['schema_version']='1.1.0';path.write_text(json.dumps(newer))
 _,assignment,_=b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)
 assert assignment['munitions_replenishment']['economics']['state']=='stale'
 newer['schema_version']='1.2.0';path.write_text(json.dumps(newer));_,assignment,_=b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)
 assert assignment['munitions_replenishment']['economics']['state']=='partial'
 newer['schema_version']='1.3.0';path.write_text(json.dumps(newer))
 with pytest.raises(ValueError,match='theme_review_invalid'):b.load_current_reviewed_theme_inputs(tmp_path,as_of=NOW)


def test_supplement_transport_normalization_retains_exact_event_and_document():
 _,ref,payload,node=selected_case();binding=deepcopy(payload['source_bindings'][node['owner_ref']]);event='evt_cik0000202058_2026q2_results';doc='disclosure_document_'+'a'*64
 def rebind(generation,document=doc,subject=event):
  key=f'event_workspace:{generation}:{subject}:{document}';node['owner_ref']=key;payload['source_bindings'][key]=binding
  return version_fingerprint(payload,ref)
 old=rebind('1'*24);legacy=version_fingerprint(payload,ref,'1.1.0')
 assert rebind('2'*24)==old
 assert version_fingerprint(payload,ref,'1.1.0')!=legacy
 assert rebind('2'*24,'disclosure_document_'+'b'*64)!=old
 assert rebind('2'*24,doc,'evt_cik0000202058_2025q2_results')!=old


def test_derived_selected_fact_preserves_each_operand_source_dependency():
 from test_program_theme_disclosure import inputs
 p,owners,_=inputs();ref=p['themes'][1]['rails']['economics']['references'][0]
 owner=owners[ref['owner_key']];payload=owner.payload();node,_=t._pointer(payload,ref['pointer'])
 # Synthetic comparable operands exercise provenance only, not a production calculation.
 node['derived']=True
 operand={key:deepcopy(node[key]) for key in ('fact_id','value','unit','period','accounting_basis','owner_ref')}
 node['numerator']=deepcopy(operand);node['denominator']=deepcopy(operand)
 key=operand['owner_ref']+':operand_fixture';binding=deepcopy(payload['source_bindings'][operand['owner_ref']]);payload['source_bindings'][key]=binding;node['numerator']['owner_ref']=key
 payload['content_id']=defense_economics_content_id(payload)
 prior=snapshot('defense_economics',payload);expected=b.reference_fingerprint(ref,'economics',prior,NOW,version='1.2.0')
 binding['observed_at']='2026-10-13T06:00:00+00:00';payload['content_id']=defense_economics_content_id(payload)
 assert b.reference_fingerprint(ref,'economics',snapshot('defense_economics',payload),NOW,version='1.2.0')!=expected


def munitions_case():
 payload=json.loads(BASE.read_bytes());payload['generated_at']=NOW
 frozen=json.loads((HERE/'fixtures/noc_siaw_theme_fact.json').read_bytes());fact=frozen['fact'];payload['profiles'][2]['axes']['economics']['facts'].append(fact);payload['source_bindings'][fact['owner_ref']]=frozen['source_binding'];payload['content_id']=defense_economics_content_id(payload)
 owner=snapshot('defense_economics',payload);ref=t.financial_fact_reference('economic',owner,fact['fact_id'])
 return payload,{'economic':owner},{'munitions_replenishment':{'contrary_case':dict(state='partial',reason_code='reported_program_cost_maturation_charge',references=[ref])}}


def test_munitions_contrary_is_exact_cost_context_with_favorable_offset():
 payload,owners,assignment=munitions_case();canonical=compose(assignment,owners)
 display=d.disclose_program_themes(canonical,owners=owners,current_owner_receipts={'economic':dict(state='available',sha256=sha256(owners['economic'].raw_bytes).hexdigest(),owner_alias_state='unchanged')})
 row=display['themes'][1]
 assert row['rail_states']['contrary_case']=='partial' and row['research_state']=='EVIDENCE_INSUFFICIENT'
 assert '68 USD million' in row['known_en'] and 'AARGM-ER' in row['known_en'] and 'favorable Sentinel' in row['known_en']
 assert 'future profitability' in row['known_en'] and '部分抵销' in row['known_zh']
 assert row['sources'][0]['row_id']=='evt_cik0001133421_2026q2_results:siaw_unfavorable_eac'
 assert row['sources'][0]['house_known_at']=='2026-10-13T05:44:47Z'


@pytest.mark.parametrize('mutation',['wrong_theme','supported','profile_text','prior_favorable','value','unit','basis','period','document','span_hash','source_url','stale_axis'])
def test_munitions_cost_context_cannot_escape_exact_disclosure_scope(mutation):
 payload,owners,assignment=munitions_case();item=assignment['munitions_replenishment']['contrary_case'];ref=item['references'][0];node,_=t._pointer(payload,ref['pointer'])
 if mutation=='wrong_theme':assignment['space']=assignment.pop('munitions_replenishment')
 if mutation=='supported':item['state']='supported'
 if mutation=='profile_text':ref.update(pointer='/profiles/2/contrary_case',row_id=payload['profiles'][2]['issuer_id'])
 if mutation=='prior_favorable':node['fact_id']='evt_cik0001133421_2026q2_results:sentinel_prior_favorable_eac';ref['row_id']=node['fact_id']
 if mutation=='value':node['value']=680.0
 if mutation=='unit':node['unit']='USD_billion'
 if mutation=='basis':node['accounting_basis']='issuer_reported_program_cost_estimate:Sentinel:favorable_EAC'
 if mutation=='period':node['period']='2025Q2';payload['source_bindings'][node['owner_ref']]['periods'].append('2025Q2')
 if mutation=='document':node['source_span']['document_id']='disclosure_document_'+'a'*64
 if mutation=='span_hash':node['source_span']['text_sha256']='a'*64
 if mutation=='source_url':node['source_span']['source_url']='https://www.sec.gov/Archives/edgar/data/changed.htm'
 if mutation=='stale_axis':payload['profiles'][2]['axes']['economics']['state']='stale'
 payload['content_id']=defense_economics_content_id(payload);owners['economic']=snapshot('defense_economics',payload)
 with pytest.raises(ValueError):compose(assignment,owners)
