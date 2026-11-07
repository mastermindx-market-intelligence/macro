"""Hermetic public-admission/transport/activation checks; no economic rebuild.

Retained five-field data are reprojected ONLY into an explicitly synthetic test
publication under the current source policy. This does not requalify the old
fixture generation, acquire inputs or assert current/served data authenticity.
"""
from copy import deepcopy
from hashlib import sha256
import gzip
import io
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import publish_r2 as publisher
from scripts import render_intl_durable as durable
from lib import intl_generation_publication as admission
from lib import config
from tests.intl_investigation_page_fixture import page_fixture, FIXTURE, render

REAL_ROOT = config.ROOT
REAL_SETTINGS = deepcopy(config.load())


def controlled_contract():
    from lib.intl_generation_publication import _assess
    from scripts.build_intl import _native_policy_document_sha256
    _, contract, _ = page_fixture()
    contract = deepcopy(contract)
    contract['generation'] = 'im-workspace-generation:11111111-2222-4333-8444-555555555555'
    contract['policy_points_ref'] = None
    for sid, e in contract['measures'].items():
        decision = e['native_evidence']['publication_decision']
        if decision:
            decision['decision_ref'] = contract['generation'] + ':' + sid
            digest = _native_policy_document_sha256({sid: decision})[sid]
            m, ev, content, qual, policy = _assess(sid, e['native_measure'], e['native_evidence'], contract['generation'], digest)
            contract['measures'][sid] = dict(native_measure=m, native_evidence=ev,
                content_identity=content, qualification_identity=qual, policy_identity=policy['policy_identity'])
            contract['policies'][sid] = policy
    return contract


def install_public_fixture(root, monkeypatch):
    from lib.intl_generation_publication import publish_generation
    # Actual configured policy sections/source config, not ready JSON input.
    settings = deepcopy(REAL_SETTINGS)
    (root/'docs').mkdir(exist_ok=True)
    (root/'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md').write_bytes(
        (REAL_ROOT/'docs/INTERNATIONAL_MACRO_DATA_CONTRACT.md').read_bytes())
    contract = controlled_contract()
    monkeypatch.setattr(config, 'ROOT', root)
    monkeypatch.setattr(config, 'load', lambda: settings)
    monkeypatch.setattr(config, 'data_dir', lambda: root/'data')
    (root/'data').mkdir(exist_ok=True)
    descriptor = publish_generation(data_root=root/'data', contract=contract)
    feeds = root/'site/feeds'; feeds.mkdir(parents=True, exist_ok=True)
    for path in (root/'data/intl/publication/generations').iterdir():
        (feeds/path.name).write_bytes(path.read_bytes())
    return contract, descriptor


class FakeClient:
    def __init__(self, public):
        self.public = public; self.puts = []; self.fail = None
        self.meta = SimpleNamespace(
            service_model=SimpleNamespace(operation_model=lambda _: SimpleNamespace(
                http={'method':'PUT','requestUri':'/{Bucket}/{Key+}'},
                input_shape=SimpleNamespace(members={key: SimpleNamespace(serialization={'location':'header','name':header})
                    for key,header in [('IfMatch','If-Match'),('IfNoneMatch','If-None-Match')]}))),
            config=SimpleNamespace(retries={'total_max_attempts':1}))
    def get_object(self, **kw):
        if kw['Key'] not in self.public:
            error = RuntimeError('not copied')
            error.response = {'Error': {'Code':'NoSuchKey'}}
            raise error
        return {'Body':io.BytesIO(self.public[kw['Key']]),'ETag':'"'+sha256(self.public[kw['Key']]).hexdigest()+'"'}
    def put_object(self, **kw):
        self.puts.append(kw)
        if self.fail: raise self.fail
        if (kw.get('IfNoneMatch') == '*' and kw['Key'] in self.public) or (
            'IfMatch' in kw and kw['IfMatch'] != '"'+sha256(self.public.get(kw['Key'], b'')).hexdigest()+'"'):
            error=RuntimeError('conditional');error.response={'ResponseMetadata':{'HTTPStatusCode':412}};raise error
        self.public[kw['Key']] = kw['Body']
        return {'ResponseMetadata':{'HTTPStatusCode':200}}


