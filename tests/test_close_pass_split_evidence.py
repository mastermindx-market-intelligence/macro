"""Synthetic HTTP → CorpActions → durable kernel → pinned-reader contract."""
from __future__ import annotations

import copy
import io
import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from engine.close_pass import massive_close as MC
from engine.close_pass import massive_split_evidence as S


class Response(io.BytesIO):
    def __init__(self, body, code=200):
        super().__init__(body)
        self.code = code


def event(event_id="event-1", **changes):
    value = dict(id=event_id, ticker="SPY", execution_date="2026-01-02", split_from=1, split_to=2, adjustment_type="forward_split")
    value.update(changes)
    return value


def page(rows=(), **changes):
    value = {"status": "OK", "results": list(rows)}
    value.update(changes)
    return json.dumps(value).encode()


@pytest.fixture(autouse=True)
def forbid_live(monkeypatch):
    monkeypatch.setattr(MC, "api_key", lambda: "SYNTHETIC_SECRET")
    def forbidden(*args, **kwargs):
        raise AssertionError("provider transport forbidden")
    monkeypatch.setattr(S, "_open_split_request", forbidden)


@pytest.fixture
def root(tmp_path):
    return tmp_path / S.ROOT_LEAF


def inject(monkeypatch, *responses):
    pending = iter(responses)
    requests = []
    def fetch(request):
        requests.append(request)
        response = next(pending)
        if isinstance(response, BaseException):
            raise response
        return Response(response) if isinstance(response, bytes) else response
    monkeypatch.setattr(S, "_open_split_request", fetch)
    return requests


def acquire(monkeypatch, *responses):
    inject(monkeypatch, *responses)
    return S.acquire_split_history("SPY", "2025-01-01", "2026-01-01")


def retain(monkeypatch, root, *responses):
    inject(monkeypatch, *responses)
    return S.retain_split_history("SPY", "2025-01-01", "2026-01-01", store_root=root)


def files(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}


def test_exact_numeric_lexemes_real_path_and_read_clock(monkeypatch, root):
    body = b'{"status":"OK","results":[{"id":"native-1","ticker":"SPY","execution_date":"2026-01-02","split_from":1.00000000000000000001,"split_to":2e+0,"adjustment_type":"forward_split","historical_adjustment_factor":5.00000000000000000000e-1,"unknown":"SYNTHETIC_SECRET"}]}'
    stored = retain(monkeypatch, root, body)
    reader = S.SplitEvidenceReader(root)
    before = S.time.time_ns()
    snap = reader.read(stored.receipt["receipt_id"])
    after = S.time.time_ns()
    assert snap.artifact == stored.artifact
    row = snap.artifact['rows'][0]
    assert row['split_from'] == '1.00000000000000000001'
    assert row['split_to'] == '2e+0'
    assert row['historical_adjustment_factor'] == '5.00000000000000000000e-1'
    assert row['execution_date'] > snap.artifact['request']['basis_date']
    assert row['page_index'] == row['row_index'] == 0
    p = snap.artifact['pages'][0]
    assert p['observed_body_sha256'] == sha256(body).hexdigest()
    assert p['body_bytes_observed'] == len(body) and p['body_complete']
    assert stored.artifact['completed_utc_ns'] <= stored.receipt['owner_intake_started_utc_ns'] <= stored.receipt['owner_receipt_assembled_utc_ns']
    assert before <= snap.read_receipt['read_started_utc_ns'] <= snap.read_receipt['read_completed_utc_ns'] <= after
    assert snap.read_receipt['generation_id'] == stored.generation_id
    assert not snap.artifact['basis_eligible'] and not snap.read_receipt['basis_eligible']
    assert snap.artifact['authority'] == S.AUTHORITY
    assert not any(b'SYNTHETIC_SECRET' in b for b in files(root).values())


