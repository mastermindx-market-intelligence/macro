"""Consumer adapter checks; require the separately admitted K3 native carrier.

Synthetic owner-qualified inputs are not real source/identity/publish acceptance.
"""
from copy import deepcopy
from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pandas as pd
import pytest

from engine.company_intelligence.current_company_context import IdentityBundle, resolve_current_company
from engine.theme_graph import native_disclosure_propagation as adapter
from lib import economic_propagation as ep

ASOF = '2026-10-19'
OBSERVED = ASOF + 'T17:00:00Z'
COMPILED = ASOF + 'T17:01:00Z'


@pytest.fixture
def native():
    records = {'security_master': [], 'issuer_master': [], 'vendor_aliases': []}
    for symbol, cik in [('ALPHA', '0000000001'), ('BETA', '0000000002')]:
        iid, sid = 'ISS:US-XNAS-' + symbol, 'SEC:US-XNAS-' + symbol
        records['security_master'].append(dict(security_id=sid, issuer_id=iid, issuer_state='RESOLVED',
            issuer_cik=cik, listing_key='US-XNAS-' + symbol, issuer_evidence_snapshot=date(2026, 8, 18),
            security_state=None, superseded_by=None))
        records['issuer_master'].append(dict(issuer_id=iid, cik=cik, status='active',
            evidence_source='sec_company_tickers', evidence_snapshot=date(2026, 8, 18)))
        records['vendor_aliases'].append(dict(vendor='store', vendor_symbol=symbol, security_id=sid,
            valid_from=None, valid_to=None))
    # A native listing may have a different inception key from its issuer.
    records['security_master'].append(dict(records['security_master'][0],
        security_id='SEC:US-XNAS-CLASSA', listing_key='US-XNAS-CLASSA'))
    records['vendor_aliases'].append(dict(vendor='store', vendor_symbol='CLASSA',
        security_id='SEC:US-XNAS-CLASSA', valid_from=None, valid_to=None))
    def bundle(data=records, commit='a'*40):
        blobs = {}
        for name, rows in data.items():
            out=BytesIO();pd.DataFrame(rows).to_parquet(out,index=False);blobs[name]=out.getvalue()
        return IdentityBundle(commit, **blobs)
    fact, edition = 'c'*64, 'd'*64
    leg={'leg_id':'sec_supplier:'+fact,'graph':'graph_1','construct':'disclosed_customer_supplier',
        'role':'supplier','role_evidence_class':'disclosed_role_specific','claim_strength':'disclosed',
        'owner_ref':{'owner_program':'gmi-theme-graph','artifact':'native_disclosure:'+fact,
                     'artifact_schema':adapter.CONTEXT_SCHEMA},
        'evidence_refs':['native_fact:sha256:'+fact,'native_edition:sha256:'+edition],
        'asof':ASOF,'known_at':ASOF+'T15:51:28Z','usability_state':'usable'}
    view={'schema':adapter.CONTEXT_SCHEMA,'status':'available','reason':None,'authority':'context_only',
        'context':{'usage':{'purpose':'private_company_intelligence_context','audience':'company_intelligence_entitled'},
        'relationship':{'kind':'disclosed_supplier','lifecycle':'reported_use','direction':'object_supplies_subject',
            'subject_id':'ISS:US-XNAS-ALPHA','object_id':'ISS:US-XNAS-BETA','product':'Widget wafers',
            'platform':'foundry_services','amount':None,'economic_share':None},
        'provenance':{'reference':{'schema':'company_intelligence.disclosed_supplier_fact/v1','sha256':fact,'byte_length':1234},
            'edition':{'schema':'company_intelligence.sec_disclosure_edition/v1','sha256':edition,'byte_length':1456},
            'fact_id':'integration:synthetic','revision':1,'generation':'synthetic-component'},
        'timing':{'identity_mode':'current','query_mode':'current','query_as_of':None,
            'sec_accepted_at':'2026-02-25T21:42:19Z','retained_retrieved_at':'2026-10-09T03:53:33Z',
            'retained_recorded_at':'2026-10-09T03:53:34Z','pinned_snapshot_at':'2026-10-09T03:53:35Z',
            'edition_known_at':'2026-10-09T03:53:35Z','identity_observed_at':ASOF+'T15:35:16Z',
            'fact_known_at':leg['known_at'],'native_fact_adopted_at':leg['known_at']},
        'mapping':{'state':'qualified_disclosed_role_input','legacy_theme_graph_edge':None,
            'propagation_hypothesis':None,'reason':None,'k3_input':leg},
        'authority':dict.fromkeys(('rank','gate','size','trade','prediction'),False)}}
    view['context']['provenance']['current_identity_sha256s'] = {
        party: resolve_current_company(bundle(), symbol, today=date.fromisoformat(ASOF))['issuer_binding']['identity_snapshot_reference']['sha256']
        for party,symbol in [('subject','ALPHA'),('object','BETA')]}
    return view,bundle,records


