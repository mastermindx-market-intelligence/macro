"""Synthetic writer-CAS tests; never evidence of production writer adoption."""
import copy
import base64
import hashlib
import json
from datetime import datetime, timezone

import pytest

from engine.research_vault import catalog, corpus, fulltext_store, fulltext_writer, ingest
from engine.research_vault import producer_generation as contract
from engine.research_vault import producer_generation_writer as writer
from engine.research_vault.r2_store import (
    BoundedReadTooLarge, HARD_MAX_STRICT_CONDITIONAL_OBJECT_BYTES, LocalStore,
)
from engine.research_vault.generation_evidence import FileGenerationEvidence, read_evidence

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


def test_evidence_identity_must_match_before_begin_effect(seeded, tmp_path):
    store, doc = seeded
    with FileGenerationEvidence.create(tmp_path / "original.jsonl", IDENTITY) as evidence:
        with pytest.raises(writer.GenerationWriteUnavailable, match="identity mismatch"):
            writer.ProducerGenerationSession.begin(
                store, doc, {**IDENTITY, "run": "other"}, now=NOW, evidence=evidence)
    assert store.events == []


def test_actual_write_intent_is_persisted_before_store_call(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        session = writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW, evidence=evidence)
        original = store.put_bytes
        def observed_put(key, data, content_type):
            event = json.loads(path.read_bytes().splitlines()[-1])["event"]
            assert event["kind"] == "write_intent"
            assert event["payload"]["key"] == key
            assert event["payload"]["sha256"] == hashlib.sha256(data).hexdigest()
            return original(key, data, content_type)
        monkeypatch.setattr(store, "put_bytes", observed_put)
        session.put(contract.CORPUS_KEY, b"original intended bytes", "application/octet-stream")
    events = read_evidence(path, expected_identity=IDENTITY)
    assert events[-1]["payload"]["outcome"] == "returned_true"


def test_failed_intent_persistence_prevents_remote_write(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    with FileGenerationEvidence.create(tmp_path / "original.jsonl", IDENTITY) as evidence:
        session = writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW, evidence=evidence)
        prior = list(store.events)
        monkeypatch.setattr(evidence, "append", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
        with pytest.raises(writer.GenerationWriteUnavailable, match="evidence unavailable"):
            session.put(contract.CORPUS_KEY, b"never sent", "application/octet-stream")
        assert store.events == prior
        assert not session.active


def test_lost_result_evidence_never_invents_confirmation(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        session = writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW, evidence=evidence)
        original = evidence.append
        def failing_result(kind, payload, **kwargs):
            if kind == "write_result":
                raise OSError("disk after effect")
            return original(kind, payload, **kwargs)
        monkeypatch.setattr(evidence, "append", failing_result)
        with pytest.raises(writer.GenerationWriteUnavailable, match="evidence unavailable"):
            session.put(contract.CORPUS_KEY, b"applied but unrecorded", "application/octet-stream")
        assert store.get_bytes(contract.CORPUS_KEY) == b"applied but unrecorded"
        assert contract.CORPUS_KEY not in session._confirmed_writes
        assert not session.active
    assert read_evidence(path, expected_identity=IDENTITY)[-1]["kind"] == "write_intent"


def test_lost_begin_response_preserves_original_unknown_without_takeover(seeded, tmp_path):
    store, doc = seeded
    store.lost_response = True
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        with pytest.raises(writer.GenerationWriteUnavailable, match="effect uncertain"):
            writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW, evidence=evidence)
    events = read_evidence(path, expected_identity=IDENTITY)
    intent = events[1]["payload"]
    assert base64.b64decode(intent["catalog_base64"]) == store.get_bytes(catalog.CATALOG_KEY)
    assert events[-1]["payload"]["outcome"] == "exception_effect_unknown"
    assert len(store.events) == 1
    current = json.loads(store.get_bytes(catalog.CATALOG_KEY))
    with pytest.raises(writer.GenerationWriteUnavailable, match="owner must settle"):
        writer.ProducerGenerationSession.begin(store, current, IDENTITY, now=NOW)
    assert len(store.events) == 1