@pytest.fixture
def delivery(tmp_path, monkeypatch):
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, 'version', lambda key: '1.43.126')
    contract, descriptor = install_public_fixture(tmp_path, monkeypatch)
    public = {}; client = FakeClient(public)
    monkeypatch.setenv('R2_BUCKET', 'controlled-public-only')
    monkeypatch.setenv('R2_ENDPOINT', 'https://'+'0'*32+'.r2.cloudflarestorage.com')
    monkeypatch.setattr(publisher, '_client', lambda *a, **k: client)
    reads = []
    def get(origin, name, limit, *, absent=False):
        assert origin == publisher._INTL_ORIGIN
        reads.append(name)
        raw = public.get('feeds/' + name)
        if raw is None and not absent: raise publisher.IntlPublicationError('controlled missing public body')
        return raw
    monkeypatch.setattr(publisher, '_intl_public_get', get)
    state = {}; checkpoints=[]
    target=publisher._capture_intl_target()
    def run(**kw):
        return publisher._publish_intl(authorize=lambda:durable.intl_public_objects(descriptor),
            state=state, checkpoint=lambda: checkpoints.append(deepcopy(state)),
            fence=kw.get('fence', lambda: None), target=target)
    return SimpleNamespace(root=tmp_path,contract=contract,descriptor=descriptor,public=public,
        client=client,state=state,run=run,checkpoints=checkpoints,reads=reads,target=target)


def test_exact_public_finite_closure_no_manifest_or_private_siblings(delivery):
    t=delivery
    (t.root/'site/feeds/private.json').write_text('{"private":"never upload"}')
    t.public['feeds/_manifest.json']=b'incumbent full manifest'
    t.run()
    assert t.state['state']=='verified'
    assert t.state['spec']['fields']==sorted(admission._INTL_PUBLIC)
    assert [p['Key'] for p in t.client.puts][-1]=='feeds/intl_generation_current.json'
    assert all(p['IfNoneMatch']=='*' for p in t.client.puts)
    assert len(t.client.puts)==3 and len(t.public)==4
    assert t.public['feeds/_manifest.json']==b'incumbent full manifest'
    assert 'feeds/private.json' not in t.public
    assert t.reads[-1]=='intl_generation_current.json'
    assert [s['state'] for s in t.checkpoints].count('put_inflight')==3
    with pytest.raises(publisher.IntlPublicationError,match='no replay'):t.run()
    assert len(t.client.puts)==3


def test_ambiguous_put_sticky_even_if_old_payload_was_identical(delivery):
    t=delivery
    t.client.fail=TimeoutError('do not copy this arbitrary text')
    with pytest.raises(publisher.IntlPublicationUnknown,match='unknown'):t.run()
    assert t.state['state']=='unknown' and len(t.client.puts)==1
    t.client.fail=None
    with pytest.raises(publisher.IntlPublicationError,match='no replay'):t.run()
    assert len(t.client.puts)==1
    assert t.checkpoints[-1]['state']=='unknown'


@pytest.mark.parametrize('failure',['credentials','conditional','ack','readback','fence','public_current','bucket_current'])
def test_failures_never_supply_activation_proof(delivery,monkeypatch,failure):
    t=delivery;kw={}
    if failure=='credentials':
        monkeypatch.setattr(publisher,'_client',lambda *a,**k:None)
        with pytest.raises(publisher.IntlPublicationError):publisher._capture_intl_target()
        assert t.client.puts==[]
        return
    elif failure=='conditional':
        e=RuntimeError();e.response={'ResponseMetadata':{'HTTPStatusCode':412}};t.client.fail=e
    elif failure=='ack':monkeypatch.setattr(t.client,'put_object',lambda **kw:{})
    elif failure=='readback':
        monkeypatch.setattr(publisher,'_intl_public_get',lambda *a,**k:None if k.get('absent') else b'corrupt')
    elif failure=='fence':kw['fence']=lambda:(_ for _ in ()).throw(publisher.IntlPublicationError('drift'))
    elif failure=='public_current':t.public['feeds/intl_generation_current.json']=b'newer selector'
    else:
        monkeypatch.setattr(t.client,'get_object',lambda **kw:{'Body':io.BytesIO(b'foreign'),'ETag':'"old"'})
    with pytest.raises(publisher.IntlPublicationError):t.run(**kw)
    with pytest.raises(publisher.IntlPublicationError):durable.verify_intl_publication(t.descriptor,t.state)
    assert t.state['state']!='verified'
    if failure in {'credentials','fence','public_current','bucket_current'}:assert t.client.puts==[]
    if failure=='conditional':assert t.state['state']=='refused'
    if failure=='ack':assert t.state['state']=='unknown'


