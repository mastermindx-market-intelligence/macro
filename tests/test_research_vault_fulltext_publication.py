"""Canonical producer reads and bounded staging; no live Store qualification."""
import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor as RealPool

import pytest
from engine.research_vault import corpus, fulltext, fulltext_store, ingest
from engine.research_vault import fulltext_publication as publication
from engine.research_vault.r2_store import LocalStore

PDF = 'a' * 64


def seed(tmp_path, ids=('report-a',), missing=()):
    store = LocalStore(tmp_path / 'store')
    conn = corpus.open_db(tmp_path / 'corpus.sqlite')
    text = 'prefixwitness ' + 'alpha ' * 11000 + ' tailwitness'
    items = []
    for rid in ids:
        item = {'id': rid, 'title': 'Synthetic', 'institution': 'Desk',
                'published_at': '2026-10-18T00:00:00Z', 'summary_points': []}
        items.append(item)
        if rid not in missing:
            corpus.upsert(conn, item, text, facts={'content_sha256': PDF, 'text_layer': 'full'})
        store.put_bytes(fulltext_store.receipt_key(rid), json.dumps({'id': rid, 'content_sha256': PDF}).encode())
        record = fulltext.build_extracted_text(report_id=rid, source_pdf_sha256=PDF,
            text=text, extractor_name=fulltext_store.EXTRACTOR_NAME,
            extractor_version=fulltext_store.EXTRACTOR_VERSION, page_count=1, text_layer_state='full')
        store.put_bytes(fulltext_store.derivative_key(rid, PDF), fulltext_store.encode_record(record))
    doc = {'schema': 'research_vault.catalog.v1', 'generated_at': '2026-10-18T00:00:00Z', 'items': items}
    return store, conn, doc


def stage(store, conn, doc, pending=(), **kwargs):
    return publication.stage_from_store(conn, doc, store, pending,
        max_rows=kwargs.get('max_rows', 100), max_body_bytes=kwargs.get('max_body_bytes', 1000000))


def test_real_canonical_stage_adds_tail_without_external_writes(tmp_path, monkeypatch):
    store, conn, doc = seed(tmp_path)
    real = store.get_bytes_strict_bounded;reads = []
    def read(key, cap):
        reads.append((key, cap));return real(key, cap)
    monkeypatch.setattr(store, 'get_bytes_strict_bounded', read)
    monkeypatch.setattr(store, 'put_bytes', lambda *_: pytest.fail('remote write'))
    result = stage(store, conn, doc)
    assert result['source_digests'] == {'report-a': PDF}
    assert result['counts']['full'] == 1
    assert len(reads) == 3 and all(not key.endswith('.pdf') for key, _ in reads)
    assert corpus.search(conn, 'tailwitness')[0]['id'] == 'report-a'
    conn.close()


def test_pending_exact_receipt_overrides_prepublication_old_revision(tmp_path, monkeypatch):
    store, conn, doc = seed(tmp_path)
    store.put_bytes(fulltext_store.receipt_key('report-a'), json.dumps({'id': 'report-a', 'content_sha256': 'b' * 64}).encode())
    real = store.get_bytes_strict_bounded;reads = []
    def read(key, cap):
        reads.append(key);return real(key, cap)
    monkeypatch.setattr(store, 'get_bytes_strict_bounded', read)
    pending = [(fulltext_store.receipt_key('report-a'), json.dumps({'id': 'report-a', 'content_sha256': PDF}).encode())]
    result = stage(store, conn, doc, pending)
    assert result['counts']['full'] == 1
    assert result['source_digests'] == {'report-a': PDF}
    assert reads == [fulltext_store.derivative_key('report-a', PDF)]
    conn.close()


def test_receipt_changed_during_load_removes_all_obsolete_body(tmp_path, monkeypatch):
    store, conn, doc = seed(tmp_path)
    real = store.get_bytes_strict_bounded
    receipt_reads = 0
    def read(key, cap):
        nonlocal receipt_reads
        if key == fulltext_store.receipt_key('report-a'):
            receipt_reads += 1
            if receipt_reads == 2:
                return json.dumps({'id': 'report-a', 'content_sha256': 'b' * 64}).encode()
        return real(key, cap)
    monkeypatch.setattr(store, 'get_bytes_strict_bounded', read)
    result = stage(store, conn, doc)
    assert result['source_digests'] == {'report-a': 'b' * 64}
    assert corpus.search(conn, 'prefixwitness') == corpus.search(conn, 'tailwitness') == []
    conn.close()