def test_actual_ingest_retains_receipt_plan_before_checkpoint_visibility(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    monkeypatch.setattr(ingest, "_list_inbox_pdfs", lambda _: ["research_inbox/synthetic.pdf"])
    monkeypatch.setattr(ingest, "_ingest_one", lambda *a, **k: {
        "status": "ingested", "item": doc["items"][0], "title_source": "sidecar",
        "facts": {"content_sha256": "b" * 64, "text_layer": "full"}})
    monkeypatch.setattr(fulltext_writer, "materialize_pending", lambda *a, **k: {"aborted": None})
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        result = ingest.run(store, tmp_path / "working.sqlite", now=NOW, checkpoint_every=1,
                            generation_identity=IDENTITY, generation_evidence=evidence)
    assert result.get("error") is None, result
    assert result["generation_complete"] is True
    events = read_evidence(path, expected_identity=IDENTITY)
    plans = [i for i, event in enumerate(events) if event["kind"] == "publication_plan"]
    corpus_writes = [i for i, event in enumerate(events) if event["kind"] == "write_intent"
                     and event["payload"]["key"] == contract.CORPUS_KEY]
    assert len(plans) == len(corpus_writes) == 2
    assert all(plan < write for plan, write in zip(plans, corpus_writes))
    for plan, corpus_write in zip(plans, corpus_writes):
        intended = base64.b64decode(events[plan]["payload"]["catalog_base64"])
        following = next(event["payload"] for event in events[corpus_write + 1:]
                         if event["kind"] == "write_intent"
                         and event["payload"]["key"] == catalog.CATALOG_KEY)
        assert base64.b64decode(following["catalog_base64"]) == intended
    pending = events[plans[0]]["payload"]["pending_receipts"]
    assert len(pending) == 1
    assert base64.b64decode(pending[0]["body_base64"]) == store.get_bytes(pending[0]["key"])
    assert events[plans[1]]["payload"]["pending_receipts"] == []
    assert events[-1]["kind"] == "terminal"
    assert events[-1]["payload"]["catalog_sha256"] == hashlib.sha256(store.get_bytes(catalog.CATALOG_KEY)).hexdigest()


def test_unknown_immutable_write_prevents_completion(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        session = writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW, evidence=evidence)
        wrapped = writer.FencedProducerStore(store, session)
        monkeypatch.setattr(store, "put_bytes_strict_conditional",
                            lambda *a, **k: (_ for _ in ()).throw(TimeoutError("lost")))
        with pytest.raises(writer.GenerationWriteUnavailable, match="immutable conditional effect uncertain"):
            wrapped.put_bytes_strict_conditional(fulltext_store.FULLTEXT_PREFIX + "synthetic.json",
                                                 b"original", expected_version=None)
        assert not session.active
        with pytest.raises(writer.GenerationWriteUnavailable):
            session.complete(doc, now=NOW)
    assert read_evidence(path, expected_identity=IDENTITY)[-1]["payload"]["outcome"] == "exception_effect_unknown"


def test_unpersisted_publication_plan_blocks_the_entire_batch(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    store.events.clear()
    with FileGenerationEvidence.create(tmp_path / "original.jsonl", IDENTITY) as evidence:
        original = evidence.append
        def refuse_plan(kind, payload, **kwargs):
            if kind == "publication_plan":
                raise OSError("disk before visibility batch")
            return original(kind, payload, **kwargs)
        monkeypatch.setattr(evidence, "append", refuse_plan)
        with pytest.raises(writer.GenerationWriteUnavailable, match="evidence unavailable"):
            ingest.run(store, tmp_path / "working.sqlite", now=NOW,
                       generation_identity=IDENTITY, generation_evidence=evidence)
    assert store.events == [("cas", catalog.CATALOG_KEY)]
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]["state"] == "BUILDING"


def test_publication_budget_includes_following_catalog_before_corpus_effect(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    store.events.clear()
    monkeypatch.setattr(ingest, "_list_inbox_pdfs", lambda _: [])
    path = tmp_path / "original.jsonl"
    planned = []
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        original = evidence.append
        def tight_batch(kind, payload, **kwargs):
            if kind == "publication_plan":
                planned.append(True)
                # Measure the actual record, then leave room for the corpus
                # intent's acknowledgement reserve but not the catalog intent.
                probe = tmp_path / "size-only.jsonl"
                with FileGenerationEvidence.create(probe, IDENTITY) as sizing:
                    before = probe.stat().st_size
                    sizing.append(kind, payload)
                    record_bytes = probe.stat().st_size - before
                evidence._bound = path.stat().st_size + record_bytes + writer.POST_EFFECT_EVIDENCE_BYTES + 2000
            return original(kind, payload, **kwargs)
        monkeypatch.setattr(evidence, "append", tight_batch)
        try:
            ingest.run(store, tmp_path / "working.sqlite", now=NOW,
                       generation_identity=IDENTITY, generation_evidence=evidence)
        except writer.GenerationWriteUnavailable:
            pass
    assert planned == [True]
    assert store.events == [("cas", catalog.CATALOG_KEY)]


def test_original_catalog_survives_loss_after_acknowledged_corpus(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    intended = {**doc["items"][0], "title": "Captured before corpus visibility"}
    monkeypatch.setattr(ingest, "_list_inbox_pdfs", lambda _: ["research_inbox/synthetic.pdf"])
    monkeypatch.setattr(ingest, "_ingest_one", lambda *a, **k: {
        "status": "ingested", "item": intended, "title_source": "sidecar",
        "facts": {"content_sha256": "b" * 64, "text_layer": "full"}})
    def process_lost(*a, **k):
        raise SystemExit("synthetic process loss before catalog call")
    monkeypatch.setattr(catalog, "publish", process_lost)
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        with pytest.raises(SystemExit, match="process loss"):
            ingest.run(store, tmp_path / "working.sqlite", now=NOW, checkpoint_every=1,
                       generation_identity=IDENTITY, generation_evidence=evidence)
    events = read_evidence(path, expected_identity=IDENTITY)
    plan = next(event["payload"] for event in events if event["kind"] == "publication_plan")
    original = base64.b64decode(plan["catalog_base64"])
    assert json.loads(original)["items"][0]["title"] == intended["title"]
    assert hashlib.sha256(original).hexdigest() == plan["catalog_sha256"]
    assert len(original) == plan["catalog_bytes"]
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))["items"][0]["title"] != intended["title"]
    assert events[-1]["kind"] == "write_result"
    assert events[-1]["payload"]["outcome"] == "returned_true"


def test_changed_catalog_after_freeze_refuses_before_visibility(seeded):
    store, doc, session, wrapped = begin(seeded)
    catalog.prepare_publication(doc, now=NOW)
    frozen = session.prepare_catalog(doc)
    doc["items"][0]["title"] = "changed after capture"
    prior = list(store.events)
    result = catalog.publish(wrapped, doc, now=NOW, prepared_bytes=frozen)
    assert result.published is False
    assert "prepared catalog changed" in result.error
    assert result.data == frozen
    assert store.events == prior


def test_prepared_catalog_keeps_original_stamp_when_publication_is_later(seeded):
    from datetime import timedelta
    store, doc, session, wrapped = begin(seeded)
    catalog.prepare_publication(doc, now=NOW)
    frozen = session.prepare_catalog(doc)
    result = catalog.publish(wrapped, doc, now=NOW + timedelta(seconds=9), prepared_bytes=frozen)
    assert result.published
    assert result.data == store.get_bytes(catalog.CATALOG_KEY) == frozen


def test_planned_catalog_conflict_never_releases_pending_receipts(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    monkeypatch.setattr(ingest, "_list_inbox_pdfs", lambda _: ["research_inbox/synthetic.pdf"])
    monkeypatch.setattr(ingest, "_ingest_one", lambda *a, **k: {
        "status": "ingested", "item": doc["items"][0], "title_source": "sidecar",
        "facts": {"content_sha256": "b" * 64, "text_layer": "full"}})
    original = store.put_bytes_strict_conditional
    def conflict_after_begin(*a, **k):
        result = original(*a, **k)
        store.conflict = True
        return result
    monkeypatch.setattr(store, "put_bytes_strict_conditional", conflict_after_begin)
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        with pytest.raises(writer.GenerationWriteUnavailable, match="conditional conflict"):
            ingest.run(store, tmp_path / "working.sqlite", now=NOW, checkpoint_every=1,
                       generation_identity=IDENTITY, generation_evidence=evidence)
    assert not any(key.startswith(fulltext_store.RECEIPT_PREFIX) for _, key in store.events)
    events = read_evidence(path, expected_identity=IDENTITY)
    assert any(e["kind"] == "publication_plan" and e["payload"]["pending_receipts"] for e in events)
    assert events[-1]["payload"]["outcome"] == "conditional_conflict"


def test_legacy_false_put_remains_unknown_in_original_evidence(seeded, tmp_path):
    store, doc = seeded
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        session = writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW, evidence=evidence)
        store.fail_key = contract.CORPUS_KEY
        with pytest.raises(writer.GenerationWriteUnavailable, match="write rejected"):
            session.put(contract.CORPUS_KEY, b"unknown remote effect", "application/octet-stream")
        assert not session.active
    assert read_evidence(path, expected_identity=IDENTITY)[-1]["payload"]["outcome"] == "returned_false_effect_unknown"


@pytest.mark.parametrize("dry_run,identity", [(True, IDENTITY), (False, None)])
def test_evidence_requires_an_explicit_real_generation(seeded, tmp_path, dry_run, identity):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    store.events.clear()
    path = tmp_path / "original.jsonl"
    with FileGenerationEvidence.create(path, IDENTITY) as evidence:
        result = ingest.run(store, tmp_path / "working.sqlite", now=NOW, dry_run=dry_run,
                            generation_identity=identity, generation_evidence=evidence)
    assert result["error"] == "generation_evidence_requires_explicit_producer"
    assert store.events == []
    assert len(read_evidence(path, expected_identity=IDENTITY)) == 1


def test_building_precedes_first_covered_put(seeded):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes("research_vault/synthetic.pdf", b"synthetic")
    assert store.events == [("cas", catalog.CATALOG_KEY),
                            ("put", "research_vault/synthetic.pdf")]
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]["state"] == "BUILDING"


