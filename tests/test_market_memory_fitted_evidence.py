"""Exact source evidence for one sealed native fitted retrieval selection.

The positive path uses the real published fitted producer classes and the
existing synthetic trusted-owner fixtures. The only substituted owner is the
selected training registration: the existing native_training fixture replaces
it with an explicit fixture stand-in. No installed fit, live fit, control
loader, persistence, study or admission path runs here, and no production
store is read.
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace

import pytest

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_episode_retrieval as baseline
from engine.neuralweb import market_memory_fitted_evidence as evidence
from engine.neuralweb import market_memory_fitted_normalization as fitted
from engine.neuralweb import market_memory_fitted_retrieval as retrieval
from engine.neuralweb import market_memory_operating_cortex_service as cortex
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_trusted as trusted
from engine.research_factory import market_memory_fitted_use as use
from tests.test_market_memory_episode_features import Policy
from tests.test_market_memory_fitted_normalization import native_training
from tests.test_market_memory_retained_context_cohort import CUTOFF, capture, load, owner

METHOD = baseline.RetainedContextMethodSpec(0, 0, "historical_hypothetical")


def fitted_selection(fixture, *, k=32, method=METHOD):
    """Run the real native fitted producer over the synthetic owner corpus."""
    population, query, window, *_ = fixture
    normalizer = fitted.fit_registered_normalizer(window, population, policy=Policy())
    cap = retrieval.retrieve_fitted_contexts(normalizer, population, query, policy=Policy(),
                                             k=k, eligibility=method)
    return cap, retrieval.disclose_fitted_retrieval(cap, policy=Policy())


class _BlockedProducer:
    """Hide one native module so the missing-dependency refusal can be tested."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname == "engine.neuralweb.market_memory_fitted_retrieval":
            raise ImportError("native fitted producer is absent on this branch")
        return None


def test_native_fitted_selection_yields_exact_owner_source_evidence(native_training, tmp_path):
    cap, value = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    packet = evidence.disclose_fitted_evidence_packet(capability, policy=Policy())

    assert packet["retrieval_id"] == value["retrieval_id"]
    assert packet["selection_sha256"] == value["selection_sha256"]
    assert packet["query"] == value["query"]
    assert packet["index_id"] == value["index_id"]
    assert packet["index_content_sha256"] == value["index_content_sha256"]
    assert packet["membership_sha256"] == value["membership_sha256"]
    assert packet["method_id"] == value["method"]["method_id"]
    assert packet["method"] == value["method"]
    assert packet["accounting"] == value["accounting"]
    assert packet["denominator"] == value["denominator"]
    assert packet["status"] == value["status"]

    # The query source card is first; the fitted neighbours follow in the
    # fitted ranking order.
    assert [card["role"] for card in packet["source_cards"]] == (
        ["query"] + ["selected_neighbor"] * len(value["selected"]))
    assert [row["context_id"] for row in packet["selected"]] == [
        item["candidate"]["context_id"] for item in value["selected"]]
    assert packet["source_cards"][0]["capture_id"] == value["query"]["capture_id"]

    # Two distinct owner digests are bound here. The fitted candidate names the
    # episode-feature projection that was ranked; the citation names the exact
    # original feature bytes that the source card quotes.
    for row, card, item in zip(packet["selected"], packet["source_cards"][1:],
                                value["selected"], strict=True):
        citation = card["facts"][0]["citation"]
        assert row["fitted_feature_sha256"] == item["candidate"]["feature_sha256"]
        assert row["owner_feature_sha256"] == citation["source_sha256"]
        assert citation["snapshot_id"] == "mmsnap_" + citation["source_sha256"]
        assert card["capture_id"] == row["capture_id"]
        assert card["context_id"] == row["context_id"]
        assert card["packet_sha256"] == row["packet_sha256"]
        assert card["evidence_basis"] == "retained_original_house_output"
        assert row["distance_q18"] == item["distance_q18"]

    # The owner's own missing features and source receipts are carried
    # through unchanged; nothing is imputed or dropped.
    receipts = {}
    for entry in pin.captures:
        path = next(reader.root.rglob(entry.query_id + ".json"))
        receipts[entry.capture_id] = json.loads(path.read_text())
    for card in packet["source_cards"]:
        receipt = receipts[card["capture_id"]]
        assert card["missing_feature_ids"] == receipt["missing_feature_ids"]
        assert card["source_receipt_ids"] == receipt["source_receipt_ids"]
        assert card["packet_sha256"] == receipt["packet_sha256"]
    assert packet["source_cards"][0]["missing_feature_ids"]


