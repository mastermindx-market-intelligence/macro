"""Synthetic writer-CAS tests; never evidence of production writer adoption."""
import copy
import json
from datetime import datetime, timezone

import pytest

from engine.research_vault import catalog, corpus, fulltext_store, fulltext_writer, ingest
from engine.research_vault import producer_generation as contract
from engine.research_vault import producer_generation_writer as writer
from engine.research_vault.r2_store import LocalStore

NOW = datetime(2026, 10, 13, tzinfo=timezone.utc)
IDENTITY = {"source_commit": "a" * 40, "run": "synthetic-test-only"}
RID = "desk-2026-10-13-note"


class RecordingStore(LocalStore):
    def __init__(self, root):
        super().__init__(root)
        self.events = []
        self.conflict = False
        self.fail_key = None
        self.lost_response = False

    def put_bytes(self, key, data, content_type="application/octet-stream"):
        self.events.append(("put", key))
        if key == self.fail_key:
            return False
        return super().put_bytes(key, data, content_type)

    def put_bytes_strict_conditional(self, key, data, *, expected_version,
                                    content_type="application/octet-stream"):
        self.events.append(("cas", key))
        if self.conflict:
            return False
        result = super().put_bytes_strict_conditional(
            key, data, expected_version=expected_version, content_type=content_type)
        if self.lost_response:
            raise TimeoutError("synthetic post-write lost response")
        return result


@pytest.fixture
def seeded(tmp_path):
    store = RecordingStore(tmp_path / "store")
    doc = {"schema": catalog.SCHEMA, "generated_at": NOW.isoformat(),
           "count": 1, "institutions": ["Desk"],
           "items": [{"id": RID, "title": "Synthetic note", "institution": "Desk"}]}
    store.put_bytes(catalog.CATALOG_KEY, json.dumps(doc).encode())
    store.events.clear()
    return store, doc


def begin(seeded):
    store, doc = seeded
    session = writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    return store, doc, session, writer.FencedProducerStore(store, session)


def test_building_precedes_first_covered_put(seeded):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes("research_vault/synthetic.pdf", b"synthetic")
    assert store.events == [("cas", catalog.CATALOG_KEY),
                            ("put", "research_vault/synthetic.pdf")]
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]["state"] == "BUILDING"


def test_conflict_means_no_covered_put(seeded):
    store, doc = seeded
    store.conflict = True
    with pytest.raises(writer.GenerationWriteUnavailable):
        writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    assert all(event[0] != "put" for event in store.events)


def test_missing_conditional_capability_means_no_writes(seeded):
    store, doc = seeded
    store.put_bytes_strict_conditional = None
    with pytest.raises(writer.GenerationWriteUnavailable):
        writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    assert store.events == []


def test_complete_closes_actual_census_but_below95_does_not_qualify(seeded):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    assert catalog.publish(wrapped, doc, now=NOW).published
    data = session.complete(doc, now=NOW)
    record = json.loads(data)["producer_generation"]
    contract.validate_generation(record)
    assert record["classification_counts"]["missing"] == 1
    assert record["corpus_sha256"] == writer._sha(b"synthetic corpus")
    assert not contract.qualify_current_generation(
        store, expected_producer_commit=IDENTITY["source_commit"],
        now=int(NOW.timestamp()), max_age_seconds=3600,
        writer_protocol_qualified=True)


def test_new_epoch_discards_every_old_complete_field(seeded):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    assert catalog.publish(wrapped, doc, now=NOW).published
    session.complete(doc, now=NOW)
    old = copy.deepcopy(doc["producer_generation"])
    second = writer.ProducerGenerationSession.begin(
        store, doc, {**IDENTITY, "run": "next-synthetic"}, now=NOW)
    new = json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]
    assert new["epoch"] != old["epoch"]
    assert set(new) == contract.BUILDING_KEYS
    assert not (set(new) & (contract.COMPLETE_KEYS - contract.BUILDING_KEYS))
    assert second.record == new


