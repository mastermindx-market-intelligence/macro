"""Concrete installed capture with synthetic files/network; no enrollment/live I/O."""
import ast
import dataclasses
from datetime import datetime
from enum import Enum
import hashlib
import io
import json
from pathlib import Path
from email.message import Message

import pandas as pd
import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import options_matrix_runtime as R
from app.options_matrix_http import MatrixHTTPRuntime
from tests.test_options_matrix_delivery import native
from tests.test_options_auth import env
from tests import test_options_matrix_delivery as D
from tests import test_options_matrix_http as H
from tests import test_options_selection_composition as F
from lib.dataos import identity


def plain(value):
    if isinstance(value, Enum): return value.value
    if isinstance(value, dict): return {k: plain(v) for k,v in value.items()}
    if isinstance(value, (tuple, list)): return [plain(v) for v in value]
    return value


@pytest.fixture
def estate(native, tmp_path, monkeypatch):
    x = native
    src = D.source(x, tmp_path)
    registry = {'datasets': [plain(dataclasses.asdict(row)) for row in src.registry.all()]}
    reg = yaml.safe_dump(registry).encode()
    (tmp_path/'config').mkdir()
    (tmp_path/'config/dataset_registry.yml').write_bytes(reg)
    row = dict(source_mode='local_retained', root='SPY', vendor='thetadata',
        dataset_id=src.binding.dataset_id, dataset_version=src.binding.dataset_version,
        source_family=src.binding.source_family,
        inputs={c.role: dict(dataset_id=c.dataset_id, version=c.version) for c in src.inputs},
        required_rights_rationale=dict(src.required_rights_rationale),
        evidence_sha256=src.evidence_sha256, registry_revision=src.registry_revision,
        registry_sha256=hashlib.sha256(reg).hexdigest())
    config = {'options_matrix_display': row, 'r2_data_plane': {'public_base':'https://synthetic.r2.dev'}}
    (tmp_path/'config.yml').write_text(yaml.safe_dump(config))
    path = tmp_path/'data/live_flow_out/options_matrix/history/SPY'/f"{x['ref'].sha256}.json"
    path.parent.mkdir(parents=True); path.write_bytes(x['raw'])
    base = tmp_path/'data/reference'; base.mkdir(parents=True)
    evidence = dict(schema='mastermind.spy_option_root_sources.v1', vendor='thetadata', root='SPY', synthetic=True)
    evidence_raw = (json.dumps(evidence, indent=2, sort_keys=True)+'\n').encode()
    alias = pd.read_parquet(io.BytesIO(x['f']['kwargs']['aliases'].body))
    alias.loc[0,'evidence_sha256'] = hashlib.sha256(evidence_raw).hexdigest()
    a=alias.iloc[0]
    alias.loc[0,'binding_sha256'] = identity.option_root_binding_sha256(
        a.vendor,a.vendor_symbol,a.security_id,a.valid_from,a.valid_to,a.known_at,a.evidence_sha256)
    alias.to_parquet(base/'vendor_aliases.parquet', index=False)
    (base/'security_master.parquet').write_bytes(x['f']['kwargs']['security_master'].body)
    (base/'_receipt.json').write_text(json.dumps({'spy_option_root': evidence}))
    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None): return F.NOW
    monkeypatch.setattr(R, 'datetime', Frozen)
    monkeypatch.setattr('scripts.observe_options_matrix_publication._utc_now', lambda: F.NOW)
    monkeypatch.delenv('R2_PUBLIC_BASE', raising=False)
    return dict(x=x, root=tmp_path, row=row, config=config, path=path)


def save_config(e):
    (e['root']/'config.yml').write_text(yaml.safe_dump(e['config']))


def installed(e):
    # Execute all four exact incumbent Matrix registration+installation statements.
    tree=ast.parse(Path('app/main.py').read_text())
    names={'options_matrix_display_router','install_matrix_display_runtime'}
    nodes=[n for n in tree.body if (isinstance(n,ast.ImportFrom) and n.module in
           {'app.options_matrix_http','app.options_matrix_runtime'}) or
           (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and
            ((isinstance(n.value.func,ast.Name) and n.value.func.id=='install_matrix_display_runtime') or
             (isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='include_router' and
              any(isinstance(a,ast.Name) and a.id in names for a in n.value.args))))]
    assert len(nodes)==4
    app=FastAPI()
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'app/main.py','exec'),{'app':app,'REPO':e['root']})
    assert type(app.state.options_matrix_display_runtime) is MatrixHTTPRuntime
    app.state.options_matrix_display_runtime=dataclasses.replace(app.state.options_matrix_display_runtime,clock=lambda:F.NOW)
    return app


