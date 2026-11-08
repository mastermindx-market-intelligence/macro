"""Read-only intended-host resource qualification, no activation or PDFs."""
import json
from pathlib import Path

import pytest
from engine.research_vault import catalog, corpus, fulltext, fulltext_store
from engine.research_vault.r2_store import LocalStore
from engine.research_vault import fulltext_qualification as qualification


def seeded(tmp_path):
    store = LocalStore(tmp_path / 'store')
    rid, digest = 'host-resource-note', 'e' * 64
    item = {'id': rid, 'title': 'Resource fixture', 'institution': 'Synthetic',
            'published_at': '2026-10-18T00:00:00Z', 'summary_points': []}
    doc = {'schema': catalog.SCHEMA, 'generated_at': '2026-10-18T00:00:00Z',
           'items': [item], 'count': 1, 'institutions': ['Synthetic']}
    store.put_bytes(catalog.CATALOG_KEY, json.dumps(doc).encode())
    text = 'word ' * 14000 + ' resource-tail-marker'
    db = tmp_path / 'corpus.sqlite';conn = corpus.open_db(db)
    corpus.upsert(conn, item, text, facts={'content_sha256': digest, 'text_layer': 'full'})
    conn.close();store.put_bytes('research_vault/corpus.sqlite', db.read_bytes())
    store.put_bytes(fulltext_store.receipt_key(rid), json.dumps({'id': rid, 'content_sha256': digest}).encode())
    record = fulltext.build_extracted_text(report_id=rid, source_pdf_sha256=digest,
        text=text, extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION, page_count=1, text_layer_state='full')
    store.put_bytes(fulltext_store.derivative_key(rid, digest), fulltext_store.encode_record(record))
    scratch = tmp_path / 'private';scratch.mkdir(mode=0o700)
    return store, scratch


def test_probe_uses_actual_index_census_and_retains_no_source_bytes(tmp_path):
    store, scratch = seeded(tmp_path)
    before = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    result = qualification.run(store, scratch_root=scratch, max_seconds=60)
    after = {p.relative_to(store.root): p.read_bytes() for p in store.root.rglob('*') if p.is_file()}
    assert before == after
    assert result['state'] == 'READONLY_RESOURCE_CHECK_PASSED'
    assert result['staged_counts']['full'] == 1
    assert result['catalog_fence_unchanged'] is True
    assert result['source_cut_unchanged'] is True
    assert result['writer_qualified'] is False
    assert result['production_accepted'] is False
    assert result['read_calls']['derivative'] == 2
    assert result['read_calls']['receipt'] == 2
    assert not list(scratch.iterdir())
    raw = json.dumps(result)
    assert 'resource-tail-marker' not in raw and 'host-resource-note' not in raw
    with pytest.raises(RuntimeError, match='read-only'):
        store.put_bytes('must-not-write', b'blocked')
    with pytest.raises(RuntimeError, match='read-only'):
        store.get_bytes('research_vault/anything.pdf')


def test_probe_reports_final_corpus_limit_without_increasing_it(tmp_path, monkeypatch):
    store, scratch = seeded(tmp_path)
    monkeypatch.setattr(qualification, 'FINAL_CORPUS_MAX_BYTES', 1)
    result = qualification.run(store, scratch_root=scratch, max_seconds=60)
    assert result['state'] == 'RESOURCE_BOUND_EXCEEDED'
    assert result['final_corpus_bytes'] > 1
    assert not list(scratch.iterdir())


def test_probe_refuses_nonprivate_scratch_before_reads(tmp_path):
    store, scratch = seeded(tmp_path);scratch.chmod(0o755)
    with pytest.raises(ValueError, match='private scratch'):
        qualification.run(store, scratch_root=scratch, max_seconds=60)


def test_probe_blocks_unlisted_object_and_pdf_reads(tmp_path):
    store, scratch = seeded(tmp_path)
    qualification._read_only(store, deadline=float('inf'), clock=lambda: 0)
    with pytest.raises(RuntimeError, match='read-only'):
        store.get_bytes_strict_bounded('research_vault/host-resource-note.pdf', 100)
    with pytest.raises(RuntimeError, match='read-only'):
        store.list_prefix('research_vault/')