def test_evidence_budget_refuses_before_begin_can_change_catalog(seeded, tmp_path):
    store, doc = seeded
    original = store.get_bytes(catalog.CATALOG_KEY)
    # Fits this small BEGIN intent, but cannot reserve all post-effect records.
    with FileGenerationEvidence.create(tmp_path / "small.jsonl", IDENTITY, max_bytes=8192) as evidence:
        with pytest.raises(writer.GenerationWriteUnavailable, match="evidence unavailable"):
            writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW, evidence=evidence)
    assert store.events == []
    assert store.get_bytes(catalog.CATALOG_KEY) == original


def test_complete_refuses_payload_never_published_in_building(seeded):
    store, doc, session, wrapped = begin(seeded)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    doc["items"][0]["title"] = "never published"
    prior = store.get_bytes(catalog.CATALOG_KEY)
    with pytest.raises(writer.GenerationWriteUnavailable, match="completion catalog was not published"):
        session.complete(doc, now=NOW)
    assert store.get_bytes(catalog.CATALOG_KEY) == prior
    assert not session.active


def test_complete_retains_specific_failure_on_subsequent_use(seeded):
    store, doc, session, wrapped = begin(seeded)
    with pytest.raises(writer.GenerationWriteUnavailable, match="final corpus publication not confirmed"):
        session.complete(doc, now=NOW)
    assert session.failure == "final corpus publication not confirmed"
    with pytest.raises(writer.GenerationWriteUnavailable, match="final corpus publication not confirmed"):
        wrapped.put_bytes("research_vault/not-sent", b"no")