def test_current_selector_conditional_existing_preimage(delivery):
    t=delivery;t.public['feeds/intl_generation_current.json']=b'old controlled selector'
    t.target.clear();t.target.update(publisher._capture_intl_target())
    t.run()
    assert t.client.puts[-1]['IfMatch']=='"'+sha256(b'old controlled selector').hexdigest()+'"'
    assert 'IfNoneMatch' not in t.client.puts[-1]


def test_local_consumed_input_drift_and_remote_newer_current_refuse(delivery):
    t=delivery;t.run()
    t.public['feeds/intl_generation_current.json']=b'newer'
    with pytest.raises(publisher.IntlPublicationError):durable.verify_intl_publication(t.descriptor,t.state)
    name=t.descriptor['artifact_name']
    t.public['feeds/intl_generation_current.json']=(t.root/'site/feeds/intl_generation_current.json').read_bytes()
    (t.root/'site/feeds'/name).write_bytes(b'drift')
    with pytest.raises(publisher.IntlPublicationError):durable.verify_intl_publication(t.descriptor,t.state)


@pytest.mark.parametrize('change',['extra','private_source','held_value','period','clock','config_denied','origin'])
def test_serialized_disclosure_refuses_before_any_write_capability(delivery,monkeypatch,change):
    from lib.intl_generation_publication import publish_generation
    t=delivery;c=deepcopy(t.contract)
    if change=='extra':c['private']='secret not to upload'
    elif change=='private_source':c['measures']['GB.policy_rate']['native_measure']['source_reference']='https://private.invalid/customer'
    elif change=='held_value':c['measures']['JP.yield_10y']['native_measure']['value']=123
    elif change=='period':c['measures']['EZ.gdp_yoy']['native_measure']['period']['start']='private text'
    elif change=='clock':c['measures']['GB.policy_rate']['native_evidence']['clocks']['requested_at']='private arbitrary text'
    elif change=='config_denied':config.load()['intl']['field_publication']['GB.policy_rate']['status']='unknown'
    else:config.load()['r2_data_plane']['public_base']='https://foreign.invalid'
    # Re-sign a well-shaped hostile input with the actual pure owner. Integrity
    # hashes alone are not a public-disclosure policy.
    if change in {'private_source','clock'}:
        from lib.intl_generation_publication import _assess
        e=c['measures']['GB.policy_rate'];policy=c['policies']['GB.policy_rate']
        m,ev,content,qual,p=_assess('GB.policy_rate',e['native_measure'],e['native_evidence'],
                                   c['generation'],policy['policy_document_sha256'])
        c['measures']['GB.policy_rate']=dict(native_measure=m,native_evidence=ev,
            content_identity=content,qualification_identity=qual,policy_identity=p['policy_identity'])
    acquired=[];monkeypatch.setattr(publisher,'_client',lambda *a,**k:acquired.append(True))
    try:
        descriptor=publish_generation(data_root=t.root/'data',contract=c)
        for p in (t.root/'data/intl/publication/generations').iterdir():(t.root/'site/feeds'/p.name).write_bytes(p.read_bytes())
        publisher._publish_intl(authorize=lambda:durable.intl_public_objects(descriptor),state={},checkpoint=lambda:None,fence=lambda:None,target=t.target)
    except (ValueError,KeyError):pass
    else:pytest.fail('unadmitted serialized disclosure accepted')
    assert acquired==[]