def test_epoch_generator_cannot_restore_predecessor_epoch(seeded, monkeypatch):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    assert catalog.publish(wrapped, doc, now=NOW).published
    session.complete(doc, now=NOW)
    prior = store.get_bytes(catalog.CATALOG_KEY)
    monkeypatch.setattr(writer, "uuid4", lambda: doc["producer_generation"]["epoch"])
    events = list(store.events)
    with pytest.raises(writer.GenerationWriteUnavailable, match="reused predecessor"):
        writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    assert store.get_bytes(catalog.CATALOG_KEY) == prior
    assert store.events == events


def test_interrupted_building_cannot_be_taken_over(seeded):
    store, doc, session, wrapped = begin(seeded)
    events = list(store.events)
    with pytest.raises(writer.GenerationWriteUnavailable, match="owner must settle"):
        writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    assert store.events == events


def test_catalog_move_refuses_checkpoint_and_complete(seeded):
    store, doc, session, wrapped = begin(seeded)
    store.put_bytes(catalog.CATALOG_KEY, b"externally moved synthetic catalog")
    assert not catalog.publish(wrapped, doc, now=NOW).published
    with pytest.raises(writer.GenerationWriteUnavailable):
        session.complete(doc, now=NOW)


def test_failed_receipt_is_not_drained_and_complete_is_refused(seeded):
    store, doc, session, wrapped = begin(seeded)
    key = fulltext_store.receipt_key(RID)
    store.fail_key = key
    pending = [(key, b"synthetic receipt")]
    assert not ingest._flush_receipts(wrapped, pending)
    assert pending == [(key, b"synthetic receipt")]
    with pytest.raises(writer.GenerationWriteUnavailable):
        session.complete(doc, now=NOW)


def test_legacy_false_receipt_write_retains_pending(seeded):
    store, _ = seeded
    key = fulltext_store.receipt_key(RID)
    store.fail_key = key
    pending = [(key, b"synthetic receipt")]
    assert not ingest._flush_receipts(store, pending)
    assert len(pending) == 1


def test_covered_success_needs_exact_corpus_readback(seeded):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    store.put_bytes(contract.CORPUS_KEY, b"different synthetic corpus")
    with pytest.raises(writer.GenerationWriteUnavailable, match="readback mismatch"):
        session.complete(doc, now=NOW)
    assert doc["producer_generation"]["state"] == "BUILDING"


def test_completion_requires_confirmed_final_corpus(seeded):
    store, doc, session, wrapped = begin(seeded)
    store.put_bytes(contract.CORPUS_KEY, b"uncovered synthetic corpus")
    with pytest.raises(writer.GenerationWriteUnavailable, match="not confirmed"):
        session.complete(doc, now=NOW)


def test_standalone_catalog_publish_cannot_reuse_old_generation(seeded):
    store, doc, session, wrapped = begin(seeded)
    before = store.get_bytes(catalog.CATALOG_KEY)
    assert not catalog.publish(store, doc, now=NOW).published
    assert store.get_bytes(catalog.CATALOG_KEY) == before


def test_standalone_catalog_cannot_bypass_by_dropping_internal_field(seeded):
    store, doc, session, wrapped = begin(seeded)
    legacy = {key: value for key, value in doc.items() if key != "producer_generation"}
    before = store.get_bytes(catalog.CATALOG_KEY)
    assert not catalog.publish(store, legacy, now=NOW).published
    assert store.get_bytes(catalog.CATALOG_KEY) == before


def test_standalone_corpus_publication_refuses_generation(seeded, tmp_path):
    store, doc, session, wrapped = begin(seeded)
    path = tmp_path / "replacement.sqlite"
    path.write_bytes(b"synthetic replacement corpus")
    events = list(store.events)
    assert not ingest.publish_corpus(store, path)
    assert store.events == events


def test_standalone_pdf_promotion_refuses_before_mutation(seeded):
    store, doc, session, wrapped = begin(seeded)
    events = list(store.events)
    result = ingest._ingest_one(store, None, "research_inbox/synthetic.pdf")
    assert result["reason"] == "generation_writer_unqualified"
    assert store.events == events


