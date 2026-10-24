"""Proposed derived sibling of program_dossier; owns no source facts.

The existing builder supplies already validated, rights-qualified owner bytes.
These structural checks do not authenticate an owner or confer display rights.
No acquisition, persistence, identifier minting or arithmetic is performed here.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import re
from pathlib import Path
from jsonschema import Draft202012Validator

_SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "contracts" / "government_revenue"

CONTRACT = 'government_program_theme_context.v1'
SCHEMA_VERSION = '1.0.0'
THEMES = ('golden_dome','munitions_replenishment','space','nato_fms_demand','fleet_sustainment_upgrades','shipbuilding')
RAILS = ('funding_stage','exposure','economics','market_context','contrary_case','next_event')
STATES = ('supported','partial','stale','unreviewed','not_asserted','projection_missing','source_unavailable','blocked')
AUTHORITY = dict(tier='display',context_only=True,can_rank=False,can_size=False,can_gate=False,can_originate_signal=False,can_add_candidates=False,can_escalate=False)
CONTRACTS = {'program_ontology':{'government_program_ontology.v1'},'program_dossier':{'government_program_dossier.v1'},'identity_atlas':{'government_revenue_identity_atlas.v1'},'fms':{'government_fms_case.v1'},'budget':{'government_budget_program_graph.v1'},'defense_economics':{'defense_economics.v1'},'company_intelligence':{'event_workspace.v1'}}
ALLOWED = {'funding_stage':{'fms','budget','program_ontology'},'exposure':{'program_ontology','identity_atlas','fms'},'economics':{'defense_economics','company_intelligence'},'market_context':{'defense_economics'},'contrary_case':{'fms','defense_economics','program_dossier','company_intelligence'},'next_event':{'program_ontology','fms','defense_economics'}}
CLOCKS = {'known_at','graph_known_at','observed_at','retrieved_at','first_observed_at','generated_at','source_available_at'}
IDS = {'id','case_key','fact_id','entity_id','issuer_id','coverage_id','evidence_id','observation_id','link_id','event_id','context_id'}

def _json(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)
def _instant(v):
 if not isinstance(v,str): raise ValueError('clock_invalid')
 try: d=datetime.fromisoformat(v.replace('Z','+00:00'))
 except ValueError: raise ValueError('clock_invalid') from None
 if d.tzinfo is None: raise ValueError('clock_invalid')
 return d

def _clocks(v):
 if isinstance(v,dict):
  for k,x in v.items():
   if k in CLOCKS and x is not None: yield _instant(x)
   else: yield from _clocks(x)
 elif isinstance(v,list):
  for x in v: yield from _clocks(x)

@dataclass(frozen=True)
class OwnerSnapshot:
 """Qualified bytes from an existing owner, not an HTTP request body."""
 owner_kind: str
 raw_bytes: bytes
 available_at: str
 admission_ref: str
 rights_state: str

 def payload(self):
  if self.owner_kind not in CONTRACTS or self.rights_state != 'qualified_public_display' or not isinstance(self.admission_ref,str) or not self.admission_ref.strip(): raise ValueError('owner_unqualified')
  try: payload=json.loads(self.raw_bytes)
  except (ValueError,TypeError): raise ValueError('owner_bytes_invalid') from None
  _json(payload)
  if not isinstance(payload,dict) or (payload.get('contract') or payload.get('schema')) not in CONTRACTS[self.owner_kind]: raise ValueError('owner_contract_invalid')
  if self.owner_kind=='program_ontology':
   from engine.government_revenue.program_ontology import load_program_ontology_graph
   load_program_ontology_graph(payload)
  elif self.owner_kind=='program_dossier':
   from engine.government_revenue.program_dossier import is_valid_program_dossier_payload
   if not is_valid_program_dossier_payload(payload):raise ValueError('program_dossier_owner_invalid')
  elif self.owner_kind=='defense_economics':
   from engine.government_revenue.defense_economics import validate_defense_economics_payload
   validate_defense_economics_payload(payload)
  elif self.owner_kind=='budget':
   from engine.government_revenue.budget_program import is_valid_budget_program_graph
   if not is_valid_budget_program_graph(payload,root=_SCHEMA_ROOT.parents[1]):raise ValueError('budget_owner_invalid')
  elif self.owner_kind=='company_intelligence':
   from engine.company_intelligence.event_workspace import validate_event_workspace
   validate_event_workspace(payload)
  else:
   schema=json.loads((_SCHEMA_ROOT / (payload['contract']+'.schema.json')).read_text())
   if next(Draft202012Validator(schema).iter_errors(payload),None) is not None: raise ValueError('owner_schema_invalid')
  available=_instant(self.available_at)
  if any(c>available for c in _clocks(payload)): raise ValueError('owner_availability_backdated')
  return payload

 def binding(self):
  p=self.payload()
  return dict(owner_kind=self.owner_kind,contract=p.get('contract') or p.get('schema'),sha256=sha256(self.raw_bytes).hexdigest(),content_id=p.get('content_id'),available_at=self.available_at,admission_ref=self.admission_ref,rights_state=self.rights_state,source_available_at=(p.get('lifecycle') or {}).get('source_available_at'),house_observed_at=(p.get('lifecycle') or {}).get('observed_at'))

def _pointer(payload,pointer):
 if not isinstance(pointer,str) or not pointer.startswith('/') or len(pointer)>512: raise ValueError('pointer_invalid')
 cur=payload; ancestry=[payload]
 for token in pointer[1:].split('/'):
  if re.search(r'~(?![01])',token): raise ValueError('pointer_invalid')
  token=token.replace('~1','/').replace('~0','~')
  try:
   if isinstance(cur,list):
    if not re.fullmatch('0|[1-9][0-9]*',token): raise ValueError('pointer_invalid')
    cur=cur[int(token)]
   elif isinstance(cur,dict): cur=cur[token]
   else: raise ValueError('pointer_invalid')
  except (KeyError,IndexError): raise ValueError('pointer_missing') from None
  ancestry.append(cur)
 return cur,ancestry

def _ref(ref,rail,owners,cutoff):
 if not isinstance(ref,dict) or set(ref)!={'owner_key','pointer','row_id'} or any(not isinstance(x,str) or not x or len(x)>512 for x in ref.values()): raise ValueError('reference_fields_invalid')
 key=ref['owner_key']
 if key not in owners: raise ValueError('reference_owner_missing')
 owner=owners[key];p=owner.payload()
 if owner.owner_kind not in ALLOWED[rail]: raise ValueError('reference_owner_wrong_rail')
 if _instant(owner.available_at)>cutoff: raise ValueError('owner_not_yet_available')
 node,ancestors=_pointer(p,ref['pointer'])
 rows=[a for a in ancestors if isinstance(a,dict) and any(a.get(k)==ref['row_id'] for k in IDS)]
 if not rows: raise ValueError('reference_row_id_mismatch')
 row=rows[-1]
 if any(c>cutoff for c in _clocks(row)): raise ValueError('reference_not_yet_known')
 # Restrict economics to actual admitted fact IDs; profile text is not a fact.
 if owner.owner_kind=='budget' and rail=='funding_stage':
  if not ref['pointer'].startswith('/documents/') or not isinstance(node,dict) or node.get('document_stage')!='allocation_plan' or 'amounts' not in node or row.get('document_kind')!='legislative_allocation_spend_plan':raise ValueError('allocation_context_reference_required')
 agreement_ref=owner.owner_kind=='program_ontology' and ref['pointer'].startswith('/public_agreement_assertions/')
 if agreement_ref:
  from engine.government_revenue import program_ontology as po
  if len(ref['pointer'].split('/'))!=3 or not isinstance(node,dict) or node.get('id')!=ref['row_id'] or not any(r['id']==node['id'] for r in po.current_public_agreement_rows(p,analysis_as_of=cutoff)):raise ValueError('agreement_reference_not_current')
 if owner.owner_kind=='program_ontology' and rail=='funding_stage' and not agreement_ref and (not ref['pointer'].startswith('/evidence/') or not isinstance(node,dict) or node.get('evidence_class')!='official_alliance_policy' or node.get('claim_scopes')!=['policy_context']): raise ValueError('policy_context_reference_required')
 if owner.owner_kind=='program_ontology' and rail=='exposure' and not ref['pointer'].startswith('/role_assertions/'): raise ValueError('documentary_participation_required')
 if owner.owner_kind=='identity_atlas' and rail=='exposure' and '/entities/' not in ref['pointer']: raise ValueError('reviewed_entity_reference_required')
 if agreement_ref and rail=='next_event':
  year=node.get('expected_launch_year')
  if isinstance(year,bool) or not isinstance(year,int) or year<cutoff.year:raise ValueError('past_agreement_target')
 if owner.owner_kind=='program_ontology' and rail=='next_event' and not agreement_ref:
  if not ref['pointer'].startswith('/milestones/') or not isinstance(node,dict):raise ValueError('milestone_reference_required')
  end=node.get('date') if node.get('temporal_kind')=='date' else (node.get('window') or {}).get('to')
  if not isinstance(end,str) or datetime.fromisoformat(end).date()<cutoff.date():raise ValueError('past_milestone_as_next_event')
 if owner.owner_kind=='fms' and rail=='next_event' and (not ref['pointer'].endswith('/advancement_condition') or not isinstance(node,str) or not node):raise ValueError('fms_condition_reference_required')
 if rail=='economics' and (not isinstance(node,dict) or node.get('fact_id')!=ref['row_id'] or (owner.owner_kind=='defense_economics' and '/axes/economics/facts/' not in ref['pointer']) or (owner.owner_kind=='company_intelligence' and not re.fullmatch(r'/facts/(0|[1-9][0-9]*)',ref['pointer']))): raise ValueError('economic_fact_reference_required')
 if rail=='economics' and owner.owner_kind=='company_intelligence':
  span=node.get('source_span') or {};receipt=span.get('receipt') or {};locator=span.get('locator') or {};life=p.get('lifecycle') or {}
  source=next((x for x in p.get('sources',[]) if isinstance(x,dict) and x.get('kind')=='issuer_release' and x.get('document_id')==span.get('document_id')),None)
  if node.get('typed_absence') is not None or any(node.get(k) is None for k in ('value','unit','period','basis')) or node.get('event_id')!=p.get('event_id') or span.get('rights_profile')!='rp_public_primary_v1' or span.get('receipt_state')!='byte_replayed' or source is None or source.get('receipt_state')!='byte_replayed' or source.get('source_sha256')!=receipt.get('source_sha256') or not isinstance(source.get('filing_key'),dict): raise ValueError('company_fact_owner_unqualified')
  fp=p.get('fiscal_period') or {};key=source.get('filing_key') or {}
  if node.get('period')!=f"{fp.get('year')}Q{fp.get('quarter')}" or not str(p.get('event_id','')).startswith('evt_cik'+str(key.get('cik'))+'_'): raise ValueError('company_fact_period_or_issuer_mismatch')
  if not life.get('observed_at') or not life.get('source_available_at') or _instant(life['source_available_at'])>_instant(life['observed_at']) or _instant(life['observed_at'])>cutoff: raise ValueError('company_fact_clock_unqualified')
  excerpt=span.get('display_excerpt');start=receipt.get('span_start_byte');end=receipt.get('span_end_byte');size=receipt.get('segment_bytes')
  if not isinstance(excerpt,str) or sha256(excerpt.encode()).hexdigest()!=span.get('text_sha256') or span.get('text_sha256')!=receipt.get('text_sha256') or any(isinstance(x,bool) or not isinstance(x,int) for x in (start,end,size)) or not 0<=start<end<=size or start!=locator.get('span_start_byte') or end!=locator.get('span_end_byte') or end-start!=len(excerpt.encode()): raise ValueError('company_fact_span_unqualified')
  try:
   literal=re.sub(r'[,$%\s]','',excerpt)
   if literal.startswith('(') and literal.endswith(')'):literal='-'+literal[1:-1]
   if isinstance(node['value'],bool) or Decimal(str(node['value']))!=Decimal(literal):raise ValueError('company_fact_literal_mismatch')
  except (InvalidOperation,TypeError):raise ValueError('company_fact_literal_mismatch') from None
 if rail=='economics' and owner.owner_kind=='defense_economics':
  axis,_=_pointer(p,ref['pointer'].split('/facts/')[0])
  if axis.get('state') not in ('supported','partial','stale'): raise ValueError('economic_axis_unqualified')
 if rail=='contrary_case' and owner.owner_kind=='company_intelligence':
  # New financial fact references use the existing provenance checks.
  # Legacy FMS/program-dossier and profile-context references keep their contract.
  _ref(ref,'economics',owners,cutoff)
 if rail=='market_context':
  basket=ref['pointer'].endswith('/axes/participation')
  if basket:
   required={'basket_context_not_issuer_alpha','current_membership_not_historical_first_seen','activity_not_capital_flow','capital_concentration_not_measured','no_scientific_or_rights_reclassification'}
   if not isinstance(node,dict) or node.get('reason_code')!='current_basket_market_participation' or not required<=set(node.get('limitations',[])) or not str(node.get('owner_ref','')).startswith('group_pulse:defense:pulse:') or len(node.get('evidence_refs',[]))!=3 or {str(x).split(':')[2] for x in node['evidence_refs'] if str(x).startswith('group_pulse:defense:')}!={'membership','pulse','baskets'} or not all(str(x).rsplit(':',1)[-1]==row.get('ticker_display') and p['source_bindings'].get(x,{}).get('owner_family')=='group_reads' for x in node['evidence_refs']):raise ValueError('shared_basket_owner_required')
  elif not any(x in ref['pointer'] for x in ('/axes/recognition/price_response','/axes/recognition/valuation_scenario')):raise ValueError('market_owner_leg_required')
 if rail=='exposure' and owner.owner_kind=='fms' and ref['pointer'].endswith('/contractors'): raise ValueError('exposure_requires_individual_review')
 return row,node

def content_id(payload):
 return 'gptc1-'+sha256(_json({k:v for k,v in payload.items() if k not in ('content_id','generated_at')}).encode()).hexdigest()[:24]

def compose_program_theme_context(assignments,*,owners,generated_at,as_of):
 """Pure projection. Assignments are reviewed context references, never truth."""
 cutoff=_instant(as_of);generated=_instant(generated_at)
 if cutoff>generated: raise ValueError('cutoff_after_generation')
 if not isinstance(assignments,dict) or set(assignments)-set(THEMES): raise ValueError('theme_ids_invalid')
 if not isinstance(owners,dict) or any(not isinstance(k,str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,128}',k) or not isinstance(v,OwnerSnapshot) for k,v in owners.items()): raise ValueError('owners_invalid')
 themes=[];used=set()
 for theme in THEMES:
  supplied=assignments.get(theme,{})
  if not isinstance(supplied,dict) or set(supplied)-set(RAILS): raise ValueError('rail_ids_invalid')
  rails={}
  for rail in RAILS:
   item=supplied.get(rail,dict(state='source_unavailable',reason_code='owner_reference_absent',references=[]))
   if not isinstance(item,dict) or set(item)!={'state','reason_code','references'} or item['state'] not in STATES or not isinstance(item['reason_code'],str) or not re.fullmatch(r'[a-z0-9_]{1,128}',item['reason_code']) or not isinstance(item['references'],list): raise ValueError('rail_fields_invalid')
   refs=item['references']
   mixed=item['reason_code']=='mixed_documentary_context'
   if mixed:
    if theme!='nato_fms_demand' or rail!='funding_stage' or item['state']!='partial':raise ValueError('mixed_documentary_context_scope_invalid')
    classes=[]
    for ref in refs:
     row,node=_ref(ref,rail,owners,cutoff);kind=owners[ref['owner_key']].owner_kind
     if kind=='fms' and row.get('stage')=='congressional_notification' and isinstance(node,dict) and node.get('case_key')==ref['row_id']:classes.append('congressional_notification_only')
     elif kind=='program_ontology' and node.get('evidence_class')=='official_alliance_policy' and node.get('claim_scopes')==['policy_context']:classes.append('policy_commitment_only')
     else:raise ValueError('mixed_documentary_reference_class_invalid')
    if set(classes)!={'congressional_notification_only','policy_commitment_only'}:raise ValueError('mixed_documentary_classes_required')
   # One legislative allocation plan plus one current prototype agreement; both
   # stay visibly partial with their own amounts and no summation.
   staged_mixed=item['reason_code']=='mixed_allocation_and_prototype_agreement'
   if staged_mixed:
    if theme!='golden_dome' or rail!='funding_stage' or item['state']!='partial':raise ValueError('mixed_allocation_agreement_scope_invalid')
    classes=[]
    for ref in refs:
     row,node=_ref(ref,rail,owners,cutoff);kind=owners[ref['owner_key']].owner_kind
     if kind=='budget' and row.get('document_kind')=='legislative_allocation_spend_plan' and isinstance(node,dict) and node.get('document_stage')=='allocation_plan':classes.append('allocation_plan_only')
     elif kind=='program_ontology' and ref['pointer'].startswith('/public_agreement_assertions/'):classes.append('prototype_agreement_only')
     else:raise ValueError('mixed_allocation_agreement_reference_class_invalid')
    if len(classes)!=2 or set(classes)!={'allocation_plan_only','prototype_agreement_only'}:raise ValueError('mixed_allocation_agreement_classes_required')
   if item['state'] in ('supported','partial','stale') and not refs: raise ValueError('evidenced_rail_reference_missing')
   for ref in refs:
    row,node=_ref(ref,rail,owners,cutoff);used.add(ref['owner_key'])
    if rail=='funding_stage' and owners[ref['owner_key']].owner_kind=='budget' and (item['state']!='partial' or item['reason_code'] not in ('allocation_plan_only','mixed_allocation_and_prototype_agreement')):raise ValueError('allocation_stage_promotion')
    if rail=='funding_stage' and owners[ref['owner_key']].owner_kind=='fms' and row.get('stage')=='congressional_notification' and (item['state']!='partial' or item['reason_code']!='congressional_notification_only' and not mixed):raise ValueError('notification_stage_promotion')
    agreement_ref=owners[ref['owner_key']].owner_kind=='program_ontology' and ref['pointer'].startswith('/public_agreement_assertions/')
    if agreement_ref and (theme!='golden_dome' or rail not in ('funding_stage','next_event') or item['state']!='partial' or item['reason_code'] not in (('prototype_agreement_only','mixed_allocation_and_prototype_agreement') if rail=='funding_stage' else ('reported_launch_availability_target',))):raise ValueError('prototype_agreement_stage_promotion')
    if rail=='funding_stage' and owners[ref['owner_key']].owner_kind=='program_ontology' and not agreement_ref and (item['state']!='partial' or item['reason_code']!='policy_commitment_only' and not mixed): raise ValueError('policy_commitment_stage_promotion')
    if rail=='economics' and owners[ref['owner_key']].owner_kind=='defense_economics':
     axis,_=_pointer(owners[ref['owner_key']].payload(),ref['pointer'].split('/facts/')[0])
     if axis['state']=='stale' and item['state'] in ('supported','partial'): raise ValueError('stale_finance_promotion')
    if rail=='contrary_case' and (owners[ref['owner_key']].owner_kind=='company_intelligence' or owners[ref['owner_key']].owner_kind=='defense_economics' and item['reason_code'] in ('reported_space_ownership_change','reported_unfunded_backlog_category','reported_program_cost_maturation_charge')):
     _ref(ref,'economics',owners,cutoff)
     allowed={'munitions_replenishment':('reported_program_cost_maturation_charge',{'evt_cik0001133421_2026q2_results:siaw_unfavorable_eac'}),'space':('reported_space_ownership_change',{'evt_cik0000202058_2026q2_results:space_business_sale_completed_terms','evt_cik0000202058_2026q2_results:space_business_sale_retained_scope'}),'shipbuilding':('reported_unfunded_backlog_category',{'evt_cik0000040533_2026q2_results:marine_unfunded_backlog'})}
     if theme not in allowed or item['state'] not in ('partial','stale') or item['reason_code']!=allowed[theme][0] or ref['row_id'] not in allowed[theme][1]:raise ValueError('theme_contrary_fact_scope_invalid')
     if item['reason_code']=='reported_program_cost_maturation_charge':
      # Fixed paragraph context is qualified only for this retained immutable report.
      # The selected numeric span alone does not license generic AARGM-ER claims.
      span=node.get('source_span') or {}
      axis,_=_pointer(owners[ref['owner_key']].payload(),ref['pointer'].split('/facts/')[0])
      if axis.get('state')=='stale' and item['state']!='stale':raise ValueError('stale_finance_promotion')
      if owners[ref['owner_key']].owner_kind!='defense_economics' or any(node.get(k)!=v for k,v in {'value':68.0,'unit':'USD_million','period':'2026Q2','accounting_basis':'issuer_reported_program_cost_estimate:SiAW:unfavorable_EAC','fact_class':'reported_eac'}.items()) or any(span.get(k)!=v for k,v in {'document_id':'disclosure_document_c0a6de7d1e4ca1fe32680d634e2e01e5ca9f52e915325170510f99b7e01f6581','text_sha256':'a21855da08cb102d1d217c53dc5824a3a795c1c1a44e971bf01ab9da3a2acbbf','source_url':'https://www.sec.gov/Archives/edgar/data/1133421/000113342126000033/noc-06302026xearningsrelea.htm'}.items()):raise ValueError('program_cost_context_source_changed')
    if rail=='market_context' and ref['pointer'].endswith('/axes/participation'):
     if item['reason_code']!='shared_defense_basket_not_theme_portfolio' or item['state'] not in ('partial','stale'):raise ValueError('shared_basket_theme_promotion')
     if node.get('state')=='stale' and item['state']!='stale':raise ValueError('stale_basket_promotion')
     if node.get('state') not in ('partial','stale'):raise ValueError('shared_basket_state_invalid')
    if rail=='market_context' and item['state']=='supported'  and (not isinstance(node,dict) or node.get('state')!='supported'): raise ValueError('market_state_promotion')
    if rail=='exposure' and item['state']=='supported':
     if owners[ref['owner_key']].owner_kind=='program_ontology':
      from engine.government_revenue import program_ontology as po
      g=owners[ref['owner_key']].payload()
      live=po.current_content_addressed_rows(g['role_assertions'],id_key='id',analysis_as_of=cutoff,retired_ids=po.retired_row_ids(g['overrides'],cutoff))
      coverage,_=po.derive_review_coverage(g,scope='participants',subject_type='program',subject_id=row['program_id'],analysis_as_of=cutoff)
      if coverage!='reviewed' or not any(r['id']==row['id'] for r in live): raise ValueError('role_not_current_reviewed')
     if owners[ref['owner_key']].owner_kind=='fms' and (not isinstance(node,dict) or node.get('identity_state')!='reviewed' or node.get('issuer_ref') is None): raise ValueError('unreviewed_exposure_promotion')
     if row.get('valid_from') is not None and _instant(row['valid_from'])>cutoff: raise ValueError('role_not_yet_valid')
     if row.get('valid_to') is not None and _instant(row['valid_to'])<=cutoff: raise ValueError('historical_role_promoted_current')
   if rail=='exposure' and item['state']=='supported':
    role_nodes=[_ref(r,rail,owners,cutoff)[1] for r in refs if owners[r['owner_key']].owner_kind=='program_ontology']
    entity_nodes=[_ref(r,rail,owners,cutoff)[1] for r in refs if owners[r['owner_key']].owner_kind=='identity_atlas']
    if not role_nodes or any(not any(e.get('entity_id')==role.get('entity_id') and e.get('verification_state') in ('reviewed','confirmed','analyst_approved') for e in entity_nodes) for role in role_nodes): raise ValueError('reviewed_participant_identity_path_missing')
   encoded=[_json(r) for r in refs]
   if len(encoded)!=len(set(encoded)): raise ValueError('duplicate_reference')
   rails[rail]=json.loads(_json(item))
  complete=all(v['state']=='supported' for v in rails.values())
  themes.append(dict(theme_id=theme,rails=rails,research_state='SOURCE_CONTEXT_COMPLETE' if complete else 'EVIDENCE_INSUFFICIENT'))
 p=dict(contract=CONTRACT,schema_version=SCHEMA_VERSION,content_id='',generated_at=generated_at,as_of=as_of,authority=dict(AUTHORITY),owner_bindings={k:owners[k].binding() for k in sorted(used)},themes=themes)
 p['content_id']=content_id(p);return p

def validate_program_theme_context(payload,*,owners):
 if not isinstance(payload,dict) or set(payload)!={'contract','schema_version','content_id','generated_at','as_of','authority','owner_bindings','themes'}: raise ValueError('snapshot_fields_invalid')
 if payload['contract']!=CONTRACT or payload['schema_version']!=SCHEMA_VERSION or payload['authority']!=AUTHORITY: raise ValueError('snapshot_contract_invalid')
 rows=payload['themes']
 if not isinstance(rows,list) or any(not isinstance(r,dict) or set(r)!={'theme_id','rails','research_state'} for r in rows) or [r['theme_id'] for r in rows]!=list(THEMES): raise ValueError('theme_inventory_invalid')
 assignments={r['theme_id']:r['rails'] for r in rows}
 expected=compose_program_theme_context(assignments,owners=owners,generated_at=payload['generated_at'],as_of=payload['as_of'])
 if payload!=expected: raise ValueError('snapshot_binding_or_state_mismatch')
 return True


def financial_fact_reference(owner_key, owner, fact_id):
 """Resolve stable admitted fact ID to this immutable revision's pointer."""
 p=owner.payload()
 if owner.owner_kind=='company_intelligence':
  hits=[f'/facts/{i}' for i,row in enumerate(p.get('facts',[])) if isinstance(row,dict) and row.get('fact_id')==fact_id]
 elif owner.owner_kind=='defense_economics':
  hits=[f'/profiles/{i}/axes/economics/facts/{j}' for i,profile in enumerate(p.get('profiles',[])) for j,row in enumerate(profile.get('axes',{}).get('economics',{}).get('facts',[])) if isinstance(row,dict) and row.get('fact_id')==fact_id]
 else: raise ValueError('financial_owner_required')
 if len(hits)!=1: raise ValueError('financial_fact_id_not_unique')
 return dict(owner_key=owner_key,pointer=hits[0],row_id=fact_id)


