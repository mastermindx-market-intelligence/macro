import os
from pathlib import Path
import json,sys,importlib.util
from copy import deepcopy
from hashlib import sha256
import pytest
try:
 from engine.government_revenue import program_theme_disclosure as d
except ImportError:
 import program_theme_disclosure as d
try:
 from engine.government_revenue import program_theme_context as t
except ImportError:
 import program_theme_context as t
R=Path(__file__).parent;REPO=Path(os.environ.get('DEFENSE_REPO_ROOT') or next((str(p) for p in Path(__file__).resolve().parents if (p/'engine/government_revenue').is_dir()), str(Path(__file__).resolve().parents[1])));t._SCHEMA_ROOT=REPO/'contracts/government_revenue'

def inputs():
 p=json.loads((R/'theme-context-with-reviewed-quartet.json').read_bytes());files={'fms':'fms_case_graph.json','ontology':'program_ontology.json','atlas':'identity_atlas.json','quartet_economics':'accepted_quartet_economics.json'};owners={};current={}
 for key,file in files.items():
  b=(R/file if key=='quartet_economics' else R/'fixtures'/file).read_bytes();binding=p['owner_bindings'][key];owners[key]=t.OwnerSnapshot(binding['owner_kind'],b,binding['available_at'],binding['admission_ref'],binding['rights_state']);current[key]=dict(state='available',sha256=sha256(b).hexdigest(),owner_alias_state='unchanged')
 return p,owners,current

def test_actual_public_native_sources_and_explanations_are_readable_reference_views():
 p,o,c=inputs();x=d.disclose_program_themes(p,owners=o,current_owner_receipts=c)
 assert len(x['themes'])==6 and all(r['research_state']=='EVIDENCE_INSUFFICIENT' for r in x['themes'])
 f=x['themes'][3];assert 'congressional notification' in f['known_en'] and 'letter of offer and acceptance' in f['next_en']
 assert any(s['url'].startswith('https://www.dsca.mil/') and 'F-100' in s['title'] for s in f['sources'])
 e=x['themes'][1];assert 'reported segment evidence' in e['known_en'] and 'program workshare' in e['known_en'];assert any(s['issuer_id'] and s['security_id'] for s in e['sources'])
 s=x['themes'][5];assert 'Virginia' in s['known_en'] and 'Electric Boat' in s['known_en'];assert any(x['program_id']=='acq-program:virginia-class-ssn' for x in s['sources'])
 assert all(r['known_zh'] and r['missing_zh'] and r['next_zh'] for r in x['themes'])
 assert 'value' not in str(x) and '24379' not in str(x) and 'program_key' not in str(x)

@pytest.mark.parametrize('change',[dict(state='source_unavailable'),dict(state='available',sha256='a'*64,owner_alias_state='unchanged'),dict(state='available',owner_alias_state='advanced')])
def test_pointer_moves_or_disappears_degrade_never_auto_remint(change):
 p,o,c=inputs();c['quartet_economics']=change;x=d.disclose_program_themes(p,owners=o,current_owner_receipts=c);row=x['themes'][1]
 assert row['rail_states']['economics'] in ('stale','source_unavailable')
 assert 'reported segment evidence' not in row['known_en'] and not row['sources']
 assert 'issuer economics' in row['missing_en'] and row['research_state']=='EVIDENCE_INSUFFICIENT'


def test_absent_current_compare_never_calls_old_owner_current():
 p,o,c=inputs();x=d.disclose_program_themes(p,owners=o,current_owner_receipts={});assert all(not r['sources'] for r in x['themes'])
 assert x['themes'][5]['rail_states']['exposure']=='source_unavailable'


def test_primary_url_and_admitted_issuer_links_are_closed_not_browser_joins():
 p,o,c=inputs();x=d.disclose_program_themes(p,owners=o,current_owner_receipts=c)
 allowed={'www.sec.gov','api.usaspending.gov','www.dsca.mil','www.war.gov','crsreports.congress.gov','www.secnav.navy.mil'}
 from urllib.parse import urlsplit
 allowed|={e['pinned_issuer_host'] for e in o['ontology'].payload()['evidence'] if e.get('evidence_class')=='issuer_disclosure'}
 assert all(urlsplit(s['url']).hostname in allowed for r in x['themes'] for s in r['sources'])
 assert all(set(s)=={'owner_key','row_id','pointer','url','title','program_id','issuer_id','security_id','source_publication_date','source_available_at','house_known_at','documentary_class','native_reason_code'} for r in x['themes'] for s in r['sources'])
 with pytest.raises(ValueError):d._primary('https://www.sec.gov.attacker.example/file',{'www.sec.gov'})
 with pytest.raises(ValueError):d._primary('http://www.sec.gov/file',{'www.sec.gov'})


