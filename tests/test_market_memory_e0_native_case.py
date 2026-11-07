"""Real selected-owner files and native source capabilities; no actual issuer.

The peer capability fixture MUST come from the actual peer owner's primitive
fixtures. No successful peer/runtime/packet facade is constructed here. Native
installation/control/domain/source scopes below are explicit synthetic fixtures.
Original production owners and private file/source validators execute unchanged.
"""
import copy
from contextlib import contextmanager
import os
import shutil
import sys
from datetime import datetime,timedelta,timezone
from hashlib import sha1,sha256
import json
from pathlib import Path
import zlib

import pytest

from tests.market_memory_native_peer_fixtures import native_peer_primitives, native_peer_capability

from engine.research_factory import market_memory_e0_native_case as case
from engine.research_factory import market_memory_e0_allocation as allocator
from engine.research_factory import market_memory_e0_task_evidence as tasks
from engine.research_factory import market_memory_contextual_registration as control
from engine.research_factory.market_memory_e0_reservations import ReservationStore
from engine.research_factory.market_memory_e0_reserved_read import _run_reserved_read
from engine.research_factory.market_memory_e0_original_case import _read_original_case
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as use
from tests.market_memory_e0_fixtures import capture,owner
from tests.test_market_memory_e0_control_records import records,canonical,record_ref,reference,ref

SOURCE_ROOT=Path(__file__).resolve().parents[1]
INTENT={'study_id':'synthetic-study','root_id':'synthetic-original-root',
        'operator_run_id':'synthetic-protected-owner','child_run_id':'synthetic-child',
        'participant_binding_sha256':'a'*64}


def write(path,body,private=True):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(body);path.chmod(0o600 if private else 0o644)



def source_guard_snapshot(source_root=SOURCE_ROOT):
    """Known public source plus Git custody metadata, hashes only in reports."""
    paths=set(case._SOURCE_PATHS)|{use.REGISTRATION,use.AUTHORITY_RECORD,
        'tests/test_market_memory_e0_native_case.py','tests/test_market_memory_e0_native_issuer.py'}
    paths.update(str(p.relative_to(source_root)) for p in
        (source_root/'contracts/market_memory').glob('e0_*.schema.json'))
    result={}
    def observe(path):
        if not os.path.lexists(path):return None
        st=path.lstat()
        body=path.read_bytes() if path.is_file() and not path.is_symlink() else b''
        return (st.st_mode,st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns,
                sha256(body).hexdigest(),os.readlink(path) if path.is_symlink() else None)
    for relative in sorted(paths):result[relative]=observe(source_root/relative)
    git=source_root/'.git';result['.git']=observe(git)
    if git.is_file():
        text=git.read_text().strip();assert text.startswith('gitdir: ')
        metadata=(git.parent/text[8:]).resolve()
    else:metadata=git
    for name in ('HEAD','config','commondir','index','packed-refs','objects','refs'):
        result['git_metadata/'+name]=observe(metadata/name)
    if (metadata/'HEAD').is_file():
        head=(metadata/'HEAD').read_text().strip()
        if head.startswith('ref: '):result['git_selected_ref']=observe(metadata/head[5:])
    return result


def _assert_fresh_install(root,temporary_parent):
    root=Path(root);parent=Path(temporary_parent)
    assert parent.is_dir() and not parent.is_symlink()
    assert root==parent/'native-install' and root.resolve()==root
    assert root!=SOURCE_ROOT and not root.is_relative_to(SOURCE_ROOT)
    assert not os.path.lexists(root), 'isolated install must be fresh before writes'