@pytest.mark.parametrize('status,kind,encoding,body',[
    (302,'application/json',None,b'{}'),(401,'application/json',None,b'{}'),
    (200,'text/html',None,b'<html>'),(200,'application/json','br',b'{}'),
    (200,'application/json','gzip',b'bad'),(200,'application/json',None,b'x'*100),
    (200,'application/json','gzip',gzip.compress(b'x'*100)),
])
def test_public_read_transport_rejects_wrong_responses(monkeypatch,status,kind,encoding,body):
    import http.client
    calls=[]
    class Response:
        def __init__(self):self.status=status
        def getheader(self,key):return {'Content-Type':kind,'Content-Encoding':encoding}.get(key)
        def read(self,n):return body[:n]
    class Connection:
        def __init__(self,host,timeout):assert host=='pub-f7ffb4441c5f4ad983ca56ec7c651c61.r2.dev'
        def request(self,*a,**k):calls.append((a,k))
        def getresponse(self):return Response()
        def close(self):pass
    monkeypatch.setattr(http.client,'HTTPSConnection',Connection)
    with pytest.raises(publisher.IntlPublicationError):publisher._intl_public_get(publisher._INTL_ORIGIN,'intl_generation_current.json',10)
    assert len(calls)==1


def test_decoded_identity_matches_consumer_and_trailing_gzip_refuses(monkeypatch):
    raw=b'{"controlled":"decoded response"}'
    assert publisher._intl_decode(gzip.compress(raw),'gzip',len(raw))==raw
    assert publisher._intl_decode(raw,'identity',len(raw))==raw
    for bad in (gzip.compress(raw)+b'extra',gzip.compress(raw)[:-2]):
        with pytest.raises(publisher.IntlPublicationError):publisher._intl_decode(bad,'gzip',len(raw))


@pytest.mark.parametrize('change',['missing-header','wrong-header','sdk-retries','wrong-method'])
def test_installed_transport_model_guard_refuses_before_put(delivery, change):
    t=delivery
    operation=t.client.meta.service_model.operation_model('PutObject')
    if change=='missing-header':operation.input_shape.members.pop('IfMatch')
    elif change=='wrong-header':operation.input_shape.members['IfMatch'].serialization['name']='X-Other'
    elif change=='sdk-retries':t.client.meta.config.retries['total_max_attempts']=2
    else:operation.http['method']='POST'
    t.client.meta.service_model.operation_model=lambda _:operation
    with pytest.raises(publisher.IntlPublicationError, match='transport'):t.run()
    assert t.client.puts==[]


def test_actual_same_vm_default_unavailable_then_bound_public_activation(delivery, monkeypatch):
    from scripts import build_intl
    from tests.test_intl_investigation_page_adapter import Links
    from lib.intl_investigation_action import build_intl_investigation_action
    from urllib.parse import parse_qs,urlsplit
    t=delivery;ws,_,_=page_fixture()
    for panel in ws['macros']+ws['risks']:
        panel['generation']=t.contract['generation']
        for sid,old in list(panel['investigation_actions'].items()):
            panel['investigation_actions'][sid]=build_intl_investigation_action(
                contract=t.contract,descriptor=t.descriptor,context_id=old['context_id'],selected_measure_ids=[sid],
                return_url=parse_qs(urlsplit(old['href']).query)['intl_return'][0])
    original=deepcopy(ws)
    class Template:
        def render(self,**vm):return render(vm['intl_workspace'])
    vm={'intl_workspace':ws, 'built':'controlled-original-calculation-clock'}
    writes=[]
    def write(path,html):path.write_text(html);writes.append(path.name)
    monkeypatch.setattr(build_intl,'write_page',write)
    build_intl._write_intl_pages(Template(),build_intl._action_unavailable_vm(vm),catalogue=None,chart_sources=None,site=t.root/'site')
    default=(t.root/'site/intl.html').read_text()
    assert Links(default).actions==[]
    assert 'Unavailable for this snapshot' in default and '此快照暂不可用' in default
    assert ws==original and vm['built']=='controlled-original-calculation-clock'
    activate=build_intl._page_activation(Template(),vm,catalogue=None,chart_sources=None,site=t.root/'site',descriptor=t.descriptor)
    with pytest.raises(publisher.IntlPublicationError):activate({'state':'verified'})
    assert writes==['intl.html','intl_stocks.html']
    t.run();pages=activate(t.state)
    actions=Links((t.root/'site/intl.html').read_text()).actions
    assert {a['data-im-investigation-field'] for a in actions}==set(admission._INTL_PUBLIC)
    assert {a['data-im-investigation-generation'] for a in actions}=={t.contract['generation']}
    assert all(sha256((t.root/p).read_bytes()).hexdigest()==h for p,h in pages.items())
    assert ws==original and vm['built']=='controlled-original-calculation-clock'
    t.public['feeds/intl_generation_current.json']=b'changed'
    with pytest.raises(publisher.IntlPublicationError):activate(t.state)
    assert len(writes)==4


