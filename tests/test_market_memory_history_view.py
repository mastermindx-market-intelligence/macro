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


def test_asset_reads_are_explicit_utf8(monkeypatch, tmp_path):
    root, receipt = archive(monkeypatch, tmp_path)
    old = Path.read_text
    assets = {'theme.css', 'market_memory_retained.css', 'market_memory_history.css', 'market_memory_history.js'}
    seen = set()
    def checked(path, *args, **kwargs):
        if path.name in assets:
            assert kwargs.get('encoding') == 'utf-8', 'locale-dependent asset decoding'
            seen.add(path.name)
        return old(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'read_text', checked)
    module().export_browser(root, tmp_path / 'utf8.html', expected_manifest_sha256=receipt['manifest_sha256'])
    assert seen == assets


def test_browser_macro_payload_contains_no_revision_end_metadata(monkeypatch, tmp_path):
    from tests.test_market_memory_history_macro import packet
    from engine.neuralweb.market_memory_history_macro import build_macro_chronology, write_macro_chronology
    root, receipt = archive(monkeypatch, tmp_path)
    chronology = build_macro_chronology(packet(), start='2020-01-01', end='2020-03-31')
    source = tmp_path / 'macro.json'
    source_receipt = write_macro_chronology(chronology, source)
    dest = tmp_path / 'no-revision-hindsight.html'
    module().export_browser(root, dest, expected_manifest_sha256=receipt['manifest_sha256'],
        macro_path=source, expected_macro_sha256=source_receipt['sha256'])
    html = dest.read_text(encoding='utf-8')
    encoded = re.search(r'<script id="mmh-macro-data"[^>]*>([^<]+)</script>', html).group(1)
    payload = json.loads(gzip.decompress(base64.b64decode(encoded)))
    assert 'first_vintage_valid_through' not in payload['columns']
    assert payload['metadata']['revision_end_metadata'] == 'withheld_from_daily_projection'
    assert json.loads(source.read_text())['events'][0]['first_vintage_valid_through'] == '2020-03-10'


def test_browser_budget_refusal_preserves_its_specific_reason(monkeypatch, tmp_path):
    root, receipt = archive(monkeypatch, tmp_path)
    manifest = json.loads((root / 'manifest.json').read_text())
    m = module()
    monkeypatch.setattr(m, 'MAX_BROWSER_BYTES', 1)
    with pytest.raises(m.HistoricalExperienceError, match='browser decoded source exceeds budget'):
        m._columnar(root, manifest, 'states', receipt['manifest_sha256'])



def test_browser_embeds_explicit_source_bound_filing_timeline(monkeypatch,tmp_path):
    from tests.test_market_memory_history_filings import payload
    root,receipt=archive(monkeypatch,tmp_path)
    source=tmp_path/'earnings_8k_dates.parquet';raw=payload();source.write_bytes(raw)
    digest=hashlib.sha256(raw).hexdigest();dest=tmp_path/'filings.html'
    result=module().export_browser(root,dest,expected_manifest_sha256=receipt['manifest_sha256'],
        filings_path=source,expected_filings_sha256=digest)
    html=dest.read_text(encoding='utf-8')
    encoded=re.search(r'<script id="mmh-filings-data"[^>]*>([^<]+)</script>',html).group(1)
    data=json.loads(gzip.decompress(base64.b64decode(encoded)))
    assert result['filing_events']==1 and result['filings_sha256']==digest
    assert data['filings_sha256']==digest and data['manifest_sha256']==receipt['manifest_sha256']
    assert len(data['rows'])==1 and data['metadata']['intraday_publication_time_verified'] is False
    assert 'id="mmh-filings-table"' in html and 'id="mmh-filings-next"' in html
    assert not any(c.startswith(('forward_','outcome')) for c in data['columns'])
    assert 'id="mmh-outcomes-data"' not in html


def test_filing_export_pair_or_filename_refuses_before_source_read(monkeypatch,tmp_path):
    root,receipt=archive(monkeypatch,tmp_path)
    from engine.neuralweb import market_memory_history_filings as filings
    monkeypatch.setattr(filings,'read_filing_timeline',lambda *a,**k:pytest.fail('decoder called before admission'))
    for kwargs in ({'filings_path':tmp_path/'earnings_8k_dates.parquet'},
                   {'filings_path':tmp_path/'outcomes-2020.parquet','expected_filings_sha256':'a'*64}):
        with pytest.raises(ValueError):
            module().export_browser(root,tmp_path/'bad.html',expected_manifest_sha256=receipt['manifest_sha256'],**kwargs)
    assert not (tmp_path/'bad.html').exists()



def test_browser_embeds_source_bound_transcript_catalog_but_no_call_text(monkeypatch,tmp_path):
    import io
    from tests.test_market_memory_history_transcripts import payload
    from engine.neuralweb.market_memory_history_transcripts import read_transcript_catalog
    root,receipt=archive(monkeypatch,tmp_path);raw=payload()
    catalog=read_transcript_catalog(io.BytesIO(raw),file_bytes=len(raw),
        source_ref='fixture:stock_earning_call_transcripts.parquet',source_version='statv1:'+'a'*64)
    source=tmp_path/'transcript-catalog.json';encoded=json.dumps(catalog,sort_keys=True).encode();source.write_bytes(encoded)
    digest=hashlib.sha256(encoded).hexdigest();dest=tmp_path/'with-calls.html'
    result=module().export_browser(root,dest,expected_manifest_sha256=receipt['manifest_sha256'],
        transcripts_catalog_path=source,expected_transcripts_catalog_sha256=digest)
    html=dest.read_text(encoding='utf-8')
    block=re.search(r'<script id="mmh-transcripts-data"[^>]*>([^<]+)</script>',html).group(1)
    data=json.loads(gzip.decompress(base64.b64decode(block)))
    assert result['transcript_records']==1 and result['transcripts_catalog_sha256']==digest
    assert data['manifest_sha256']==receipt['manifest_sha256']
    assert data['metadata']['publication_time_verified'] is False
    assert 'Original words, not instructions.' not in html
    assert 'id="mmh-transcripts-table"' in html and 'id="mmh-transcript-request"' in html
    assert 'id="mmh-outcomes-data"' not in html


def test_bad_transcript_catalog_binding_refuses_before_export(monkeypatch,tmp_path):
    root,receipt=archive(monkeypatch,tmp_path)
    with pytest.raises(ValueError):
        module().export_browser(root,tmp_path/'bad.html',expected_manifest_sha256=receipt['manifest_sha256'],
            transcripts_catalog_path=tmp_path/'catalog.json')
    assert not (tmp_path/'bad.html').exists()