@contextmanager
def isolated_install(temporary_parent,monkeypatch,*,after_copy=None):
    """Fixture-only install: source checkout and its Git are never writable targets.

    Module origins/schema roots explicitly point to byte-identical TEMP copies;
    the real native validators and source/Git checks are never replaced.
    """
    root=Path(temporary_parent)/'native-install'
    before=source_guard_snapshot()
    _assert_fresh_install(root,temporary_parent)
    try:
        root.mkdir(mode=0o755)
        paths=set(case._SOURCE_PATHS)|{use.REGISTRATION,use.AUTHORITY_RECORD}
        paths.update(str(p.relative_to(SOURCE_ROOT)) for p in
            (SOURCE_ROOT/'contracts/market_memory').glob('e0_*.schema.json'))
        for relative in sorted(paths):
            assert not Path(relative).is_absolute() and '..' not in Path(relative).parts
            source=SOURCE_ROOT/relative;target=root/relative
            assert source.is_file() and not source.is_symlink()
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target);target.chmod(0o644)
            assert target.read_bytes()==source.read_bytes()
        # BEFORE any later setup which may fail; never restore by writing source.
        for relative in paths:
            if relative.endswith('.py'):
                name=relative[:-3].replace('/','.')
                if name.endswith('.__init__'):name=name[:-9]
                module=sys.modules.get(name)
                if module is not None:monkeypatch.setattr(module,'__file__',str(root/relative))
        control._validator.cache_clear();control._task_validator.cache_clear()
        control._reviewer_plan_validator.cache_clear()
        if after_copy is not None:after_copy(root) # TEST failure injection only.
        yield root
    finally:
        control._validator.cache_clear();control._task_validator.cache_clear()
        control._reviewer_plan_validator.cache_clear()
        assert source_guard_snapshot()==before, 'fixture changed original source/Git metadata'

def native_object_database(root,paths,*,temporary_parent):
    """Pure fixture objects, NOT a Macro checkout/worktree or Git mutation.

    Unchanged native _verify_source invokes real Git against this synthetic
    commit/tree/blob closure and compares real source file bytes afterwards.
    """
    root=Path(root);parent=Path(temporary_parent)
    assert root==parent/'native-install' and root.resolve()==root and root.is_dir()
    assert root!=SOURCE_ROOT and not root.is_relative_to(SOURCE_ROOT)
    assert not os.path.lexists(root/'.git'), 'never overwrite an existing Git directory/gitfile'
    git=root/'.git';(git/'objects').mkdir(parents=True,exist_ok=False)
    def obj(kind,body):
        data=kind.encode()+b' '+str(len(body)).encode()+b'\0'+body
        digest=sha1(data).hexdigest();dest=git/'objects'/digest[:2]/digest[2:]
        if not dest.exists():write(dest,zlib.compress(data),False)
        return digest
    tree={}
    for relative in paths:
        here=tree
        parts=Path(relative).parts
        for part in parts[:-1]:here=here.setdefault(part,{})
        here[parts[-1]]=obj('blob',(root/relative).read_bytes())
    def store_tree(value):
        body=b''
        for name,entry in sorted(value.items(),key=lambda item:item[0]+('/' if isinstance(item[1],dict) else '')):
            directory=isinstance(entry,dict);digest=store_tree(entry) if directory else entry
            body+=(b'40000' if directory else b'100644')+b' '+name.encode()+b'\0'+bytes.fromhex(digest)
        return obj('tree',body)
    tree_id=store_tree(tree)
    commit=obj('commit',('tree '+tree_id+'\nauthor Synthetic Fixture <fixture@invalid> 0 +0000\ncommitter Synthetic Fixture <fixture@invalid> 0 +0000\n\nExplicit synthetic native installation\n').encode())
    write(git/'config',b'[core]\nrepositoryformatversion=0\nbare=false\n',False)
    write(git/'HEAD',b'ref: refs/heads/fixture\n',False)
    write(git/'refs/heads/fixture',(commit+'\n').encode(),False)
    return commit


def publish(root,records):
    rr=record_ref(records['registration'],'study_id')
    records['closure']['registration_ref']=rr;cr=record_ref(records['closure'],'closure_id')
    records['publication'].update(registration_ref=rr,closure_ref=cr);pr=record_ref(records['publication'],'publication_id')
    records['installation'].update(registration_ref=rr,closure_ref=cr,publication_ref=pr)
    records['access'].update(registration_ref=rr,publication_ref=pr)
    return rr,pr


def retain(root,value,identity='object_id'):
    r=record_ref(value,identity);write(root/(r['sha256']+'.json'),canonical(value));return r


@pytest.fixture
def native_world(tmp_path,monkeypatch,records,native_peer_capability):
    with isolated_install(tmp_path,monkeypatch) as installed_root:
        yield from _native_world(tmp_path,monkeypatch,records,native_peer_capability,installed_root)


