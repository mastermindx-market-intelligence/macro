"""W5B source closure on the real trusted writer, with adversarial consumers."""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from hashlib import sha256

import pytest

from engine.neuralweb import market_memory_operating_cortex as synthetic
from engine.neuralweb import market_memory_operating_cortex_service as service
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_episode_retrieval import corpus, result
from tests.test_market_memory_retained_context_cohort import owner, capture


@pytest.fixture
def evidence(tmp_path, monkeypatch):
    population, query, a, b, q = corpus(tmp_path, monkeypatch)
    selection, selected = result(population, query)
    reader, pin = owner(tmp_path)
    return selection, selected, reader, pin, a, b, q


def build(evidence, *, policy=None, claims=()):
    selection, _, reader, pin, *_ = evidence
    policy = Policy() if policy is None else policy
    cap = service.build_real_evidence_packet(selection, reader, pin, policy=policy, claims=claims)
    return cap, service.disclose_real_evidence_packet(cap, policy=policy)


def test_exact_selected_original_byte_spans_and_factual_limits(evidence):
    _, value = build(evidence)
    selection, selected, reader, pin, a, b, q = evidence
    assert value["selection_sha256"] == selected["selection_sha256"]
    assert value["denominator"] == selected["denominator"]
    assert value["accounting"] == selected["accounting"]
    assert value["owner"]["generation_id"] == pin.generation_id
    assert {card["context_id"] for card in value["source_cards"]} == {
        a.packet["context_id"], b.packet["context_id"], q.packet["context_id"]}
    for card, stored in ((card, next(s for s in (a, b, q) if s.packet["context_id"] == card["context_id"]))
                         for card in value["source_cards"]):
        original = reader.read_macro_feature_from_pinned_generation(pin, query_id=stored.capture_receipt["query_id"])
        body = cohort.canonical(original)
        for fact in card["facts"]:
            cite = fact["citation"]
            span = body[cite["start_byte"]:cite["end_byte_exclusive"]]
            assert sha256(body).hexdigest() == cite["source_sha256"]
            assert sha256(span).hexdigest() == cite["span_sha256"]
            assert span.decode() == cite["quoted_json"]
            assert json.loads(span) == fact["value"] == original["state"][fact["field"]]
            assert fact["structural_source_closure"] is True
            assert fact["underlying_component_truth_authenticated"] is False
    assert value["state_differences"]
    assert all(row["meaning"] == "different_dated_outputs_not_a_logical_contradiction"
               for row in value["state_differences"])
    assert not any(value["claims"].values())
    assert synthetic.INPUT_PROFILE == "synthetic_fixture_only"


def test_cited_false_narrative_never_becomes_semantically_supported(evidence):
    context = evidence[-1].packet["context_id"]
    claim = service.AnalystClaim("wrong-causal-claim", "This snapshot proves guaranteed positive returns.",
                                (context,), ("growth_score",), "A loss would contradict the assertion.")
    _, value = build(evidence, claims=(claim,))
    audit = value["analyst_claim_audit"][0]
    assert audit["structural_source_closure"] is True
    assert len(audit["citation_refs"]) == 1
    assert audit["citation_refs"][0]["context_id"] == context
    assert audit["citation_refs"][0]["json_pointer"] == "/state/growth_score"
    assert audit["entailment"] == "not_assessed"
    assert audit["unsupported_status"] == "unassessed_not_supported"
    assert audit["contradictory_evidence_review"] == "not_performed"
    assert audit["falsifier_status"] == "named_not_tested"
    assert "contradictory_external_evidence_not_assessed" in value["missing_evidence"]


def test_unselected_claim_refused_before_original_reads(evidence, monkeypatch):
    claim = service.AnalystClaim("outside", "Unselected source", ("mmctx_" + "f" * 64,), ("quad",))
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_receipt",
                        lambda *a, **k: pytest.fail("unselected source read"))
    with pytest.raises(service.RealEvidenceError, match="unselected"):
        build(evidence, claims=(claim,))


@pytest.mark.parametrize("action", ["read_real_synthesis_capture_metadata", "read_real_synthesis_source",
                                     "use_retained_house_output_for_evidence_synthesis"])