def test_installed_local_capture_native_request_emits_exact(estate,env):
    app=installed(estate)
    response=TestClient(app).post(H.route_url(estate['x']),content=estate['x']['selected'],headers=H.route_headers())
    assert response.status_code==200 and response.content==estate['x']['raw']
    assert env.auth_calls==3 and env.store_calls==1
    assert response.headers['cache-control']=='private, no-store'


def test_install_is_lazy_and_uses_no_files_or_network(monkeypatch,tmp_path):
    monkeypatch.setattr(R, '_regular_bytes', lambda *a,**k: (_ for _ in ()).throw(AssertionError('startup read')))
    app=FastAPI(); R.install_matrix_display_runtime(app,repo=tmp_path)
    assert isinstance(app.state.options_matrix_display_runtime.capture,R.DeployedMatrixCapture)


@pytest.mark.parametrize('defect,code',[
    ('config','configuration_missing:options_matrix_display'),
    ('rights','configuration_missing:required_rights_rationale'),
    ('mode','source_mode_unavailable'),('registry','native_registry_digest_mismatch'),
    ('dataset','native_produced_contracts_unavailable'),('root','identity_scope_unavailable'),
    ('matrix','capture_file_missing:'),('identity','capture_file_missing:vendor_aliases.parquet')])
def test_named_missing_facts_fail_closed(estate,defect,code):
    e=estate
    if defect=='config': e['config'].pop('options_matrix_display')
    if defect=='rights': e['row'].pop('required_rights_rationale')
    if defect=='mode': e['row']['source_mode']='automatic-fallback'
    if defect=='registry': e['row']['registry_sha256']='0'*64
    if defect=='dataset': e['row']['dataset_id']='synthetic.unenrolled'
    if defect=='root': e['row']['root']='QQQ'
    if defect=='matrix': e['path'].unlink()
    if defect=='identity': (e['root']/'data/reference/vendor_aliases.parquet').unlink()
    save_config(e)
    with pytest.raises(R.MatrixCaptureUnavailable,match=code): R.DeployedMatrixCapture(e['root'])(e['x']['ref'])


def test_missing_config_has_named_server_diagnostic_without_browser_detail(estate,env,caplog):
    estate['config'].pop('options_matrix_display');save_config(estate)
    response=TestClient(installed(estate)).post(H.route_url(estate['x']),content=estate['x']['selected'],headers=H.route_headers())
    assert response.status_code==503 and env.auth_calls==1
    assert 'configuration_missing:options_matrix_display' in caplog.text
    assert 'options_matrix_display' not in response.text


@pytest.mark.parametrize('kind',['file_symlink','directory_symlink','fifo','oversize'])
def test_local_reader_refuses_nonregular_or_escaping_paths(tmp_path,kind):
    real=tmp_path/'real';real.mkdir();(real/'file').write_bytes(b'abc')
    rel='real/file'
    if kind=='file_symlink': (tmp_path/'link').symlink_to(real/'file');rel='link'
    if kind=='directory_symlink': (tmp_path/'link').symlink_to(real,target_is_directory=True);rel='link/file'
    if kind=='fifo':
        import os
        os.mkfifo(tmp_path/'pipe');rel='pipe'
    limit=1 if kind=='oversize' else 10
    with pytest.raises(R.MatrixCaptureUnavailable):R._regular_bytes(tmp_path,rel,limit,100,lambda:0)


def test_local_read_elapsed_budget_is_enforced(tmp_path):
    (tmp_path/'file').write_bytes(b'abc')
    ticks=iter([0,0,2])
    with pytest.raises(R.MatrixCaptureUnavailable,match='capture_deadline_exceeded'):
        R._regular_bytes(tmp_path,'file',10,1,lambda:next(ticks))


class Response:
    def __init__(self,raw,url,status=200,headers=None):
        self.raw=io.BytesIO(raw);self.status=status;self.url=url;self.closed=False
        self.headers=Message()
        for k,v in (headers or {'Content-Length':str(len(raw))}).items():self.headers[k]=v
    def geturl(self):return self.url
    def read1(self,n):return self.raw.read(n)
    def __enter__(self):return self
    def __exit__(self,*args):self.closed=True


