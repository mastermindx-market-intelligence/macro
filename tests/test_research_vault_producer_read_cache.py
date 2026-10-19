"""Cold/warm real producer paths and immutable source-cut invalidation."""
import hashlib
import json
import sqlite3
import zlib
from datetime import timedelta

import pytest

from engine.research_vault import catalog, corpus, fulltext, fulltext_store, fulltext_writer, ingest
from engine.research_vault import producer_generation as contract
from engine.research_vault import producer_generation_writer as writer
from engine.research_vault import producer_read_cache as cache
from tests.test_research_vault_producer_generation_writer import (
    RecordingStore, NOW, IDENTITY, RID, _seed_discovery_record,
)


@pytest.fixture
def ready(tmp_path, monkeypatch):
    store = RecordingStore(tmp_path / 'store')
    item = {'id': RID, 'title': 'Synthetic note', 'institution': 'Desk'}
    doc = {'schema': catalog.SCHEMA, 'generated_at': NOW.isoformat(),
           'count': 1, 'institutions': ['Desk'], 'items': [item]}
    store.put_bytes(catalog.CATALOG_KEY, json.dumps(doc).encode())
    _seed_discovery_record(store, doc, tmp_path)
    monkeypatch.setattr(fulltext_writer, 'materialize_pending', lambda *a, **kw: {'aborted': None})
    return store, doc


def run(store, tmp_path, name, offset=0, **kwargs):
    return ingest.run(store, tmp_path / (name + '.sqlite'), now=NOW + timedelta(seconds=offset),
        generation_identity={**IDENTITY, 'run': name},
        generation_clock=lambda: NOW + timedelta(seconds=offset + 2), **kwargs)


def member_reads(store, monkeypatch):
    actual = store.get_bytes_strict_bounded;seen = []
    def read(key, maximum):
        if key.startswith((fulltext_store.RECEIPT_PREFIX, fulltext_store.FULLTEXT_PREFIX)):
            seen.append(key)
        return actual(key, maximum)
    monkeypatch.setattr(store, 'get_bytes_strict_bounded', read)
    return seen


def test_cold_generation_reads_each_member_only_in_begin_and_final_censuses(ready, tmp_path, monkeypatch):
    store, _ = ready;seen = member_reads(store, monkeypatch)
    result = run(store, tmp_path, 'cold')
    assert result.get('error') is None, result
    assert result['generation_complete'] is True
    assert len(seen) == 4  # no stage/idempotency re-GET; two fresh receipt+record cuts
    assert seen.count(fulltext_store.receipt_key(RID)) == 2
    assert result['fulltext_discovery']['full'] == 1


def test_warm_generation_reuses_only_its_source_bound_completed_starting_cut(ready, tmp_path, monkeypatch):
    store, _ = ready
    assert run(store, tmp_path, 'cold').get('error') is None
    seen = member_reads(store, monkeypatch)
    result = run(store, tmp_path, 'warm', 10)
    assert result.get('error') is None, result
    assert result['generation_complete'] is True
    assert len(seen) == 2  # the final fresh census is never skipped
    p = tmp_path / 'published.sqlite';p.write_bytes(store.get_bytes(contract.CORPUS_KEY))
    conn = corpus.open_db(p)
    assert corpus.search(conn, 'bodytailwitness')[0]['id'] == RID
    cut = json.loads(conn.execute('SELECT value FROM meta WHERE key=?', (writer.FULLTEXT_SOURCE_CUT_KEY,)).fetchone()[0])
    assert cut['schema'].endswith('.v2') and set(cut['records']) == {RID}
    conn.close()


def test_new_source_commit_gets_a_fresh_begin_census(ready, tmp_path, monkeypatch):
    store, _ = ready
    assert run(store, tmp_path, 'cold').get('error') is None
    seen = member_reads(store, monkeypatch)
    result = ingest.run(store, tmp_path / 'upgrade.sqlite', now=NOW + timedelta(seconds=10),
        generation_identity={**IDENTITY, 'source_commit': 'b' * 40, 'run': 'upgrade'},
        generation_clock=lambda: NOW + timedelta(seconds=12))
    assert result.get('error') is None, result
    assert len(seen) == 4


def test_same_pdf_changed_canonical_record_refuses_complete(ready, tmp_path, monkeypatch):
    store, _ = ready
    def replace_record(*a, **kw):
        record = fulltext.build_extracted_text(report_id=RID, source_pdf_sha256='c' * 64,
            text='changed canonical contents', extractor_name=fulltext_store.EXTRACTOR_NAME,
            extractor_version=fulltext_store.EXTRACTOR_VERSION, page_count=1, text_layer_state='full')
        store.put_bytes(fulltext_store.derivative_key(RID, 'c' * 64), fulltext_store.encode_record(record))
        return {'aborted': None}
    monkeypatch.setattr(fulltext_writer, 'materialize_pending', replace_record)
    result = run(store, tmp_path, 'changed-record')
    assert result['generation_complete'] is False
    assert 'cached canonical source cut changed' in result['generation_error']
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))[contract.GENERATION_FIELD]['state'] == 'BUILDING'