@pytest.mark.parametrize("run", [" padded", "padded ", "padded\n"])
def test_padded_identity_refuses_before_store_effect(seeded, run):
    store, doc = seeded
    with pytest.raises(writer.GenerationWriteUnavailable, match="identity required"):
        writer.ProducerGenerationSession.begin(store, doc, {**IDENTITY, "run": run}, now=NOW)
    assert store.events == []


def test_unbounded_catalog_version_refuses_before_store_effect(seeded, monkeypatch):
    from engine.research_vault.r2_store import VersionedBytes
    store, doc = seeded
    data = store.get_bytes(catalog.CATALOG_KEY)
    monkeypatch.setattr(store, "get_bytes_strict_bounded_versioned",
                        lambda *a: VersionedBytes(data, "v" * 4097))
    with pytest.raises(writer.GenerationWriteUnavailable, match="catalog version"):
        writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    assert store.events == []


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


def _seed_discovery_record(store, doc, tmp_path):
    from engine.research_vault import fulltext
    text = 'bodyprefix ' + 'alpha ' * 11000 + ' bodytailwitness'
    digest = 'c' * 64
    p = tmp_path / 'discovery-source.sqlite'
    conn = corpus.open_db(p)
    corpus.upsert(conn, doc['items'][0], text,
                  facts={'content_sha256': digest, 'text_layer': 'full'})
    conn.close()
    store.put_bytes(contract.CORPUS_KEY, p.read_bytes())
    store.put_bytes(fulltext_store.receipt_key(RID), json.dumps({
        'id': RID, 'pdf_key': 'research_inbox/seeded.pdf',
        'content_sha256': digest}).encode())
    record = fulltext.build_extracted_text(report_id=RID, source_pdf_sha256=digest,
        text=text, extractor_name=fulltext_store.EXTRACTOR_NAME,
        extractor_version=fulltext_store.EXTRACTOR_VERSION,
        page_count=1, text_layer_state='full')
    store.put_bytes(fulltext_store.derivative_key(RID, digest),
                    fulltext_store.encode_record(record))
    return text, digest


