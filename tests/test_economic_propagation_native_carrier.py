"""K3-only synthetic native-carrier tests; no consumer modules or real admission."""
from copy import deepcopy
import hashlib
import json

import pytest
from lib import economic_propagation as ep
from lib import economic_propagation_v2 as ep2

ASOF = '2026-10-19'
OBSERVED = ASOF + 'T17:00:00Z'
COMPILED = ASOF + 'T17:01:00Z'


@pytest.fixture
def native():
    def party(symbol, cik):
        iid = 'ISS:US-XNAS-' + symbol
        return {'issuer_id': iid, 'security_id': 'SEC:US-XNAS-' + symbol,
            'identity_receipt': {'schema':'company_intelligence.current_issuer_identity/v1',
                'identity_mode':'current','issuer_id':iid,'evidenced_cik':cik,'source_commit':'a'*40,
                'sources':{name:{'sha256':'b'*64,'byte_length':100} for name in
                    ('security_master','vendor_aliases','issuer_master')},
                'evidence_source':'sec_company_tickers','evidence_snapshot':'2026-08-18'}}
    subject,obj = party('ALPHA','0000000001'),party('BETA','0000000002')
    binding={'schema':'economic_propagation.native_supplier_binding/v1','kind':'disclosed_supplier',
        'lifecycle':'reported_use','direction':'object_supplies_subject','identity_mode':'current',
        'current_identity_observed_at':OBSERVED,'subject':subject,'object':obj}
    def resolution(party):
        raw=json.dumps(party['identity_receipt'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        return {'resolution_state':'RESOLVED','issuer_id':party['issuer_id'],'security_id':party['security_id'],
            'resolution_asof':ASOF,'owner_ref':{'owner_program':'stock-identity',
                'artifact':'sha256:'+hashlib.sha256(raw).hexdigest(),
                'artifact_schema':'company_intelligence.current_issuer_identity/v1'}}
    fact,edition='c'*64,'d'*64
    leg={'leg_id':'sec_supplier:'+fact,'graph':'graph_1','construct':'disclosed_customer_supplier',
        'role':'supplier','role_evidence_class':'disclosed_role_specific','claim_strength':'disclosed',
        'owner_ref':{'owner_program':'gmi-theme-graph','artifact':'native_disclosure:'+fact,
            'artifact_schema':'theme_graph.native_economic_context/v1'},
        'evidence_refs':['native_fact:sha256:'+fact,'native_edition:sha256:'+edition],
        'asof':ASOF,'known_at':ASOF+'T15:51:28Z','usability_state':'usable',
        'native_disclosure_binding':binding}
    admission={k:deepcopy(leg[k]) for k in ('graph','construct','owner_ref','evidence_refs','asof','known_at',
        'native_disclosure_binding')}
    admission.update(generator_id='gen_disclosed_customer_supplier',coverage_state='partial')
    return {'source_event':{'event_id':'synthetic-owner-event','owner_ref':{'owner_program':'edgar-ingest',
                'artifact':'synthetic/event','artifact_schema':'synthetic.owner_event/v1'},
            'event_class':'other_owner_event','source_identity':resolution(subject),
            'event_time':ASOF+'T16:00:00Z','known_at':ASOF+'T16:01:00Z'},
        'target':{'requested_key':'BETA','resolution':resolution(obj)},'asof':ASOF,'compiled_at':COMPILED,
        'relationship_paths':[leg],'generator_admissions':[admission],
        'alternative_classes':['sector_factor'],'review_by':'2026-11-20'}


def make(native):
    return ep2.compose_hypothesis_v2(**deepcopy(native))


def rehash(record):
    record['content_sha256']=ep2.content_sha256(record)
    return record


def codes(record):
    return {finding.code for finding in ep2.validate_hypothesis_v2(rehash(record))}


def test_positive_native_admission_is_supported_graph1_but_no_mechanism(native):
    before=deepcopy(native);r=make(native)
    assert ep2.validate_hypothesis_v2(r)==[]
    assert r['graph_states']=={'graph_1':'supported','graph_2':'absent','graph_3':'absent'}
    assert r['abstention']['reasons']==['no_mechanism_hypothesized']
    assert r['abstention']['abstained'] is True
    assert r['mechanism']['state']=='abstained'
    assert r['economic_share'] is None
    assert all(r['authority'][k] is False for k in ('entry','gating','ranking','sizing','trading','originates_signals'))
    assert native==before and make(native)==r
    assert r['generator_admissions'][0]['coverage_state']=='partial'
    assert all(not ref.startswith('supplies:') for ref in r['relationship_paths'][0]['evidence_refs'])


@pytest.mark.parametrize('mutation', ['schema','artifact_digest','fact_digest','edition_digest','role','graph2',
    'graph3','kind_c01','current_mode','missing_binding','receipt_generation','receipt_sources','receipt_issuer',
    'security_grain','direction','future_receipt','historical_cutoff','future_observation','future_adoption',
    'unpaired_admission','covered_instead_of_partial'])
def test_rehashed_native_carrier_cannot_launder_misbindings(native,mutation):
    r=make(native);leg=r['relationship_paths'][0];admission=r['generator_admissions'][0]
    b=leg['native_disclosure_binding']
    if mutation=='schema':leg['owner_ref']['artifact_schema']='company_intelligence.private_product_integration/v2'
    elif mutation=='artifact_digest':leg['owner_ref']['artifact']='native_disclosure:'+'e'*64
    elif mutation=='fact_digest':leg['evidence_refs'][0]='native_fact:sha256:'+'e'*64
    elif mutation=='edition_digest':leg['evidence_refs'][1]='native_edition:sha256:invalid'
    elif mutation=='role':leg['role']='customer'
    elif mutation in ('graph2','graph3'):
        leg['graph']='graph_2' if mutation=='graph2' else 'graph_3'
        leg['construct']='theme_membership' if mutation=='graph2' else 'etf_tracking'
    elif mutation=='kind_c01':b['kind']='product_integration';b['lifecycle']='planned'
    elif mutation=='current_mode':b['identity_mode']='historical'
    elif mutation=='missing_binding':del leg['native_disclosure_binding']
    elif mutation=='receipt_generation':b['object']['identity_receipt']['source_commit']='e'*40
    elif mutation=='receipt_sources':b['object']['identity_receipt']['sources']['issuer_master']['sha256']='e'*64
    elif mutation=='receipt_issuer':b['object']['identity_receipt']['issuer_id']=b['subject']['issuer_id']
    elif mutation=='security_grain':b['object']['security_id']='SEC:US-XNAS-OTHER'
    elif mutation=='direction':b['direction']='subject_supplies_object'
    elif mutation=='future_receipt':b['object']['identity_receipt']['evidence_snapshot']='2026-10-20'
    elif mutation=='historical_cutoff':r['asof']='2026-02-25'
    elif mutation=='future_observation':b['current_identity_observed_at']=ASOF+'T17:02:00Z'
    elif mutation=='future_adoption':leg['known_at']=ASOF+'T17:02:00Z';admission['known_at']=leg['known_at']
    elif mutation=='unpaired_admission':admission['evidence_refs'][1]='native_edition:sha256:'+'e'*64
    elif mutation=='covered_instead_of_partial':admission['coverage_state']='covered'
    expected = 'K3D_V2_R001' if mutation in {'graph2','graph3','kind_c01','current_mode','direction'} else 'K3D_R038'
    assert expected in codes(r),mutation


def test_native_refs_cannot_be_moved_to_graph2_or_graph3_even_with_new_construct(native):
    for field,graph,construct,basis in [('similarity_evidence','graph_2','theme_membership','shared_theme_vocabulary'),
                                       ('market_evidence','graph_3','etf_tracking','incorporation_state')]:
        r=make(native);leg=r['relationship_paths'][0]
        row={k:deepcopy(leg[k]) for k in ('leg_id','owner_ref','evidence_refs','asof','known_at','usability_state')}
        row.update(graph=graph,construct=construct)
        row['comparability_basis' if graph=='graph_2' else 'market_state_basis']=basis
        r[field]=[row]
        assert 'K3D_R038' in codes(r)


def test_old_membership_edge_grammar_still_refuses_graph1_laundering(native):
    r=make(native)
    for row in [r['relationship_paths'][0],r['generator_admissions'][0]]:
        del row['native_disclosure_binding']
        row['owner_ref']={'owner_program':'gmi-theme-graph','artifact':'data/theme_graph/edges.parquet',
                          'artifact_schema':'theme_graph.edges.v1'}
        row['evidence_refs']=['member_of:co:fake->theme:fake@2026-01-01']
    assert 'K3D_R035' in codes(r)


def test_source_event_is_required_and_future_owner_event_is_refused(native):
    native['source_event']=None
    with pytest.raises(ep.EconomicPropagationError,match='K3D_V2_INPUT_SHAPE: source_event'):
        make(native)


def test_future_owner_event_preserves_lookahead_guard(native):
    native['source_event']['known_at']='2026-10-20T00:00:00Z'
    with pytest.raises(ep.EconomicPropagationError,match='K3D_R061'):
        make(native)
