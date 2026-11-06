"""Real private owner with explicitly synthetic source bars; no live label reads."""
from dataclasses import replace
import copy
import hashlib
import json

import pytest

from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_technical_store as store
from engine.neuralweb import market_memory_technical_observation as obs
from tests import test_market_memory_technical_store as fixtures


class SyntheticMetadataPolicy:
    policy_id = 'synthetic-test-only.metadata.v1'

    def __init__(self, resource):
        self.resource = resource
        self.calls = []
        self.revoked = False

    def check(self, action, resource):
        assert action in {'read_retained_source_bar_metadata', 'disclose_retained_source_bar_metadata'}
        assert resource == self.resource
        self.calls.append(action)
        if self.revoked:
            raise PermissionError('synthetic revocation')


@pytest.fixture
def retained(tmp_path, monkeypatch):
    root, saved = fixtures._capture(tmp_path, monkeypatch)
    pin = store.pin_technical_actual_output_generation(root)
    source_id = pin.captures[0].source_observation_id
    policy = SyntheticMetadataPolicy({'profile':store.STORE_PROFILE,'store_id':pin.store_id,
        'generation_id':pin.generation_id,'generation_sha256':pin.generation_sha256,
        'source_observation_id':source_id})
    return root,pin,source_id,policy


def _read(values):
    root,pin,source_id,policy = values
    return store.read_retained_source_bar_metadata(root,technical_pin=pin,
        source_observation_id=source_id,policy=policy)


def test_exact_date_projection_never_reads_values_or_feature_body(retained,monkeypatch):
    def forbidden(*args,**kwargs):
        pytest.fail('price-bearing owner path was invoked')
    monkeypatch.setattr(store,'_load_capture',forbidden)
    monkeypatch.setattr(obs,'project_current_spy_raw_close_ratio',forbidden)
    monkeypatch.setattr(obs,'validate_technical_snapshot_bundle',forbidden)
    monkeypatch.setattr(obs,'_read_spy_parquet',forbidden)
    original_json=store._read_json
    def metadata_only(path,**kwargs):
        assert 'feature object' not in kwargs['label']
        return original_json(path,**kwargs)
    monkeypatch.setattr(store,'_read_json',metadata_only)
    original_read=obs.pq.ParquetFile.read
    reads=[]
    def date_only(self,*args,**kwargs):
        assert not args and kwargs == {'columns':['date'],'use_threads':False}
        reads.append(kwargs)
        return original_read(self,**kwargs)
    monkeypatch.setattr(obs.pq.ParquetFile,'read',date_only)
    cap=_read(retained)
    data=store.disclose_retained_source_bar_metadata(cap,policy=retained[3])
    assert data['bar_sessions']==[x.isoformat() for x in fixtures._sessions()]
    assert len(reads)==1 and data['feature_body_read'] is False
    assert data['available_at']=='2026-08-10T02:00:00Z'
    assert data['freshness']['policy'].endswith('max_one_lag.v1')
    assert data['source_observation_id']==retained[2]
    assert not any(key in json.dumps(data) for key in ('start_close','end_close','"state"','object_key','technicals-v1/'))
    assert retained[3].calls == ['read_retained_source_bar_metadata','disclose_retained_source_bar_metadata','disclose_retained_source_bar_metadata']


def test_policy_denial_precedes_private_store_io(retained,monkeypatch):
    retained[3].revoked=True
    monkeypatch.setattr(store,'validate_technical_actual_output_store_root',lambda *_:pytest.fail('private IO before authorization'))
    with pytest.raises(PermissionError): _read(retained)


def test_current_revocation_blocks_previously_qualified_metadata(retained):
    cap=_read(retained); retained[3].revoked=True
    with pytest.raises(PermissionError): store.disclose_retained_source_bar_metadata(cap,policy=retained[3])


@pytest.mark.parametrize('field,value',[('generation_sha256','0'*64),('captures',()),('ancestry_generation_ids',())])
def test_forged_pin_is_reauthenticated(retained,field,value):
    root,pin,sid,policy=retained
    forged=replace(pin,**{field:value})
    if forged == pin: pytest.skip('fixture has the same ancestry')
    policy.resource.update({key:getattr(forged,key) for key in ('store_id','generation_id','generation_sha256')})
    with pytest.raises(store.MarketMemoryTechnicalStoreError): _read((root,forged,sid,policy))


def test_caller_constructed_capability_does_not_grant_disclosure(retained):
    cap=_read(retained)
    with pytest.raises(PermissionError):
        store.disclose_retained_source_bar_metadata(replace(cap,_token=object()),policy=retained[3])


def test_complete_source_object_rebuilt_not_just_identity(retained,monkeypatch):
    original=obs.read_source_bar_metadata
    def altered(inputs):
        value=original(inputs);value['source_observation']['limitations']['unbound_drift']=True
        return value
    monkeypatch.setattr(obs,'read_source_bar_metadata',altered)
    with pytest.raises(store.MarketMemoryTechnicalStoreError,match='full source metadata'):_read(retained)