def test_actual_generation_publishes_discoverable_full_body_before_complete(seeded, tmp_path, monkeypatch):
    from engine.research_vault import fulltext_index
    store, doc = seeded
    text, _ = _seed_discovery_record(store, doc, tmp_path)
    monkeypatch.setattr(fulltext_writer, 'materialize_pending', lambda *a, **k: {'aborted': None})
    result = ingest.run(store, tmp_path / 'working.sqlite', now=NOW,
                        generation_identity=IDENTITY)
    assert result.get('error') is None, result
    assert result['generation_complete'] is True
    p = tmp_path / 'published-read.sqlite'
    p.write_bytes(store.get_bytes(contract.CORPUS_KEY))
    conn = corpus.open_db(p)
    try:
        assert [row['id'] for row in corpus.search(conn, 'bodytailwitness')] == [RID]
        assert conn.execute('SELECT body FROM documents WHERE doc_id=?', (RID,)).fetchone()[0] == text
        actual = json.loads(store.get_bytes(catalog.CATALOG_KEY))
        assert fulltext_index.discovery_coverage(conn, actual, {RID}) == 'FULL_TEXT'
    finally:
        conn.close()


def test_actual_generation_refuses_pdf_revision_change_after_body_publication(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_discovery_record(store, doc, tmp_path)
    def changed_after_corpus(*args, **kwargs):
        store.put_bytes(fulltext_store.receipt_key(RID), json.dumps({
            'id': RID, 'content_sha256': 'd' * 64}).encode())
        return {'aborted': None}
    monkeypatch.setattr(fulltext_writer, 'materialize_pending', changed_after_corpus)
    result = ingest.run(store, tmp_path / 'working.sqlite', now=NOW,
                        generation_identity=IDENTITY)
    assert result['generation_complete'] is False
    assert result['error'] == 'generation_completion_failed'
    assert 'fulltext source cut changed' in result['generation_error']
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))['producer_generation']['state'] == 'BUILDING'