def test_same_pdf_changed_receipt_metadata_refuses_complete(ready, tmp_path, monkeypatch):
    store, _ = ready
    def replace_receipt(*a, **kw):
        raw = json.loads(store.get_bytes(fulltext_store.receipt_key(RID)))
        raw['pdf_key'] = 'research_inbox/changed-location.pdf'
        store.put_bytes(fulltext_store.receipt_key(RID), json.dumps(raw).encode())
        return {'aborted': None}
    monkeypatch.setattr(fulltext_writer, 'materialize_pending', replace_receipt)
    result = run(store, tmp_path, 'changed-receipt')
    assert result['generation_complete'] is False
    assert 'cached canonical source cut changed' in result['generation_error']


def test_changed_restored_corpus_refuses_before_new_begin_cas(ready, tmp_path):
    store, _ = ready
    assert run(store, tmp_path, 'cold').get('error') is None
    original_catalog = store.get_bytes(catalog.CATALOG_KEY)
    p = tmp_path / 'tampered.sqlite';p.write_bytes(store.get_bytes(contract.CORPUS_KEY))
    conn = sqlite3.connect(p);conn.execute("UPDATE documents SET title='tampered'");conn.commit();conn.close()
    store.put_bytes(contract.CORPUS_KEY, p.read_bytes());store.events.clear()
    result = run(store, tmp_path, 'tampered-image', 10)
    assert result['error'] == 'generation_start_failed'
    assert store.events == []
    assert store.get_bytes(catalog.CATALOG_KEY) == original_catalog


def test_raw_cache_limit_refuses_before_first_cas(ready, tmp_path, monkeypatch):
    store, _ = ready;before = store.get_bytes(catalog.CATALOG_KEY);store.events.clear()
    monkeypatch.setattr(cache, 'MAX_RAW_BYTES', 8)
    result = run(store, tmp_path, 'too-small')
    assert result['error'] == 'generation_start_failed'
    assert store.events == [] and store.get_bytes(catalog.CATALOG_KEY) == before


@pytest.mark.parametrize('payload,size', [(zlib.compress(b'x' * 1000), 32), (zlib.compress(b'x') + b'extra', 1)])
def test_cached_compression_cannot_expand_past_bound_or_hide_trailing_bytes(payload, size):
    with pytest.raises(ValueError):
        cache._unpack(payload, hashlib.sha256(b'x' * size).hexdigest(), size, 32)


def test_later_derivative_gets_only_one_payload_fetch_before_warm_begin(ready, tmp_path, monkeypatch):
    store, _ = ready
    key = fulltext_store.derivative_key(RID, 'c' * 64)
    canonical = store.get_bytes(key);store._p(key).unlink()
    def create_after_corpus(*a, **kw):
        store.put_bytes(key, canonical);return {'aborted': None}
    monkeypatch.setattr(fulltext_writer, 'materialize_pending', create_after_corpus)
    first = run(store, tmp_path, 'initial-missing')
    assert first.get('error') is None, first
    assert first['fulltext_discovery']['full'] == 0
    seen = member_reads(store, monkeypatch)
    second = run(store, tmp_path, 'payload-catchup', 10)
    assert second.get('error') is None, second
    assert second['fulltext_discovery']['full'] == 1
    assert seen.count(key) == 2  # one missing cached payload + final fresh census
    assert seen.count(fulltext_store.receipt_key(RID)) == 1


def test_growing_image_bound_refuses_before_corpus_write_without_journal(ready, tmp_path, monkeypatch):
    store, _ = ready
    original = store.get_bytes(contract.CORPUS_KEY)
    monkeypatch.setattr(contract, 'CORPUS_MAX_BYTES', len(original) + 16384)
    store.events.clear()
    with pytest.raises(writer.GenerationWriteUnavailable, match='corpus outside'):
        run(store, tmp_path, 'image-growth')
    assert store.get_bytes(contract.CORPUS_KEY) == original
    assert ('put', contract.CORPUS_KEY) not in store.events
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))[contract.GENERATION_FIELD]['state'] == 'BUILDING'


def test_own_pdf_correction_remains_valid_across_checkpoint_and_final_stage(ready, tmp_path, monkeypatch):
    store, doc = ready
    corrected = 'd' * 64
    text = 'correctednativeprefix ' + 'beta ' * 14000 + ' correctedtail'
    monkeypatch.setattr(ingest, '_list_inbox_pdfs', lambda _: ['research_inbox/correction.pdf'])
    def intake(_store, conn, _key, **kwargs):
        facts = {'content_sha256': corrected, 'text_layer': 'full'}
        corpus.upsert(conn, doc['items'][0], text, facts=facts)
        return {'status': 'ingested', 'item': doc['items'][0], 'title_source': 'sidecar', 'facts': facts}
    monkeypatch.setattr(ingest, '_ingest_one', intake)
    result = run(store, tmp_path, 'checkpoint-correction', checkpoint_every=1)
    assert result.get('error') is None, result
    assert result['generation_complete'] is True
    p = tmp_path / 'corrected-published.sqlite';p.write_bytes(store.get_bytes(contract.CORPUS_KEY))
    conn = corpus.open_db(p)
    try:
        assert corpus.search(conn, 'correctednativeprefix')[0]['id'] == RID
        assert corpus.search(conn, 'bodytailwitness') == []
        assert corpus.search(conn, 'correctedtail') == []  # new derivative belongs to a later image
    finally:
        conn.close()


