"""Offline guards for replacing one existing dated GEX object, never discovery."""
import hashlib
import json
from copy import deepcopy

import pytest

from engine.options_exposure_projection import encode_projection_cells
from scripts import repair_gex_history as repair

KEY = 'options_hub/gex_history/SPY/2026-10-16.json'
ETAG = '"639d57f8e9c055db5ad2a47d29b67950"'


@pytest.fixture
def artifact(tmp_path):
    metric = dict(expected=2, received=2, qualified=2, missing=0,
                  status='complete_observed', net=0, gross=2, known_net=0,
                  known_gross=2, qualified_population_id='synthetic', call=1,
                  put=-1, exclusions={})
    cell = dict(expiry='2026-10-23', economic_expiry_at='2026-10-23T20:00:00Z',
                strike=100, population_id='synthetic',
                gamma=metric, vanna=metric, charm=metric,
                joint=dict(expected=2, received=2, qualified=2, missing=0,
                           population_id='synthetic', model_ref='synthetic', complete=True))
    projection = dict(schema='options_hub.exposure_projection/v2', root='SPY',
                      clocks={'source_session': '2026-10-16'}, cell_count=1,
                      cells_status='complete', **encode_projection_cells([cell]))
    payload = dict(schema='options_hub.gex/v1', root='SPY', asof='2026-10-16',
                   by_strike=[{'strike': 100, 'gex_bn': 0}], exposure_projection=projection)
    body = json.dumps(payload, indent=2).encode()
    path = tmp_path / 'native.json'; path.write_bytes(body)
    binding = dict(schema='options_hub.gex_archive_correction/v1', root='SPY',
                   session='2026-10-16', key=KEY, bucket='synthetic-bucket', expected_etag=ETAG,
                   input_sha256=hashlib.sha256(body).hexdigest(), input_bytes=len(body),
                   expected_existing_sha256='a' * 64)
    return path, body, payload, binding


class Client:
    def __init__(self, response=None, error=None):
        self.calls = []; self.error = error
        self.response = response if response is not None else {
            'ResponseMetadata': {'HTTPStatusCode': 200, 'RetryAttempts': 0}, 'ETag': '"new"'}
    def put_object(self, **kwargs):
        self.calls.append(kwargs)
        if self.error: raise self.error
        return self.response
    def __getattr__(self, name):
        raise AssertionError('unexpected storage method: ' + name)


class ServiceError(Exception):
    def __init__(self, status, code):
        self.response = {'Error': {'Code': code, 'Message': 'SECRET_SENTINEL'},
                         'ResponseMetadata': {'HTTPStatusCode': status}}
        super().__init__('SECRET_SENTINEL')


def invoke(artifact, client=None, **kwargs):
    path, _, _, binding = artifact
    return repair.correct_archive_artifact(path, binding, apply=True,
            client_factory=lambda: client, bucket='synthetic-bucket', **kwargs)


def test_conditional_write_uses_bound_bytes_once_and_never_index(artifact):
    client = Client(); result = invoke(artifact, client)
    assert client.calls == [dict(Bucket='synthetic-bucket', Key=KEY, Body=artifact[1],
                                ContentType='application/json', IfMatch=ETAG)]
    assert result['status'] == 'acknowledged' and result['wrapper_invocations'] == 1
    assert result['remote_bytes_equal'] is None and result['physical_attempts'] is None


@pytest.mark.parametrize('field,value', [
    ('schema','other'), ('bucket','invalid/bucket'), ('root','QQQ'), ('root','../SPY'), ('session','2026-02-30'),
    ('key','options_hub/gex/SPY.json'), ('key','options_hub/gex_history/SPY/dates.json'),
    ('input_sha256','b'*64), ('input_bytes',1), ('input_bytes',True),
    ('input_bytes',9*1024*1024), ('expected_etag',''), ('expected_etag','*'),
    ('expected_etag','W/"weak"'), ('expected_etag','"a", "b"'),
    ('expected_etag','"a\r\nb"'), ('expected_existing_sha256','bad'),
])
def test_invalid_binding_refuses_before_client(artifact, field, value):
    path, _, _, binding = artifact; binding[field] = value
    def forbidden(): raise AssertionError('client constructed')
    result = repair.correct_archive_artifact(path, binding, apply=True, client_factory=forbidden)
    assert result['status'] == 'not_attempted' and result['wrapper_invocations'] == 0


@pytest.mark.parametrize('mutation', ['root', 'asof', 'projection', 'cells', 'truncated', 'schema', 'duplicate', 'nan'])
def test_wrong_native_document_refuses_even_when_hash_matches(artifact, mutation):
    path, _, payload, binding = artifact; d = deepcopy(payload)
    if mutation in ('root','asof','schema'): d[mutation] = 'wrong'
    elif mutation == 'projection': del d['exposure_projection']
    elif mutation == 'cells': d['exposure_projection']['cells'] = []
    elif mutation == 'truncated': d['exposure_projection']['cells_status'] = 'payload_limit'
    body = json.dumps(d).encode()
    if mutation == 'duplicate': body = b'{"root":"SPY",' + body[1:]
    if mutation == 'nan': body = body[:-1] + b',"bad":NaN}'
    path.write_bytes(body); binding.update(input_bytes=len(body), input_sha256=hashlib.sha256(body).hexdigest())
    client = Client(); result = invoke(artifact, client)
    assert result['status'] == 'not_attempted' and client.calls == []