def test_default_main_wiring_uses_unavailable_copy_and_only_private_same_call_continuation():
    import ast,inspect
    from scripts import build_intl
    tree=ast.parse(inspect.getsource(build_intl.main))
    writes=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='_write_intl_pages']
    assert len(writes)==1
    assert isinstance(writes[0].args[1],ast.Call) and writes[0].args[1].func.id=='_action_unavailable_vm'
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='activate_pages' for n in ast.walk(tree))


def test_checkpoint_failure_precedes_any_put(delivery):
    t=delivery
    with pytest.raises(OSError):publisher._publish_intl(authorize=lambda:durable.intl_public_objects(t.descriptor),
        state={},checkpoint=lambda:(_ for _ in ()).throw(OSError('controlled checkpoint failed')),
        fence=lambda:None,target=t.target)
    assert t.client.puts==[]


def add_points(t, change=None):
    """Explicitly synthetic typed point companion, using its actual pure owner."""
    from lib.intl_policy_publication import build_policy_points,publish_policy_points,MAPPING_POLICY
    from lib.intl_generation_publication import publish_generation
    from scripts.build_intl import _native_policy_document_sha256
    from lib.intl_ecb_policy_publication import SOURCE_URL
    receipt={'requested_at':'2026-11-04T00:00:00Z','response_received_at':'2026-11-04T00:00:01Z',
        'input_verified_at':'2026-11-04T00:00:02Z','committed_at':'2026-11-04T00:00:03Z',
        'provider_published_at':None,'revision_vintage':None}
    ecb={'status':'ready','receipt_sha256':'1'*64,'receipt':{**receipt,'source_url':SOURCE_URL},
        'parsed':{'observations':[{'date':'2026-11-04','value':2.5,'status':'observed',
                                  'source_status_raw':'A','source_confidentiality_raw':'F'}]}}
    boe={'status':'ready','receipt_sha256':'2'*64,'receipt':{**receipt,
        'source_url':t.contract['measures']['GB.policy_rate']['native_measure']['source_reference'].partition('#')[0],
        'rows':[{'date':'2026-11-02','value':3.75,'status':'observed','source_updated_raw':'2026-11-02 00:00:00'}]}}
    doc=_native_policy_document_sha256({'mapping':{'owner_ref':'scripts/build_intl.py','policy_ref':MAPPING_POLICY}})['mapping']
    points=build_policy_points(generation=t.contract['generation'],ecb=ecb,boe=boe,policies=t.contract['policies'],
        mapping_policy=config.load()['intl']['policy_comparison_publication'],mapping_document_sha256=doc,evaluated_at='2026-11-04T00:00:04Z')
    assert points is not None
    if change:change(points)
    t.contract['policy_points_ref']=publish_policy_points(data_root=t.root/'data',contract=points)
    t.descriptor.clear();t.descriptor.update(publish_generation(data_root=t.root/'data',contract=t.contract))
    for path in (t.root/'data/intl/publication/generations').iterdir():(t.root/'site/feeds'/path.name).write_bytes(path.read_bytes())
    return points


def test_policy_points_exact_public_companion_precedes_generation(delivery):
    t=delivery;add_points(t);t.run()
    assert len(t.client.puts)==4 and t.client.puts[0]['Key'].startswith('feeds/intl_policy_points_')
    assert t.state['state']=='verified'