def test_checkpoint_image_has_its_own_current_bound_source_cut(ready, tmp_path, monkeypatch):
    store, doc = ready
    monkeypatch.setattr(ingest, '_list_inbox_pdfs', lambda _: ['research_inbox/same-source.pdf'])
    monkeypatch.setattr(ingest, '_ingest_one', lambda *a, **kw: {
        'status': 'ingested', 'item': doc['items'][0], 'title_source': 'sidecar',
        'facts': {'content_sha256': 'c' * 64, 'text_layer': 'full'}})
    real = store.put_bytes;checked = []
    def observed(key, data, content_type='application/octet-stream'):
        if key == contract.CORPUS_KEY:
            conn = sqlite3.connect(':memory:');conn.deserialize(data)
            try:
                cut = json.loads(conn.execute('SELECT value FROM meta WHERE key=?', (writer.FULLTEXT_SOURCE_CUT_KEY,)).fetchone()[0])
                assert cut['schema'].endswith('.v2')
                assert set(cut['records']) == {RID}
                checked.append(cut['catalog_payload_sha256'])
            finally:conn.close()
        return real(key, data, content_type)
    monkeypatch.setattr(store, 'put_bytes', observed)
    result = run(store, tmp_path, 'checkpoint-bound', checkpoint_every=1)
    assert result.get('error') is None, result
    assert len(checked) == 2  # both checkpoint and final images are independently bound


def test_sealed_cache_image_bound_refuses_before_begin_cas(ready, tmp_path, monkeypatch):
    store, _ = ready
    original_catalog = store.get_bytes(catalog.CATALOG_KEY)
    original_corpus = store.get_bytes(contract.CORPUS_KEY)
    monkeypatch.setattr(contract, 'CORPUS_MAX_BYTES', len(original_corpus) + 1)
    store.events.clear()
    result = run(store, tmp_path, 'sealed-image-growth')
    assert result['error'] == 'generation_start_failed'
    assert 'sealed cache corpus outside' in result['generation_error']
    assert store.events == []
    assert store.get_bytes(catalog.CATALOG_KEY) == original_catalog
    assert store.get_bytes(contract.CORPUS_KEY) == original_corpus


def test_cache_cohort_turnover_prunes_retired_rows_and_reopens(ready, tmp_path, monkeypatch):
    store, doc = ready
    from engine.research_vault import fulltext_index
    monkeypatch.setattr(fulltext_index, 'MAX_ROWS', 1)
    p = tmp_path / 'turnover.sqlite';p.write_bytes(store.get_bytes(contract.CORPUS_KEY))
    snapshot = cache.CorpusReadCache(p, doc)
    members = writer._census(store, doc, read_cache=snapshot);snapshot.seal(members)
    new_item = {'id': 'replacement-report', 'title': 'Replacement', 'institution': 'Desk'}
    replacement = {**doc, 'items': [new_item]}
    raw = json.dumps({'id': new_item['id'], 'content_sha256': 'f' * 64}).encode()
    conn = corpus.open_db(p)
    corpus.upsert(conn, new_item, 'new native prefix', facts={'content_sha256': 'f' * 64})
    staged = snapshot.stage(conn, replacement, [(fulltext_store.receipt_key(new_item['id']), raw)],
                            max_rows=1, max_body_bytes=1000000)
    conn.commit()
    assert staged['source_digests'] == {new_item['id']: 'f' * 64}
    assert [row[0] for row in conn.execute('SELECT report_id FROM producer_read_cache')] == [new_item['id']]
    conn.close()
    reopened = cache.CorpusReadCache(p, replacement)
    try:
        assert set(reopened.sizes) == {new_item['id']}
        assert reopened.total == len(raw)
    finally:reopened.close()


def test_fullbody_stage_reads_cache_under_writer_cache_spill(ready, tmp_path):
    store, doc = ready
    p = tmp_path / 'spilled-writer.sqlite'
    p.write_bytes(store.get_bytes(contract.CORPUS_KEY))
    snapshot = cache.CorpusReadCache(p, doc)
    snapshot.seal(writer._census(store, doc, read_cache=snapshot))
    conn = corpus.open_db(p)
    try:
        conn.execute('PRAGMA cache_size=1')
        conn.execute('PRAGMA cache_spill=1')
        conn.execute('INSERT INTO meta(key,value) VALUES(?,?)', ('spill-padding', 'x' * 131072))
        staged = snapshot.stage(conn, doc, [], max_rows=10000, max_body_bytes=256 * 1024 * 1024)
        assert staged['counts']['full'] == 1
        conn.commit()
        assert corpus.search(conn, 'bodytailwitness')[0]['id'] == RID
    finally:
        conn.close()
