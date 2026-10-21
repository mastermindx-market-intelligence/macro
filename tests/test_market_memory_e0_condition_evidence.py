"""Sealed E0 condition evidence over the real retained-owner capture fixtures."""
import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest

from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_operating_cortex_service as service
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.research_factory import market_memory_e0_baselines as baselines
from engine.research_factory import market_memory_e0_condition_evidence as evidence
from tests.market_memory_e0_fixtures import CUTOFF, Policy, capture, load, owner

ACCESS = (cohort.RetainedContextAccessError, features.EpisodeFeatureAccessError)
REDACTED_KEYS = {"schema", "authority", "source_cards", "state_differences",
                 "explicit_method_identity_redacted", "actual_blinding_established", "limitations"}
SYNTHESIS_ACTIONS = ("read_real_synthesis_source", "use_retained_house_output_for_evidence_synthesis",
                     "disclose_real_synthesis_source")


class DenyContext(Policy):
    def __init__(self, context_id, actions):
        super().__init__()
        self.context_id = context_id
        self.actions = frozenset(actions)

    def check(self, action, resource):
        super().check(action, resource)
        if action in self.actions and (resource == self.context_id or (
                isinstance(resource, dict) and resource.get("context_id") == self.context_id)):
            raise PermissionError("context_revoked:" + self.context_id)


@pytest.fixture()
def chain(tmp_path, monkeypatch):
    stored = [capture(tmp_path, monkeypatch, session=session, growth=growth) for session, growth in (
        ("2026-08-10", 0.2), ("2026-08-11", 0.8), ("2026-08-12", 0.2), ("2026-08-21", 0.2))]
    reader, pin = owner(tmp_path)
    query = stored[2]
    feature = features.read_episode_feature_capability(reader, pin,
        query_id=query.capture_receipt["query_id"], subject_id=query.packet["subject"]["subject_id"],
        query_cutoff=CUTOFF, policy=Policy())
    selections = baselines.build_condition_selections(load(reader, pin, query), feature,
        policy=Policy(), k=1, method=retrieval.RetainedContextMethodSpec(0, 0, "historical_hypothetical"))
    return SimpleNamespace(stored=stored, reader=reader, pin=pin, selections=selections)


def _sealed(chain):
    return evidence.build_condition_evidence(chain.selections, chain.reader, chain.pin, policy=Policy())


def _items(payload):
    return {item["condition"]: item for item in payload["conditions"]}


def test_sealed_payload_binds_real_sources_and_disclaims_study(chain):
    payload = evidence.disclose_condition_evidence(_sealed(chain), policy=Policy())
    assert payload["schema"] == "research_factory.market_memory_e0_condition_evidence.v1"
    assert payload["authority"] == "display_only"
    assert payload["cost_scope"] == "joint_native_source_union_not_isolated_condition_cost"
    assert payload["source_reader_sha256"] == service._IMPORTED_SOURCE_SHA256
    assert [item["condition"] for item in payload["conditions"]] == list(evidence.CONDITIONS)
    assert not any(payload[key] for key in ("study_admitted", "labels_read", "provider_invoked",
                                            "evaluation_performed", "runtime_writes"))
    assert payload["limitations"] == ["original_house_output_not_constituent_truth",
        "subsequent_outcomes_not_attached", "semantic_entailment_not_assessed",
        "exact_registered_task_and_study_admission_not_established",
        "independent_reviewers_and_blinding_not_established"]


def test_no_memory_returns_the_query_card_only(chain):
    payload = evidence.disclose_condition_evidence(_sealed(chain), policy=Policy())
    item = _items(payload)["no_memory"]
    assert item["status"] == "WITHHELD_BY_CONDITION" and item["returned"] == 0
    assert [card["context_id"] for card in item["source_cards"]] == [payload["query"]["context_id"]]
    assert item["state_differences"] == []


def test_recency_takes_newer_session_while_fixed_keeps_closer_older(chain):
    items = _items(evidence.disclose_condition_evidence(_sealed(chain), policy=Policy()))
    sel = _items(baselines.disclose_condition_selections(chain.selections, policy=Policy()))
    newer, older = sel["recency"]["selected"][0], sel["fixed_l1"]["selected"][0]
    assert (newer["source_session"], newer["context_id"]) == ("2026-08-11", chain.stored[1].packet["context_id"])
    assert (older["source_session"], older["context_id"]) == ("2026-08-10", chain.stored[0].packet["context_id"])
    assert [card["context_id"] for card in items["recency"]["source_cards"][1:]] == [newer["context_id"]]
    assert [card["context_id"] for card in items["fixed_l1"]["source_cards"][1:]] == [older["context_id"]]
    growth = [d for d in items["recency"]["state_differences"] if d["field"] == "growth_score"]
    assert [(d["context_id"], d["query_value"], d["neighbor_value"]) for d in growth] == [
        (newer["context_id"], 0.2, 0.8)]
    assert not [d for d in items["fixed_l1"]["state_differences"] if d["field"] == "growth_score"]


def test_every_card_quotes_exactly_five_exact_json_spans(chain):
    payload = evidence.disclose_condition_evidence(_sealed(chain), policy=Policy())
    for item in payload["conditions"]:
        for card in item["source_cards"]:
            assert [fact["field"] for fact in card["facts"]] == list(service.FIELDS)
            for fact in card["facts"]:
                assert fact["citation"]["json_pointer"] == "/state/" + fact["field"]
                quote = fact["citation"]["quoted_json"]
                assert quote == cohort.canonical(fact["value"]).decode("utf-8")
                assert json.loads(quote) == fact["value"]
                assert fact["citation"]["span_sha256"] == sha256(quote.encode("utf-8")).hexdigest()