def test_failure_on_skipped_trailing_corpus_row_rolls_back_full_stage(tmp_path, monkeypatch):
    store, conn, doc = seed(tmp_path, ('report-a', 'report-b'), missing={'report-b'})
    real = store.get_bytes_strict_bounded
    def read(key, cap):
        if key == fulltext_store.derivative_key('report-b', PDF):
            raise OSError('missing-row final source read failed')
        return real(key, cap)
    monkeypatch.setattr(store, 'get_bytes_strict_bounded', read)
    with pytest.raises(OSError, match='missing-row'):
        stage(store, conn, doc)
    assert corpus.search(conn, 'tailwitness') == []
    assert corpus.search(conn, 'prefixwitness')[0]['id'] == 'report-a'
    assert conn.execute("SELECT value FROM meta WHERE key='fulltext_index_publication'").fetchone() is None
    conn.close()


def test_all_absent_rows_still_have_complete_current_source_cut(tmp_path):
    store, conn, doc = seed(tmp_path, ('report-a', 'report-b'), missing={'report-a', 'report-b'})
    result = stage(store, conn, doc)
    assert result['counts']['missing_rows'] == 2
    assert result['source_digests'] == {'report-a': PDF, 'report-b': PDF}
    conn.close()


@pytest.mark.parametrize('bad', ['rows', 'body', 'duplicate', 'unknown', 'wrong_id'])
def test_bad_bounds_or_pending_plan_refuses_before_reads(tmp_path, monkeypatch, bad):
    store, conn, doc = seed(tmp_path)
    pending = [(fulltext_store.receipt_key('report-a'), json.dumps({'id': 'report-a', 'content_sha256': PDF}).encode())]
    kwargs = {}
    if bad == 'rows':kwargs['max_rows'] = 0
    elif bad == 'body':kwargs['max_body_bytes'] = 0
    elif bad == 'duplicate':pending *= 2
    elif bad == 'unknown':pending = [('research_inbox/_processed/other.json', pending[0][1])]
    else:pending = [(pending[0][0], b'{"id":"other"}')]
    monkeypatch.setattr(store, 'get_bytes_strict_bounded', lambda *_: pytest.fail('read before validation'))
    with pytest.raises(ValueError):stage(store, conn, doc, pending, **kwargs)
    conn.close()


def test_unknown_store_keeps_serial_reads(tmp_path, monkeypatch):
    store, conn, doc = seed(tmp_path, ('report-a', 'report-b'))
    real = store.get_bytes_strict_bounded;threads = set()
    def read(key, cap):
        threads.add(threading.get_ident());return real(key, cap)
    monkeypatch.setattr(store, 'get_bytes_strict_bounded', read)
    stage(store, conn, doc)
    assert threads == {threading.get_ident()}
    conn.close()


def test_synthetic_qualified_window_bounds_submitted_unfinished_members(tmp_path, monkeypatch):
    # Exercises only the window mechanism. This does not qualify a LocalStore
    # or replace the incumbent exact-R2 qualification tests.
    store, conn, doc = seed(tmp_path, tuple('report-' + str(n) for n in range(12)))
    monkeypatch.setattr(ingest, '_receipt_read_workers', lambda *_: 4)
    lock = threading.Lock();state = {'outstanding': 0, 'maximum': 0}
    class ObservedPool(RealPool):
        def submit(self, *a, **kw):
            with lock:
                state['outstanding'] += 1
                state['maximum'] = max(state['maximum'], state['outstanding'])
            future = super().submit(*a, **kw)
            def completed(_):
                with lock:state['outstanding'] -= 1
            future.add_done_callback(completed)
            return future
    monkeypatch.setattr(publication, 'ThreadPoolExecutor', ObservedPool)
    result = stage(store, conn, doc)
    assert result['counts']['full'] == 12
    assert state['maximum'] <= 4 and state['outstanding'] == 0
    conn.close()