def test_valid_cursor_page_and_sanitized_scope(monkeypatch, root):
    next_url = S.ENDPOINT + '?cursor=opaque_cursor==&apiKey=BODY_SECRET'
    calls = inject(monkeypatch, page([event()], next_url=next_url), page([event('event-2', execution_date='2026-01-03')]))
    stored = S.retain_split_history('SPY', '2025-01-01', '2026-01-01', store_root=root)
    assert stored.artifact['status'] == 'complete' and len(stored.artifact['rows']) == 2
    assert len(calls) == 2
    assert parse_qs(urlsplit(calls[0].full_url).query) == {'ticker':['SPY'],'execution_date.gte':['2025-01-01'],'sort':['execution_date.asc'],'limit':['1000']}
    assert parse_qs(urlsplit(calls[1].full_url).query) == {'cursor':['opaque_cursor==']}
    assert calls[1].get_header('Authorization') == 'Bearer SYNTHETIC_SECRET'
    assert not any(b'BODY_SECRET' in b or b'opaque_cursor' in b for b in files(root).values())


@pytest.mark.parametrize('suffix', [
    '?cursor=x&ticker=QQQ', '?cursor=x&sort=execution_date.desc',
    '?cursor=x&execution_date.gte=2024-01-01', '?cursor=x&limit=5000',
    '?cursor=x&cursor=x', '?cursor=x&adjusted=true', '?apiKey=x',
    '?cursor=x#fragment', '?cursor=%0A', '?cursor=x&order=asc',
])
def test_pagination_scope_refuses_before_second_request(monkeypatch, root, suffix):
    calls = inject(monkeypatch, page([event()], next_url=S.ENDPOINT + suffix))
    stored = S.retain_split_history('SPY','2025-01-01','2026-01-01',store_root=root)
    assert len(calls) == 1
    assert stored.artifact['status'] == 'partial' and stored.artifact['failure_kind'] == 'pagination'
    assert S.SplitEvidenceReader(root).read(stored.receipt['receipt_id']).artifact == stored.artifact


@pytest.mark.parametrize('url', ['https://evil.example/stocks/v1/splits?cursor=x','https://api.massive.com/stocks/v2/splits?cursor=x','http://api.massive.com/stocks/v1/splits?cursor=x','https://api.massive.com:443/stocks/v1/splits?cursor=x','https://secret@api.massive.com/stocks/v1/splits?cursor=x'])
def test_pagination_host_path_refuses(monkeypatch, url):
    a = acquire(monkeypatch, page([], next_url=url))
    assert a['failure_kind'] == 'pagination' and a['status'] == 'failed'


def test_empty_and_later_failure_are_distinct_and_recoverable(monkeypatch, root):
    empty = retain(monkeypatch, root, page())
    partial = retain(monkeypatch, root, page([event()],next_url=S.ENDPOINT+'?cursor=x'), urllib.error.URLError('SYNTHETIC_SECRET'))
    failed = retain(monkeypatch, root, urllib.error.URLError('SYNTHETIC_SECRET'))
    recovery = retain(monkeypatch, root, page([event()]))
    reader = S.SplitEvidenceReader(root)
    for stored, status in [(empty,'complete'),(partial,'partial'),(failed,'failed'),(recovery,'complete')]:
        snap = reader.read(stored.receipt['receipt_id'])
        assert snap.artifact['status'] == status
    assert empty.artifact['rows'] == [] and empty.artifact['pages'][0]['rows_received'] == 0
    assert partial.artifact['pages'][1]['observed_body_sha256'] is None
    assert partial.artifact['pages'][1]['outcome'] == 'transport'
    assert len(reader.receipts()) == 4