def test_actual_generation_staging_cache_read_failure_does_not_publish_candidate_body(seeded, tmp_path, monkeypatch):
    from engine.research_vault.producer_read_cache import CorpusReadCache
    store, doc = seeded
    _seed_discovery_record(store, doc, tmp_path)
    before = store.get_bytes(contract.CORPUS_KEY)
    real = CorpusReadCache._entry
    def failing_stage(self, rid, **kwargs):
        if self.sealed and not kwargs.get('receipt_only'):
            raise OSError('synthetic staging cache read failed')
        return real(self, rid, **kwargs)
    monkeypatch.setattr(CorpusReadCache, '_entry', failing_stage)
    with pytest.raises(OSError, match='synthetic staging cache read failed'):
        ingest.run(store, tmp_path / 'working.sqlite', now=NOW,
                   generation_identity=IDENTITY)
    assert store.get_bytes(contract.CORPUS_KEY) == before
    assert json.loads(store.get_bytes(catalog.CATALOG_KEY))['producer_generation']['state'] == 'BUILDING'


def test_actual_generation_planned_new_receipt_keeps_native_prefix_until_next_derivative(seeded, tmp_path, monkeypatch):
    store, doc = seeded
    _seed_real_corpus(store, tmp_path)
    rid, digest = 'new-planned-receipt', 'e' * 64
    item = {'id': rid, 'title': 'New pending receipt', 'institution': 'Desk',
            'published_at': NOW.isoformat(), 'summary_points': []}
    text = 'newnativeprefix ' + 'alpha ' * 11000 + ' nextgenerationtail'
    monkeypatch.setattr(ingest, '_list_inbox_pdfs', lambda _: ['research_inbox/new.pdf'])
    def new_row(_store, conn, _key, **kwargs):
        facts = {'content_sha256': digest, 'text_layer': 'full'}
        corpus.upsert(conn, item, text, facts=facts)
        return {'status': 'ingested', 'item': item, 'title_source': 'sidecar', 'facts': facts}
    monkeypatch.setattr(ingest, '_ingest_one', new_row)
    monkeypatch.setattr(fulltext_writer, 'materialize_pending', lambda *a, **k: {'aborted': None})
    assert store.get_bytes(fulltext_store.receipt_key(rid)) is None
    result = ingest.run(store, tmp_path / 'working.sqlite', now=NOW,
                        checkpoint_every=0, generation_identity=IDENTITY)
    assert result.get('error') is None, result
    assert result['generation_complete'] is True
    assert fulltext_store.parse_receipt_digest(store.get_bytes(fulltext_store.receipt_key(rid)), rid) == digest
    p = tmp_path / 'published-read.sqlite';p.write_bytes(store.get_bytes(contract.CORPUS_KEY))
    conn = corpus.open_db(p)
    try:
        assert [row['id'] for row in corpus.search(conn, 'newnativeprefix')] == [rid]
        assert corpus.search(conn, 'nextgenerationtail') == []
        assert conn.execute('SELECT fulltext_binding FROM documents WHERE doc_id=?', (rid,)).fetchone()[0] is None
    finally:
        conn.close()

def test_existing_oversize_catalog_runs_a_real_generation(seeded):
    """BEGIN/checkpoint/COMPLETE over an existing >16 KiB committed catalog."""
    store, doc = seeded
    doc["synthetic_padding"] = "x" * (24 * 1024)
    assert store.put_bytes(catalog.CATALOG_KEY, json.dumps(doc).encode())
    store.events.clear()
    session = writer.ProducerGenerationSession.begin(store, doc, IDENTITY, now=NOW)
    wrapped = writer.FencedProducerStore(store, session)
    wrapped.put_bytes(contract.CORPUS_KEY, b"synthetic corpus")
    assert catalog.publish(wrapped, doc, now=NOW).published
    record = json.loads(session.complete(doc, now=NOW))["producer_generation"]
    assert record["state"] == "COMPLETE"
    stored = json.loads(store.get_bytes(catalog.CATALOG_KEY))["producer_generation"]
    assert stored["state"] == "COMPLETE"
    assert len(store.get_bytes(catalog.CATALOG_KEY)) > 16 * 1024


# Canonical catalog CAS must use the existing producer allocation.
CATALOG_KEY = "research_vault/catalog.json"
CATALOG_ALLOWANCE = 16 * 1024 * 1024
LEGACY_LIMIT = HARD_MAX_STRICT_CONDITIONAL_OBJECT_BYTES
COMMITTED_CATALOG_BYTES = 3_598_794  # actual committed production catalog size


def _store(tmp_path):
    return LocalStore(tmp_path / "store")


