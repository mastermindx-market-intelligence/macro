"""Synthetic owner integration; never production admission or a real source grant."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from engine.company_intelligence import issuer_disclosures as n
from engine.company_intelligence import issuer_disclosure_owner as o
from engine.company_intelligence import issuer_disclosure_publication as pub
from engine.company_intelligence import issuer_disclosure_selection as selection
from engine.company_intelligence import sec_supplier_adoption as supplier
from engine.earnings_release.receipts import receipt_for_char_span
from engine.research_vault.r2_store import LocalStore
from engine.theme_graph import economic_context as gmi
from engine.theme_graph import issuer_economic_context as issuer_gmi
from tests.test_company_disclosure_owner import FixtureSource
from tests.test_company_pinned_relationship_candidates import fixture as pinned_fixture, inspect as pinned_inspect


def canon(x):
    return n._canonical(x)


@pytest.fixture
def case(tmp_path):
    body = b'SYNTHETIC: Aurora buys Widget wafers from Boreal.'
    f = pinned_fixture(tmp_path / 'native', body=body)
    candidate = f.candidate
    candidate['receipt'] = receipt_for_char_span(source=body.decode(), source_sha256=o.digest(body),
        char_start=0, char_end=len(body)).to_dict()
    candidate['assertion'].update(kind='disclosed_supplier', lifecycle='reported_use')
    identities = {}
    for party, symbol, cik in [('subject', 'ALPHA', '0000000001'), ('object', 'BETA', '0000000002')]:
        identities[party] = {'schema': o.context.RECEIPT_SCHEMA, 'identity_mode': 'current',
            'issuer_id': 'ISS:US-XNAS-' + symbol, 'evidenced_cik': cik, 'source_commit': 'a'*40,
            'sources': {name: {'sha256': 'b'*64, 'byte_length': 100} for name in o.IDENTITY_SOURCES},
            'evidence_source': 'sec_company_tickers', 'evidence_snapshot': '2024-02-01'}
    candidate['identity_annotations'] = {p + '_id': identities[p]['issuer_id'] for p in identities}
    inspection = pinned_inspect(f)
    assert inspection['inspection_status'] == 'INSPECTABLE'
    role_review = {'decision':'supported_disclosed_supplier_in_selected_filing','direction':'object_supplies_subject',
        'candidate_id':candidate['candidate_id'],'source_sha256':candidate['receipt']['source_sha256'],
        'span_sha256':candidate['receipt']['span_sha256'],'snapshot_id':inspection['native_source_binding']['snapshot_id'],
        'supplier_label':'Boreal'}
    prepared = supplier.prepare_supplier_input(candidate, inspection, identities=identities,
        identity_queries={'subject': 'ALPHA', 'object': 'BETA'},
        identity_observed_at='2024-03-03T10:00:00Z', reviewed_at='2024-03-03T11:00:00Z', role_review=role_review)
    e, fact = prepared['edition'], prepared['proposed_fact']; s=e['sec_source']
    policy = {'schema': supplier.POLICY_SCHEMA, 'basis_id': 'SYNTHETIC-POLICY',
        'recorded_at': '2024-03-04T10:00:00Z', 'reviewer': 'synthetic fixture',
        'evidence_kind': 'published_source_reuse_policy', 'decision': 'covered_for_described_use',
        'rights_family': 'sec_public_filing_facts',
        'source_policy_evidence': [{'url': url, 'section': 'synthetic', 'finding': 'synthetic',
            'verification': 'synthetic'} for url in supplier.POLICY_URLS],
        'source': {'accession': s['accession'], 'reporting_cik': s['issuer_cik'], 'archive_url': s['archive_url'],
            'raw_sha256': e['source_sha256'], 'byte_start': fact['span']['start_byte'],
            'byte_end': fact['span']['end_byte'], 'span_sha256': fact['span']['text_sha256']},
        'permitted_use': {'purpose': n.SEC_SUPPLIER_PURPOSE, 'audience': n.SEC_SUPPLIER_AUDIENCE,
            'paid_product_display': True, 'fact_retention': True, 'source_attribution_required': True,
            'kind': 'disclosed_supplier', 'lifecycle': 'reported_use', 'subject': 'Aurora', 'object': 'Boreal',
            'direction': 'object_supplies_subject', 'product_scope': 'Widget', 'amount': None,
            'economic_share': None, 'source_quotation': False, 'source_body_export': False, 'reviewer_text': False},
        'scope_limits': ['SYNTHETIC fixture; no actual policy or production acceptance']}
    theme = yaml.safe_dump({'families': {'sec_public_filing_facts':
        {'rights_class': 'derived_display_ok', 'auth_class': 'keyless_public'}}}).encode()
    spec = supplier.adopt_supplier_input(prepared, adopted_at='2024-03-05T10:00:00Z',
        ruling_raw=canon(policy), theme_sources_raw=theme)
    registry = Path(o.REGISTRY_PATH).read_bytes()
    snapshot = o.qualify_records('a'*40, canon(spec), canon(policy), registry, identities, theme_sources_raw=theme)
    return SimpleNamespace(body=body, pinned=f, prepared=prepared, identities=identities, candidate=candidate,
        inspection=inspection, policy=policy, theme=theme, spec=spec, snapshot=snapshot, registry=registry,
        source=FixtureSource(snapshot), state=LocalStore(tmp_path/'state'), artifacts=LocalStore(tmp_path/'artifacts'))


def qualify(c, spec=None, policy=None, identities=None, theme=None):
    spec=deepcopy(c.spec if spec is None else spec)
    policy=c.policy if policy is None else policy
    spec['ruling_reference'] = o.object_ref(canon(policy))
    return o.qualify_records('a'*40, canon(spec), canon(policy), c.registry,
        c.identities if identities is None else identities, theme_sources_raw=c.theme if theme is None else theme)


def publish_synthetic(c):
    intent = pub.prepare_publication(c.source, c.state, expected_current_version=None)
    return pub.publish_generation(c.source, c.state, c.artifacts,
        lambda snapshot: supplier.PinnedSupplierSource(snapshot, c.pinned.authority), intent=intent)


def test_native_owner_publication_read_selection_and_gmi_are_one_current_binding(case):
    c=case
    assert c.prepared['adoption_state']=='NOT_ADOPTED' and c.prepared['proposed_fact']['known_at'] is None
    assert c.prepared['publication_permitted'] is c.prepared['paid_consumer_permitted'] is False
    published=publish_synthetic(c)
    assert published['status']=='COMMITTED_OBSERVED'
    owner=o.CurrentDisclosureOwner(c.source, c.state)
    req=n.Request(c.spec['fact']['fact_id'],o.PURPOSE,o.AUDIENCE)
    result=n.read_disclosure(c.artifacts,owner,req)
    assert result['schema']=='company_intelligence.private_disclosed_supplier/v1'
    assert result['fact']['kind']=='disclosed_supplier' and result['fact']['lifecycle']=='reported_use'
    assert result['supplier_binding']['direction']=='object_supplies_subject'
    assert result['supplier_binding']['adopted_at']=='2024-03-05T10:00:00Z'
    assert result['source_timing']['published_at'] is None
    assert c.body.decode() not in str(result) and 'value_text' not in str(result)
    native_selection=selection.read_issuer_selection(owner,owner,lambda:c.artifacts,
        c.spec['fact']['subject_id'],purpose=o.PURPOSE,audience=o.AUDIENCE)
    assert native_selection['selections'][0]['kind']=='disclosed_supplier'
    assert native_selection['selections'][0]['lifecycle']=='reported_use'
    context=issuer_gmi.read_issuer_economic_context(owner,owner,lambda:c.artifacts,c.spec['fact']['subject_id'],
        purpose=o.PURPOSE,audience=o.AUDIENCE)
    assert context['status']=='available'
    row=context['context']['relationships'][0]; leg=row['mapping']['k3_input']
    assert leg['construct']=='disclosed_customer_supplier' and leg['graph']=='graph_1'
    assert leg['role']=='supplier' and leg['role_evidence_class']=='disclosed_role_specific'
    assert row['mapping']['propagation_hypothesis'] is row['mapping']['legacy_theme_graph_edge'] is None
    assert row['relationship']['amount'] is row['relationship']['economic_share'] is None
    assert row['relationship']['direction']=='object_supplies_subject'
    assert row['timing']['sec_accepted_at']=='2024-02-26T16:00:00.000000Z'
    assert row['timing']['retained_retrieved_at']=='2024-03-01T12:00:00.000000Z'
    assert row['timing']['pinned_snapshot_at']=='2024-03-02T12:00:00.000000Z'
    assert row['timing']['native_fact_adopted_at']=='2024-03-05T10:00:00Z'
    assert not any(row['authority'].values()) and not any(row['limitations'].values())
    assert row['source_attribution']['archive_url']==c.policy['source']['archive_url']


def test_current_identity_never_becomes_historical_even_with_forged_instant_admission(case):
    c=case; publish_synthetic(c); owner=o.CurrentDisclosureOwner(c.source,c.state)
    req=n.Request(c.spec['fact']['fact_id'],o.PURPOSE,o.AUDIENCE)
    admitted=owner.resolve(req)
    for cutoff in ['2024-02-26T16:00:00Z','2024-03-06T12:00:00Z']:
        historical=replace(req,mode='historical',as_of=cutoff)
        forged=replace(admitted,request=historical,publication_precision='instant',identity_mode='historical')
        with pytest.raises(n.DisclosureError,match='HISTORICAL_BINDING_UNAVAILABLE'):
            forged.validate(historical,None)


@pytest.mark.parametrize('field', ['retrieved_at','recorded_at','snapshot_at'])
def test_future_source_clocks_refuse(case,field):
    e=deepcopy(case.spec['edition']); e['sec_source'][field]=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    with pytest.raises(n.DisclosureError,match='SEC_SOURCE_CLOCK_INVALID'):
        n.validate_edition(e)


def test_future_adoption_or_adoption_before_identity_review_and_policy_refuses(case):
    for when in [(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(), '2024-03-02T11:00:00Z', '2024-03-04T09:00:00Z']:
        with pytest.raises(n.DisclosureError):
            supplier.adopt_supplier_input(case.prepared,adopted_at=when,ruling_raw=canon(case.policy),theme_sources_raw=case.theme)


@pytest.mark.parametrize('field,value', [('decision','denied'), ('rights_family','private_c01')])
def test_policy_denial_or_c01_family_substitution_refuses(case,field,value):
    policy=deepcopy(case.policy); policy[field]=value
    with pytest.raises(n.DisclosureError,match='SEC_FACT_POLICY_NOT_QUALIFIED'):
        qualify(case,policy=policy)


@pytest.mark.parametrize('field,value', [('purpose','other_purpose'),('source_quotation',True),
    ('source_body_export',True),('reviewer_text',True),('source_attribution_required',False),('amount',1),('product_scope','other')])
def test_unapproved_purpose_body_export_or_role_scope_refuses(case,field,value):
    policy=deepcopy(case.policy); policy['permitted_use'][field]=value
    with pytest.raises(n.DisclosureError,match='PURPOSE_NOT_ADMITTED'):
        qualify(case,policy=policy)


def test_source_family_config_alone_cannot_admit_another_filing(case):
    policy=deepcopy(case.policy); policy['source']['raw_sha256']='f'*64
    with pytest.raises(n.DisclosureError,match='POLICY_SOURCE_MISMATCH'):
        qualify(case,policy=policy)
    with pytest.raises(n.DisclosureError,match='SEC_FACT_POLICY_NOT_QUALIFIED'):
        qualify(case,theme=yaml.safe_dump({'families':{}}).encode())


def test_c01_schema_cannot_be_relabelled_as_supplier(case):
    fact=deepcopy(case.spec['fact']); fact['schema']=n.FACT_SCHEMA; fact.pop('qualification')
    with pytest.raises(n.DisclosureError):
        n.validate_fact(fact)
    spec=deepcopy(case.spec); spec['schema']=o.OWNER_SCHEMA_V1
    with pytest.raises(n.DisclosureError,match='OWNER_SPEC_INVALID'):
        qualify(case,spec=spec)


@pytest.mark.parametrize('party', ['subject','object'])
def test_qualified_current_identity_cannot_be_replaced_by_annotation(case,party):
    identities=deepcopy(case.identities); identities[party]['issuer_id']='ISS:US-XNAS-OTHER'
    with pytest.raises(n.DisclosureError,match='CURRENT_IDENTITY_CHANGED'):
        qualify(case,identities=identities)


def test_mismatched_pinned_receipt_or_unreviewed_supplier_label_refuses(case):
    inspection=deepcopy(case.inspection); inspection['native_source_binding']['retrieval_receipt']['content_sha256']='f'*64
    with pytest.raises(n.DisclosureError,match='PINNED_RECEIPT_MISMATCH'):
        supplier.prepare_supplier_input(case.candidate,inspection,identities=case.identities,
            identity_queries={'subject':'ALPHA','object':'BETA'},identity_observed_at='2024-03-03T10:00:00Z',reviewed_at='2024-03-03T11:00:00Z',
            role_review=None)
    policy=deepcopy(case.policy); policy['permitted_use']['object']='Another entity'
    with pytest.raises(n.DisclosureError,match='POLICY_ROLE_MISMATCH'):
        qualify(case,policy=policy)


def test_purpose_denial_precedes_source_or_artifact_io(case):
    c=case; publish_synthetic(c); current=o.CurrentDisclosureOwner(c.source,c.state)
    request=n.Request(c.spec['fact']['fact_id'],'other_purpose',o.AUDIENCE)
    class NoIO:
        def __getattr__(self,name):
            raise AssertionError('purpose denial must precede artifact reads')
    result=gmi.read_economic_context(NoIO(),current,request)
    assert result['status']=='unavailable' and result['context'] is None


def test_native_source_replay_rejects_changed_evidence_before_returning_bytes(case):
    c=case; spec=deepcopy(c.spec); spec['edition']['sec_source']['retrieval_receipt_id']='wrong'
    source=supplier.PinnedSupplierSource(SimpleNamespace(spec=spec),c.pinned.authority)
    e=spec['edition']
    with pytest.raises(n.DisclosureError,match='SEC_SOURCE_BINDING_MISMATCH'):
        source.read_source(disclosure_id=e['disclosure_id'],edition_reference=n.validate_edition(e),
            source_sha256=e['source_sha256'],expected_byte_length=e['source_byte_length'],max_byte_length=n.MAX_SEC_SOURCE_BYTES)


def test_supplier_larger_native_sec_limit_does_not_widen_c01_limit(case):
    e=deepcopy(case.spec['edition']); e['source_byte_length']=2*1024*1024
    assert n.validate_edition(e).schema==n.SEC_EDITION_SCHEMA
    e.pop('sec_source'); e['schema']=n.EDITION_SCHEMA
    with pytest.raises(n.DisclosureError,match='INTEGER_INVALID'):
        n.validate_edition(e)


def test_pinned_literal_replay_alone_never_becomes_a_positive_role_review(case):
    with pytest.raises(n.DisclosureError,match='ROLE_REVIEW_REQUIRED'):
        supplier.prepare_supplier_input(case.candidate,case.inspection,identities=case.identities,
            identity_queries={'subject':'ALPHA','object':'BETA'},identity_observed_at='2024-03-03T10:00:00Z',
            reviewed_at='2024-03-03T11:00:00Z',role_review=None)


def test_restricted_field_grant_cannot_expose_supplier_identity_metadata(case):
    c=case
    manifest=o.make_manifest(c.snapshot,'2024-03-06T10:00:00Z')
    req=n.Request(c.spec['fact']['fact_id'],o.PURPOSE,o.AUDIENCE)
    admission=replace(o.admission(c.snapshot,manifest,req),allowed_fields=frozenset({'fact_id','kind','lifecycle'}))
    with pytest.raises(n.DisclosureError,match='SUPPLIER_FIELD_GRANT_REQUIRED'):
        admission.validate(req,None)


def refreshed_identities(c):
    identities = deepcopy(c.identities)
    for receipt in identities.values():
        receipt['source_commit'] = 'c'*40
        for source in receipt['sources'].values():
            source['sha256'] = 'd'*64
    return identities


def test_provenance_refresh_preserves_published_fact_and_returns_fresh_identity_binding(case):
    c=case; published=publish_synthetic(c); identities=refreshed_identities(c)
    c.source.value=qualify(c,identities=identities)
    current=o.CurrentDisclosureOwner(c.source,c.state)
    req=n.Request(c.spec['fact']['fact_id'],o.PURPOSE,o.AUDIENCE)
    read=n.read_disclosure(c.artifacts,current,req)
    assert read['generation']==published['generation']
    assert read['supplier_binding']['subject_identity']==c.spec['fact']['subject_identity']
    assert read['supplier_binding']['current_subject_identity']==o.digest(canon(identities['subject']))
    assert read['supplier_binding']['current_object_identity']==o.digest(canon(identities['object']))
    assert read['supplier_binding']['current_subject_identity']!=read['supplier_binding']['subject_identity']
    selected=selection.read_issuer_selection(current,current,lambda:c.artifacts,c.spec['fact']['subject_id'],
        purpose=o.PURPOSE,audience=o.AUDIENCE)
    assert selected['issuer_binding']['identity_snapshot_reference']['sha256']==read['supplier_binding']['current_subject_identity']


@pytest.mark.parametrize('key,value',[('evidenced_cik','0000000003'),('evidence_source','other'),('evidence_snapshot','2024-02-02')])
def test_supplier_continuity_never_admits_semantic_or_evidence_change(case,key,value):
    identities=refreshed_identities(case);identities['subject'][key]=value
    with pytest.raises(n.DisclosureError): qualify(case,identities=identities)


def test_supplier_continuity_refuses_missing_policy_and_split_generation(case):
    spec=deepcopy(case.spec);del spec['identity_continuity']
    with pytest.raises(n.DisclosureError):qualify(case,spec=spec)
    spec=deepcopy(case.spec);spec['identity_continuity']['semantic_fields'].remove('evidenced_cik')
    with pytest.raises(n.DisclosureError):qualify(case,spec=spec)
    identities=refreshed_identities(case);identities['object']['source_commit']='e'*40
    with pytest.raises(n.DisclosureError,match='IDENTITY_GENERATION_SPLIT'):qualify(case,identities=identities)


def test_supplier_inflight_provenance_change_refuses_current_read(case):
    c=case;publish_synthetic(c);fresh=qualify(c,identities=refreshed_identities(c))
    c.source.calls=0
    def change():
        if c.source.calls==2:c.source.value=fresh
    c.source.action=change
    with pytest.raises(n.DisclosureError,match='CURRENT_GENERATION_CHANGED'):
        o.CurrentDisclosureOwner(c.source,c.state).resolve(n.Request(c.spec['fact']['fact_id'],o.PURPOSE,o.AUDIENCE))
