"""Bounded synthetic mechanism tests; original-parent custody is not simulated proof."""
from datetime import timedelta
import hashlib
import json
from pathlib import Path

import pytest

from engine.research_vault import catalog, producer_generation as contract
from engine.research_vault import generation_continuation as continuation
from engine.research_vault.generation_continuation import (
    _continue_after_original_exit as continue_tail, OriginalContinuationUnavailable,
)
from engine.research_vault.generation_evidence import FileGenerationEvidence, read_evidence
from engine.research_vault.generation_recovery import (
    inspect_settled_publication, RecoveryPlanUnavailable,
)
from tests import test_research_vault_generation_recovery as _fixtures

IDENTITY, NOW = _fixtures.IDENTITY, _fixtures.NOW


@pytest.fixture
def original():
    fixtures = _fixtures.RecoverabilityTests()
    yield fixtures
    fixtures.doCleanups()


def invoke(path, digest, store, **kwargs):
    return continue_tail(store, path, expected_identity=IDENTITY,
                         original_capture_sha256=digest,
                         clock=lambda: NOW + timedelta(seconds=20), **kwargs)


def count_writes(monkeypatch, store):
    calls = []
    real = store.put_bytes_strict_conditional
    def conditional(key, body, **kw):
        calls.append((key, body, kw))
        return real(key, body, **kw)
    monkeypatch.setattr(store, "put_bytes_strict_conditional", conditional)
    monkeypatch.setattr(store, "put_bytes", lambda *_a, **_k: pytest.fail("unconditional replay"))
    return calls, real


@pytest.mark.parametrize("issued", [0, 1, 2])
def test_only_unissued_receipts_and_complete_same_original_generation(original, monkeypatch, issued):
    path, digest, events, receipts, store = original.fixture(issued, promote=True)
    before = path.read_bytes()
    old = json.loads(store.get_bytes(catalog.CATALOG_KEY))[contract.GENERATION_FIELD]
    calls, _ = count_writes(monkeypatch, store)
    result = invoke(path, digest, store)
    assert [c[0] for c in calls] == [r[0] for r in receipts[issued:]] + [catalog.CATALOG_KEY]
    assert all(c[2]["expected_version"] is None for c in calls[:-1])
    assert calls[-1][2]["expected_version"] is not None
    final = json.loads(result["catalog_bytes"])[contract.GENERATION_FIELD]
    assert final["state"] == "COMPLETE"
    assert final["epoch"] == old["epoch"]
    assert final["producer_run"] == IDENTITY["run"]
    assert final["producer_source_commit"] == IDENTITY["source_commit"]
    assert path.read_bytes() == before
    assert hashlib.sha256(before).hexdigest() == digest
    continuation = path.parent / "continuation.jsonl"
    retained = read_evidence(continuation, expected_identity=IDENTITY,
                             expected_sha256=result["continuation_capture_sha256"])
    assert retained[1]["kind"] == "continuation_origin"
    assert retained[1]["payload"]["original_capture_sha256"] == digest
    assert retained[-1]["kind"] == "terminal"
    assert continuation.stat().st_mode & 0o777 == 0o600
    assert result["receipt_count"] == 2 - issued
    # The continuation is not a new original plan, and no second attempt runs.
    with pytest.raises(RecoveryPlanUnavailable):
        inspect_settled_publication(continuation, expected_identity=IDENTITY,
            original_capture_sha256=result["continuation_capture_sha256"])
    size = len(calls)
    with pytest.raises(OriginalContinuationUnavailable):
        invoke(path, digest, store)
    assert len(calls) == size


@pytest.mark.parametrize("changed", ["capture", "corpus", "pdf", "catalog", "existing_slot"])
def test_invalid_original_or_live_bytes_refuse_without_writes(original, monkeypatch, changed):
    path, digest, _, _, store = original.fixture(promote=True)
    if changed == "capture":
        digest = "0" * 64
    elif changed == "existing_slot":
        (path.parent / "continuation.jsonl").write_bytes(b"original slot survives")
    else:
        key = {"corpus": contract.CORPUS_KEY, "pdf": "research_vault/report-a.pdf",
               "catalog": catalog.CATALOG_KEY}[changed]
        store.put_bytes(key, b"changed")
    calls, _ = count_writes(monkeypatch, store)
    with pytest.raises(OriginalContinuationUnavailable):
        invoke(path, digest, store)
    assert calls == []
    if changed == "existing_slot":
        assert (path.parent / "continuation.jsonl").read_bytes() == b"original slot survives"