def test_plain_legacy_catalog_publish_stays_compatible(seeded):
    store, doc = seeded
    assert catalog.publish(store, doc, now=NOW).published
    assert "producer_generation" not in json.loads(store.get_bytes(catalog.CATALOG_KEY))


def test_uncertain_cas_is_not_retried_or_adopted(seeded):
    store, doc = seeded
    store.lost_response = True
    with pytest.raises(writer.GenerationWriteUnavailable, match="effect uncertain"):
        writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    assert len(store.events) == 1
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]["state"] == "BUILDING"


def test_catalog_conditional_bypass_is_rejected(seeded):
    store, doc, session, wrapped = begin(seeded)
    with pytest.raises(writer.GenerationWriteUnavailable):
        wrapped.put_bytes_strict_conditional(catalog.CATALOG_KEY, b"old COMPLETE",
                                             expected_version=session.catalog_version)


def _seed_real_corpus(store, tmp_path):
    path = tmp_path / "published.sqlite"
    conn = corpus.open_db(path)
    corpus.upsert(conn, {"id": RID, "title": "Synthetic note", "institution": "Desk"},
                  "synthetic indexed body")
    conn.close()
    store.put_bytes(contract.CORPUS_KEY, path.read_bytes())


def test_actual_ingest_pass_completes_one_fenced_census(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    monkeypatch.setattr(fulltext_writer, "materialize_pending", lambda *a, **k: {"aborted": None})
    store.events.clear()
    result = ingest.run(store, tmp_path / "working.sqlite", now=NOW,
                        generation_identity=IDENTITY)
    assert result.get("error") is None, result
    assert result["generation_complete"] is True
    actual = json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]
    assert actual["state"] == "COMPLETE"
    assert actual["producer_run"] == IDENTITY["run"]
    assert store.events[0] == ("cas", catalog.CATALOG_KEY)
    assert set(result["timing_s"]) >= {"restore_s", "processed_index_s", "publication_s"}


def test_actual_unidentified_ingest_refuses_before_covered_write(seeded, tmp_path):
    store, doc, session, wrapped = begin(seeded)
    _seed_real_corpus(store, tmp_path)
    store.events.clear()
    result = ingest.run(store, tmp_path / "working.sqlite", now=NOW)
    assert result["error"] == "generation_writer_unqualified"
    assert store.events == []


def test_actual_dry_run_never_starts_fence(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    store.events.clear()
    result = ingest.run(store, tmp_path / "working.sqlite", now=NOW, dry_run=True,
                        generation_identity=IDENTITY)
    assert result.get("error") is None
    assert store.events == []
    assert "generation_complete" not in result


def test_confirmed_receipt_changed_before_complete_refuses(seeded):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    key = fulltext_store.receipt_key(RID)
    wrapped.put_bytes(key, b"synthetic unparseable receipt")
    store.put_bytes(key, b"changed synthetic receipt")
    with pytest.raises(writer.GenerationWriteUnavailable, match="readback mismatch"):
        session.complete(doc, now=NOW)


@pytest.mark.parametrize("when", [datetime(2026, 10, 13), datetime(2026, 10, 12, tzinfo=timezone.utc)])
def test_completion_requires_aware_nonbackwards_clock(seeded, when):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    prior = store.get_bytes(catalog.CATALOG_KEY)
    with pytest.raises(writer.GenerationWriteUnavailable, match="completion clock"):
        session.complete(doc, now=when)
    assert store.get_bytes(catalog.CATALOG_KEY) == prior
    assert not session.active


def test_ingest_completion_samples_clock_after_materializer(seeded, tmp_path, monkeypatch):
    from datetime import timedelta
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    phases = []
    def materialize(*args, **kwargs):
        phases.append("materialize")
        return {"aborted": None}
    def completion_clock():
        assert phases == ["materialize"]
        phases.append("completed")
        return NOW + timedelta(seconds=5)
    monkeypatch.setattr(fulltext_writer, "materialize_pending", materialize)
    result = ingest.run(store, tmp_path / "working.sqlite", now=NOW,
                        generation_identity=IDENTITY, generation_clock=completion_clock)
    assert result["generation_complete"] is True
    record = json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]
    assert record["completed_at"] == record["started_at"] + 5
    assert phases == ["materialize", "completed"]