def _synthetic_catalog(target_bytes: int) -> bytes:
    """One deterministic synthetic catalog of an exact serialized size."""
    doc = {"schema": "synthetic-catalog", "count": 2959, "items": []}
    prefix = json.dumps(doc, separators=(",", ":"))[:-1]
    member = '"synthetic_padding":"'
    padding = target_bytes - len(prefix) - len(",") - len(member) - len('"}')
    assert padding > 0, target_bytes
    raw = (prefix + "," + member + "x" * padding + '"}').encode()
    assert len(raw) == target_bytes
    json.loads(raw)  # stays one valid JSON document
    return raw


def _seed(store, key, body):
    assert store.put_bytes(key, body)
    assert store.get_bytes(key) == body


def test_committed_size_catalog_conditional_write_succeeds(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(COMMITTED_CATALOG_BYTES)
    _seed(store, CATALOG_KEY, original)
    version = LocalStore._local_version(original)
    # The producer reads the predecessor through the catalog allocation.
    readback = store.get_bytes_strict_bounded_versioned(CATALOG_KEY, CATALOG_ALLOWANCE)
    assert readback.data == original
    assert readback.version == version
    replacement = _synthetic_catalog(COMMITTED_CATALOG_BYTES + 11)
    assert store.put_bytes_strict_conditional(
        CATALOG_KEY, replacement, expected_version=version)
    assert store.get_bytes(CATALOG_KEY) == replacement
    assert store.get_bytes_strict_bounded_versioned(
        CATALOG_KEY, CATALOG_ALLOWANCE).version == LocalStore._local_version(replacement)


def test_stale_and_create_only_expectations_never_touch_oversize_catalog(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(COMMITTED_CATALOG_BYTES)
    _seed(store, CATALOG_KEY, original)
    stale = LocalStore._local_version(b"stale synthetic predecessor")
    assert not store.put_bytes_strict_conditional(
        CATALOG_KEY, b"never", expected_version=stale)
    assert not store.put_bytes_strict_conditional(
        CATALOG_KEY, b"never", expected_version=None)
    assert store.get_bytes(CATALOG_KEY) == original


def test_exact_catalog_allowance_boundary_still_succeeds(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(CATALOG_ALLOWANCE)
    _seed(store, CATALOG_KEY, original)
    assert store.put_bytes_strict_conditional(
        CATALOG_KEY, b"replacement at the exact allowance",
        expected_version=LocalStore._local_version(original))


def test_catalog_allowance_ends_at_the_producer_allocation(tmp_path):
    store = _store(tmp_path)
    original = _synthetic_catalog(CATALOG_ALLOWANCE + 1)
    _seed(store, CATALOG_KEY, original)
    with pytest.raises(BoundedReadTooLarge):
        store.put_bytes_strict_conditional(
            CATALOG_KEY, b"never", expected_version=LocalStore._local_version(original))
    assert store.get_bytes(CATALOG_KEY) == original


@pytest.mark.parametrize("key", [
    "research_vault/nested/catalog.json",
    "research_vault/catalog.json.bak",
    "research_vault/CATALOG.json",
    "research_inbox/catalog.json",
])
def test_noncanonical_keys_keep_the_legacy_ceiling(tmp_path, key):
    store = _store(tmp_path)
    original = b"p" * (LEGACY_LIMIT + 1)
    _seed(store, key, original)
    version = LocalStore._local_version(original)
    with pytest.raises(BoundedReadTooLarge):
        store.put_bytes_strict_conditional(key, b"never", expected_version=version)
    assert store.get_bytes(key) == original
    # Below the legacy ceiling the same key still conditionally writes.
    small = b"within the legacy ceiling"
    _seed(store, key, small)
    assert store.put_bytes_strict_conditional(
        key, b"replacement below the legacy ceiling",
        expected_version=LocalStore._local_version(small))


def test_catalog_allowance_matches_the_producer_constant():
    from engine.research_vault import producer_generation
    from engine.research_vault import r2_store
    assert r2_store._CONDITIONAL_CATALOG_MAX_BYTES == producer_generation.CATALOG_MAX_BYTES