def inputs(native, **overrides):
    view,bundle,_=native
    kw=dict(identity_bundle=bundle(),subject_symbol='ALPHA',object_symbol='BETA',
            identity_observed_at=OBSERVED,asof=ASOF,compiled_at=COMPILED)
    kw.update(overrides)
    return adapter.bind_current_supplier(view,**kw)


def event(binding):
    return {'event_id':'synthetic-owner-event','owner_ref':{'owner_program':'edgar-ingest',
        'artifact':'synthetic/event','artifact_schema':'synthetic.owner_event/v1'},
        'event_class':'other_owner_event','source_identity':binding['source_identity'],
        'event_time':ASOF+'T16:00:00Z','known_at':ASOF+'T16:01:00Z'}


def test_missing_event_keeps_role_inputs_and_never_fabricates_event(native):
    view,bundle,_=native
    out=adapter.compose_current_supplier(view,identity_bundle=bundle(),subject_symbol='ALPHA',object_symbol='BETA',
        identity_observed_at=OBSERVED,asof=ASOF,compiled_at=COMPILED,review_by='2026-11-20')
    assert (out['status'],out['reason'],out['hypothesis'])==('context_only','SOURCE_EVENT_REQUIRED',None)
    assert out['inputs']['relationship_paths'][0]['role']=='supplier'
    assert 'source_event' not in out['inputs']
    i=out['inputs'];supplied=event(i);before=deepcopy(supplied)
    out=adapter.compose_current_supplier(view,identity_bundle=bundle(),subject_symbol='ALPHA',object_symbol='BETA',
        identity_observed_at=OBSERVED,asof=ASOF,compiled_at=COMPILED,source_event=supplied,review_by='2026-11-20')
    assert out['status']=='abstained' and out['reason']=='NO_MECHANISM_HYPOTHESIZED'
    assert out['hypothesis']['source_event']==before==supplied


@pytest.mark.parametrize('mutation', ['c01_schema','planned','magnitude','direction','subject_id','purpose',
    'historical','bad_carrier','clock_order','future_adoption','missing_grain','bundle_not_native',
    'stale_native_receipt','split_generation'])
def test_pure_binder_requires_exact_native_context_and_current_owner_inputs(native,mutation):
    c=native[0]['context'];kw={}
    if mutation=='c01_schema':c['provenance']['reference']['schema']='company_intelligence.product_integration_fact/v1'
    elif mutation=='planned':c['relationship'].update(kind='product_integration',lifecycle='planned')
    elif mutation=='magnitude':c['relationship']['economic_share']=0.5
    elif mutation=='direction':c['relationship']['direction']='subject_supplies_object'
    elif mutation=='subject_id':c['relationship']['subject_id']='ISS:US-XNAS-OTHER'
    elif mutation=='purpose':c['usage']['purpose']='training'
    elif mutation=='historical':c['timing']['query_mode']='historical';c['timing']['query_as_of']='2026-02-25'
    elif mutation=='bad_carrier':c['mapping']['k3_input']['evidence_refs'][0]='supplies:fake'
    elif mutation=='clock_order':c['timing']['sec_accepted_at']='2026-10-10T00:00:00Z'
    elif mutation=='future_adoption':c['timing']['fact_known_at']='2026-10-20T00:00:00Z'
    elif mutation=='missing_grain':kw['object_symbol']='MISSING'
    elif mutation=='bundle_not_native':kw['identity_bundle']={'source_commit':'a'*40}
    elif mutation=='stale_native_receipt':c['provenance']['current_identity_sha256s']['subject']='e'*64
    elif mutation=='split_generation':kw['identity_bundle']=native[1](commit='e'*40)
    with pytest.raises(ep.EconomicPropagationError):inputs(native,**kw)


