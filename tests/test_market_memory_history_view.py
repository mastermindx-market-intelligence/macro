"""A private browser projection is not a public or PIT archive admission."""
import base64
import gzip
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import re
import pytest
from tests.test_market_memory_history_archive import request,fake_reader

NAME='engine.neuralweb.market_memory_history_view'

def module():
    assert importlib.util.find_spec(NAME) is not None,'private history browser exporter is not implemented'
    return importlib.import_module(NAME)

def archive(monkeypatch,tmp_path):
    from engine.neuralweb import market_memory_history_archive as ar
    monkeypatch.setattr(ar,'read_research_history',fake_reader)
    root=tmp_path/'archive'; receipt=ar.write_archive(ar.assemble_history(request()),root)
    return root,receipt

def test_browser_export_exists():
    assert callable(module().export_browser)

def test_default_browser_export_contains_no_outcomes(monkeypatch,tmp_path):
    root,r=archive(monkeypatch,tmp_path); dest=tmp_path/'history.html'
    result=module().export_browser(root,dest,expected_manifest_sha256=r['manifest_sha256'])
    html=dest.read_text()
    assert result['html_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest()
    assert 'id="mmh-data"' in html
    assert 'id="mmh-outcomes-data"' not in html
    assert 'connect-src' in html and "'none'" in html
    payload=re.search(r'<script id="mmh-data"[^>]*>([^<]+)</script>',html).group(1)
    data=json.loads(gzip.decompress(base64.b64decode(payload)))
    assert data['manifest_sha256']==r['manifest_sha256']
    assert len(data['rows'])==10
    assert not any(c.startswith('forward_') for c in data['columns'])
    assert 'RETROSPECTIVE_EXPLORATORY' in html

def test_explicit_outcomes_export_is_separate(monkeypatch,tmp_path):
    root,r=archive(monkeypatch,tmp_path); dest=tmp_path/'study.html'
    module().export_browser(root,dest,expected_manifest_sha256=r['manifest_sha256'],include_outcomes=True)
    html=dest.read_text()
    assert 'id="mmh-outcomes-data"' in html
    assert 'id="mmh-outcomes" hidden' in html

def test_export_preserves_source_and_refuses_clobber(monkeypatch,tmp_path):
    root,r=archive(monkeypatch,tmp_path); before=(root/'manifest.json').read_bytes()
    dest=tmp_path/'history.html'; m=module()
    m.export_browser(root,dest,expected_manifest_sha256=r['manifest_sha256'])
    assert (root/'manifest.json').read_bytes()==before
    with pytest.raises(FileExistsError): m.export_browser(root,dest,expected_manifest_sha256=r['manifest_sha256'])

def test_default_export_does_not_read_outcomes(monkeypatch,tmp_path):
    root,r=archive(monkeypatch,tmp_path)
    for p in root.glob('outcomes-*.parquet'): p.unlink()
    module().export_browser(root,tmp_path/'history.html',expected_manifest_sha256=r['manifest_sha256'])
    with pytest.raises(ValueError):
        module().export_browser(root,tmp_path/'invalid.html',expected_manifest_sha256=r['manifest_sha256'],include_outcomes=True)

def test_corrupt_source_does_not_emit_browser(monkeypatch,tmp_path):
    root,r=archive(monkeypatch,tmp_path)
    next(root.glob('states-*.parquet')).write_bytes(b'broken')
    dest=tmp_path/'history.html'
    with pytest.raises(ValueError): module().export_browser(root,dest,expected_manifest_sha256=r['manifest_sha256'])
    assert not dest.exists()

def test_macro_projection_requires_exact_paired_source_digest(monkeypatch,tmp_path):
    from tests.test_market_memory_history_macro import packet
    from engine.neuralweb.market_memory_history_macro import build_macro_chronology,write_macro_chronology
    root,r=archive(monkeypatch,tmp_path)
    c=build_macro_chronology(packet(),start='2020-01-01',end='2020-03-31')
    path=tmp_path/'macro.json';mr=write_macro_chronology(c,path)
    dest=tmp_path/'history.html'
    result=module().export_browser(root,dest,expected_manifest_sha256=r['manifest_sha256'],macro_path=path,expected_macro_sha256=mr['sha256'])
    assert result['macro_events']==2 and result['macro_sha256']==mr['sha256']
    html=dest.read_text();assert 'id="mmh-macro-data"' in html and 'Macro first prints' in html
    assert 'id="mmh-benchmark-heading"' in html
    with pytest.raises(ValueError):
        module().export_browser(root,tmp_path/'bad.html',expected_manifest_sha256=r['manifest_sha256'],macro_path=path)