def test_public_retained_mode_uses_existing_origin_no_credentials_or_fallback(estate,monkeypatch,env):
    e=estate;e['row']['source_mode']='r2_public';save_config(e)
    calls=[];responses=[]
    class Opener:
        def open(self,req,timeout):
            calls.append((req,timeout)); r=Response(e['x']['raw'],req.full_url);responses.append(r);return r
    monkeypatch.setattr(R.urllib.request,'build_opener',lambda *args:Opener())
    # The local history can be absent; explicitly selected R2 is the sole read.
    e['path'].unlink()
    response=TestClient(installed(e)).post(H.route_url(e['x']),content=e['x']['selected'],headers=H.route_headers())
    assert response.status_code==200 and response.content==e['x']['raw']
    assert len(calls)==1 and calls[0][1]==2 and responses[0].closed
    assert calls[0][0].full_url=='https://synthetic.r2.dev/'+e['x']['ref'].key
    assert {k.lower() for k in dict(calls[0][0].header_items())}=={'user-agent','accept-encoding'}


@pytest.mark.parametrize('defect',['redirect','encoding','length','oversize','short','status','deadline'])
def test_public_read_is_bounded_no_redirect_transform_or_recovery(estate,defect):
    ref=estate['x']['ref'];raw=estate['x']['raw'];url='https://synthetic.r2.dev/'+ref.key
    headers={'Content-Length':str(len(raw))}
    if defect=='encoding':headers['Content-Encoding']='gzip'
    if defect=='length':headers['Content-Length']='1'
    r=Response(raw+b'x' if defect=='oversize' else raw[:-1] if defect=='short' else raw,
               'https://other.invalid/' if defect=='redirect' else url,
               status=503 if defect=='status' else 200,headers=headers)
    class Opener:
        def open(self,*args,**kw):return r
    ticks=iter([0,0,2]) if defect=='deadline' else None
    with pytest.raises(R.MatrixCaptureUnavailable):
        R._public_retained('https://synthetic.r2.dev',ref,1,(lambda:next(ticks)) if ticks else (lambda:0),Opener())
    assert r.closed


def test_duplicate_configuration_cannot_override_binding():
    with pytest.raises(R.MatrixCaptureUnavailable,match='configuration_duplicate_key'):
        R._yaml(b'options_matrix_display:\n  vendor: first\n  vendor: second\n')


def test_capture_slots_remain_held_until_actual_late_work_settles(estate, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    capture=R.DeployedMatrixCapture(estate['root'])
    entered=[threading.Event(),threading.Event()];release=threading.Event()
    count=iter(range(2))
    def late(ref):
        entered[next(count)].set()
        assert release.wait(2)
        raise R.MatrixCaptureUnavailable('synthetic_read_failed')
    monkeypatch.setattr(capture,'_capture',late)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures=[executor.submit(capture,estate['x']['ref']) for _ in range(2)]
        try:
            assert all(event.wait(1) for event in entered)
            # HTTP owners may already have left; the actual calls still own slots.
            with pytest.raises(R.MatrixCaptureUnavailable,match='capture_capacity_unavailable'):
                capture(estate['x']['ref'])
        finally:
            release.set()
        for future in futures:
            with pytest.raises(R.MatrixCaptureUnavailable,match='synthetic_read_failed'):future.result()
    monkeypatch.setattr(capture,'_capture',lambda ref:'settled')
    assert capture(estate['x']['ref'])=='settled'
    assert capture(estate['x']['ref'])=='settled'


def test_capture_slots_release_after_missing_configuration(tmp_path):
    (tmp_path/'config.yml').write_text('r2_data_plane: {}\n')
    capture=R.DeployedMatrixCapture(tmp_path)
    for _ in range(3):
        with pytest.raises(R.MatrixCaptureUnavailable,match='configuration_missing:options_matrix_display'):
            capture(F.R.reference_for_bytes('SPY', F.encoded({'schema':F.R.SCHEMA,'root':'SPY','session':'2026-10-12'})))


def test_same_size_file_rewrite_during_read_is_refused(tmp_path,monkeypatch):
    path=tmp_path/'file';path.write_bytes(b'abc')
    original=R.os.read; changed=False
    def rewriting(fd,n):
        nonlocal changed
        value=original(fd,n)
        if not changed:
            changed=True;path.write_bytes(b'xyz')
        return value
    monkeypatch.setattr(R.os,'read',rewriting)
    with pytest.raises(R.MatrixCaptureUnavailable,match='capture_file_changed'):
        R._regular_bytes(tmp_path,'file',10,100,lambda:0)