def test_security_is_resolved_by_native_master_never_derived_from_issuer(native):
    i=inputs(native,subject_symbol='CLASSA')
    assert i['source_identity']['issuer_id']=='ISS:US-XNAS-ALPHA'
    assert i['source_identity']['security_id']=='SEC:US-XNAS-CLASSA'


def test_wrong_source_event_identity_refuses(native):
    i=inputs(native);e=event(i);e['source_identity']['security_id']='SEC:US-XNAS-OTHER'
    view,bundle,_=native
    with pytest.raises(ep.EconomicPropagationError,match='EVENT_IDENTITY_MISMATCH'):
        adapter.compose_current_supplier(view,identity_bundle=bundle(),subject_symbol='ALPHA',object_symbol='BETA',
            identity_observed_at=OBSERVED,asof=ASOF,compiled_at=COMPILED,source_event=e,review_by='2026-11-20')


def test_supplier_projection_pins_current_receipts_without_changing_fact_decisions(native):
    from engine.theme_graph import economic_context as gmi
    from engine.company_intelligence import issuer_disclosures as owner
    view,_,_=native;c=view['context'];p=c['provenance'];t=c['timing']
    def reference(value):
        return SimpleNamespace(**value,payload=lambda:deepcopy(value))
    admission=SimpleNamespace(reference=reference(p['reference']),edition=reference(p['edition']),
        generation=p['generation'],known_at=t['fact_known_at'],identity_mode='current')
    fact={**c['relationship'],'fact_id':p['fact_id'],'revision':p['revision']};fact.pop('direction')
    selected={'schema':'company_intelligence.private_disclosed_supplier/v1','authority':'context_only',
        'fact':fact,'reference':p['reference'],'edition':p['edition'],'generation':p['generation'],
        'source_timing':{'published_date':'2026-02-25','published_at':None,'publication_precision':'date',
            'known_at':t['edition_known_at'],'sec_source':{
                'accepted_at':t['sec_accepted_at'],'retrieved_at':t['retained_retrieved_at'],
                'recorded_at':t['retained_recorded_at'],'snapshot_at':t['pinned_snapshot_at'],
                'archive_url':'https://www.sec.gov/Archives/edgar/data/1/synthetic.htm',
                'accession':'synthetic','document_id':'synthetic'}},
        'supplier_binding':{'direction':'object_supplies_subject','identity_mode':'current',
            'identity_observed_at':t['identity_observed_at'],
            'current_subject_identity':p['current_identity_sha256s']['subject'],
            'current_object_identity':p['current_identity_sha256s']['object'],
            'subject_identity':'e'*64,'object_identity':'f'*64}}
    request=owner.Request(p['fact_id'],'private_company_intelligence_context','company_intelligence_entitled')
    out=gmi._project_selected(admission,request,selected)
    assert out['status']=='available'
    assert out['context']['provenance']['current_identity_sha256s']==p['current_identity_sha256s']
    assert 'subject_identity' not in out['context']['provenance']
    del selected['supplier_binding']['current_object_identity']
    out=gmi._project_selected(admission,request,selected)
    assert out['status']=='unavailable' and out['reason']=='NATIVE_PROJECTION_CONTRACT_MISMATCH'