@pytest.mark.parametrize("failure", ["conflict", "lost_ack", "complete_conflict"])
def test_new_uncertainty_or_conflict_is_retained_and_never_replayed(original, monkeypatch, failure):
    path, digest, _, receipts, store = original.fixture(promote=True)
    before = path.read_bytes()
    original_catalog = store.get_bytes(catalog.CATALOG_KEY)
    real = store.put_bytes_strict_conditional
    calls = []
    def fail(key, body, **kwargs):
        calls.append(key)
        if failure == "complete_conflict":
            return False if key == catalog.CATALOG_KEY else real(key, body, **kwargs)
        if failure == "lost_ack":
            real(key, body, **kwargs)
            raise OSError("PRIVATE_TRANSPORT_DETAIL")
        return False
    monkeypatch.setattr(store, "put_bytes_strict_conditional", fail)
    monkeypatch.setattr(store, "put_bytes", lambda *_a, **_k: pytest.fail("unconditional write"))
    with pytest.raises(OriginalContinuationUnavailable, match="^ORIGINAL_CONTINUATION_UNAVAILABLE$"):
        invoke(path, digest, store)
    assert len(calls) == (3 if failure == "complete_conflict" else 1)
    assert path.read_bytes() == before
    assert store.get_bytes(catalog.CATALOG_KEY) == original_catalog
    retained = read_evidence(path.parent / "continuation.jsonl", expected_identity=IDENTITY)
    assert retained[-1]["kind"] == "write_result"
    assert retained[-1]["payload"]["outcome"] in {"exception_effect_unknown", "conditional_conflict"}
    size = len(calls)
    with pytest.raises(OriginalContinuationUnavailable):
        invoke(path, digest, store)
    assert len(calls) == size


def test_original_uncertainty_refuses_even_when_its_receipt_is_visible(original, monkeypatch):
    path, _, events, _, store = original.fixture(issued=1, promote=True)
    # Synthetic original trace: actual effect is visible, but its return is
    # represented as uncertain. This is not a settlement or custody proof.
    alternate = path.parent / "uncertain-original.jsonl"
    with FileGenerationEvidence.create(alternate, IDENTITY) as sink:
        for event in events[1:]:
            payload = dict(event["payload"])
            if event is events[-1]:
                assert event["kind"] == "write_result"
                payload["outcome"] = "returned_false_effect_unknown"
            sink.append(event["kind"], payload)
    calls, _ = count_writes(monkeypatch, store)
    with pytest.raises(OriginalContinuationUnavailable):
        invoke(alternate, sink.capture_sha256, store)
    assert calls == []
    assert not (path.parent / "continuation.jsonl").exists()


