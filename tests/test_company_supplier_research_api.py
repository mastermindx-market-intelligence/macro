"""Private transport and runtime boundaries; synthetic owners, never production."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import json

import pytest
from fastapi.testclient import TestClient

from app import company_disclosures as api
from app import company_supplier_research as research
from engine.theme_graph import economic_context
from tests.test_company_disclosures_api import boundary, selection_boundary, private_headers
from tests.test_company_issuer_disclosures import sample
from tests.test_company_disclosure_owner import case
from tests.test_h20_supplier_conditional import captured, native_context, synthetic_identity_base, compose, BODY


@pytest.fixture
def route(selection_boundary):
    b, owner, _ = selection_boundary
    b[4].admission = replace(b[4].admission, allowed_fields=economic_context.REQUIRED_FIELDS)
    return b, owner, '/api/company-intelligence/private/supplier-research/'+b[4].admission.request.fact_id


def get(route, suffix='', headers=None):
    b, _, url = route
    return b[0].get(url+suffix, headers={'Authorization':'Bearer synthetic-token'} if headers is None else headers)


def refused(response, status):
    assert response.status_code == status, response.text
    private_headers(response)
    assert response.json()['automatic_retry_permitted'] is False


def test_authentication_precedes_every_owner_or_store_read(route):
    b, _, url = route
    refused(TestClient(b[-1].app).get(url), 401)
    assert b[3] == [] and b[4].calls == 0


@pytest.mark.parametrize('mutation', [{'features':['site_full']},{'tier':'free'},{'status':'canceled'}])
def test_actual_private_feature_precedes_research(route,mutation):
    b,owner,_=route; b[2].update(mutation)
    refused(get(route),403)
    assert b[4].calls == owner.calls == 0 and 'private_store' not in b[3]


@pytest.mark.parametrize('suffix', ['?source=sec','?mechanism=demand_transfer','?as_of=2020-01-01',
    '?generation=old','?purpose=research','?audience=all','?store=/tmp','?fact_id=other'])
def test_callers_cannot_choose_source_mechanism_clock_or_authority(route,suffix):
    b,owner,_=route; refused(get(route,suffix),400)
    assert b[4].calls == owner.calls == 0 and 'private_store' not in b[3]


def test_real_native_planned_fact_refuses_hypothesis_without_event_source_io(route,monkeypatch):
    monkeypatch.setattr(research,'_retained_event',lambda *_:pytest.fail('planned input opened event store'))
    b,_,_=route
    response=get(route)
    assert response.status_code==200,response.text
    private_headers(response)
    value=response.json()
    assert value['schema']==research.SCHEMA and value['status']=='context_only'
    assert value['reason']=='NO_QUALIFIED_SUPPLIER_ROLE' and value['candidate'] is None
    assert value['disclosure']['fact']['lifecycle']=='planned'
    assert b[3]==['authenticate','entitlement','private_store','authenticate','entitlement']
    assert b[4].calls>=4


def test_source_revocation_or_user_change_at_return_withholds_context(route,monkeypatch):
    b,_,_=route; original=b[5].get_bytes_strict_bounded
    def revoke(*args,**kwargs):
        b[2]['features']=[]
        return original(*args,**kwargs)
    monkeypatch.setattr(b[5],'get_bytes_strict_bounded',revoke)
    refused(get(route),403)


def test_changed_principal_at_final_boundary_withholds_result(route,monkeypatch):
    from app import paywall,billing
    b,_,_=route; count=[]
    def identify(token):
        count.append(token); uid='synthetic-user' if len(count)==1 else 'other-user'
        return SimpleNamespace(status='ok',uid=uid,record={'id':uid})
    monkeypatch.setattr(paywall,'_resolve_identity',identify)
    monkeypatch.setattr(billing,'read_entitlement',lambda uid:b[2])
    refused(get(route),401); assert len(count)==2


def test_source_failure_does_not_leak_or_retry(route,monkeypatch):
    calls=[]
    def broken(*args,**kwargs):
        calls.append(1); raise RuntimeError('secret source text /private/path')
    monkeypatch.setattr(research,'read_supplier_research',broken)
    response=get(route);refused(response,503)
    assert calls==[1] and 'secret' not in response.text and 'private/path' not in response.text


@pytest.mark.parametrize('edge',['selection','admission'])
def test_late_native_change_is_not_a_stale_positive(route,edge):
    b,owner,_=route
    if edge=='selection':owner.change_at=3
    else:b[4].change_at=6
    refused(get(route),503)


def test_native_candidate_projection_has_no_source_body_or_inferred_outcome(captured,native_context):
    native=compose(captured,native_context)
    result=research._project(native)
    assert result['mechanism']['state']=='hypothesized'
    assert result['observed']['occurrence_at'] is None
    assert result['observed']['adopted_at']!=result['observed']['retrieved_at']
    assert result['empirical_evaluation']=='not_performed'
    assert not any(result['authority'].values())
    assert result['lineage']=={'same_document':True,'independent_corroboration':False}
    assert result['contextual_refusal']['hypothesis'] is None
    assert len(json.dumps(result).encode())<16000
    for omitted in ['display_excerpt','manifest_key','source_span','source_document',BODY.decode()]:
        assert omitted not in json.dumps(result)


def test_native_record_mutation_refuses_projection(captured,native_context):
    value=compose(captured,native_context)
    value['candidate']['mechanism']['predicted_operating_direction']='improves'
    with pytest.raises(Exception,match='RESEARCH_COMPOSITION_INVALID'):
        research._project(value)


@pytest.mark.parametrize('change',['none','other_supplier','missing_identity','changed_identity','late_identity','late_head','late_admission'])
def test_current_composition_admits_pair_before_source_and_rechecks_afterward(
        captured,native_context,sample,monkeypatch,change):
    """Native binder/composer + source qualification; synthetic transport seams.

    The existing bundle reader's byte/admission checks are covered separately;
    this isolates access order and post-source continuity without a new store.
    """
    from datetime import datetime as dt,timezone
    from engine.company_intelligence import issuer_disclosures as n
    from engine.company_intelligence.current_context_runtime import CommittedCompanyContextOwner
    from engine.company_intelligence.current_company_context import IdentityBundle
    from tests.test_h20_supplier_conditional import qualify
    view,bundle_factory=native_context
    binding=bundle_factory();parts=sample[4].admission
    admission=replace(parts,reference=replace(parts.reference,schema=n.SUPPLIER_FACT_SCHEMA),
        subject_binding=n.SubjectIdentityBinding('ISS:US-XNAS-NVDA','0001045810',
            'company_intelligence.current_issuer_identity/v1','a'*64,200,'b'*64))
    req=admission.request;item=SimpleNamespace(admission=admission,request=req,payload={'synthetic':'disclosure'})
    selected=SimpleNamespace(issuer_id=admission.subject_binding.issuer_id)
    reads=[];identities=[];heads=[];source_opened=[]
    def preflight(*_):
        reads.append(1)
        return replace(admission,generation='different') if change=='late_admission' and source_opened else admission
    monkeypatch.setattr(n,'preflight',preflight)
    monkeypatch.setattr(research.selection,'read_issuer_disclosure_bundle',lambda *a,**k:SimpleNamespace(selection=selected,disclosures=(item,)))
    monkeypatch.setattr(research.selection,'_resolve',lambda *a:selected)
    monkeypatch.setattr(research.economic_context,'_project_selected',lambda *a:view)
    monkeypatch.setattr(research,'_protected_records',lambda owner:('a'*40,{}))
    class Clock:
        @staticmethod
        def now(tz):return dt(2026,10,19,18,1,tzinfo=timezone.utc)
    monkeypatch.setattr(research,'datetime',Clock)
    owner=CommittedCompanyContextOwner(__import__('pathlib').Path('.'))
    def identity(*_):
        identities.append(1)
        if change=='missing_identity':return None
        if change=='changed_identity' or (change=='late_identity' and source_opened):
            return replace(binding,source_commit='b'*40)
        return binding
    monkeypatch.setattr(owner,'current_identity_bundle',identity)
    monkeypatch.setattr(owner,'_head',lambda:'b'*40 if change=='late_head' else 'a'*40)
    def event(_):source_opened.append(1);return qualify(captured)
    monkeypatch.setattr(research,'_retained_event',event)
    if change=='other_supplier':view['context']['relationship']['object_id']='ISS:US-XNAS-OTHER'
    reader=SimpleNamespace(authority=object(),store_factory=lambda:pytest.fail('unexpected store construction'),selection_owner=object())
    if change=='none':
        result=research.read_supplier_research(reader,owner,req.fact_id,purpose=req.purpose,audience=req.audience)
        assert result['status']=='available' and result['candidate']['empirical_evaluation']=='not_performed'
        assert len(identities)==2 and source_opened==[1]
    else:
        with pytest.raises(Exception):
            research.read_supplier_research(reader,owner,req.fact_id,purpose=req.purpose,audience=req.audience)
        assert source_opened==([] if change in ['other_supplier','missing_identity','changed_identity'] else [1])
