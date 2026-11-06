"""Issuer consumer proof over the real native selector, with synthetic state."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import json

import pytest

from engine.company_intelligence import issuer_disclosures as native
from engine.company_intelligence import issuer_disclosure_selection as selection
from engine.theme_graph import economic_context
from engine.theme_graph import issuer_economic_context as consumer
from tests.test_company_issuer_disclosures import sample, SyntheticSourceReader
from tests.test_gmi_native_economic_context import qualified_local_owner


class Directory:
    def __init__(self, value):
        self.value, self.calls, self.change_at = value, 0, None
    def resolve_issuer(self, *args):
        self.calls += 1
        if self.value is not None and self.calls == self.change_at:
            return replace(self.value, generation="changed-selection")
        return self.value


@pytest.fixture
def issuer_case(sample):
    body, edition, fact, req, authority, store = sample
    issuer = "ISS:US-XNAS-TEST"
    edition.update(issuer_id=issuer, disclosure_id=native.disclosure_id(issuer, edition['source_key']))
    fact.update(disclosure_id=edition['disclosure_id'], subject_id=issuer,
        fact_id=native.fact_id(edition['disclosure_id'], fact['claim_key']),
        edition=native.validate_edition(edition).payload())
    req = replace(req, fact_id=fact['fact_id'])
    binding = native.SubjectIdentityBinding(issuer, '0000000001', 'synthetic.issuer_snapshot/v1',
        '9'*64, 200, fact['subject_identity'])
    authority.admission = replace(authority.admission, request=req,
        reference=native.validate_fact(fact), edition=native.validate_edition(edition),
        allowed_fields=economic_context.REQUIRED_FIELDS, subject_binding=binding)
    native.publish_disclosure(store, authority, req, edition=edition, fact=fact,
        source_reader=SyntheticSourceReader(body))
    entry = selection.SelectionEntry(req.fact_id, native.validate_fact(fact), native.validate_edition(edition))
    snapshot = selection.IssuerSelection(issuer, binding.evidenced_cik, binding.snapshot_schema,
        binding.snapshot_sha256, binding.snapshot_byte_length, authority.admission.generation,
        req.purpose, req.audience, (entry,))
    case = SimpleNamespace(body=body, edition=edition, fact=fact, request=req, authority=authority,
        store=store, owner=Directory(snapshot), issuer=issuer, factory_calls=0)
    def factory():
        case.factory_calls += 1
        return store
    case.factory = factory
    authority.calls = store.reads = 0
    return case


def read(case, **changes):
    return consumer.read_issuer_economic_context(changes.get('owner',case.owner),
        changes.get('authority',case.authority), changes.get('factory',case.factory),
        changes.get('issuer',case.issuer), purpose=changes.get('purpose',case.request.purpose),
        audience=changes.get('audience',case.request.audience))


def reset(case):
    case.owner.calls = case.authority.calls = case.store.reads = case.factory_calls = 0


def unavailable(result, reason=None):
    assert result == {'schema':consumer.SCHEMA, 'status':'unavailable',
        'reason':reason or result['reason'], 'context':None, 'authority':'context_only'}
    assert 'reference' not in json.dumps(result) and 'generation' not in json.dumps(result)


def test_issuer_reads_each_fact_once_and_matches_legacy_io(issuer_case, monkeypatch):
    case=issuer_case; calls=[]; original=native.read_disclosure
    def observed(*args,**kwargs):
        calls.append(args[2].fact_id)
        return original(*args,**kwargs)
    monkeypatch.setattr(native,'read_disclosure',observed)
    selected=selection.read_issuer_selection(case.owner,case.authority,case.factory,case.issuer,
        purpose=case.request.purpose,audience=case.request.audience)
    legacy_counts=(case.owner.calls,case.authority.calls,case.store.reads,case.factory_calls)
    assert len(calls)==1
    reset(case); calls.clear(); before=deepcopy(case.store.objects); writes=case.store.writes
    result=read(case)
    assert result['status']=='available'
    assert (case.owner.calls,case.authority.calls,case.store.reads,case.factory_calls)==legacy_counts
    assert calls==[case.fact['fact_id']]
    c=result['context']; row=c['relationships'][0]
    assert c['issuer_binding']==selected['issuer_binding'] and c['generation']==selected['generation']
    assert row['provenance']['reference']==selected['selections'][0]['fact_reference']
    assert row['relationship']['lifecycle']=='planned'
    assert row['mapping']['legacy_theme_graph_edge'] is None
    assert case.store.objects==before and case.store.writes==writes


def test_legacy_response_exact_shape_is_unchanged(issuer_case):
    c=issuer_case; snap=c.owner.value; e=snap.selections[0]
    result=selection.read_issuer_selection(c.owner,c.authority,c.factory,c.issuer,
        purpose=c.request.purpose,audience=c.request.audience)
    assert result=={'schema':selection.SCHEMA,'generation':snap.generation,'identity_mode':'current',
        'issuer_role':'subject_disclosing_company','issuer_binding':{'issuer_id':c.issuer,
        'evidenced_cik':snap.evidenced_cik,'identity_snapshot_reference':{'schema':snap.identity_snapshot_schema,
        'sha256':snap.identity_snapshot_sha256,'byte_length':snap.identity_snapshot_byte_length}},
        'selections':[{'fact_id':e.fact_id,'fact_reference':e.fact_reference.payload(),
        'edition_reference':e.edition_reference.payload(),'kind':'product_integration','lifecycle':'planned'}]}


def test_usage_and_distinct_clocks_survive_company_entry(issuer_case):
    c=issuer_case; result=read(c)['context']; row=result['relationships'][0]
    assert result['usage']==row['usage']=={'purpose':c.request.purpose,'audience':c.request.audience}
    assert row['timing']['source_published_date']==c.edition['published_date']
    assert row['timing']['source_published_at'] is None
    assert row['timing']['fact_known_at']==c.fact['known_at']
    assert row['timing']['edition_known_at']==c.edition['known_at']
    assert row['relationship']['amount'] is None and row['relationship']['economic_share'] is None
    assert not any(row['limitations'].values())
    assert result['coverage']=={'scope':'native_owner_current_subject_selection',
        'selected_count':1,'selection_limit':16,'global_relationship_coverage_established':False}


def test_qualified_empty_is_not_unavailable_or_global_absence(issuer_case):
    c=issuer_case;c.owner.value=replace(c.owner.value,selections=())
    r=read(c);assert r['status']=='available' and r['context']['relationships']==[]
    assert r['context']['generation']==c.owner.value.generation
    assert r['context']['coverage']['global_relationship_coverage_established'] is False
    assert c.factory_calls==c.store.reads==c.authority.calls==0
    c.owner.value=None
    unavailable(read(c),'SELECTION_UNAVAILABLE')


@pytest.mark.parametrize('issuer',['MU','',None,'cik:0000000001',' ISS:US-XNAS-TEST','ISS:US-XNAS-OTHER'])
def test_no_ticker_cik_or_different_issuer_allocation(issuer_case,issuer):
    c=issuer_case;unavailable(read(c,issuer=issuer))
    assert c.factory_calls==c.store.reads==0


@pytest.mark.parametrize('field',sorted(economic_context.REQUIRED_FIELDS))
def test_all_grants_precede_any_private_store(issuer_case,field):
    c=issuer_case;c.authority.admission=replace(c.authority.admission,
        allowed_fields=economic_context.REQUIRED_FIELDS-{field})
    unavailable(read(c),'FIELD_GRANT_INVALID' if field in {'fact_id','kind','lifecycle'} else 'PROJECTION_FIELDS_NOT_ADMITTED')
    assert c.factory_calls==c.store.reads==0


@pytest.mark.parametrize('field,value',[('generation','different'),('purpose','different'),('audience','different'),
    ('evidenced_cik','0000000009'),('identity_snapshot_sha256','a'*64),('identity_snapshot_schema','different:v1'),
    ('identity_snapshot_byte_length',201)])
def test_selection_identity_usage_and_generation_are_native_bound(issuer_case,field,value):
    c=issuer_case;c.owner.value=replace(c.owner.value,**{field:value})
    unavailable(read(c));assert c.factory_calls==c.store.reads==0


@pytest.mark.parametrize('size',[2,17])
def test_duplicate_or_overflow_selections_refuse(issuer_case,size):
    c=issuer_case;c.owner.value=replace(c.owner.value,selections=c.owner.value.selections*size)
    unavailable(read(c));assert c.factory_calls==c.store.reads==0


def test_selection_change_after_fact_read_withholds_everything(issuer_case):
    c=issuer_case;c.owner.change_at=2
    unavailable(read(c),'SELECTION_CHANGED');assert c.store.reads>0


@pytest.mark.parametrize('at',[2,3,4])
def test_all_native_admission_rechecks_still_bind(issuer_case,at):
    c=issuer_case;c.authority.change_at=at
    unavailable(read(c))


def test_dictionary_is_not_an_owner_selection(issuer_case):
    c=issuer_case;c.owner.value={'issuer_id':c.issuer,'generation':'fake'}
    unavailable(read(c),'SELECTION_UNAVAILABLE');assert c.factory_calls==0


def test_factory_exception_is_sanitized_without_retry(issuer_case):
    calls=[]
    def broken():
        calls.append(1);raise RuntimeError('/private/secret/token')
    unavailable(read(issuer_case,factory=broken),'PRIVATE_STORE_UNAVAILABLE')
    assert calls==[1]


def test_pre_read_revocation_returns_no_previous_positive(issuer_case):
    c=issuer_case;assert read(c)['status']=='available';c.authority.deny=True;reset(c)
    unavailable(read(c),'SOURCE_NOT_ADMITTED');assert c.factory_calls==c.store.reads==0


def test_corrupt_fact_does_not_become_partial_company_context(issuer_case):
    c=issuer_case;key='company_intelligence/issuer_disclosures/v1/facts/'+c.authority.admission.reference.sha256+'.json'
    c.store.objects[key]=b'corrupt'
    unavailable(read(c),'PRIVATE_OBJECT_MISMATCH')


def test_missing_subject_attestation_refuses_before_store(issuer_case):
    c=issuer_case;c.authority.admission=replace(c.authority.admission,subject_binding=None)
    unavailable(read(c),'SELECTION_IDENTITY_MISMATCH');assert c.factory_calls==0


def test_no_historical_mode_or_chosen_generation_api(issuer_case):
    c=issuer_case
    with pytest.raises(TypeError):
        consumer.read_issuer_economic_context(c.owner,c.authority,c.factory,c.issuer,
            purpose=c.request.purpose,audience=c.request.audience,as_of='2024-01-01')
    assert c.factory_calls==0


@pytest.mark.parametrize('fields',[{'subject_id'},frozenset({'raw_source'}),None,True])
def test_additional_field_requirements_cannot_grant_new_rights(issuer_case,fields):
    c=issuer_case
    with pytest.raises(native.DisclosureError,match='PROJECTION_FIELD_REQUIREMENT_INVALID'):
        selection.read_issuer_disclosure_bundle(c.owner,c.authority,c.factory,c.issuer,
            purpose=c.request.purpose,audience=c.request.audience,required_fields=fields)
    assert c.owner.calls==c.factory_calls==0


def test_fresh_results_do_not_mutate_native_store_or_other_responses(issuer_case):
    c=issuer_case;a=read(c);b=read(c);assert a==b and a is not b
    a['context']['relationships'][0]['relationship']['product']='modified'
    a['context']['issuer_binding']['identity_snapshot_reference']['sha256']='0'*64
    assert read(c)==b


def test_actual_current_owner_readonly_store_single_pass(qualified_local_owner):
    from engine.company_intelligence import issuer_disclosure_owner as owner
    value,published=qualified_local_owner;source,state,artifacts,*_=value
    actual=owner.CurrentDisclosureOwner(source,owner.ReadOnlyLocalObjects(state.root))
    readonly=owner.ReadOnlyLocalObjects(artifacts.root);issuer=source.value.spec['fact']['subject_id']
    frozen={str(p):p.read_bytes() for root in (state.root,artifacts.root) for p in root.rglob('*') if p.is_file()}
    result=consumer.read_issuer_economic_context(actual,actual,lambda:readonly,issuer,
        purpose=owner.PURPOSE,audience=owner.AUDIENCE)
    assert result['status']=='available'
    assert result['context']['generation']==published['generation']
    assert result['context']['relationships'][0]['relationship']['subject_id']==issuer
    assert result['context']['relationships'][0]['provenance']['reference']==native.validate_fact(source.value.spec['fact']).payload()
    assert frozen=={str(p):p.read_bytes() for root in (state.root,artifacts.root) for p in root.rglob('*') if p.is_file()}
    source.value=replace(source.value,ruling_revision='0'*64)
    unavailable(consumer.read_issuer_economic_context(actual,actual,lambda:readonly,issuer,
        purpose=owner.PURPOSE,audience=owner.AUDIENCE))


@pytest.fixture
def multi_case(issuer_case):
    c=issuer_case
    first=c.authority.admission
    other=deepcopy(c.fact);other['claim_key']='fixture-second-integration'
    other['fact_id']=native.fact_id(other['disclosure_id'],other['claim_key'])
    request=replace(c.request,fact_id=other['fact_id'])
    second=replace(first,request=request,reference=native.validate_fact(other))
    class MultiAuthority:
        def __init__(self):
            self.admissions={first.request.fact_id:first,second.request.fact_id:second}
            self.calls=0;self.deny_at=None
        def resolve(self,req):
            self.calls+=1
            return None if self.calls==self.deny_at else self.admissions.get(req.fact_id)
        def authorize_publication(self,req,candidate):
            a=self.resolve(req)
            return replace(a,operation='publish') if a is not None else None
    c.authority=MultiAuthority()
    native.publish_disclosure(c.store,c.authority,request,edition=c.edition,fact=other,
        source_reader=SyntheticSourceReader(c.body))
    entries=c.owner.value.selections+(selection.SelectionEntry(other['fact_id'],second.reference,second.edition),)
    c.owner.value=replace(c.owner.value,selections=tuple(sorted(entries,key=lambda e:e.fact_id)))
    reset(c);return c


def test_multiple_selected_facts_are_read_once_each(multi_case,monkeypatch):
    c=multi_case;calls=[];original=native.read_disclosure
    def observed(*args,**kwargs):
        calls.append(args[2].fact_id);return original(*args,**kwargs)
    monkeypatch.setattr(native,'read_disclosure',observed)
    selected=selection.read_issuer_selection(c.owner,c.authority,c.factory,c.issuer,
        purpose=c.request.purpose,audience=c.request.audience)
    baseline=(c.owner.calls,c.authority.calls,c.store.reads,c.factory_calls)
    reset(c);calls.clear();result=read(c)
    assert result['status']=='available' and len(result['context']['relationships'])==2
    assert calls==[e.fact_id for e in c.owner.value.selections]
    assert (c.owner.calls,c.authority.calls,c.store.reads,c.factory_calls)==baseline
    assert [r['provenance']['fact_id'] for r in result['context']['relationships']]==[e['fact_id'] for e in selected['selections']]


def test_later_selected_fact_missing_grant_prevents_all_artifact_io(multi_case):
    c=multi_case;last=c.owner.value.selections[-1].fact_id
    c.authority.admissions[last]=replace(c.authority.admissions[last],
        allowed_fields=economic_context.REQUIRED_FIELDS-{'platform'})
    unavailable(read(c),'PROJECTION_FIELDS_NOT_ADMITTED')
    assert c.factory_calls==c.store.reads==0


def test_later_corrupt_fact_withholds_earlier_verified_context(multi_case):
    c=multi_case;last=c.owner.value.selections[-1]
    c.store.objects['company_intelligence/issuer_disclosures/v1/facts/'+last.fact_reference.sha256+'.json']=b'corrupt'
    result=read(c);unavailable(result,'PRIVATE_OBJECT_MISMATCH')
    assert c.factory_calls==1 and c.store.reads>0
    assert c.owner.value.selections[0].fact_id not in json.dumps(result)


def test_final_last_admission_recheck_withholds_whole_batch(multi_case):
    c=multi_case;c.authority.deny_at=8  # 2 preflights + 4 native checks + 2 final checks
    unavailable(read(c),'SOURCE_NOT_ADMITTED')
    assert c.authority.calls==8 and c.factory_calls==1


def test_ordered_selection_contract_is_preserved(multi_case):
    c=multi_case;c.owner.value=replace(c.owner.value,selections=tuple(reversed(c.owner.value.selections)))
    unavailable(read(c),'SELECTION_DUPLICATE_OR_UNORDERED');assert c.factory_calls==0


def test_legacy_metadata_selection_does_not_gain_new_field_requirements(issuer_case):
    c=issuer_case;c.authority.admission=replace(c.authority.admission,
        allowed_fields=frozenset({'fact_id','kind','lifecycle','subject_id'}))
    result=selection.read_issuer_selection(c.owner,c.authority,c.factory,c.issuer,
        purpose=c.request.purpose,audience=c.request.audience)
    assert len(result['selections'])==1 and 'product' not in result['selections'][0]
    reset(c);unavailable(read(c),'PROJECTION_FIELDS_NOT_ADMITTED')
    assert c.factory_calls==c.store.reads==0