def _native_world(tmp_path,monkeypatch,records,native_peer_capability,installed_root):
    # native_peer_capability is supplied by ROOT's genuine peer-module fixtures;
    # only native OS/auth/file primitives may be substituted there.
    peer=case._peer_owner();peer_binding=peer.broker_service_binding(native_peer_capability)
    a=capture(tmp_path,monkeypatch,session='2026-08-01',growth=0.2)
    b=capture(tmp_path,monkeypatch,session='2026-08-02',growth=0.8)
    q=capture(tmp_path,monkeypatch,session='2026-08-12',growth=0.2)
    reader,pin=owner(tmp_path);cutoff='2026-08-20T12:00:00.000000Z'
    refs=[{key:item.capture_receipt[key] for key in tasks._IDENTITY} for item in (q,a,b)]
    membership={'owner':{'profile':pin.profile,'store_id':pin.store_id,'generation_id':pin.generation_id,'generation_sha256':pin.generation_sha256},
        'query_candidates':[{**item,'subject':q.packet['subject'],'first_available_for_contextual_analysis':cutoff} for item in refs]}
    frozen=canonical(membership)
    monkeypatch.setitem(control._FROZEN_DOMAIN_DIGESTS,'membership',sha256(frozen).hexdigest())
    task={**refs[0],'task_id':'fixture-task','subject_id':q.packet['subject']['subject_id'],
          'instrument_id':q.packet['subject']['instrument_id'],'analysis_cutoff':cutoff,
          'mode':'historical_hypothetical','k':1,'question':'Compare retained house outputs and state their limitations.',
          'required_facet_ids':['growth','source-limits'],'original_evidence':refs}
    task['question_sha256']=sha256(task['question'].encode()).hexdigest()
    manifest={k:v['const'] for k,v in control._task_validator().schema['properties'].items() if 'const' in v}
    manifest.update(object_id='fixture-tasks',tasks=[task]);manifest_bytes=canonical(manifest)
    reg=records['registration'];reg['corpus'].update({k:membership['owner'][k] for k in membership['owner']})
    reg['corpus']['membership_ref']=reference(frozen,'market_memory.e0_original_owner_metadata_membership.v1','fixture-membership')
    reg['tasks_ref']=reference(manifest_bytes,control._TASK_SCHEMA,'fixture-tasks')
    method=retrieval.RetainedContextMethodSpec(5,5,task['mode'])
    method_record={'schema':tasks.METHOD_SCHEMA,'object_id':'fixture-method','authority':'display_only',
                   'study_id':INTENT['study_id'],'tasks_ref':reg['tasks_ref'],'method_spec':method.disclosure()}
    method_bytes=canonical(method_record);reg['implementation']['method_ref']=reference(method_bytes,tasks.METHOD_SCHEMA,'fixture-method')
    assignment=allocator.allocate_condition_order(seed_hex=reg['allocation']['seed_hex'],study_id=reg['study_id'],
        tasks_sha256=reg['tasks_ref']['sha256'],task_ids=[task['task_id']])
    assignment_bytes=canonical(assignment);reg['allocation']['assignment_ref']=reference(assignment_bytes,assignment['schema'],assignment['allocation_sha256'])
    binding=case.selected_condition.binding
    reg['allocation']['algorithm_ref']={'schema':'python.source.v1','object_id':'fixture-native-allocator',
        'sha256':binding.ALLOCATOR_SOURCE_SHA256,'bytes':binding.ALLOCATOR_SOURCE_BYTES}
    participants=[{'principal_ref':ref('original-reviewer-'+str(i)),'qualification_ref':ref('qualification-'+str(i)),
                   'independence_ref':ref('independence-'+str(i))} for i in range(3)]
    schema=control._reviewer_plan_validator().schema
    reg['design_ref']['sha256']=schema['properties']['protocol_sha256']['const']
    plan={k:v['const'] for k,v in schema['properties'].items() if 'const' in v}
    plan.update(object_id='fixture-reviewer-plan',study_id=reg['study_id'],preregistered_at=reg['registered_at'],
        tasks_ref=reg['tasks_ref'],reviewers=participants[:2],adjudicator=participants[2],
        assignments=[{'task_id':task['task_id'],'reviewer_principal_ids':[x['principal_ref']['object_id'] for x in participants[:2]],
                      'adjudicator_principal_id':participants[2]['principal_ref']['object_id']}],
        blinding={k:v['const'] for k,v in schema['$defs']['blinding']['properties'].items()})
    plan_bytes=canonical(plan);reg['reviewer_plan_ref']=reference(plan_bytes,plan['schema'],plan['object_id'])
    records['installation']['expires_at']=(datetime.now(timezone.utc)+timedelta(days=2)).isoformat(timespec='microseconds').replace('+00:00','Z')
    records['installation']['permitted_actions'].append('read_registered_condition_outputs')
    rr,pr=publish(tmp_path,records)
    monkeypatch.setattr(case,'_INSTALLED_ROOT',installed_root)
    monkeypatch.setattr(case,'_CONTROL_ROOT',tmp_path/'controls')
    monkeypatch.setattr(case,'_SOURCE_ROOT',reader.root)
    config_path=installed_root/use.REGISTRATION;original_config=config_path.read_bytes()
    registration_schema_path=installed_root/'contracts/market_memory/e0_registration.v1.schema.json'
    original_registration_schema=registration_schema_path.read_bytes()
    synthetic_registration_schema=json.loads(original_registration_schema)
    for key in ('store_id','generation_id','generation_sha256'):
        synthetic_registration_schema['properties']['corpus']['properties'][key]['const']=membership['owner'][key]
    # Explicit root-approved installation/domain fixture substitution, not a
    # validator-success stub or a production schema/pin change.
    write(registration_schema_path,canonical(synthetic_registration_schema),False)
    control._validator.cache_clear()
    config=json.loads(original_config);config['store_id']=pin.store_id;config['allowed_subject_ids']=[task['subject_id']]
    # Explicit administrative source-scope fixture, unchanged authority/method/
    # actions/false lifecycle grants. No load_registration success stub.
    write(config_path,canonical(config),False)
    commit=native_object_database(installed_root,case._SOURCE_PATHS,temporary_parent=tmp_path)
    service={'schema':case._SERVICE,'object_id':'fixture-native-service','issuer_id':'MACRO_LINUX_NATIVE_E0_ISSUER',
        'protocol':'memory.e0.native_issuer.v3','installation_id':records['installation']['installation_id'],
        'installation_epoch':records['installation']['installation_epoch'],'registration_ref':rr,'publication_ref':pr,
        'source_commit':commit,'protected_mode':'PROTECTED_MEMORY_EXECUTION',
        **{k:peer_binding[k] for k in ('ssh_key_fingerprint','restriction_profile','forced_command','native_executable','journal_profile')}}
    directory=case._CONTROL_ROOT/sha256(INTENT['study_id'].encode()).hexdigest();directory.mkdir(parents=True,mode=0o700)
    service_ref=retain(directory,service)
    recipient={'schema':case._RECIPIENT,'object_id':'fixture-native-recipient','service_ref':service_ref,
        'installation_id':service['installation_id'],'installation_epoch':service['installation_epoch'],
        'registration_ref':rr,'publication_ref':pr,'owner_principal_ref':records['installation']['owner_principal_ref'],
        'operation_id':'original-operation','intent':copy.deepcopy(INTENT),
        'protected_owner_ref':ref('actual-protected-owner-FIXTURE'),
        'control_admission_ref':ref('actual-Control-admission-FIXTURE'),
        'protected_mode':'PROTECTED_MEMORY_EXECUTION','reviewer_principal_ref':participants[0]['principal_ref'],
        'original_recipient':{'recipient_kind':'native_broker_service','principal_ref':service_ref,
            'ssh_key_fingerprint':peer_binding['ssh_key_fingerprint']},
        'recipient_permissions':['delegate_original_child_input','read_original_child_result'],
        'task_id':task['task_id'],'slot':assignment['assignments'][0]['order'].index('fixed_l1'),
        'actions':sorted(case._ACTIONS),'purpose':'read_source_scoped_participant_input',
        'source_use':{'source_registration_sha256':sha256(config_path.read_bytes()).hexdigest(),
            'source_authority_sha256':config['source_authority']['sha256'],'corpus':membership['owner'],
            'subject_id':task['subject_id'],'query_cutoff':cutoff,'mode':task['mode'],
            'method_spec':method.disclosure(),'k':1,'maximum_looks':3}}
    recipient_ref=retain(directory,recipient)
    records['installation']['admin_receipt_ref']=service_ref;records['access']['scope_ref']=recipient_ref
    for data in (manifest_bytes,frozen,method_bytes,assignment_bytes,plan_bytes):write(directory/(sha256(data).hexdigest()+'.json'),data)
    selected={'schema':case.owner.SELECTED_SCHEMA,'study_id':INTENT['study_id'],'source_commit':commit,
        'control_refs':{k:retain(directory,records[k],identity) for k,(_kind,identity) in case.owner._CONTROL_KEYS.items()}}
    write(directory/'SELECTED.json',canonical(selected))
    reservations=directory/'reservations';reservations.mkdir(mode=0o700)
    store=ReservationStore(reservations,{'study_id':INTENT['study_id'],'installation_id':service['installation_id'],
        'installation_epoch':service['installation_epoch'],'registration_sha256':rr['sha256'],'publication_sha256':pr['sha256']})
    store.initialize(3)  # TEST setup only; implementation NEVER initializes.
    world={'cap':native_peer_capability,'records':records,'selected':selected,'directory':directory,'store':store,
           'recipient':recipient,'service':service,'source_config':config_path,'task':task,
           'installed_root':installed_root,'temporary_root':tmp_path}
    fixture_record={'original_corpus_qualification':False,'source_captures':'three genuine native SYNTHETIC captures',
        'peer_source_sha256':sha256(Path(peer.__file__).read_bytes()).hexdigest(),
        'peer_source_acceptance':'COMPOSED_PROFILE2_SOURCE_REVIEW_PENDING; primitive fixture is NOT installed two-host/auth proof',
        'schema_corpus_fixture':{'original_sha256':sha256(original_registration_schema).hexdigest(),
            'fixture_sha256':sha256(registration_schema_path.read_bytes()).hexdigest(),
            'substituted_fields':{key:membership['owner'][key] for key in ('store_id','generation_id','generation_sha256')}},
        'membership_digest_fixture':sha256(frozen).hexdigest(),
        'source_use_fixture':{'registration_sha256':sha256(config_path.read_bytes()).hexdigest(),
            'substituted_fields':['store_id','allowed_subject_ids'],'five_day_method_and_authority_unchanged':True},
        'real_synthetic_source_commit':commit,'selected_source_paths':list(case._SOURCE_PATHS),
        'protected_owner_admission':'Explicit native-admin grant fixture; NOT observed remote M2Control',
        'source_or_study_admission':False}
    world['fixture_record']=fixture_record
    (tmp_path/'FIXTURE_AUTHORITY_SUBSTITUTIONS.json').write_text(json.dumps(fixture_record,sort_keys=True,indent=2)+'\n')
    yield world # Only temporary copies changed; no source restoration writes exist.