def test_fitted_selection_diverges_from_the_baseline_top_one(native_training, tmp_path, monkeypatch):
    population, _, window, a, b, old_query = native_training
    normalizer = fitted.fit_registered_normalizer(window, population, policy=Policy())
    far_same_category = capture(tmp_path, monkeypatch, session="2026-08-09",
                                growth=0.9, cycle="early")
    new_query = capture(tmp_path, monkeypatch, session="2026-08-13", growth=0.2, cycle="early")
    reader, pin = owner(tmp_path)
    new_population = load(reader, pin, new_query)
    query = features.read_episode_feature_capability(
        reader, pin, query_id=new_query.capture_receipt["query_id"],
        subject_id=new_query.packet["subject"]["subject_id"],
        query_cutoff=CUTOFF, policy=Policy())
    cap = retrieval.retrieve_fitted_contexts(normalizer, new_population, query, policy=Policy(),
                                             k=1, eligibility=METHOD)
    value = retrieval.disclose_fitted_retrieval(cap, policy=Policy())
    baseline_value = baseline.disclose_episode_retrieval(cap._eligibility, policy=Policy())
    assert baseline_value["selected"][0]["candidate"]["context_id"] == far_same_category.packet["context_id"]
    assert value["selected"][0]["candidate"]["context_id"] == old_query.packet["context_id"]

    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    packet = evidence.disclose_fitted_evidence_packet(capability, policy=Policy())
    assert [row["context_id"] for row in packet["selected"]] == [old_query.packet["context_id"]]
    assert packet["selected"][0]["context_id"] != baseline_value["selected"][0]["candidate"]["context_id"]
    assert [card["context_id"] for card in packet["source_cards"]] == [
        new_query.packet["context_id"], old_query.packet["context_id"]]
    assert packet["denominator"]["eligible_representatives"] == 4


def test_every_packet_claim_remains_explicitly_false(native_training, tmp_path):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    packet = evidence.disclose_fitted_evidence_packet(capability, policy=Policy())
    assert set(packet["claims"]) == {
        "semantic_entailment_established", "causal_claim_established",
        "forecast_skill_established", "independent_episodes_established",
        "training_eligible", "promotion_eligible",
        "operational_source_admission_granted", "operational_study_admission",
        "action_admitted", "source_activated"}
    assert all(flag is False for flag in packet["claims"].values())
    assert packet["authority"] == dict(mm.AUTHORITY)
    assert packet["selection_claims"] == json.loads(cap._body)["claims"]
    for name in ("operational_study_admission", "historical_fit_existence_authenticated",
                 "historical_index_existence_authenticated"):
        assert packet["selection_claims"][name] is False
    assert "fitted_selection_better_than_baseline_not_established" in packet["missing_evidence"]


def test_only_the_native_sealed_producer_type_is_accepted(native_training, tmp_path):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)

    class Impostor:
        _body = cap._body
        _digest = cap._digest
        _seal = cap._seal

    baseline_capability = baseline.disclose_episode_retrieval(cap._eligibility, policy=Policy())
    for impostor in (Impostor(), baseline_capability, json.loads(cap._body),
                     {"selected": [], "query_owner": {}}):
        with pytest.raises(evidence.FittedEvidenceError,
                           match="exact_native_fitted_retrieval_capability_required"):
            evidence.build_fitted_evidence_packet(impostor, reader, pin, policy=Policy())


def test_unsealed_or_corrupted_native_selection_is_refused(native_training, tmp_path):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    object.__setattr__(cap, "_seal", None)
    with pytest.raises(retrieval.FittedRetrievalError):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


def test_wrong_generation_pin_and_missing_capture_are_refused(native_training, tmp_path):
    cap, value = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    with pytest.raises(evidence.FittedEvidenceError, match="exact_selection_generation_mismatch"):
        evidence.build_fitted_evidence_packet(cap, reader,
                                              replace(pin, generation_sha256="f" * 64),
                                              policy=Policy())
    selected = value["selected"][0]["candidate"]["capture_id"]
    trimmed = replace(pin, captures=tuple(entry for entry in pin.captures
                                          if entry.capture_id != selected))
    with pytest.raises(evidence.FittedEvidenceError, match="fitted_candidate_not_in_pinned_generation"):
        evidence.build_fitted_evidence_packet(cap, reader, trimmed, policy=Policy())