def test_raw_cas_reads_charge_nested_budget_even_on_hash_failure(tmp_path):
    body=b'bounded raw source';path=tmp_path/'source';path.write_bytes(body)
    with pit.bounded_owner_reads(maximum_bytes=128) as outer:
        with pit.bounded_owner_reads(maximum_bytes=64) as inner:
            with pytest.raises(store.MarketMemoryTechnicalStoreError):
                store._read_raw(path,digest='0'*64,expected_bytes=len(body),limit=32,label='test')
        assert outer.bytes_read==inner.bytes_read==len(body)
        assert outer.objects_opened==inner.objects_opened==1


def test_outer_total_budget_cannot_be_reset_by_metadata_scope(retained):
    with pit.bounded_owner_reads(maximum_bytes=1):
        with pytest.raises(store.MarketMemoryTechnicalStoreError,match='budget'):_read(retained)


@pytest.mark.parametrize('mode',['duplicate','unordered','midday'])
def test_date_only_helper_rejects_noncanonical_dates(mode):
    frame=fixtures._frame();dates=list(frame.index)
    if mode=='duplicate':dates[1]=dates[0]
    elif mode=='unordered':dates[0],dates[1]=dates[1],dates[0]
    else:dates[0]=dates[0]+fixtures.pd.Timedelta(hours=1)
    frame.index=fixtures.pd.DatetimeIndex(dates,name='date')
    # Build input bytes without invoking the rich projector for malformed bars.
    fetcher=fixtures._Fetcher(fixtures._responses(frame=frame))
    inputs=obs.PinnedTechnicalInputs(fetched=obs.fetch_current_spy_daily_inputs(fetcher=fetcher),pinned_sources=fixtures._pinned_sources())
    with pytest.raises(obs.MarketMemoryTechnicalObservationError):obs.read_source_bar_metadata(inputs)


@pytest.mark.parametrize('kind',['body','resource','policy'])
def test_dataclass_clone_cannot_forge_owner_seal(retained,kind):
    cap=_read(retained)
    if kind=='body':
        value=json.loads(cap._body);value['bar_sessions']=['1900-01-01']
        body=pit._canonical_bytes(value)
        forged=replace(cap,_body=body,_body_sha256=hashlib.sha256(body).hexdigest())
    elif kind=='resource':
        value=json.loads(cap._resource);value['source_observation_id']='mmtechsrc_'+'0'*64
        forged=replace(cap,_resource=pit._canonical_bytes(value))
    else:
        retained[3].policy_id='changed-policy'
        forged=replace(cap,_policy_id='changed-policy')
    with pytest.raises(PermissionError):
        store.disclose_retained_source_bar_metadata(forged,policy=retained[3])


def test_numeric_column_statistics_are_never_inspected(retained,monkeypatch):
    original=obs.pq.ParquetFile
    class Column:
        def __init__(self,value):self.value=value
        @property
        def statistics(self):pytest.fail('numeric statistics read')
        def __getattr__(self,name):return getattr(self.value,name)
    class Group:
        def __init__(self,value):self.value=value
        def column(self,index):return Column(self.value.column(index))
        def __getattr__(self,name):return getattr(self.value,name)
    class Metadata:
        def __init__(self,value):self.value=value
        def row_group(self,index):return Group(self.value.row_group(index))
        def __getattr__(self,name):return getattr(self.value,name)
    class Parquet:
        def __init__(self,*args,**kwargs):
            self.value=original(*args,**kwargs);self.metadata=Metadata(self.value.metadata)
        def read(self,**kwargs):
            assert kwargs=={'columns':['date'],'use_threads':False}
            return self.value.read(**kwargs)
        def __getattr__(self,name):return getattr(self.value,name)
    monkeypatch.setattr(obs.pq,'ParquetFile',Parquet)
    assert store.disclose_retained_source_bar_metadata(_read(retained),policy=retained[3])['bar_sessions']


@pytest.mark.parametrize('damage',['tamper','symlink'])
def test_new_metadata_path_authenticates_original_raw_cas(retained,damage,tmp_path):
    root,pin,sid,policy=retained
    receipt,_=store._read_json(store._capture_path(root,pin.captures[0].capture_id),limit=store._MAX_RECEIPT_BYTES,label='test receipt')
    ref=receipt['source_bodies']['spy_daily_parquet'];path=store._source_body_path(root,ref['sha256'])
    if damage=='tamper':path.write_bytes(b'corrupt')
    else:
        target=tmp_path/'replacement';target.write_bytes(path.read_bytes());path.unlink();path.symlink_to(target)
    with pytest.raises(store.MarketMemoryTechnicalStoreError):_read(retained)