def test_current_receipt_reader_rejects_new_generation_without_changing_review(tmp_path):
 p,o,c=inputs();review=json.loads((R/'program_theme_assignments.v1.json').read_bytes());before=deepcopy(review)
 for key,ref in review['owners'].items():
  target=tmp_path/ref['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(o[key].raw_bytes)
 marker=R/'fixtures/event_workspace_manifest.json';m=json.loads(marker.read_bytes());target=tmp_path/'data/company_intelligence/event_workspaces/manifest.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(marker.read_bytes())
 # Unchanged accepted generation is current; missing marker fails closed.
 current=d.read_current_theme_owner_receipts(tmp_path,review=review,retained_owners=o);assert current['quartet_economics']['owner_alias_state']=='unchanged'
 target.unlink();current=d.read_current_theme_owner_receipts(tmp_path,review=review,retained_owners=o);assert current['quartet_economics']['state']=='source_unavailable' and review==before

def test_current_alias_advance_demotes_old_quarter_even_if_cached_file_same(tmp_path):
 p,o,c=inputs();review=json.loads((R/'program_theme_assignments.v1.json').read_bytes())
 for key,ref in review['owners'].items():
  target=tmp_path/ref['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(o[key].raw_bytes)
 source=R/'fixtures/event_workspace_manifest.json';m=json.loads(source.read_bytes());old='evt_cik0000936468_2026q2_results';new='evt_cik0000936468_2026q3_results'
 m['aliases']['LMT/2026Q3']=new;m['aliases'][new]=new
 target=tmp_path/'data/company_intelligence/event_workspaces/manifest.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(m))
 current=d.read_current_theme_owner_receipts(tmp_path,review=review,retained_owners=o)
 assert current['quartet_economics']['sha256']==c['quartet_economics']['sha256'] and current['quartet_economics']['owner_alias_state']=='advanced'
 display=d.disclose_program_themes(p,owners=o,current_owner_receipts=current)
 assert display['themes'][1]['rail_states']['economics']=='stale'


def space_comparison_rows():
 # Synthetic domain discriminators; the retained real-source replay is separate.
 facts=[]
 for metric,values,unit in [('sales',(2753,2646),'USD_million'),('operating_profit',(236,280),'USD_million'),('margin',(8.6,10.6),'percent')]:
  for prior,value in enumerate(values):
   facts.append({'fact_id':'evt_cik0001133421_2026q2_results:issuer_space_segment_'+metric+('_prior' if prior else ''),'value':value,'unit':unit,'period':'2025Q2' if prior else '2026Q2','accounting_basis':'issuer_reported_segment:Space Systems:reported'})
 return facts


def test_space_sales_growth_does_not_imply_profit_growth_or_cash():
 facts=space_comparison_rows();resolved=[('economics','defense_economics',f,None) for f in facts]
 story=d._theme_economic_story('space',resolved)
 assert 'sales rose while operating profit and margin fell' in story[0]
 assert '现金生成' in story[1] and '营业利润与利润率下降' in story[1]
 assert '91' not in story[0] and 'guidance' not in story[0]
 assert len(d._FACT_LABELS.keys() & {f['fact_id'].rsplit(':',1)[-1] for f in facts})==6


@pytest.mark.parametrize('defect',['missing_prior','half_year','wrong_unit','wrong_segment','foreign_issuer','profit_grew','margin_grew','duplicate','boolean','infinite','nan'])
def test_space_direction_requires_comparable_complete_operands(defect):
 facts=space_comparison_rows()
 if defect=='missing_prior':facts.pop()
 elif defect=='half_year':facts[1]['period']='2025H1'
 elif defect=='wrong_unit':facts[0]['unit']='USD_billion'
 elif defect=='wrong_segment':facts[0]['accounting_basis']='issuer_reported_segment:Defense Systems:reported'
 elif defect=='foreign_issuer':facts[0]['fact_id']=facts[0]['fact_id'].replace('0001133421','0000936468')
 elif defect=='profit_grew':facts[2]['value']=500
 elif defect=='margin_grew':facts[4]['value']=12
 elif defect=='duplicate':facts.append(deepcopy(facts[0]))
 elif defect=='infinite':facts[0]['value']=float('inf')
 elif defect=='nan':facts[0]['value']=float('nan')
 else:facts[0]['value']=True
 resolved=[('economics','defense_economics',f,None) for f in facts]
 assert d._space_reported_comparison(resolved) is None
 assert 'sales rose' not in d._theme_economic_story('space',resolved)[0]


def space_adverse_row():
 return {'fact_id':'evt_cik0001133421_2026q2_results:issuer_space_gem63xl_unfavorable_eac','value':91,'unit':'USD_million','period':'2026Q2','fact_class':'reported_eac','accounting_basis':'issuer_reported_program_cost_estimate:GEM63XL:unfavorable_EAC'}


def test_adverse_estimate_keeps_cash_and_halo_effect_unasserted():
 facts=space_comparison_rows()+[space_adverse_row()]
 story=d._theme_economic_story('space',[('economics','defense_economics',f,None) for f in facts])
 assert 'GEM63XL adjustment concerns estimated completion costs' in story[0]
 assert "does not establish cash paid or HALO's financial effect" in story[0]
 assert '预计完工成本' in story[1] and '不能确认已支付现金或HALO的财务影响' in story[1]


@pytest.mark.parametrize('defect',['missing','duplicate','wrong_year','half_year','wrong_unit','cash_basis','foreign_issuer','wrong_class','boolean','negative','infinite'])
def test_adverse_interpretation_requires_its_own_current_qualified_fact(defect):
 fact=space_adverse_row();extras=[fact]
 if defect=='missing':extras=[]
 elif defect=='duplicate':extras.append(deepcopy(fact))
 elif defect=='wrong_year':fact['period']='2025Q2'
 elif defect=='half_year':fact['period']='2026H1'
 elif defect=='wrong_unit':fact['unit']='USD_billion'
 elif defect=='cash_basis':fact['accounting_basis']='cash_paid'
 elif defect=='foreign_issuer':fact['fact_id']=fact['fact_id'].replace('0001133421','0000936468')
 elif defect=='wrong_class':fact['fact_class']='reported_cashflow'
 elif defect=='boolean':fact['value']=True
 elif defect=='negative':fact['value']=-91
 else:fact['value']=float('inf')
 story=d._theme_economic_story('space',[('economics','defense_economics',f,None) for f in space_comparison_rows()+extras])
 assert 'sales rose' in story[0] and 'GEM63XL adjustment' not in story[0]


# --- C1 repair: native reviewed FMS case with source_surface=state ---

class _StubFmsOwner:
 owner_kind='fms'
 def __init__(self,payload): self._payload=payload;self.raw_bytes=json.dumps(payload,sort_keys=True,separators=(',',':')).encode()
 def payload(self): return self._payload

def _fms_case(observations,*,case_key='fms:transmittal:26-82',capability_title='Norway – 155mm HE M795 Projectile'):
 return dict(case_key=case_key,case_state='current',stage='congressional_notification',capability_title=capability_title,advancement_condition='official_evidence_of_offered_accepted_or_implemented_loa',observations=observations,clocks=dict(first_observed_at='2026-08-26T11:01:35+00:00',official_web_publication_date=dict(provenance='state_header_date',value='2026-08-05')))

def _fms_payload(case):
 return dict(contract='government_fms_case.v1',schema_version='1.0.0',content_id='fms-test-'+case['case_key'],cases=[case])

def _fms_ref(case_key='fms:transmittal:26-82'):
 return dict(owner_key='fms',pointer='/cases/0/advancement_condition',row_id=case_key)

def _state_obs(url='https://www.state.gov/releases/bureau-of-political-military-affairs/2026/08/norway-155mm-high-explosive-he-m795-projectile/'):
 return dict(source_surface='state',source_url=url,response_sha256='e546eb90ae5716f48808bd951c1c3781d8973d2404c808b13bc27003239e96b1',known_at='2026-08-26T11:01:35+00:00')

def _dsca_obs(url='https://www.dsca.mil/Press-Media/Major-Arms-Sales/ArticleDisplay/Article/4321/'):
 return dict(source_surface='dsca',source_url=url,response_sha256='a'*64,known_at='2026-08-26T11:01:35+00:00')


def test_resolve_admits_state_primary_when_dsca_observation_absent():
 case=_fms_case([_state_obs()]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 en,zh,sources=d._resolve(ref,'funding_stage',{'fms':owner})
 assert 'congressional notification' in en
 assert sources and sources[0]['url'].startswith('https://www.state.gov/')
 assert sources[0]['documentary_class']=='congressional_notification' and sources[0]['native_reason_code']=='congressional_notification_only'
 assert sources[0]['source_publication_date']=='2026-08-05' and sources[0]['house_known_at']=='2026-08-26T11:01:35+00:00'


def test_resolve_keeps_dsca_first_when_both_surfaces_present():
 case=_fms_case([_dsca_obs(),_state_obs()]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 _,_,sources=d._resolve(ref,'funding_stage',{'fms':owner})
 assert len(sources)==1 and sources[0]['url'].startswith('https://www.dsca.mil/')


def test_resolve_state_primary_preserves_next_event_context_for_norway26_82():
 case=_fms_case([_state_obs()]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 en,zh,_=d._resolve(ref,'next_event',{'fms':owner})
 assert 'letter of offer and acceptance' in en and '要约和接受函' in zh


def test_resolve_dsca_only_keeps_dsca_url_and_primary_class():
 case=_fms_case([_dsca_obs()]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 _,_,sources=d._resolve(ref,'funding_stage',{'fms':owner})
 assert sources[0]['url'].startswith('https://www.dsca.mil/') and sources[0]['documentary_class']=='congressional_notification'


def test_resolve_rejects_state_observation_missing_response_sha256():
 obs=_state_obs();obs.pop('response_sha256');case=_fms_case([obs]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 with pytest.raises(ValueError,match='fms_primary_receipt_missing'):d._resolve(ref,'funding_stage',{'fms':owner})


def test_resolve_rejects_federal_register_only_case():
 obs=dict(source_surface='federal_register',source_url='https://www.federalregister.gov/documents/full_text/text/2026/08/28/2026-17565.txt',response_sha256='6e31e63cc170a75d531525f02da0cb045f5a397bc8e0142b086e1c81bc504c3f',known_at='2026-09-16T07:29:57+00:00')
 case=_fms_case([obs]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 with pytest.raises(ValueError,match='fms_primary_receipt_missing'):d._resolve(ref,'funding_stage',{'fms':owner})


@pytest.mark.parametrize('bad_url',['http://www.state.gov/releases/x/','https://user:pass@www.state.gov/releases/x/','https://www.state.gov.attacker.example/releases/x/'])
def test_resolve_rejects_state_url_with_wrong_scheme_userinfo_or_lookalike_host(bad_url):
 case=_fms_case([_state_obs(url=bad_url)]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 with pytest.raises(ValueError,match='public_primary_url_unqualified'):d._resolve(ref,'funding_stage',{'fms':owner})


def test_resolve_rejects_state_surface_pointing_to_dsca_host():
 case=_fms_case([_state_obs(url='https://www.dsca.mil/Press-Media/x/')]);owner=_StubFmsOwner(_fms_payload(case));ref=_fms_ref()
 with pytest.raises(ValueError,match='public_primary_url_unqualified'):d._resolve(ref,'funding_stage',{'fms':owner})


def test_native_state_receipt_condition_survives_complete_public_validation():
 p,owners,current=inputs()
 assignments={row['theme_id']:deepcopy(row['rails']) for row in p['themes']}
 case=owners['fms'].payload()['cases'][63]
 assert case['case_key']=='fms:transmittal:26-82' and case['source_coverage']['classification']=='state_and_fr'
 assignments['munitions_replenishment']['next_event']={
  'state':'partial','reason_code':'condition_not_scheduled_date',
  'references':[{'owner_key':'fms','pointer':'/cases/63/advancement_condition','row_id':case['case_key']}]}
 context=t.compose_program_theme_context(assignments,owners=owners,generated_at=p['generated_at'],as_of=p['as_of'])
 public=d.disclose_program_themes(context,owners=owners,current_owner_receipts=current)
 row=next(x for x in public['themes'] if x['theme_id']=='munitions_replenishment')
 assert row['rail_states']['next_event']=='partial'
 assert 'letter of offer and acceptance' in row['next_en'] and '要约和接受函' in row['next_zh']
 source=next(x for x in row['sources'] if x['row_id']==case['case_key'])
 assert source['url']==case['observations'][0]['source_url']
 assert source['documentary_class']=='congressional_notification' and source['native_reason_code']=='congressional_notification_only'
 assert source['issuer_id'] is None and source['security_id'] is None
 assert all(x['research_state']=='EVIDENCE_INSUFFICIENT' for x in public['themes'])
 assert d.validate_public_theme_disclosure(public)