@pytest.mark.parametrize('body,reason', [
    (b'{}','response_status'), (b'{"status":"OK"}','results_missing'),
    (b'{"status":"OK","results":null}','results_missing'),
    (b'{"status":"OK","results":[],"status":"OK"}','malformed_json'),
    (b'{"status":"OK","results":[],"metadata":{"a":1,"a":2}}','malformed_json'),
    (b'{"status":"OK","results":[],"metadata":NaN}','malformed_json'),
    (b'\xff','malformed_json'), (b'not json','malformed_json'),
    (b'{"status":"DELAYED","results":[]}','response_status'),
    (b'{"status":"OK","ticker":"spy","results":[]}','response_identity'),
    (b'{"status":"OK","results":[],"next_url":null}','pagination'),
])
def test_malformed_never_complete_but_persisted(monkeypatch, root, body, reason):
    stored = retain(monkeypatch, root, body)
    snap = S.SplitEvidenceReader(root).read(stored.receipt['receipt_id'])
    assert snap.artifact['failure_kind'] == reason and snap.artifact['status'] == 'failed'
    assert snap.artifact['pages'][0]['observed_body_sha256'] == sha256(body).hexdigest()


@pytest.mark.parametrize('changes', [dict(id=None),dict(id=''),dict(split_from=0),dict(split_to=-1),dict(split_to=None),dict(split_from='1'),dict(split_to=True),dict(adjustment_type='unknown'),dict(adjustment_type=[]),dict(historical_adjustment_factor=None),dict(execution_date='2026-02-30')])
def test_invalid_event_fields_refuse(monkeypatch, root, changes):
    s = retain(monkeypatch, root, page([event(**changes)]))
    assert s.artifact['failure_kind'] == 'malformed_row'
    assert S.SplitEvidenceReader(root).read(s.receipt['receipt_id']).artifact['rows'] == []


@pytest.mark.parametrize('changes', [dict(ticker='spy'),dict(ticker='QQQ'),dict(execution_date='2024-01-01')])
def test_event_identity_refuses(monkeypatch, changes):
    assert acquire(monkeypatch,page([event(**changes)]))['failure_kind'] == 'response_identity'


@pytest.mark.parametrize('second', [event(), event(split_to=3)])
def test_duplicate_or_conflicting_native_id_refuses(monkeypatch, root, second):
    s = retain(monkeypatch,root,page([event()],next_url=S.ENDPOINT+'?cursor=x'),page([second]))
    assert s.artifact['failure_kind'] == 'duplicate_id' and len(s.artifact['rows']) == 1
    assert s.artifact['pages'][1]['rows_received'] == 1


def test_aba_reclassification_omission_immutable_and_old_pin(monkeypatch, root):
    a = retain(monkeypatch,root,page([event()]))
    pinned = S.SplitEvidenceReader(root,generation_id=a.generation_id)
    old = pinned.read(a.receipt['receipt_id'])
    immutable = files(root)
    b = retain(monkeypatch,root,page([event(split_to=3, adjustment_type='stock_dividend')]))
    c = retain(monkeypatch,root,page([event()]))
    omitted = retain(monkeypatch,root,page())
    assert len({x.receipt['capture_id'] for x in [a,b,c,omitted]}) == 4
    assert a.artifact['rows'] == c.artifact['rows'] and a.receipt['artifact_sha256'] != c.receipt['artifact_sha256']
    replay = pinned.read(a.receipt['receipt_id'])
    assert replay.artifact == old.artifact and replay.owner_receipt == old.owner_receipt
    assert replay.read_receipt['generation_id'] == a.generation_id
    with pytest.raises(S.K.SourceNotFound): pinned.read(b.receipt['receipt_id'])
    for path, body in immutable.items():
        if path != 'SOURCE_HEAD.json': assert (root/path).read_bytes() == body
    assert len(S.SplitEvidenceReader(root).receipts()) == 4


def test_same_identity_replay_and_conflict(monkeypatch, root):
    a = retain(monkeypatch,root,page([event()]))
    before = files(root)
    replay = S.intake_split_acquisition(a.artifact,store_root=root)
    assert not replay.created and files(root) == before
    changed = copy.deepcopy(a.artifact)
    changed['rows'][0]['split_to'] = '3'
    S._seal(changed)
    with pytest.raises(S.SplitEvidenceError,match='acquisition_id_conflict'):
        S.intake_split_acquisition(changed,store_root=root)
    assert files(root) == before