def test_duplicate_fitted_candidate_is_refused(native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    original = retrieval.disclose_fitted_retrieval

    def duplicated(capability, *, policy):
        disclosed = original(capability, policy=policy)
        disclosed["selected"] = disclosed["selected"] + disclosed["selected"][:1]
        return disclosed

    monkeypatch.setattr(retrieval, "disclose_fitted_retrieval", duplicated)
    with pytest.raises(evidence.FittedEvidenceError, match="duplicate_selected_context"):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


@pytest.mark.parametrize("change, expected", [
    ("feature_sha256", "fitted_candidate_feature_digest_mismatch"),
    ("projection_id", "fitted_candidate_feature_digest_mismatch"),
    ("context_id", "fitted_candidate_identity_mismatch"),
])
def test_wrong_fitted_candidate_feature_or_identity_is_refused(
        native_training, tmp_path, monkeypatch, change, expected):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    original = retrieval.disclose_fitted_retrieval

    def altered(capability, *, policy):
        disclosed = original(capability, policy=policy)
        candidate = disclosed["selected"][0]["candidate"]
        if change == "feature_sha256":
            candidate["feature_sha256"] = "f" * 64
        elif change == "projection_id":
            candidate["projection_id"] = "mmepisodefeatures_" + "f" * 64
        else:
            candidate["context_id"] = "mmctx_" + "f" * 64
        return disclosed

    monkeypatch.setattr(retrieval, "disclose_fitted_retrieval", altered)
    with pytest.raises(evidence.FittedEvidenceError, match=expected):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


@pytest.mark.parametrize("change, expected", [
    ("membership_sha256", "fitted_population_membership_mismatch"),
    ("query_owner", "query_owner_binding_mismatch"),
])
def test_wrong_fitted_membership_or_query_owner_is_refused(
        native_training, tmp_path, monkeypatch, change, expected):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    original = retrieval.disclose_fitted_retrieval

    def altered(capability, *, policy):
        disclosed = original(capability, policy=policy)
        if change == "membership_sha256":
            disclosed["membership_sha256"] = "f" * 64
        else:
            disclosed["query_owner"] = {**disclosed["query_owner"],
                                       "subject_id": "mmsecurity_" + "f" * 64}
        return disclosed

    monkeypatch.setattr(retrieval, "disclose_fitted_retrieval", altered)
    with pytest.raises(evidence.FittedEvidenceError, match=expected):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


def test_right_revoked_during_source_use_is_caught_by_the_final_recheck(native_training, tmp_path):
    _, _, _, a, b, _ = native_training
    cap, value = fitted_selection(native_training, k=1)
    selected = value["selected"][0]["candidate"]["context_id"]
    loser = b if selected == a.packet["context_id"] else a
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())

    class RevokeDuringSourceUse(Policy):
        """Revoke an unreturned pool row only once source use has begun."""

        revoked = False

        def check(self, action, resource):
            if action == "use_retained_house_output_for_evidence_synthesis":
                self.revoked = True
            if (self.revoked and action == "compare_retained_macro_feature"
                    and resource.get("query_id") == loser.capture_receipt["query_id"]):
                raise PermissionError("pool revoked while disclosing sources")
            super().check(action, resource)

    with pytest.raises(features.EpisodeFeatureAccessError):
        evidence.disclose_fitted_evidence_packet(capability, policy=RevokeDuringSourceUse())


def test_source_card_citation_must_match_the_owner_feature_digest(native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    original = cortex._read_source_cards

    def altered(*args, **kwargs):
        cards, resources = original(*args, **kwargs)
        cards[0]["facts"][0]["citation"]["source_sha256"] = "f" * 64
        return cards, resources

    monkeypatch.setattr(cortex, "_read_source_cards", altered)
    with pytest.raises(evidence.FittedEvidenceError, match="source_fact_feature_digest_mismatch"):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


def test_packet_body_must_still_bind_to_the_original_fitted_selection(native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    original = retrieval.disclose_fitted_retrieval

    def altered(disclosed_capability, *, policy):
        value = original(disclosed_capability, policy=policy)
        return {**value, "retrieval_id": "mmfittedretrieval_" + "f" * 64}

    monkeypatch.setattr(retrieval, "disclose_fitted_retrieval", altered)
    with pytest.raises(evidence.FittedEvidenceError, match="original_fitted_selection_changed"):
        evidence.disclose_fitted_evidence_packet(capability, policy=Policy())


def test_generation_metadata_is_authorized_before_the_pinned_index_is_used(native_training, tmp_path):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)

    class DenySecondGenerationMetadata(Policy):
        """The shared read path authorizes the generation metadata again.

        This module must have authorized it once on its own before it
        consulted the pinned generation index.
        """

        def __init__(self):
            super().__init__()
            self.seen = 0

        def check(self, action, resource):
            if action == "read_real_synthesis_generation_metadata":
                self.seen += 1
                if self.seen > 1:
                    raise PermissionError("generation metadata authorized twice")
            super().check(action, resource)

    with pytest.raises(cohort.RetainedContextAccessError):
        evidence.build_fitted_evidence_packet(cap, reader, pin,
                                              policy=DenySecondGenerationMetadata())


def test_source_disclosure_revocation_blocks_reuse(native_training, tmp_path):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())

    class Denied(Policy):
        def check(self, action, resource):
            if action in ("disclose_real_synthesis_source",
                          "use_retained_house_output_for_evidence_synthesis"):
                raise PermissionError("source use revoked")
            super().check(action, resource)

    with pytest.raises(cohort.RetainedContextAccessError):
        evidence.disclose_fitted_evidence_packet(capability, policy=Denied())