def test_denominator_and_selection_binding_preserved(chain):
    payload = evidence.disclose_condition_evidence(_sealed(chain), policy=Policy())
    sel = baselines.disclose_condition_selections(chain.selections, policy=Policy())
    assert payload["denominator"] == sel["denominator"] == {
        "expected_captures": 4, "accounted_captures": 4, "eligible_representatives": 2}
    shared = ("query", "query_owner", "membership_sha256", "condition_selection_sha256",
              "fixed_selection_sha256", "method_spec", "requested_k")
    assert all(payload[key] == sel[key] for key in shared) and payload["requested_k"] == 1
    assert payload["accounting"] == sel["accounting"]


def test_method_redacted_view_omits_condition_and_method(chain):
    capability = _sealed(chain)
    payload = evidence.disclose_condition_evidence(capability, policy=Policy())
    for condition in evidence.CONDITIONS:
        view = evidence.disclose_method_redacted_view(capability, condition=condition, policy=Policy())
        assert set(view) == REDACTED_KEYS
        assert view["schema"] == "research_factory.market_memory_e0_method_redacted_sources.v1"
        assert (view["explicit_method_identity_redacted"] is True
                and view["actual_blinding_established"] is False)
        assert view["limitations"] == ["source_dates_and_counts_may_reveal_condition",
            "original_house_output_not_constituent_truth", "subsequent_outcomes_not_attached",
            "no_semantic_causal_predictive_or_action_authority"]
        assert view["source_cards"] == _items(payload)[condition]["source_cards"]
        assert view["state_differences"] == _items(payload)[condition]["state_differences"]


def test_revoked_unreturned_candidate_blocks_before_any_owner_read(chain, monkeypatch):
    cached = _sealed(chain)
    sel = baselines.disclose_condition_selections(chain.selections, policy=Policy())
    eligible = {row["context_id"] for row in sel["accounting"] if row["reason"] == "numerically_eligible"}
    fixed_ids = [ref["context_id"] for ref in _items(sel)["fixed_l1"]["selected"]]
    assert eligible.difference(fixed_ids) == {chain.stored[1].packet["context_id"]}
    reads = []
    monkeypatch.setattr(service, "_read_source_cards", lambda *args, **kwargs: reads.append(args))
    revoked = DenyContext(chain.stored[1].packet["context_id"], ("compare_retained_macro_feature",))
    with pytest.raises(features.EpisodeFeatureAccessError):
        baselines.disclose_condition_selections(chain.selections, policy=revoked)
    with pytest.raises(features.EpisodeFeatureAccessError):
        evidence.disclose_method_redacted_view(cached, condition="no_memory", policy=revoked)
    with pytest.raises(features.EpisodeFeatureAccessError):
        evidence.build_condition_evidence(chain.selections, chain.reader, chain.pin, policy=revoked)
    assert reads == []


def test_selected_source_revocation_refuses_read_and_cached_payload(chain, monkeypatch):
    sel = baselines.disclose_condition_selections(chain.selections, policy=Policy())
    denied = DenyContext(_items(sel)["fixed_l1"]["selected"][0]["context_id"], SYNTHESIS_ACTIONS)
    capability = _sealed(chain)
    assert evidence.disclose_condition_evidence(capability, policy=Policy())
    monkeypatch.setattr(type(chain.reader), "read_pinned_capture_projections",
                        lambda *a, **k: pytest.fail("revoked source reached payload read"))
    with pytest.raises(ACCESS):
        evidence.disclose_condition_evidence(capability, policy=denied)
    reads, real = [], service._read_source_cards
    monkeypatch.setattr(service, "_read_source_cards",
                        lambda *args, **kwargs: reads.append(args) or real(*args, **kwargs))
    with pytest.raises(ACCESS):
        evidence.build_condition_evidence(chain.selections, chain.reader, chain.pin, policy=denied)
    assert len(reads) == 1


def test_changed_generation_and_forged_inputs_are_refused(chain):
    tampered = replace(chain.pin, generation_sha256="f" * 64)
    with pytest.raises((pit.MarketMemoryPITError, ValueError)):
        evidence.build_condition_evidence(chain.selections, chain.reader, tampered, policy=Policy())
    payload = evidence.disclose_condition_evidence(_sealed(chain), policy=Policy())
    with pytest.raises(evidence.E0ConditionEvidenceError, match="sealed_condition_evidence_required"):
        evidence.disclose_condition_evidence(payload, policy=Policy())
    with pytest.raises(evidence.E0ConditionEvidenceError, match="sealed_condition_evidence_required"):
        evidence.E0ConditionEvidence(cohort.canonical(payload), chain.selections, b"[]")
    with pytest.raises(evidence.E0ConditionEvidenceError):
        evidence.disclose_method_redacted_view(payload, condition="no_memory", policy=Policy())
    with pytest.raises(evidence.E0ConditionEvidenceError, match="registered_condition_required"):
        evidence.disclose_method_redacted_view(_sealed(chain), condition="memory_free", policy=Policy())
