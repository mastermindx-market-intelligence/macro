"""Synthetic additive publication only; no production operation is invoked."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from engine.company_intelligence import issuer_disclosures as n
from engine.company_intelligence import issuer_disclosure_owner as o
from engine.company_intelligence import issuer_disclosure_publication as p
from engine.company_intelligence import issuer_disclosure_preflight as gate
from engine.company_intelligence import sec_supplier_adoption as supplier
from engine.company_intelligence.issuer_disclosure_selection import read_issuer_selection
from tests.test_company_disclosure_owner import case as c01_case
from tests.test_sec_supplier_adoption import case as sec_case


class SpyState:
    def __init__(self, backing):
        self.backing=backing; self.writes=[]; self.action=None

    def __getattr__(self,name):
        return getattr(self.backing,name)

    def put_bytes_strict_conditional(self,key,raw,**kwargs):
        self.writes.append(key)
        result=self.backing.put_bytes_strict_conditional(key,raw,**kwargs)
        if self.action:
            self.action(key,raw)
        return result


@pytest.fixture
def both(c01_case,sec_case):
    source,state,artifacts,factory,*_=c01_case
    first=p.publish_generation(source,state,artifacts,factory,
        intent=p.prepare_publication(source,state,expected_current_version=None))
    req=n.Request(source.value.spec['fact']['fact_id'],o.PURPOSE,o.AUDIENCE)
    old=n.read_disclosure(artifacts,o.CurrentDisclosureOwner(source,state),req)
    ref=o.object_ref(n._canonical(o.make_manifest(source.value, first['intent']['manifest']['computed_at'])))
    raw=state.get_bytes_strict_bounded('generations/'+ref['sha256']+'.json',n.MAX_OBJECT_BYTES)
    return SimpleNamespace(c01=source,sec=sec_case.source,state=SpyState(state),artifacts=artifacts,
        factory=lambda snap:supplier.PinnedSupplierSource(snap,sec_case.pinned.authority),
        c01_request=req,c01_response=old,c01_reference=ref,c01_raw=raw,
        prior=state.get_bytes_strict_bounded_versioned(o.CURRENT_KEY,n.MAX_OBJECT_BYTES))


def prepare(c):
    return p.prepare_publication(c.sec,c.state,expected_current_version=c.prior.version,
        mode=p.APPEND_MODE,preserved_sources={n.FACT_SCHEMA:c.c01})


def append(c,intent=None):
    return p.publish_generation(c.sec,c.state,c.artifacts,c.factory,intent=prepare(c) if intent is None else intent,
        preserved_sources={n.FACT_SCHEMA:c.c01})


def current(c):
    return o.CurrentDisclosureOwner(c.c01,c.state,supplier_sources={n.SUPPLIER_FACT_SCHEMA:c.sec})


def sec_request(c):
    return n.Request(c.sec.value.spec['fact']['fact_id'],o.PURPOSE,o.AUDIENCE)


def test_append_preserves_exact_c01_component_response_and_uses_one_pointer_cas(both):
    c=both; saved={str(x):x.read_bytes() for x in c.artifacts.root.rglob('*') if x.is_file()}
    result=append(c)
    assert c.state.writes.count(o.CURRENT_KEY)==1
    assert 'generations/'+c.c01_reference['sha256']+'.json' not in c.state.writes
    assert c.state.get_bytes_strict_bounded('generations/'+c.c01_reference['sha256']+'.json',n.MAX_OBJECT_BYTES)==c.c01_raw
    assert all(__import__('pathlib').Path(path).read_bytes()==raw for path,raw in saved.items())
    owner=current(c)
    assert n.read_disclosure(c.artifacts,owner,c.c01_request)==c.c01_response
    supplied=n.read_disclosure(c.artifacts,owner,sec_request(c))
    assert supplied['generation']==result['generation']
    assert supplied['fact']['kind']=='disclosed_supplier'
    assert result['collection_reference']['sha256'] not in {result['generation'],c.c01_response['generation']}
    _,_,collection=o.read_current_manifest(c.state)
    assert len(collection['members'])==2 and collection['members'][0]['fact_id']<collection['members'][1]['fact_id']
    for req,expected in [(c.c01_request,c.c01_response),(sec_request(c),supplied)]:
        selection=read_issuer_selection(owner,owner,lambda:c.artifacts,expected['fact']['subject_id'],
            purpose=o.PURPOSE,audience=o.AUDIENCE)
        assert selection['generation']==expected['generation']
        assert selection['selections'][0]['fact_id']==req.fact_id
    assert owner.authorize_publication(sec_request(c),owner.resolve(sec_request(c)).reference) is None


def test_supplier_revocation_or_missing_supplier_configuration_never_qualifies_c01_through_supplier(both):
    c=both;append(c)
    def denied():
        raise n.DisclosureError('PURPOSE_NOT_ADMITTED')
    c.sec.action=denied
    assert n.read_disclosure(c.artifacts,current(c),c.c01_request)==c.c01_response
    with pytest.raises(n.DisclosureError,match='PURPOSE_NOT_ADMITTED'):
        current(c).resolve(sec_request(c))
    c.sec.action=None
    assert n.read_disclosure(c.artifacts,o.CurrentDisclosureOwner(c.c01,c.state),c.c01_request)==c.c01_response
    c.c01.action=lambda: (_ for _ in ()).throw(AssertionError('wrong source must not be qualified'))
    with pytest.raises(n.DisclosureError,match='SOURCE_SCHEMA_NOT_CONFIGURED'):
        o.CurrentDisclosureOwner(c.c01,c.state).resolve(sec_request(c))


@pytest.mark.parametrize('field', ['fact_id','subject_id'])
def test_rehashed_legacy_dispatch_substitution_refuses_before_writes(both,field):
    c=both;intent=prepare(c)
    value='integration:'+'f'*64 if field=='fact_id' else 'ISS:US-XNAS-OTHER'
    intent['preserved_members'][0][field]=value
    intent['collection']['members']=sorted([*intent['preserved_members'],
        o.member_descriptor(c.sec.value,intent['manifest_reference'])],key=lambda x:x['fact_id'])
    intent['collection_reference']=o.object_ref(n._canonical(intent['collection']))
    with pytest.raises(n.DisclosureError,match='PUBLICATION_INTENT_CHANGED'):
        append(c,intent)
    assert not c.state.writes


def test_append_requires_legacy_metadata_source_and_existing_exact_current(both):
    c=both
    with pytest.raises(n.DisclosureError,match='PRESERVED_SOURCE_REQUIRED'):
        p.prepare_publication(c.sec,c.state,expected_current_version=c.prior.version,mode=p.APPEND_MODE)
    intent=prepare(c)
    c.state.backing.put_bytes_strict_conditional(o.CURRENT_KEY,b'{}',expected_version=c.prior.version,content_type='application/json')
    with pytest.raises(n.DisclosureError,match='PUBLICATION_PREDECESSOR_CHANGED'):
        append(c,intent)
    assert not c.state.writes


def test_post_cas_supplier_failure_is_sticky_unknown_without_rollback(both):
    c=both
    def on_write(key,raw):
        if key==o.CURRENT_KEY:
            c.sec.action=lambda: (_ for _ in ()).throw(n.DisclosureError('SOURCE_REVOKED'))
    c.state.action=on_write
    with pytest.raises(n.DisclosureError) as raised:
        append(c)
    assert raised.value.effect_unknown and not raised.value.automatic_retry_permitted
    assert c.state.writes.count(o.CURRENT_KEY)==1
    assert c.state.get_bytes_strict_bounded_versioned(o.CURRENT_KEY,n.MAX_OBJECT_BYTES)!=c.prior
    assert n.read_disclosure(c.artifacts,current(c),c.c01_request)==c.c01_response


def test_pre_cas_identity_drift_leaves_old_current_selected(both):
    c=both;intent=prepare(c)
    def on_write(key,raw):
        if key=='generations/'+intent['collection_reference']['sha256']+'.json':
            identities=deepcopy(c.sec.value.current_identities)
            for r in identities.values():
                r['source_commit']='f'*40
            c.sec.value=replace(c.sec.value,current_identities_raw=n._canonical(identities))
    c.state.action=on_write
    with pytest.raises(n.DisclosureError,match='PUBLICATION_AUTHORITY_CHANGED'):
        append(c,intent)
    assert o.CURRENT_KEY not in c.state.writes
    assert c.state.get_bytes_strict_bounded_versioned(o.CURRENT_KEY,n.MAX_OBJECT_BYTES)==c.prior


def test_append_duplicate_existing_fact_refuses_instead_of_replaying(both):
    c=both;append(c);c.state.writes.clear()
    prior=c.state.get_bytes_strict_bounded_versioned(o.CURRENT_KEY,n.MAX_OBJECT_BYTES)
    with pytest.raises(n.DisclosureError,match='CURRENT_MEMBER_DUPLICATE_OR_UNORDERED'):
        p.prepare_publication(c.sec,c.state,expected_current_version=prior.version,mode=p.APPEND_MODE)
    assert not c.state.writes


@pytest.mark.parametrize('bad', ['duplicate','limit','nested','unknown_schema','subject_ambiguous'])
def test_collection_rejects_bad_members_without_body_or_source_access(both,bad):
    c=both;append(c)
    _,_,collection=o.read_current_manifest(c.state)
    if bad=='duplicate': collection['members'].append(deepcopy(collection['members'][0]))
    elif bad=='limit': collection['members']*=9
    elif bad=='nested':
        raw=n._canonical(collection);ref=o.object_ref(raw)
        c.state.backing.put_bytes_strict_conditional('generations/'+ref['sha256']+'.json',raw,expected_version=None,content_type='application/json')
        collection['members'][0]['manifest']=ref
    elif bad=='unknown_schema': collection['members'][0]['fact_schema']='other_schema'
    else:
        collection['members'][0]['subject_id']=collection['members'][1]['subject_id']
    raw=n._canonical(collection);ref=o.object_ref(raw)
    c.state.backing.put_bytes_strict_conditional('generations/'+ref['sha256']+'.json',raw,expected_version=None,content_type='application/json')
    prior=c.state.get_bytes_strict_bounded_versioned(o.CURRENT_KEY,n.MAX_OBJECT_BYTES)
    pointer=n._canonical({'schema':o.POINTER_SCHEMA,'manifest':ref})
    c.state.backing.put_bytes_strict_conditional(o.CURRENT_KEY,pointer,expected_version=prior.version,content_type='application/json')
    c.c01.action=c.sec.action=lambda: (_ for _ in ()).throw(AssertionError('no source qualification expected'))
    with pytest.raises(n.DisclosureError):
        if bad=='subject_ambiguous': current(c).resolve_issuer(collection['members'][0]['subject_id'],o.PURPOSE,o.AUDIENCE)
        else: current(c).resolve(c.c01_request)


def test_preflight_append_binds_complete_intent_and_default_mode_is_conserved(both):
    c=both;intent=prepare(c)
    expected={'code_version':c.sec.value.code_version,'mode':p.APPEND_MODE}
    with pytest.raises(n.DisclosureError,match='PREFLIGHT_APPEND_BINDING_REQUIRED'):
        gate.bind_prepared_intent(c.sec,intent,expected)
    snapshot=gate.bind_prepared_intent(c.sec,intent,expected,
        same_manifest=lambda snap,value:p.validate_publication_intent(c.sec,c.state,value,
            preserved_sources={n.FACT_SCHEMA:c.c01})[0]==snap)
    assert snapshot==c.sec.value
    with pytest.raises(n.DisclosureError,match='PREFLIGHT_MODE_DRIFT'):
        gate.bind_prepared_intent(c.sec,intent,{**expected,'mode':'PROMOTE_CURRENT'},same_manifest=lambda *_:True)
    legacy=p.prepare_publication(c.sec,c.state,expected_current_version=c.prior.version)
    assert legacy['schema']=='company_intelligence.native_publication_intent/v1'
    assert legacy['mode']=='PROMOTE_CURRENT'
    assert set(legacy)=={'schema','manifest','manifest_reference','expected_current_version','expected_current_sha256','mode'}


def test_append_origin_set_is_additive_and_missing_loaded_module_refuses(tmp_path):
    from tests.test_company_disclosure_preflight import GitStub
    from types import SimpleNamespace
    modules={};blobs={}
    for i,name in enumerate((*gate.MODULE_NAMES,*gate.APPEND_MODULE_NAMES)):
        path='origin_'+str(i)+'.py';raw=('# synthetic '+name+'\n').encode()
        (tmp_path/path).write_bytes(raw);blobs[path]=raw
        modules[name]=SimpleNamespace(__file__=str(tmp_path/path))
    git=GitStub(tmp_path,'a'*40,blobs)
    default=gate.collect_on_disk_provenance(git,modules)
    appended=gate.collect_on_disk_provenance(git,modules,mode=p.APPEND_MODE)
    assert tuple(x['module'] for x in default['modules'])==gate.MODULE_NAMES
    assert tuple(x['module'] for x in appended['modules'])==(*gate.MODULE_NAMES,*gate.APPEND_MODULE_NAMES)
    assert appended['modules'][:len(default['modules'])]==default['modules']
    del modules['engine.fundamental_forensics.source_sync']
    with pytest.raises(n.DisclosureError,match='PREFLIGHT_MODULE_ORIGIN'):
        gate.collect_on_disk_provenance(git,modules,mode=p.APPEND_MODE)


def test_collection_cardinality_is_exactly_sixteen_metadata_slots():
    members=[{'fact_id':'integration:'+f'{i:064x}', 'subject_id':'ISS:US-XNAS-SYNTH'+str(i),
        'fact_schema':n.FACT_SCHEMA,'manifest':{'sha256':f'{i+100:064x}','byte_length':100}}
        for i in range(1,18)]
    o.validate_members(members[:16])  # Structural capacity only, not native adoption.
    with pytest.raises(n.DisclosureError,match='CURRENT_MEMBER_LIMIT'):
        o.validate_members(members)