def resolve(world,**changes):
    return case._resolve_current_case(world['cap'],operation_id=changes.get('operation_id','original-operation'),
                                      intent=changes.get('intent',copy.deepcopy(INTENT)))


def inventory(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_real_selected_native_owner_to_packet_and_original_reservation(native_world):
    world=native_world;context=resolve(world)
    store=case._reservation_store(context);intent=case._original_case_intent(context)
    original_inventory=inventory(store.directory);loaded=[]
    def authorize(phase,operation_id,original):
        assert operation_id=='original-operation' and original==intent;case._check_context(context)
    def load_actual_native_sources():
        # The unchanged native reservation owner must have retained PENDING
        # BEFORE actual cohort/feature/source-card acquisition, not a pre-read.
        state=store.snapshot()
        assert state['reserved_looks']==1 and state['consumed_looks']==0
        raw=case._build_case_input(context);loaded.append(raw)
        return raw
    def qualify(body,operation_id,original):
        assert original==intent and operation_id=='original-operation'
        descriptors=case.packet.extract_selected_citations(body,input_sha256=sha256(body).hexdigest())
        assert len(descriptors)==10
        assert all(x['citation']['source_sha256']!=x['packet_sha256'] for x in descriptors)
        doc=json.loads(body[:-len(case.packet.SUFFIX)])
        assert doc['source_view']['actual_blinding_established'] is False and 'original_evidence' not in doc['task']
        fact=case._original_recipient_fact(context,original_intent=original)
        assert fact['recipient_kind']=='native_broker_service'
        assert fact['principal_ref']==world['recipient']['service_ref']
    result=_run_reserved_read(store,'original-operation',intent,authorize=authorize,
                              load=load_actual_native_sources,qualify=qualify)
    assert len(loaded)==1 and result==loaded[0] and store.snapshot()['consumed_looks']==1
    assert original_inventory!=inventory(store.directory)
    snapshot=inventory(store.directory)
    state,original=_read_original_case(store,'original-operation',intent,authorize=authorize,qualify=qualify)
    assert (state,original)==('COMPLETE',result) and len(loaded)==1 and inventory(store.directory)==snapshot


@pytest.mark.parametrize('field,value',[('root_id','other-root'),('child_run_id','other-child'),
    ('participant_binding_sha256','f'*64)])
def test_wrong_current_recipient_before_source_or_store(native_world,field,value,monkeypatch):
    def forbidden(*a,**k):pytest.fail('wrong recipient reached source acquisition')
    monkeypatch.setattr(case.cohort,'read_retained_context_cohort',forbidden)
    intent=copy.deepcopy(INTENT);intent[field]=value
    before=inventory(native_world['store'].directory)
    with pytest.raises(case.NativeCaseError,match='recipient_intent'):
        resolve(native_world,intent=intent)
    assert inventory(native_world['store'].directory)==before


@pytest.mark.parametrize('change',['revoked','contaminated','slot','adjudicator','service_peer','method','original_recipient','recipient_permission','slot_rebinding'])
def test_native_control_or_grant_mutation_refuses(native_world,change):
    world=native_world;context=resolve(world)
    if change in ('revoked','contaminated'):
        records=world['records'];records['access']['status']='revoked' if change=='revoked' else 'active'
        records['access']['contamination_state']='contaminated' if change=='contaminated' else 'clean'
        world['selected']['control_refs']['access']=retain(world['directory'],records['access'],'access_state_id')
    else:
        recipient=copy.deepcopy(world['recipient'])
        if change=='slot':recipient['slot']=True
        elif change=='slot_rebinding':recipient['slot']=(recipient['slot']+1)%3
        elif change=='adjudicator':recipient['reviewer_principal_ref']=ref('unknown-adjudicator')
        elif change=='original_recipient':recipient['original_recipient']['principal_ref']=ref('wrong-original-service')
        elif change=='recipient_permission':recipient['recipient_permissions']=['read_original_child_result']
        elif change=='service_peer':
            service=copy.deepcopy(world['service']);service['ssh_key_fingerprint']='SHA256:'+'A'*43
            recipient['service_ref']=retain(world['directory'],service)
        else:recipient['source_use']['method_spec']['purge_calendar_days']=0
        world['records']['access']['scope_ref']=retain(world['directory'],recipient)
        world['selected']['control_refs']['access']=retain(world['directory'],world['records']['access'],'access_state_id')
    write(world['directory']/'SELECTED.json',canonical(world['selected']))
    with pytest.raises((case.NativeCaseError,case.owner.E0InstalledControlError)):
        case._check_context(context)


def test_extra_reference_corruption_and_native_source_drift_withhold(native_world):
    world=native_world;context=resolve(world)
    path=world['directory']/(world['records']['access']['scope_ref']['sha256']+'.json')
    original=path.read_bytes();write(path,original+b' ')
    with pytest.raises(case.NativeCaseError,match='reference_bytes'):
        case._check_context(context)
    write(path,original)
    path=world['installed_root']/'contracts/market_memory/e0_native_bindings.v3.schema.json';original=path.read_bytes()
    try:
        write(path,original+b'\n',False)
        with pytest.raises(case.owner.E0InstalledControlError,match='installed_source_changed'):
            case._check_context(context)
    finally:write(path,original,False)


def test_context_mutation_and_unissued_objects_refuse(native_world):
    context=resolve(native_world)
    with pytest.raises(case.NativeCaseError):case._check_context({})
    with pytest.raises(case.NativeCaseError):copy.copy(context)
    original=context._body
    try:
        object.__setattr__(context,'_body',original+b' ')
        with pytest.raises(case.NativeCaseError):case._check_context(context)
    finally:object.__setattr__(context,'_body',original)


@pytest.mark.parametrize('operation,intent', [
    (True,INTENT),('bad/path',INTENT),('original-operation',{}),
    ('original-operation',{**INTENT,'role':'reviewer'}),
    ('original-operation',{**INTENT,'participant_binding_sha256':True}),
    ('original-operation',{**INTENT,'child_run_id':'child\n'}),
])
def test_request_validation_before_peer_or_native_metadata(operation,intent,monkeypatch):
    def forbidden():pytest.fail('invalid request reached peer/control/source')
    monkeypatch.setattr(case,'_peer_owner',forbidden)
    with pytest.raises(case.NativeCaseError):
        case._resolve_current_case(None,operation_id=operation,intent=intent)


def test_unissued_context_has_stable_refusal_before_native_metadata(monkeypatch):
    def forbidden():pytest.fail('unissued context reached peer/control/source')
    monkeypatch.setattr(case,'_peer_owner',forbidden)
    for value in ({},None,object(),object.__new__(case.NativeE0CaseContext)):
        with pytest.raises(case.NativeCaseError,match='owner_native_case_(?:factory_)?required'):
            case._check_context(value)



def test_qualification_has_no_source_acquisition_or_store_status(native_world,monkeypatch):
    def forbidden(*a,**k):pytest.fail('qualification reached source acquisition/store')
    monkeypatch.setattr(case.trusted.TrustedFileAsKnownAtReader,'read_pinned_generation',forbidden)
    monkeypatch.setattr(case.cohort,'read_retained_context_cohort',forbidden)
    monkeypatch.setattr(case,'_reservation_store',forbidden)
    monkeypatch.setattr(case.ReservationStore,'_locked',forbidden)
    context=resolve(native_world)
    metadata=case._current_case_binding(context)
    assert metadata['recipient_grant_ref']['sha256']==native_world['records']['access']['scope_ref']['sha256']
    assert not {'task','condition','slot','input','locator','source_cards','original_recipient'} & metadata.keys()


def test_revocation_after_real_source_io_withholds(native_world,monkeypatch):
    world=native_world;context=resolve(world)
    original=case.trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    called=[]
    def revoke_after_original(*args,**kwargs):
        result=original(*args,**kwargs);called.append(True)
        access=world['records']['access'];access['status']='revoked'
        world['selected']['control_refs']['access']=retain(world['directory'],access,'access_state_id')
        write(world['directory']/'SELECTED.json',canonical(world['selected']))
        return result
    monkeypatch.setattr(case.trusted.TrustedFileAsKnownAtReader,'read_pinned_capture_projections',revoke_after_original)
    before=inventory(world['store'].directory)
    with pytest.raises((case.NativeCaseError,case.cohort.RetainedContextAccessError)):
        case._build_case_input(context)
    assert called and inventory(world['store'].directory)==before



def test_original_service_recipient_fact_joins_exact_original_intent(native_world):
    context=resolve(native_world);original=case._original_case_intent(context)
    fact=case._original_recipient_fact(context,original_intent=original)
    assert fact=={'schema':'research_factory.market_memory_e0_original_recipient.v3',
        'recipient_kind':'native_broker_service','principal_ref':native_world['recipient']['service_ref'],
        'ssh_key_fingerprint':native_world['service']['ssh_key_fingerprint'],
        'original_operation_id':'original-operation',
        'pre_input_intent_sha256':sha256(canonical(INTENT)).hexdigest()}
    changed=copy.deepcopy(original);changed['binding']['recipient']['original_recipient']['principal_ref']=ref('wrong-audience')
    with pytest.raises(case.NativeCaseError,match='original_native_case_intent_mismatch'):
        case._original_recipient_fact(context,original_intent=changed)



def test_source_rights_change_withholds_existing_case_before_source_payload(native_world,monkeypatch):
    context=resolve(native_world);path=native_world['source_config'];original=path.read_bytes()
    value=json.loads(original);value['revoked_capture_ids']=[native_world['task']['capture_id']]
    def forbidden(*a,**k):pytest.fail('revoked source rights reached source payload')
    monkeypatch.setattr(case.cohort,'read_retained_context_cohort',forbidden)
    try:
        write(path,canonical(value),False)
        with pytest.raises(case.NativeCaseError,match='native_source_scope_or_method_mismatch'):
            case._build_case_input(context)
    finally:write(path,original,False)



def test_second_resolution_cannot_mix_rebound_native_grant_metadata(native_world,monkeypatch):
    world=native_world;context=resolve(world);original=case._resolve_current_case;calls=[]
    def observe_actual_resolution(*args,**kwargs):
        current=original(*args,**kwargs);calls.append(True)
        if len(calls)==1:
            recipient=copy.deepcopy(world['recipient']);recipient['slot']=(recipient['slot']+1)%3
            world['records']['access']['scope_ref']=retain(world['directory'],recipient)
            world['selected']['control_refs']['access']=retain(world['directory'],world['records']['access'],'access_state_id')
            write(world['directory']/'SELECTED.json',canonical(world['selected']))
        return current
    monkeypatch.setattr(case,'_resolve_current_case',observe_actual_resolution)
    with pytest.raises(case.NativeCaseError,match='native_case_changed_during_binding'):
        case._current_case_binding(context)
    assert len(calls)==2



def test_factory_issuance_clone_and_selection_integrity_before_private_reads(native_world,monkeypatch):
    context=resolve(native_world)
    fields=('_body','_digest','_inputs','_peer','_peer_binding','_selection','_seal')
    clone=object.__new__(case.NativeE0CaseContext)
    for name in fields:object.__setattr__(clone,name,getattr(context,name))
    def forbidden():pytest.fail('unissued or mutated context reached peer/control/source')
    monkeypatch.setattr(case,'_peer_owner',forbidden)
    with pytest.raises(case.NativeCaseError,match='factory_required'):case._check_context(clone)
    with pytest.raises(case.NativeCaseError,match='factory_required'):
        case.NativeE0CaseContext(context._body,context._inputs,context._peer,context._peer_binding,
                                context._selection,_key=context._seal)
    for name in fields:
        original=getattr(context,name)
        replacement=(original+b' ') if type(original) is bytes else ('0'*64 if name=='_digest'
            else tuple(list(original)+[b'changed']) if name=='_inputs' else object())
        try:
            object.__setattr__(context,name,replacement)
            with pytest.raises(case.NativeCaseError,match='issued_state_changed'):
                case._check_context(context)
        finally:object.__setattr__(context,name,original)


@pytest.mark.parametrize('existing_git',['directory','gitfile'])
def test_fixture_rejects_existing_git_without_replacement(tmp_path,existing_git):
    root=tmp_path/'native-install';root.mkdir()
    git=root/'.git'
    if existing_git=='directory':git.mkdir();(git/'HEAD').write_bytes(b'ref: refs/heads/do-not-touch\n')
    else:git.write_bytes(b'gitdir: /explicit/not-a-target\n')
    before=inventory(root)
    with pytest.raises(AssertionError,match='never overwrite'):
        native_object_database(root,(),temporary_parent=tmp_path)
    assert inventory(root)==before
    with pytest.raises(AssertionError,match='fresh before writes'):_assert_fresh_install(root,tmp_path)


def test_fixture_setup_failure_preserves_original_source_and_git(tmp_path,monkeypatch):
    before=source_guard_snapshot();called=[]
    def failure(root):
        assert root!=SOURCE_ROOT and root.parent==tmp_path
        write(root/use.REGISTRATION,b'explicit temporary setup failure only',False)
        called.append(True);raise RuntimeError('explicit setup failure')
    with pytest.raises(RuntimeError,match='explicit setup failure'):
        with isolated_install(tmp_path,monkeypatch,after_copy=failure):pytest.fail('must not yield')
    assert called and source_guard_snapshot()==before