def test_named_synthesis_rights_before_payload(evidence, monkeypatch, action):
    monkeypatch.setattr(trusted, "_load_stored_with_feature",
                        lambda *a, **k: pytest.fail("denied synthesis payload read"))
    with pytest.raises(cohort.RetainedContextAccessError):
        build(evidence, policy=Policy({action}))


def test_actual_source_resource_before_payload_and_cached_disclosure(evidence, monkeypatch):
    cap, value = build(evidence)
    denied_source = evidence[-1].capture_receipt["source_receipt_ids"][0]
    class DeniedSource(Policy):
        def check(self, action, resource):
            if action in ("read_real_synthesis_source", "disclose_real_synthesis_source"):
                if denied_source in resource.get("source_receipt_ids", []):
                    raise PermissionError("synthesis source revoked")
            return super().check(action, resource)
    monkeypatch.setattr(trusted, "_load_stored_with_feature",
                        lambda *a, **k: pytest.fail("revoked source read"))
    with pytest.raises(cohort.RetainedContextAccessError):
        build(evidence, policy=DeniedSource())
    with pytest.raises(cohort.RetainedContextAccessError):
        service.disclose_real_evidence_packet(cap, policy=DeniedSource())


def test_revocation_after_payload_prevents_result(evidence, monkeypatch):
    class RevokingPolicy(Policy):
        revoked = False
        def check(self, action, resource):
            if self.revoked and action == "disclose_real_synthesis_source":
                raise PermissionError("revoked before return")
            return super().check(action, resource)
    policy = RevokingPolicy()
    original = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    def revoke(*args, **kwargs):
        rows = original(*args, **kwargs)
        policy.revoked = True
        return rows
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", revoke)
    with pytest.raises(cohort.RetainedContextAccessError):
        build(evidence, policy=policy)


def test_changed_original_feature_cannot_forge_a_span(evidence, monkeypatch):
    original = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_projections
    def corrupt(*args, **kwargs):
        rows = original(*args, **kwargs)
        feature = copy.deepcopy(rows[0].feature)
        feature["state"]["growth_score"] = 0.99
        return (replace(rows[0], feature=feature), *rows[1:])
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections", corrupt)
    with pytest.raises(service.RealEvidenceError, match="feature_bytes_mismatch"):
        build(evidence)


def test_different_generation_and_raw_dict_never_authorize(evidence):
    selection, selected, reader, pin, *_ = evidence
    with pytest.raises(service.RealEvidenceError, match="generation_mismatch"):
        service.build_real_evidence_packet(selection, reader, replace(pin, generation_sha256="f" * 64), policy=Policy())
    with pytest.raises(Exception, match="capability_required"):
        service.build_real_evidence_packet(selected, reader, pin, policy=Policy())
    cap, value = build(evidence)
    with pytest.raises(service.RealEvidenceError, match="owner_verified"):
        service.disclose_real_evidence_packet(value, policy=Policy())
    with pytest.raises(service.RealEvidenceError, match="owner_verified"):
        service.RealEvidenceCapability(b"{}", selection, [])


def test_payload_and_output_bounds_are_fail_closed(evidence, monkeypatch):
    monkeypatch.setattr(service, "MAX_OWNER_PAYLOAD_BYTES", 1)
    monkeypatch.setattr(trusted, "_load_stored_with_feature",
                        lambda *a, **k: pytest.fail("oversized payload read"))
    with pytest.raises(service.RealEvidenceError, match="owner_read_byte_bound"):
        build(evidence)


def test_equal_copy_pin_walks_once_and_accounts_every_owner_read(evidence, monkeypatch):
    original = pit._read_canonical_object
    reads = []
    def measured(*args, **kwargs):
        result = original(*args, **kwargs)
        reads.append((kwargs["label"], len(result[1])))
        return result
    monkeypatch.setattr(pit, "_read_canonical_object", measured)
    values = []
    for pin in (evidence[3], replace(evidence[3])):
        reads.clear()
        with pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024) as budget:
            cap = service.build_real_evidence_packet(evidence[0], evidence[2], pin, policy=Policy())
        values.append(service.disclose_real_evidence_packet(cap, policy=Policy()))
        assert sum(label == "trusted store HEAD" for label, _ in reads) == 1
        assert budget.bytes_read == sum(size for _, size in reads)
        assert budget.objects_opened == len(reads)
        assert any("ancestor" in label for label, _ in reads)
    assert values[0] == values[1]