@pytest.mark.parametrize('change',['extra','private_source','confidential','nonfinite','clock','mapping'])
def test_resigned_point_companion_not_just_digest_qualifies_public_fields(delivery,change):
    t=delivery
    def mutate(p):
        if change=='extra':p['series']['GB']['private']='secret'
        elif change=='private_source':p['series']['GB']['source_reference']='https://private.invalid/customer'
        elif change=='confidential':p['series']['EZ']['rows'][0]['source_confidentiality_raw']='N'
        elif change=='nonfinite':p['series']['EZ']['rows'][0]['value']=None
        elif change=='clock':p['series']['GB']['clocks']['requested_at']='private arbitrary body'
        else:p['mapping']['metadata']='denied'
    add_points(t,mutate)
    with pytest.raises((ValueError,KeyError)):t.run()
    assert t.client.puts==[] and t.state=={}


def test_actual_incumbent_sdk_serialized_headers_and_retry_config(monkeypatch):
    # This test deliberately requires the declared selected-mode SDK pair.
    # No credential discovery, DNS, request, bucket or metadata service call.
    import boto3,botocore
    assert boto3.__version__=='1.40.0' and botocore.__version__=='1.40.0'
    monkeypatch.setenv('R2_ENDPOINT','https://example.invalid')
    monkeypatch.setenv('R2_ACCESS_KEY_ID','synthetic-no-authority')
    monkeypatch.setenv('R2_SECRET_ACCESS_KEY','synthetic-no-authority')
    selected=publisher._client(1,single_attempt=True)
    binding=publisher._intl_transport_contract(selected)
    assert binding['conditions']==['If-Match','If-None-Match'] and binding['total_max_attempts']==1
    ordinary=publisher._client(1)
    assert ordinary.meta.config.retries=={'total_max_attempts':11,'mode':'adaptive'}


def test_missing_selected_descriptor_never_enters_bulk_publisher(monkeypatch):
    monkeypatch.setattr(publisher,'_client',lambda *a,**k:pytest.fail('no bulk fallback'))
    with pytest.raises(publisher.IntlPublicationError,match='callback'):
        publisher._publish_intl(authorize=None,state={},checkpoint=lambda:None,fence=lambda:None,target=None)


def test_wrong_credential_endpoint_refuses_before_client(delivery,monkeypatch):
    monkeypatch.setenv('R2_ENDPOINT','https://foreign.invalid')
    monkeypatch.setattr(publisher,'_client',lambda *a,**k:pytest.fail('wrong credential destination'))
    with pytest.raises(publisher.IntlPublicationError,match='endpoint'):publisher._capture_intl_target()
    assert delivery.client.puts==[]


@pytest.mark.parametrize('status',[301,307,403,500])
def test_actual_sdk_redirect_and_error_never_resend(monkeypatch,status):
    from botocore.awsrequest import AWSResponse
    monkeypatch.setenv('R2_ENDPOINT','https://example.invalid')
    monkeypatch.setenv('R2_ACCESS_KEY_ID','synthetic-no-authority')
    monkeypatch.setenv('R2_SECRET_ACCESS_KEY','synthetic-no-authority')
    client=publisher._client(1,single_attempt=True);requests=[]
    class Body:
        def stream(self,amt=None):yield b'<Error><Code>AccessDenied</Code></Error>'
    def send(request):
        requests.append((request.method,request.url))
        return AWSResponse(request.url,status,{'x-amz-bucket-region':'us-west-2'},Body())
    monkeypatch.setattr(client._endpoint.http_session,'send',send)
    with pytest.raises(publisher.IntlPublicationError):client.put_object(
        Bucket='controlled-public-only',Key='feeds/intl_generation_current.json',Body=b'{}',IfNoneMatch='*')
    assert len(requests)==1 and requests[0][0]=='PUT'
    assert requests[0][1].startswith('https://example.invalid/')


def test_selected_mode_is_not_exposed_by_incumbent_cli_or_public_api():
    import inspect
    assert 'intl_descriptor' not in inspect.signature(publisher.publish).parameters
    assert 'authorize' not in inspect.signature(publisher.publish).parameters