@pytest.mark.parametrize('materialize,forensics,bootstrap,census,expected', [
    (False, False, False, False, 0),
    (True, False, False, False, 1),
    (False, True, False, False, 1),
    (False, False, True, False, 1),
    (False, False, False, True, 1),
])
def test_actual_workflow_admission_keeps_readonly_mode_exclusive(materialize, forensics, bootstrap, census, expected):
    import os
    import subprocess
    import yaml
    p = Path(__file__).resolve().parents[1] / '.github/workflows/research-ingest.yml'
    workflow = yaml.safe_load(p.read_text())
    step = next(s for s in workflow['jobs']['ingest']['steps'] if s.get('name') == 'admit one explicit producer mode')
    script = step['run'].replace('${{ inputs.run_census }}', str(census).lower())
    result = subprocess.run(['/bin/bash', '-c', script], env={**os.environ,
        'QUALIFICATION_ONLY': 'true', 'MATERIALIZE_ONLY': str(materialize).lower(),
        'PUBLISH_FORENSICS': str(forensics).lower(), 'BOOTSTRAP_FORENSICS': str(bootstrap).lower()},
        capture_output=True, text=True)
    assert result.returncode == expected


def test_workflow_resource_mode_fences_all_existing_effect_steps():
    import yaml
    p = Path(__file__).resolve().parents[1] / '.github/workflows/research-ingest.yml'
    workflow = yaml.safe_load(p.read_text())
    steps = workflow['jobs']['ingest']['steps']
    for name in ('bootstrap Filing Forensics private state', 'research vault ingest (hourly)',
                 'commit catalog snapshot (salvage-push)', 'grade Research Vault source-content freshness',
                 'research vault id-set census (read-only)', 'upload census report',
                 'fail the lane if ingest or source freshness failed'):
        step = next(s for s in steps if s.get('name') == name)
        assert '!inputs.qualify_discovery_only' in step['if'], name
    probe = next(s for s in steps if s.get('name') == 'read-only full-body resource qualification')
    assert 'github.event_name' in probe['if'] and 'inputs.qualify_discovery_only' in probe['if']
    assert 'fulltext_qualification' in probe['run']


def test_probe_never_accepts_a_moved_catalog_fence(tmp_path):
    from engine.research_vault.r2_store import VersionedBytes
    store, scratch = seeded(tmp_path)
    real = store.get_bytes_strict_bounded_versioned
    calls = 0
    def moved(key, bound):
        nonlocal calls
        calls += 1
        result = real(key, bound)
        return VersionedBytes(result.data, result.version + '-changed') if calls > 1 else result
    store.get_bytes_strict_bounded_versioned = moved
    result = qualification.run(store, scratch_root=scratch, max_seconds=60)
    assert result['state'] == 'OBSERVATION_CHANGED'
    assert result['catalog_fence_unchanged'] is False
    assert result['production_accepted'] is False
    assert not list(scratch.iterdir())


def test_probe_deadline_refuses_before_first_store_read(tmp_path):
    store, scratch = seeded(tmp_path)
    ticks = iter([0, 2])
    result = qualification.run(store, scratch_root=scratch, max_seconds=1,
        clock=lambda: next(ticks, 2))
    assert result['state'] == 'READONLY_RESOURCE_CHECK_UNAVAILABLE'
    assert result['error_class'] == 'TimeoutError'
    assert result['read_calls'] == {}
    assert not list(scratch.iterdir())


def test_probe_does_not_pass_when_final_sqlite_validation_exceeds_deadline(tmp_path, monkeypatch):
    store, scratch = seeded(tmp_path)
    ticks = {'now': 0}
    original = qualification._validate_fulltext_source_cut
    def late(*args):
        original(*args)
        ticks['now'] = 61
    monkeypatch.setattr(qualification, '_validate_fulltext_source_cut', late)
    result = qualification.run(store, scratch_root=scratch, max_seconds=60,
        clock=lambda: ticks['now'])
    assert result['elapsed_seconds'] == 61
    assert result['state'] == 'RESOURCE_TIME_BOUND_EXCEEDED'
    assert result['production_accepted'] is False
    assert not list(scratch.iterdir())