def test_unreturned_pool_revocation_blocks_disclosure(native_training, tmp_path):
    _, _, _, a, b, _ = native_training
    cap, value = fitted_selection(native_training, k=1)
    selected = value["selected"][0]["candidate"]["context_id"]
    loser = b if selected == a.packet["context_id"] else a

    class DeniedLoser(Policy):
        def check(self, action, resource):
            if (action == "compare_retained_macro_feature"
                    and resource.get("query_id") == loser.capture_receipt["query_id"]):
                raise PermissionError("unreturned use revoked")
            super().check(action, resource)

    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    with pytest.raises(features.EpisodeFeatureAccessError):
        evidence.disclose_fitted_evidence_packet(capability, policy=DeniedLoser())


def test_selected_training_owner_change_revokes_disclosure(native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    window = native_training[2]
    changed = use.TrainingWindowCapability(window._body, b"different-selected-owner",
                                          _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: changed)
    with pytest.raises(use.FittedUseError, match="window_changed"):
        evidence.disclose_fitted_evidence_packet(capability, policy=Policy())


def test_tampered_source_bytes_are_refused(native_training, tmp_path):
    cap, value = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    target = value["selected"][0]["candidate"]["capture_id"]
    entry = next(item for item in pin.captures if item.capture_id == target)
    receipt_path = next(reader.root.rglob(entry.query_id + ".json"))
    receipt = json.loads(receipt_path.read_text())
    feature_object = reader.root / receipt["feature_snapshot"]["object_key"]
    original = feature_object.read_bytes()
    feature_object.write_bytes(b"{}")
    try:
        with pytest.raises(pit.MarketMemoryStoreError):
            evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    finally:
        feature_object.write_bytes(original)


def test_aggregate_owner_read_bound_is_enforced(native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    monkeypatch.setattr(evidence, "MAX_OWNER_PAYLOAD_BYTES", 1)
    with pytest.raises(evidence.FittedEvidenceError, match="aggregate_owner_read_byte_bound_exceeded"):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


def test_owner_read_ceiling_is_the_existing_lexical_ceiling():
    assert evidence.MAX_OWNER_PAYLOAD_BYTES == 64 * 1024 * 1024
    assert cortex.MAX_OWNER_PAYLOAD_BYTES == evidence.MAX_OWNER_PAYLOAD_BYTES


def test_abstained_fitted_selection_is_kept_honest(native_training, tmp_path, monkeypatch):
    method = baseline.RetainedContextMethodSpec(2, 0, "historical_hypothetical")
    original = native_training[2]
    body = json.loads(original._body)
    body["eligibility_method_spec"] = method.disclosure()
    window = use.TrainingWindowCapability(retrieval.cohort.canonical(body),
                                          original._selection, _key=use._TOKEN)
    monkeypatch.setattr(use, "prepare_registered_training_window", lambda: window)
    fixture = (*native_training[:2], window, *native_training[3:])
    cap, value = fitted_selection(fixture, method=method)
    assert value["status"] == "ABSTAINED"
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    packet = evidence.disclose_fitted_evidence_packet(capability, policy=Policy())
    assert packet["status"] == "ABSTAINED"
    assert packet["reason"] == value["reason"]
    assert packet["selected"] == []
    assert [card["role"] for card in packet["source_cards"]] == ["query"]
    assert sorted(row["reason"] for row in packet["accounting"]) == [
        "query_self", "registered_purge", "registered_purge"]
    assert all(flag is False for flag in packet["claims"].values())


def test_disclosure_returns_detached_output(native_training, tmp_path):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    first = evidence.disclose_fitted_evidence_packet(capability, policy=Policy())
    first["selected"][0]["context_id"] = "mmctx_" + "f" * 64
    first["claims"]["semantic_entailment_established"] = True
    second = evidence.disclose_fitted_evidence_packet(capability, policy=Policy())
    assert second["selected"][0]["context_id"] != "mmctx_" + "f" * 64
    assert second["claims"]["semantic_entailment_established"] is False


def test_serialized_packet_grants_no_authority(native_training, tmp_path):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    capability = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    with pytest.raises(evidence.FittedEvidenceError, match="owner_verified_fitted_evidence_required"):
        evidence.disclose_fitted_evidence_packet(json.loads(capability._body), policy=Policy())
    with pytest.raises(evidence.FittedEvidenceError, match="owner_verified_fitted_evidence_required"):
        evidence.FittedEvidenceCapability(capability._body, cap, [])
    object.__setattr__(capability, "_body", b"{}")
    with pytest.raises(evidence.FittedEvidenceError, match="owner_verified_fitted_evidence_required"):
        evidence.disclose_fitted_evidence_packet(capability, policy=Policy())


def test_missing_native_producer_is_refused_before_any_owner_read(native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("owner read before the missing-producer refusal")

    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation", forbidden)
    monkeypatch.delitem(sys.modules, "engine.neuralweb.market_memory_fitted_retrieval", raising=False)
    monkeypatch.setattr(sys, "meta_path", [_BlockedProducer()] + list(sys.meta_path))
    with pytest.raises(evidence.FittedEvidenceError, match="native_fitted_retrieval_producer_unavailable"):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


def test_missing_shared_read_helper_is_refused_before_any_owner_read(native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("owner read before the missing-helper refusal")

    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation", forbidden)
    monkeypatch.delattr(cortex, "_read_source_cards")
    with pytest.raises(evidence.FittedEvidenceError, match="shared_source_card_helper_unavailable"):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())


@pytest.mark.parametrize("field", ["query_owner", "query", "method", "denominator",
                                   "status", "selected", "claims", "authority"])
def test_entire_native_selection_remains_bound_on_redisclosure(
        native_training, tmp_path, monkeypatch, field):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    sealed = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    original = retrieval.disclose_fitted_retrieval

    def changed(selection, *, policy):
        value = original(selection, policy=policy)
        if field == "selected":
            value[field] = list(reversed(value[field]))
        elif field == "status":
            value[field] = "ABSTAINED"
        else:
            value[field] = {**value[field], "unexpected_changed_binding": True}
        return value

    monkeypatch.setattr(retrieval, "disclose_fitted_retrieval", changed)
    with pytest.raises(evidence.FittedEvidenceError, match="original_fitted_selection_changed"):
        evidence.disclose_fitted_evidence_packet(sealed, policy=Policy())


def test_native_binding_is_rechecked_after_source_authorization(
        native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    sealed = evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
    original = retrieval.disclose_fitted_retrieval
    changed = False

    class ChangeDuringSourceUse(Policy):
        def check(self, action, resource):
            nonlocal changed
            if action == "use_retained_house_output_for_evidence_synthesis":
                changed = True
            return super().check(action, resource)

    def disclosure(selection, *, policy):
        value = original(selection, policy=policy)
        if changed:
            value["denominator"]["returned"] += 1
        return value

    monkeypatch.setattr(retrieval, "disclose_fitted_retrieval", disclosure)
    with pytest.raises(evidence.FittedEvidenceError, match="original_fitted_selection_changed"):
        evidence.disclose_fitted_evidence_packet(sealed, policy=ChangeDuringSourceUse())


def test_query_projection_cannot_change_under_the_same_capture_identity(
        native_training, tmp_path, monkeypatch):
    cap, _ = fitted_selection(native_training)
    reader, pin = owner(tmp_path)
    original = retrieval.disclose_fitted_retrieval

    def disclosure(selection, *, policy):
        value = original(selection, policy=policy)
        value["query"]["projection_id"] = "mmepisodefeatures_" + "f" * 64
        return value

    monkeypatch.setattr(retrieval, "disclose_fitted_retrieval", disclosure)
    with pytest.raises(evidence.FittedEvidenceError, match="query_owner_binding_mismatch"):
        evidence.build_fitted_evidence_packet(cap, reader, pin, policy=Policy())