def test_complete_read_failure_closes_writer_without_complete(seeded, monkeypatch):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    def refused(*args):
        raise RuntimeError("synthetic census read unavailable")
    monkeypatch.setattr(writer, "_census", refused)
    with pytest.raises(writer.GenerationWriteUnavailable):
        session.complete(doc, now=NOW)
    assert session.active is False
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]["state"] == "BUILDING"
    with pytest.raises(writer.GenerationWriteUnavailable):
        wrapped.put_bytes("research_vault/never.pdf", b"never")


def test_census_qualified_client_overlaps_four_reads_and_preserves_order(monkeypatch):
    import io
    import threading
    from engine.research_vault import r2_store
    from tests import test_research_vault_producer_generation as fixture
    data = fixture.MemoryStore()
    fixture.build_generation(data, {f"r-{n}": "full" for n in range(8)})
    document = json.loads(data.objects[catalog.CATALOG_KEY])
    barrier = threading.Barrier(4, timeout=2)
    class Client:
        def get_object(self, *, Bucket, Key):
            try:
                barrier.wait()
            except threading.BrokenBarrierError:
                pass
            raw = data.objects[Key]
            return {"Body":io.BytesIO(raw), "ContentLength":len(raw)}
    monkeypatch.setattr(r2_store, "_r2_client", lambda:Client())
    actual = writer._census(r2_store.R2Store("fixture"), document)
    assert not barrier.broken, "qualified strict reads must overlap in bounded groups of four"
    expected = writer._census(data, document)
    assert actual == expected


def test_census_failure_drains_started_window_without_starting_a_fifth(monkeypatch):
    import io
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from engine.research_vault import r2_store
    ready, release, failing = threading.Event(), threading.Event(), threading.Event()
    barrier = threading.Barrier(4, timeout=3)
    calls, lock = [], threading.Lock()
    class Client:
        def get_object(self, *, Bucket, Key):
            with lock:
                calls.append(Key)
            barrier.wait()
            ready.set()
            if Key == fulltext_store.receipt_key("r-0"):
                failing.set()
                raise RuntimeError("ordered fixture failure")
            assert release.wait(5)
            return {"Body":io.BytesIO(b"{}"), "ContentLength":2}
    monkeypatch.setattr(r2_store, "_r2_client", lambda:Client())
    doc = {"schema":catalog.SCHEMA,"generated_at":NOW.isoformat(),"count":8,
           "institutions":[],"items":[{"id":f"r-{n}"} for n in range(8)]}
    with ThreadPoolExecutor(max_workers=1) as pool:
        result = pool.submit(writer._census, r2_store.R2Store("fixture"), doc)
        try:
            assert ready.wait(4) and failing.wait(1)
            assert not result.done(), "started reads must remain owned until settled"
            assert len(calls) == 4
        finally:
            release.set()
        with pytest.raises(RuntimeError, match="ordered fixture failure"):
            result.result(timeout=5)
    assert sorted(calls) == [fulltext_store.receipt_key(f"r-{n}") for n in range(4)]


def test_fenced_store_retains_qualified_receipt_reader_window(monkeypatch):
    from engine.research_vault import r2_store
    monkeypatch.setattr(r2_store, "_r2_client", lambda:object())
    base = r2_store.R2Store("fixture")
    # Only delegation identity matters here; no read or write is performed.
    session = object.__new__(writer.ProducerGenerationSession)
    session.store = base
    assert ingest._receipt_read_workers(writer.FencedProducerStore(base, session), 4) == 4
    injected = r2_store.R2Store("fixture", client=object())
    session.store = injected
    assert ingest._receipt_read_workers(writer.FencedProducerStore(injected, session), 4) == 1