def test_full_admitted_corpus_leaves_budget_for_required_checks(original, monkeypatch):
    # Scale the production 256 MiB corpus/read-budget boundary to 4 KiB.
    # The actual analyzer, reads and same-epoch completion still execute;
    # this avoids a 256 MiB allocation in every CI run.
    scale = (256 * 1024 * 1024) // 4096
    monkeypatch.setattr(contract, "CORPUS_MAX_BYTES", 4096)
    path, digest, _, _, store = original.fixture(promote=True, corpus_bytes=b"c" * 4096)
    real_live = continuation.inspect_live_settled_publication

    def scaled_live(*args, **kwargs):
        supplied_budget = kwargs.pop("byte_budget", 256 * 1024 * 1024)
        return real_live(*args, byte_budget=supplied_budget // scale, **kwargs)

    monkeypatch.setattr(continuation, "inspect_live_settled_publication", scaled_live)
    result = invoke(path, digest, store)
    assert json.loads(result["catalog_bytes"])[contract.GENERATION_FIELD]["state"] == "COMPLETE"


@pytest.mark.parametrize('changed', [False, True])
def test_original_continuation_checks_published_fulltext_source_cut(original, tmp_path, monkeypatch, changed):
    from engine.research_vault import corpus
    from engine.research_vault.producer_generation_writer import FULLTEXT_SOURCE_CUT_KEY
    document = {'schema': catalog.SCHEMA, 'generated_at': NOW.isoformat(), 'count': 2,
        'institutions': ['Desk'], 'items': [
            {'id': rid, 'title': 'Synthetic ' + rid, 'institution': 'Desk'}
            for rid in ('report-a', 'report-b')]}
    sources = {rid: hashlib.sha256(rid.encode()).hexdigest() for rid in ('report-a', 'report-b')}
    if changed:
        sources['report-a'] = 'f' * 64
    p = tmp_path / 'staged.sqlite';conn = corpus.open_db(p)
    conn.execute('INSERT INTO meta(key,value) VALUES(?,?)', (FULLTEXT_SOURCE_CUT_KEY,
        json.dumps({'schema': 'research_vault.producer_fulltext_source_cut.v1',
                    'catalog_payload_sha256': contract.compute_catalog_payload_digest(document),
                    'sources': sources})))
    conn.commit();conn.close()
    path, digest, _, _, store = original.fixture(issued=2, promote=True, corpus_bytes=p.read_bytes())
    before = path.read_bytes()
    calls, _ = count_writes(monkeypatch, store)
    if changed:
        with pytest.raises(OriginalContinuationUnavailable):
            invoke(path, digest, store)
        assert calls == []
        assert json.loads(store.get_bytes(catalog.CATALOG_KEY))[contract.GENERATION_FIELD]['state'] == 'BUILDING'
    else:
        result = invoke(path, digest, store)
        assert json.loads(result['catalog_bytes'])[contract.GENERATION_FIELD]['state'] == 'COMPLETE'
        assert [call[0] for call in calls] == [catalog.CATALOG_KEY]
    assert path.read_bytes() == before


@pytest.mark.parametrize('changed_record', [False, True])
def test_original_continuation_checks_used_canonical_hash_with_same_pdf(original, tmp_path, monkeypatch, changed_record):
    from engine.research_vault import corpus, fulltext, fulltext_index, fulltext_store
    from engine.research_vault.producer_generation_writer import record_fulltext_source_cut
    document = {'schema': catalog.SCHEMA, 'generated_at': NOW.isoformat(), 'count': 2,
        'institutions': ['Desk'], 'items': [
            {'id': rid, 'title': 'Synthetic ' + rid, 'institution': 'Desk'}
            for rid in ('report-a', 'report-b')]}
    digests = {rid: hashlib.sha256(rid.encode()).hexdigest() for rid in ('report-a', 'report-b')}
    records = {rid: fulltext.build_extracted_text(report_id=rid, source_pdf_sha256=digests[rid],
        text='canonical original ' * 100, extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION, page_count=1, text_layer_state='full')
        for rid in digests}
    blobs = {rid: fulltext_store.encode_record(value) for rid, value in records.items()}
    receipts = {rid: json.dumps({'id': rid, 'content_sha256': digests[rid]}).encode() for rid in digests}
    p = tmp_path / 'bound-canonical.sqlite';conn = corpus.open_db(p)
    for item in document['items']:
        corpus.upsert(conn, item, records[item['id']]['text'], facts={'content_sha256': digests[item['id']]})
    fulltext_index.stage(conn, document, record_loader=records.get, source_digest_reader=digests.get,
        max_rows=2, max_body_bytes=1000000)
    record_fulltext_source_cut(conn, document, digests,
        receipt_digests={rid: hashlib.sha256(raw).hexdigest() for rid, raw in receipts.items()},
        record_digests={rid: hashlib.sha256(raw).hexdigest() for rid, raw in blobs.items()})
    conn.commit();conn.close()
    path, digest, _, _, store = original.fixture(issued=2, promote=True, corpus_bytes=p.read_bytes())
    for rid, raw in blobs.items():
        store.put_bytes(fulltext_store.derivative_key(rid, digests[rid]), raw)
    if changed_record:
        altered = fulltext.build_extracted_text(report_id='report-a', source_pdf_sha256=digests['report-a'],
            text='changed canonical source', extractor_name=fulltext_store.EXTRACTOR_NAME,
            extractor_version=fulltext_store.EXTRACTOR_VERSION, page_count=1, text_layer_state='full')
        store.put_bytes(fulltext_store.derivative_key('report-a', digests['report-a']), fulltext_store.encode_record(altered))
    before = path.read_bytes();calls, _ = count_writes(monkeypatch, store)
    if changed_record:
        with pytest.raises(OriginalContinuationUnavailable):invoke(path, digest, store)
        assert calls == []
    else:
        result = invoke(path, digest, store)
        assert json.loads(result['catalog_bytes'])[contract.GENERATION_FIELD]['state'] == 'COMPLETE'
        assert [call[0] for call in calls] == [catalog.CATALOG_KEY]
    assert path.read_bytes() == before