@pytest.mark.parametrize('bound', ['_MAX_OBJECT_BYTES','_MAX_RECEIPT_BYTES','_MAX_GENERATION_BYTES','_MAX_GENERATION_RECEIPTS'])
def test_capacity_does_not_change_prior_bytes(monkeypatch, root, bound):
    retain(monkeypatch,root,page([event()]))
    new = acquire(monkeypatch,page([event('new')]))
    before = files(root)
    # Keep the existing objects readable when testing envelope capacities.
    limit = {'_MAX_OBJECT_BYTES':len(S.K._canonical_bytes(new))-1,'_MAX_RECEIPT_BYTES':1,'_MAX_GENERATION_BYTES':len(next(v for k,v in before.items() if k.endswith('.json') and b'previous_generation_id' in v and b'event' not in v)),'_MAX_GENERATION_RECEIPTS':1}[bound]
    if bound == '_MAX_GENERATION_BYTES':
        limit = max(len(v) for k,v in before.items() if 'source_generations/' in k)
    monkeypatch.setattr(S.K,bound,limit)
    with pytest.raises((S.SplitEvidenceError,S.K.SourceStoreError)):
        S.intake_split_acquisition(new,store_root=root)
    assert files(root) == before


def test_failed_head_publish_orphan_recovery_and_conflict(monkeypatch, root):
    a = retain(monkeypatch,root,page([event()]))
    b = acquire(monkeypatch,page([event('b')]))
    old_head = S.K._head_path(root).read_bytes()
    replace = S.K.os.replace
    def fail(source, destination):
        if Path(destination) == S.K._head_path(root):
            raise OSError("injected publication failure")
        return replace(source, destination)
    monkeypatch.setattr(S.K.os,"replace",fail)
    with pytest.raises(S.K.SourceStoreError,match="cannot advance source HEAD"):
        S.intake_split_acquisition(b,store_root=root)
    assert S.K._head_path(root).read_bytes() == old_head
    assert len(S.SplitEvidenceReader(root).receipts()) == 1
    changed = copy.deepcopy(b);changed['rows'][0]['split_to']='9';S._seal(changed)
    with pytest.raises(S.SplitEvidenceError,match='conflict'):
        S.intake_split_acquisition(changed,store_root=root)
    monkeypatch.setattr(S.K.os,'replace',replace)
    result = S.intake_split_acquisition(b,store_root=root)
    assert len(S.SplitEvidenceReader(root).receipts()) == 2
    assert S.SplitEvidenceReader(root).read(result.receipt['receipt_id']).artifact == b


def test_concurrent_updates_serialized_without_lost_attempt(monkeypatch, root):
    acquisitions = [acquire(monkeypatch,page([event(str(i))])) for i in range(8)]
    barrier = threading.Barrier(8)
    def write(a):
        barrier.wait()
        return S.intake_split_acquisition(a,store_root=root)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(write,acquisitions))
    reader = S.SplitEvidenceReader(root)
    assert len(reader.receipts()) == 8
    for result in results:
        assert reader.read(result.receipt['receipt_id']).artifact == result.artifact


def test_response_and_page_and_row_bounds(monkeypatch, root):
    oversized = retain(monkeypatch,root,b'x'*(S.MAX_RESPONSE_BYTES+2))
    p = oversized.artifact['pages'][0]
    assert p['outcome'] == 'response_capacity' and p['body_bytes_observed'] == S.MAX_RESPONSE_BYTES+1 and not p['body_complete']
    repeated = acquire(monkeypatch,page([],next_url=S.ENDPOINT+'?cursor=x'),page([],next_url=S.ENDPOINT+'?cursor=x'))
    assert repeated['failure_kind'] == 'repeated_cursor'
    eight = acquire(monkeypatch,*[page([],next_url=S.ENDPOINT+f'?cursor=x{i}') for i in range(8)])
    assert len(eight['pages']) == 8 and eight['failure_kind'] == 'page_capacity'
    monkeypatch.setattr(S,'MAX_ROWS',2)
    rows = retain(monkeypatch,root,page([event(str(i)) for i in range(3)]))
    assert rows.artifact['failure_kind'] == 'row_capacity' and len(rows.artifact['rows']) == 2


