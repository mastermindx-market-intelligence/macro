"""Bounded synthetic mechanism tests; original-parent custody is not simulated proof."""
from datetime import timedelta
import hashlib
import json
from pathlib import Path

import pytest

from engine.research_vault import catalog, producer_generation as contract
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