def test_generation_metadata_denial_precedes_pin_reads(evidence, monkeypatch):
    denied = []
    class Deny(Policy):
        def check(self, action, resource):
            if action == "read_real_synthesis_generation_metadata":
                assert "subject_id" not in resource
                assert resource["requested_subject_id"] == evidence[-1].packet["subject"]["subject_id"]
                denied.append(action)
                raise PermissionError("generation denied")
            return super().check(action, resource)
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation",
                        lambda *a, **k: pytest.fail("denied generation was read"))
    with pytest.raises(Exception, match="source_usage_not_admitted"):
        build(evidence, policy=Deny())
    assert denied == ["read_real_synthesis_generation_metadata"]


def test_nested_budget_cannot_reset_parent_and_failed_bytes_are_charged(tmp_path):
    path = tmp_path / "object.json"
    body = b'{"a":1}'
    path.write_bytes(body)
    with pit.bounded_owner_reads(maximum_bytes=len(body) + 1) as outer:
        with pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024) as inner:
            pit._read_canonical_object(path, limit=100, label="test")
            with pytest.raises(pit.OwnerReadBudgetError):
                pit._read_canonical_object(path, limit=100, label="test")
        assert outer.bytes_read == inner.bytes_read == len(body)
    path.write_bytes(b'{"a": 1}')
    with pit.bounded_owner_reads(maximum_bytes=100) as budget:
        with pytest.raises(pit.MarketMemoryStoreError, match="canonical"):
            pit._read_canonical_object(path, limit=100, label="test")
        assert budget.bytes_read == path.stat().st_size
    # The failed scope is reset; ordinary legacy reads retain their old behavior.
    path.write_bytes(body)
    assert pit._read_canonical_object(path, limit=100, label="test")[1] == body


def test_cumulative_budget_refuses_before_crossing_request_ceiling(evidence, monkeypatch):
    with pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024) as measured:
        build(evidence)
    monkeypatch.setattr(service, "MAX_OWNER_PAYLOAD_BYTES", measured.bytes_read - 1)
    with pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024) as measured:
        with pytest.raises(service.RealEvidenceError, match="owner_read_byte_bound"):
            build(evidence)
    assert measured.bytes_read <= service.MAX_OWNER_PAYLOAD_BYTES


def test_output_byte_bound_and_unique_claim_bound(evidence, monkeypatch):
    claim = service.AnalystClaim("duplicate", "Test", (evidence[-1].packet["context_id"],), ("quad",))
    with pytest.raises(service.RealEvidenceError, match="unique_analyst_claims"):
        build(evidence, claims=(claim, claim))
    monkeypatch.setattr(service, "MAX_PACKET_BYTES", 1)
    with pytest.raises(service.RealEvidenceError, match="packet_byte_bound"):
        build(evidence)


def test_future_append_and_return_mutation_do_not_rewrite_original_selection(evidence, tmp_path, monkeypatch):
    cap, value = build(evidence)
    original = copy.deepcopy(value)
    value["source_cards"].clear()
    capture(tmp_path, monkeypatch, session="2026-08-21", growth=0.5)
    assert service.disclose_real_evidence_packet(cap, policy=Policy()) == original
    assert build(evidence)[1] == original


def test_metadata_resource_does_not_assert_unread_subject(evidence):
    policy = Policy()
    build(evidence, policy=policy)
    metadata = [r for a, r in policy.calls if a == "read_real_synthesis_capture_metadata"]
    assert metadata and all("subject_id" not in r for r in metadata)
    sources = [r for a, r in policy.calls if a in ("read_real_synthesis_source", "disclose_real_synthesis_source")]
    assert sources and all(r["subject_id"] == evidence[-1].packet["subject"]["subject_id"] for r in sources)
    assert all(r["source_receipt_ids"] and r["packet_sha256"] and r["feature_sha256"] for r in sources)