def test_partial_body_read_retains_observed_prefix(monkeypatch, root):
    class Broken(Response):
        def read(self,n):
            if self.tell(): raise OSError('SYNTHETIC_SECRET')
            return super().read(3)
    s = retain(monkeypatch,root,Broken(b'abcdef'))
    p = s.artifact['pages'][0]
    assert p['observed_body_sha256'] == sha256(b'abc').hexdigest() and p['body_bytes_observed'] == 3
    assert p['outcome'] == 'transport' and not p['body_complete']


@pytest.mark.parametrize('location',[S.ENDPOINT+'?ticker=QQQ','https://evil.example/splits'])
def test_standard_urllib_redirect_not_followed(monkeypatch,root,location):
    calls=[]
    class SyntheticHTTPS(urllib.request.HTTPSHandler):
        def https_open(self,req):
            from email.message import Message
            headers=Message();headers['Location']=location
            calls.append(req.full_url)
            response=urllib.response.addinfourl(io.BytesIO(b'no secret retention'),headers,req.full_url,302)
            response.msg='Found'
            return response
    opener=urllib.request.build_opener(S._NoRedirect(),SyntheticHTTPS())
    monkeypatch.setattr(S,'_open_split_request',lambda req: opener.open(req,timeout=30))
    stored=S.retain_split_history('SPY','2025-01-01','2026-01-01',store_root=root)
    assert len(calls)==1 and stored.artifact['failure_kind']=='redirect'
    assert stored.artifact['rows']==[]


def test_implementation_errors_are_not_hidden(monkeypatch):
    def fail(req): raise RuntimeError('implementation defect')
    monkeypatch.setattr(S,'_open_split_request',fail)
    with pytest.raises(RuntimeError,match='implementation defect'):
        S.acquire_split_history('SPY','2025-01-01','2026-01-01')


def test_nanosecond_precision_without_caller_clock(monkeypatch,root):
    base=1_800_000_000_000_000_001
    ticks=iter(range(base,base+100))
    monkeypatch.setattr(S.time,'time_ns',lambda:next(ticks))
    result=retain(monkeypatch,root,page())
    snapshot=S.SplitEvidenceReader(root).read(result.receipt['receipt_id'])
    assert result.artifact['started_utc_ns']==base
    assert result.artifact['pages'][0]['request_started_utc_ns']==base+1
    assert snapshot.read_receipt['read_completed_utc_ns'] > result.receipt['owner_receipt_assembled_utc_ns']
    assert snapshot.read_receipt['read_completed_utc_ns'] % 1000 != 0


def test_private_namespace_and_opt_in_default_unchanged(monkeypatch,tmp_path):
    with pytest.raises(S.K.SourceStoreError,match='dedicated private family'):
        S.retain_split_history('SPY','2025-01-01','2026-01-01',store_root=tmp_path/'other')
    assert MC.DEFAULT_BASE_URL=='https://api.polygon.io' and MC.SPLITS_PATH=='/v3/reference/splits'
    paths=[]
    def old_fetch(path,params):
        paths.append(path);return {'status':'OK','results':[]}
    assert MC.corp_action_tickers('2026-01-02',fetch=old_fetch).complete
    assert paths == [MC.SPLITS_PATH,MC.DIVIDENDS_PATH]


def test_registry_declares_only_proposed_source():
    from lib.dataos.registry import load_registry
    row=load_registry().get('reference.corporate_actions.massive_split_evidence')
    assert row.status.value=='PROPOSED'