@pytest.mark.parametrize('error,status', [
    (ServiceError(412,'PreconditionFailed'),'conflict'), (ServiceError(404,'NoSuchKey'),'conflict'),
    (TimeoutError('SECRET_SENTINEL'),'unknown'), (ServiceError(403,'AccessDenied'),'denied'),
])
def test_conflict_denial_or_ambiguity_never_retries(artifact, error, status):
    client = Client(error=error); result = invoke(artifact, client)
    assert result['status'] == status and len(client.calls) == 1
    assert result['remote_bytes_equal'] is None and 'SECRET_SENTINEL' not in json.dumps(result)


@pytest.mark.parametrize('response', [{}, {'ResponseMetadata': {'HTTPStatusCode': 204}},
                                      {'ResponseMetadata': {'HTTPStatusCode': True}}])
def test_malformed_ack_is_unknown_not_success(artifact, response):
    client = Client(response=response); result = invoke(artifact, client)
    assert result['status'] == 'unknown' and len(client.calls) == 1


def test_bytes_are_not_reread_after_client_creation(artifact):
    path, body, _, binding = artifact; client = Client()
    def factory(): path.write_bytes(b'changed-after-validation'); return client
    result = repair.correct_archive_artifact(path, binding, apply=True,
        client_factory=factory, bucket='synthetic-bucket')
    assert result['status'] == 'acknowledged' and client.calls[0]['Body'] == body


def test_cli_dry_run_never_constructs_client_and_never_recomputes(artifact, monkeypatch, capsys):
    path, _, _, binding = artifact
    bp=path.with_name('binding.json'); bp.write_text(json.dumps(binding))
    def forbidden(*a, **kw): raise AssertionError('unexpected legacy/client path')
    from scripts import build_options_hub_nightly as hub
    monkeypatch.setattr(hub, '_r2_client', forbidden)
    monkeypatch.setattr(repair, 'repair_root', forbidden)
    monkeypatch.setattr(hub, 'load_exposure_contexts', forbidden)
    assert repair.main(['--correct-artifact',str(path),'--correction-binding',str(bp)]) == 0
    result=json.loads(capsys.readouterr().out)
    assert result['status']=='prepared' and result['wrapper_invocations']==0


@pytest.mark.parametrize('extra', [['--apply'], ['--publish'], ['--apply','--publish','--roots','SPY']])
def test_cli_rejects_ambiguous_or_mixed_mode(artifact, extra):
    path, _, _, binding = artifact; bp=path.with_name('binding.json'); bp.write_text(json.dumps(binding))
    with pytest.raises(SystemExit):
        repair.main(['--correct-artifact',str(path),'--correction-binding',str(bp),*extra])


@pytest.mark.parametrize('field', ['schema','root','session','key','bucket','expected_etag',
                                  'input_sha256','input_bytes','expected_existing_sha256'])
def test_missing_binding_field_is_not_attempted(artifact, field):
    artifact[3].pop(field); client=Client()
    result=invoke(artifact,client)
    assert result['status']=='not_attempted' and client.calls==[]


def test_bucket_mismatch_stops_before_client_construction(artifact):
    path, _, _, binding=artifact
    def forbidden(): raise AssertionError('wrong destination client')
    result=repair.correct_archive_artifact(path,binding,apply=True,
        bucket='another-bucket',client_factory=forbidden)
    assert result['status']=='not_attempted' and result['reason']=='bucket_mismatch'


def test_transport_guard_cannot_strip_projection_for_correction(artifact, monkeypatch):
    from engine import options_exposure_projection as exposure
    monkeypatch.setattr(exposure,'fit_gex_transport',lambda p:(True,{**p,'exposure_projection':{}}))
    client=Client(); result=invoke(artifact,client)
    assert result['reason']=='whole_envelope_transport_refused' and client.calls==[]


def test_client_unavailable_is_not_attempted(artifact):
    result=invoke(artifact,None)
    assert result['status']=='not_attempted' and result['wrapper_invocations']==0


@pytest.mark.parametrize('error,expected_exit', [(None,0),(ServiceError(412,'PreconditionFailed'),1),
                                               (TimeoutError('private'),1)])
def test_opt_in_cli_exit_and_no_legacy_or_index_work(artifact, monkeypatch, capsys,error,expected_exit):
    from scripts import build_options_hub_nightly as hub
    path, _, _, binding=artifact; bp=path.with_name('binding.json');bp.write_text(json.dumps(binding))
    client=Client(error=error)
    def forbidden(*a,**kw):raise AssertionError('legacy/index path invoked')
    monkeypatch.setenv('R2_BUCKET','synthetic-bucket')
    monkeypatch.setattr(hub,'_r2_client',lambda:client)
    monkeypatch.setattr(hub,'load_exposure_contexts',forbidden)
    monkeypatch.setattr(hub,'publish_gex_history_index',forbidden)
    monkeypatch.setattr(repair,'repair_root',forbidden)
    assert repair.main(['--correct-artifact',str(path),'--correction-binding',str(bp),
                        '--apply','--publish'])==expected_exit
    result=json.loads(capsys.readouterr().out)
    assert result['wrapper_invocations']==1 and len(client.calls)==1