THEME_REVIEW_CONTRACT = 'government_program_theme_assignment_review.v1'
THEME_REVIEW_PATH = 'config/government_revenue/program_theme_assignments.v1.json'


def load_reviewed_program_theme_inputs(root, *, review_path=THEME_REVIEW_PATH):
 """Builder-only read of exact reviewed assignment/owner files; no HTTP input."""
 root=Path(root).resolve()
 def local_file(relative):
  if not isinstance(relative,str) or not relative or Path(relative).is_absolute():raise ValueError('theme_owner_path_invalid')
  path=(root/relative).resolve()
  if not path.is_relative_to(root):raise ValueError('theme_owner_path_outside_root')
  return path
 raw=local_file(review_path).read_bytes()
 try:review=json.loads(raw)
 except (ValueError,TypeError):raise ValueError('theme_review_invalid') from None
 if not isinstance(review,dict) or set(review)!={'contract','schema_version','reviewed_at','reviewer','owners','assignments'} or review['contract']!=THEME_REVIEW_CONTRACT or review['schema_version']!='1.0.0' or not isinstance(review['reviewer'],str) or not review['reviewer'].strip() or not isinstance(review['owners'],dict):raise ValueError('theme_review_invalid')
 _instant(review['reviewed_at']);owners={}
 fields={'owner_kind','path','sha256','available_at','admission_ref','rights_state'}
 for key,ref in review['owners'].items():
  if not isinstance(ref,dict) or set(ref)!=fields or not re.fullmatch('[a-f0-9]{64}',str(ref.get('sha256',''))):raise ValueError('theme_review_owner_invalid')
  body=local_file(ref['path']).read_bytes()
  if sha256(body).hexdigest()!=ref['sha256']:raise ValueError('theme_review_owner_hash_mismatch')
  owner=OwnerSnapshot(ref['owner_kind'],body,ref['available_at'],ref['admission_ref'],ref['rights_state']);owner.payload()
  if _instant(owner.available_at)>_instant(review['reviewed_at']):raise ValueError('theme_review_before_owner_available')
  owners[key]=owner
 return review['assignments'],owners


def build_reviewed_program_theme_context(root, *, generated_at, as_of, review_path=THEME_REVIEW_PATH):
 """Existing builder seam; publication/API remains incumbent root owner."""
 assignments,owners=load_reviewed_program_theme_inputs(root,review_path=review_path)
 return compose_program_theme_context(assignments,owners=owners,generated_at=generated_at,as_of=as_of)