@pytest.mark.parametrize("mutation", [
    lambda a: a['pages'][0].update(rows_retained=0),
    lambda a: a['pages'][0].update(response_completed_utc_ns=a['completed_utc_ns']+1),
    lambda a: a['pages'][0].update(outcome=[]),
    lambda a: a.update(failure_kind=[]),
    lambda a: a['rows'][0].update(extra='unreviewed'),
    lambda a: a.update(basis_eligible=True),
])
def test_resealed_inconsistent_acquisitions_refuse_before_store(monkeypatch,root,mutation):
    a=acquire(monkeypatch,page([event()]))
    mutation(a);S._seal(a)
    with pytest.raises(S.SplitEvidenceError):
        S.intake_split_acquisition(a,store_root=root)
    assert not root.exists()


def test_opt_in_owner_entry_runs_actual_path(monkeypatch,root):
    inject(monkeypatch,page([event()]))
    stored=MC.retain_split_history('SPY','2025-01-01','2026-01-01',store_root=root)
    assert S.SplitEvidenceReader(root).read(stored.receipt['receipt_id']).artifact['status']=='complete'


def test_seal_and_stored_object_tamper_fail(monkeypatch,root):
    acquired=acquire(monkeypatch,page([event()]))
    bad=copy.deepcopy(acquired);bad['rows'][0]['split_to']='9'
    with pytest.raises(S.SplitEvidenceError,match='seal_mismatch'):
        S.intake_split_acquisition(bad,store_root=root)
    stored=S.intake_split_acquisition(acquired,store_root=root)
    p=S.K._object_path(root,stored.receipt['artifact_sha256'])
    changed=copy.deepcopy(acquired);changed['rows'][0]['split_to']='9';S._seal(changed)
    p.write_bytes(S.K._canonical_bytes(changed))
    with pytest.raises(S.K.SourceStoreError,match='object hash mismatch'):
        S.SplitEvidenceReader(root).read(stored.receipt['receipt_id'])


def test_declared_invariants_allowed_on_next_page(monkeypatch):
    url=S.ENDPOINT+'?cursor=ok&ticker=SPY&execution_date.gte=2025-01-01&sort=execution_date.asc&limit=1000'
    a=acquire(monkeypatch,page([],next_url=url),page())
    assert a['status']=='complete' and len(a['pages'])==2


def test_intake_rejects_future_without_backdating(monkeypatch,root):
    a=acquire(monkeypatch,page())
    monkeypatch.setattr(S.time,'time_ns',lambda:a['completed_utc_ns']-1)
    with pytest.raises(S.SplitEvidenceError,match='future_acquisition'):
        S.intake_split_acquisition(a,store_root=root)
    assert not root.exists()


def framed_response(body, *, mode='length', missing=0):
    import http.client
    class Socket:
        def makefile(self, mode):
            return io.BytesIO(wire)
    if mode == 'length':
        wire = b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)+missing).encode() + b'\r\n\r\n' + body
    else:
        wire = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n' + format(len(body),'x').encode() + b'\r\n' + body + b'\r\n'
        if mode == 'chunked':
            wire += b'0\r\n\r\n'
    response = http.client.HTTPResponse(Socket())
    response.begin()
    return response


@pytest.mark.parametrize('mode,missing', [('length',10),('truncated_chunked',0)])
def test_real_http_framing_failure_is_retained_not_complete(monkeypatch, root, mode, missing):
    body = page()
    stored = retain(monkeypatch,root,framed_response(body,mode=mode,missing=missing))
    snapshot = S.SplitEvidenceReader(root).read(stored.receipt['receipt_id'])
    assert snapshot.artifact['status'] == 'failed'
    assert snapshot.artifact['failure_kind'] == 'http_framing'
    p = snapshot.artifact['pages'][0]
    assert p['body_complete'] is False and p['rows_received'] is None
    assert p['body_bytes_observed'] == len(body)
    assert p['observed_body_sha256'] == sha256(body).hexdigest()
    assert snapshot.artifact['rows'] == []


@pytest.mark.parametrize('mode', ['length','chunked'])
def test_real_http_complete_framing_positive(monkeypatch, root, mode):
    body = page([event()])
    stored = retain(monkeypatch,root,framed_response(body,mode=mode))
    snapshot = S.SplitEvidenceReader(root).read(stored.receipt['receipt_id'])
    assert snapshot.artifact['status'] == 'complete'
    p = snapshot.artifact['pages'][0]
    assert p['body_complete'] is True and p['body_bytes_observed'] == len(body)
    assert p['observed_body_sha256'] == sha256(body).hexdigest()
    assert len(snapshot.artifact['rows']) == 1


@pytest.mark.parametrize('location', ['row','top'])
def test_numeric_ticker_token_is_not_a_string_identity(monkeypatch,root,location):
    row = event(ticker=1234 if location=='row' else '1234')
    body = page([row],**({'ticker':1234} if location=='top' else {}))
    inject(monkeypatch,body)
    stored = S.retain_split_history('1234','2025-01-01','2026-01-01',store_root=root)
    snap = S.SplitEvidenceReader(root).read(stored.receipt['receipt_id'])
    assert snap.artifact['status']=='failed' and snap.artifact['failure_kind']=='response_identity'
    assert snap.artifact['rows']==[]


def test_string_numeric_spelling_ticker_remains_valid(monkeypatch,root):
    body=b'{"status":"OK","ticker":"1234","results":[{"id":"native","ticker":"1234","execution_date":"2026-01-02","split_from":1.00000000000000000001,"split_to":2e+0,"adjustment_type":"forward_split"}]}'
    inject(monkeypatch,body)
    stored=S.retain_split_history('1234','2025-01-01','2026-01-01',store_root=root)
    assert stored.artifact['status']=='complete'
    assert stored.artifact['rows'][0]['split_from']=='1.00000000000000000001'
    assert stored.artifact['rows'][0]['split_to']=='2e+0'


def test_http_exception_before_response_retains_fixed_failure(monkeypatch,root):
    import http.client
    stored=retain(monkeypatch,root,http.client.BadStatusLine('SYNTHETIC_SECRET'))
    snap=S.SplitEvidenceReader(root).read(stored.receipt['receipt_id'])
    assert snap.artifact['failure_kind']=='http_framing'
    p=snap.artifact['pages'][0]
    assert p['http_status'] is None and p['observed_body_sha256'] is None and p['body_complete'] is False
    assert not any(b'SYNTHETIC_SECRET' in b for b in files(root).values())


def test_later_page_framing_failure_retains_prior_rows_and_failed_page(monkeypatch,root):
    body=page([event('second')])
    stored=retain(monkeypatch,root,page([event()],next_url=S.ENDPOINT+'?cursor=next'),framed_response(body,missing=10))
    snap=S.SplitEvidenceReader(root).read(stored.receipt['receipt_id'])
    assert snap.artifact['status']=='partial' and snap.artifact['failure_kind']=='http_framing'
    assert len(snap.artifact['rows'])==1 and len(snap.artifact['pages'])==2
    assert snap.artifact['pages'][1]['observed_body_sha256']==sha256(body).hexdigest()


def test_incomplete_read_prefix_remains_bounded(monkeypatch,root):
    import http.client
    class Interrupted(Response):
        def read(self,n):
            raise http.client.IncompleteRead(b'x'*n,10)
    stored=retain(monkeypatch,root,Interrupted(b''))
    p=stored.artifact['pages'][0]
    assert stored.artifact['failure_kind']=='http_framing'
    assert p['body_bytes_observed']==65536 and p['body_complete'] is False
    assert p['observed_body_sha256']==sha256(b'x'*65536).hexdigest()


def test_unrelated_valueerror_still_propagates(monkeypatch):
    def fail(req): raise ValueError('implementation defect')
    monkeypatch.setattr(S,'_open_split_request',fail)
    with pytest.raises(ValueError,match='implementation defect'):
        S.acquire_split_history('SPY','2025-01-01','2026-01-01')
